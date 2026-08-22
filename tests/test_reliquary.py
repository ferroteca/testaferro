# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Unit tests for the reliquary provider binding: executable
interrogation and the Testaferro-managed reliquary home.

`binding` is testaferro.reliquary; `reliquary_dist` is the provider
distribution it drives. What is stubbed below is `reliquary_dist.
Session`'s own methods (0.1.0a2, P26 — every provider verb this
binding calls is one of them now), patched with `autospec=True` so a
side effect receives the session instance as its own first argument.
"""

import contextlib
import json
import os
import pathlib
import subprocess
import sys
from unittest import mock

import pytest

from testaferro import cache, cpputest

from helpers import (RELIQUARY_AVAILABLE, new_format_exe_bytes,
                     plain_dos_exe_bytes, requires_reliquary)

if RELIQUARY_AVAILABLE:
    import reliquary as reliquary_dist
    from testaferro import at_rest
    from testaferro import environments
    from testaferro import reliquary as binding
    from testaferro.backend import GuestOutputError


@pytest.fixture(autouse=True, scope="module")
def _no_install():
    """No case in this file may install a guest system (P10).

    Building the default image boots a machine and installs FreeDOS
    into it — minutes, not milliseconds — so a test that reaches it
    unstubbed does not merely run slowly. It did exactly that once:
    the old default was a *download* and the case that exercised it
    mocked `reliquary.fetch_media`, which stopped being the seam the
    day the default became an install. Nothing failed; it just
    installed an operating system. This makes the next such slip fail
    on the spot, and a case that wants a default image stubs
    `_cached_default_image` for itself.
    """
    if not RELIQUARY_AVAILABLE:
        yield
        return
    patch = mock.patch.object(
        binding, "_build_default_image",
        side_effect=AssertionError(
            "the unit tier may not install a guest system: stub "
            "_cached_default_image() in this test (P10)"))
    patch.start()
    yield
    patch.stop()


EMPTY_RUN_OUTPUT = (
    "OK (2 tests, 0 ran, 0 checks, 0 ignored, 2 filtered out, 0 ms)\n")
RUN_ONE_OUTPUT = (
    "TEST(Vring, Wraps) - 0 ms\n"
    "OK (2 tests, 1 ran, 1 checks, 0 ignored, 1 filtered out, 0 ms)\n")


@contextlib.contextmanager
def _patched(*patches):
    """Enter several patches together, yielding the last one's mock."""
    with contextlib.ExitStack() as stack:
        entered = [stack.enter_context(patch) for patch in patches]
        yield entered[-1]


@requires_reliquary
class DiscoveryTests:
    """`discover()` passes reliquary's host probe through as data:
    its names, its order, its detail, nothing interpreted."""

    def test_reliquarys_probe_is_reported_under_its_provider(self):
        from testaferro import reliquary as binding

        probe = (
            reliquary_dist.backends.Availability(
                backend="qemu", available=True, version="9.0",
                executable="/usr/bin/qemu-system-i386",
                detail="on PATH"),
            reliquary_dist.backends.Availability(
                backend="virtualbox", available=False,
                detail="VBoxManage not found"),
        )
        with mock.patch.object(reliquary_dist.backends, "discover",
                               return_value=probe) as probed:
            found = binding.discover()

        probed.assert_called_once_with()
        assert [(f.provider, f.backend, f.available, f.executable,
                 f.version, f.detail) for f in found] == [
            ("reliquary", "qemu", True, "/usr/bin/qemu-system-i386",
             "9.0", "on PATH"),
            ("reliquary", "virtualbox", False, None, None,
             "VBoxManage not found"),
        ]


@requires_reliquary
class SuiteBackendDispatchTests:
    """The guard on suite_backend(); the per-format naming matrix
    lives with the classifier in test_binfmt."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.tempdir = tmp_path

    def _exe(self, content):
        path = self.tempdir / "SUITE.EXE"
        path.write_bytes(content)
        return path

    def test_rejects_windows_pe_executable(self):
        exe = self._exe(new_format_exe_bytes(b"PE\0\0"))

        with pytest.raises(ValueError, match=r"Windows \(PE\)"):
            binding.suite_backend(exe)

    def test_rejects_pe_x86_naming_the_architecture(self):
        machine = (0x014C).to_bytes(2, "little")
        exe = self._exe(new_format_exe_bytes(b"PE\0\0" + machine))

        with pytest.raises(ValueError, match=r"Windows x86 \(PE\)"):
            binding.suite_backend(exe)

    def test_accepts_headerless_image_like_a_com_program(self):
        # .com-style raw 8086 code has no magic at all — nothing to
        # prove, so it must pass through for the guest to judge
        exe = self._exe(b"\xb4\x09\xba\x00\x01\xcd\x21\xc3")

        assert binding.suite_backend(exe) is not None

    def test_missing_executable_raises_at_dispatch(self):
        with pytest.raises(FileNotFoundError):
            binding.suite_backend(self.tempdir / "MISSING.EXE")


class _BindingFixture:
    """Shared setup: a DOS exe, a custom image, and a private cache."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.tempdir = tmp_path
        root = self.tempdir
        self.exe = root / "SUITE.EXE"
        self.exe.write_bytes(plain_dos_exe_bytes())
        self.image = root / "custom.img"
        self.image.write_bytes(b"custom dos")
        cache_patch = mock.patch.object(
            cache, "cache_root", return_value=str(root / "cache"))
        cache_patch.start()
        yield
        cache_patch.stop()

    def _blueprint(self, home):
        """The machine spec Testaferro authored for one run home."""
        path = os.path.join(home, "blueprints", "testaferro.rlqb")
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)[0]

    def _guest_homes_seen(self, backend, calls=1):
        """Run one whole guest session, returning the reliquary home
        (and boot image bytes) each guest run was scoped to. The fake
        reads them off the authored blueprint, so a run that stops
        declaring its own home or boot drive fails loudly.

        Every caller declares a **boot image**, deliberately: the
        zero-configuration path now boots a layered system disk, and
        both layering it and building it are things this tier may not
        do (P10). What is under test here is Testaferro's own
        bookkeeping, which a floppy exercises just as well.
        """
        seen = []

        def fake_exec(session, command, *, machine=None, timeout=None,
                      blueprint=None, check=False):
            home = session._context.home_dir
            drives = self._blueprint(home)["drives"]
            image = drives["floppy0"]["location"]["local"]
            with open(image, "rb") as boot:
                seen.append((home, boot.read()))
            return tuple(EMPTY_RUN_OUTPUT.splitlines())

        with self._fake_machine(exec_side_effect=fake_exec):
            backend.start_guest()
            try:
                for _ in range(calls):
                    backend.run_all()
            finally:
                backend.stop_guest()
        return seen

    def _fake_machine(self, exec_side_effect=None, **exec_kwargs):
        """Stub only what needs a live virtual machine.

        Machine *creation* is real: reliquary parses the blueprint
        Testaferro authored, resolves its media and materializes the
        drives, all of which is cheap and hypervisor-free. Booting is
        not — `start_machine` starts a guest for real (P10) — so every
        call that needs a running machine is stubbed and nothing else.

        **`run_script` is one of them, and not obviously.** A script's
        `machine` header is a precondition reliquary *establishes*:
        the readiness script says `running`, so running one against a
        machine this fixture never really started starts it for real.
        Stubbing `start_machine` alone is not enough, and the way that
        announces itself is a unit run booting QEMU.

        Creation stays cheap only while every drive's media is `use`
        (attached in place). A blueprint declaring a blank (`size`)
        makes reliquary reach for an external image tool, which belongs
        in an integration test instead.

        Every patch here is `autospec=True`: 0.1.0a2 moved these from
        module functions to `Session` methods (P26), so a side effect
        now receives the session instance as its own first argument —
        `fake_exec` above reads `session._context.home_dir` off it,
        where the old fake read a `context=` kwarg no method takes any
        more.
        """
        return _patched(
            mock.patch.object(reliquary_dist.Session, "start_machine",
                              autospec=True),
            mock.patch.object(reliquary_dist.Session, "stop_machine",
                              autospec=True),
            mock.patch.object(reliquary_dist.Session, "run_script",
                              autospec=True),
            mock.patch.object(reliquary_dist.Session, "get_machine_var",
                              autospec=True, return_value="yes"),
            mock.patch.object(reliquary_dist.Session, "exec",
                              autospec=True, side_effect=exec_side_effect,
                              **exec_kwargs))

@requires_reliquary
class ReliquarySuiteBackendTests(_BindingFixture):
    """Backend behavior within one guest session."""

    def test_a_guest_runs_in_a_fresh_home_with_the_caller_boot_image(self):
        # No run open, so the guest home sits at the cache root rather
        # than inside a run's area (D15).
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        [(home, image)] = self._guest_homes_seen(backend)

        assert home.startswith(
            os.path.join(cache.cache_root(), "guests"))
        assert image == b"custom dos"
        assert not os.path.exists(home)

    def test_each_guest_session_gets_its_own_home(self):
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        homes = [self._guest_homes_seen(backend)[0][0] for _ in range(2)]

        assert homes[0] != homes[1]

    def test_machine_template_becomes_this_guests_blueprint(self):
        source = self.tempdir / "msdos.img"
        source.write_bytes(b"template image")
        template = environments.EnvironmentSpec({
            "drives": {"floppy0": {"name": "msdos",
                                   "location": {"local": str(source)}}}})
        backend = binding.suite_backend(self.exe, machine_config=template)

        with self._fake_machine():
            backend.start_guest()
            try:
                drives = self._blueprint(backend._home)["drives"]
                # The declaration passes through untouched; reliquary
                # owns materialization, so it stays a template.
                assert (drives["floppy0"]["location"]["local"]
                        == str(source))
                assert (template.drives["floppy0"]["location"]
                        == {"local": str(source)})
            finally:
                backend.stop_guest()

    def test_the_boot_floppy_is_never_a_staging_target(self):
        """The work drive is a standing fixture, not a reaction.

        The declared boot image here is ten bytes of text, not a FAT
        volume — which no longer matters, because the default
        location was never going to be the boot floppy in the first
        place. Testaferro's own vvfat work drive is a sibling of
        whatever else the machine declares, always, so the suite
        lands there regardless of whether the boot image could have
        taken a write at all (0.1.0a2, D108 retired the reactive
        fallback along with the report it depended on to recreate the
        machine after a failed write).
        """
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        with self._fake_machine():
            backend.start_guest()
            try:
                home = backend._home
                drives = self._blueprint(home)["drives"]
                work = drives["hdd0"]["location"]["local"]
                assert work == os.path.join(home, "work")
                staged = pathlib.Path(work) / "SUITE.EXE"
                assert staged.read_bytes() == self.exe.read_bytes()
                # The appended drive is served whole, so the set is at
                # its root rather than in a directory under it.
                assert backend.location == "C:\\"
            finally:
                backend.stop_guest()

    def test_files_are_staged_beside_the_suite(self):
        fixture = self.tempdir / "DATA.TXT"
        fixture.write_bytes(b"fixture bytes")
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        files=[str(fixture)])

        with self._fake_machine():
            backend.start_guest()
            try:
                work = pathlib.Path(backend._home) / "work"
                assert ((work / "SUITE.EXE").read_bytes()
                        == self.exe.read_bytes())
                assert (work / "DATA.TXT").read_bytes() == b"fixture bytes"
            finally:
                backend.stop_guest()

    def test_a_declared_directory_contributes_its_contents(self):
        # `files=["fixtures"]` lands the fixtures where a guest program
        # looks for them, not one directory deeper.
        tree = self.tempdir / "fixtures"
        tree.mkdir()
        (tree / "CASE.DAT").write_bytes(b"case")
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        files=[str(tree)])

        with self._fake_machine():
            backend.start_guest()
            try:
                work = pathlib.Path(backend._home) / "work"
                assert (work / "CASE.DAT").read_bytes() == b"case"
            finally:
                backend.stop_guest()

    def test_the_testers_boot_image_is_read_and_never_written(self):
        # P5's promise, and it was not kept: the image was attached in
        # place, so a guest writing to A: — which DOS does for reasons
        # of its own — edited the file its tester handed over. What
        # boots is Testaferro's copy inside the guest's own home.
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        with self._fake_machine():
            backend.start_guest()
            try:
                booted = self._blueprint(
                    backend._home)["drives"]["floppy0"]["location"]["local"]
                home = backend._home
            finally:
                backend.stop_guest()

        assert pathlib.Path(booted) != pathlib.Path(self.image)
        assert pathlib.Path(booted).parent == pathlib.Path(home)
        # and it is a copy, not an empty placeholder
        assert pathlib.Path(self.image).read_bytes() == b"custom dos"

    def test_two_guest_sessions_do_not_share_a_writable_floppy(self):
        # One run, two suites: each gets its own copy, so neither can
        # hand the other a floppy it has changed.
        binding.start(boot_image=self.image)
        try:
            booted = []

            for _ in range(2):
                backend = binding.suite_backend(self.exe)
                with self._fake_machine():
                    backend.start_guest()
                    try:
                        booted.append(self._blueprint(backend._home)
                                      ["drives"]["floppy0"]["location"]
                                      ["local"])
                    finally:
                        backend.stop_guest()

            assert booted[0] != booted[1]
        finally:
            binding.stop()

    def test_the_argv_budget_is_the_typed_line_less_the_program(self):
        # COMMAND.COM takes 126 characters of line; the program and its
        # separating space come off that, and the DOS argument tail
        # (125) caps it from the other side (F3).
        backend = binding.suite_backend(self.exe, boot_image=self.image)
        backend._location = "D:\\"

        assert backend._argv_budget() == min(
            125, 126 - len("D:\\" + os.path.basename(self.exe)) - 1)

    def test_the_default_system_is_built_once_and_then_reused(self):
        # `_build_default_image()` performs a real FreeDOS install, so
        # it is stubbed here and belongs to integration — the seam to
        # mock is this one, and no longer a download. Mocking the wrong
        # seam does not fail: it installs an operating system, which is
        # how this rule got broken once already (P10).
        built = []

        def fake_build(destination):
            built.append(destination)
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            with open(destination, "wb") as image:
                image.write(b"freedos")

        backend = binding.suite_backend(self.exe)
        with mock.patch.object(binding, "_build_default_image",
                               side_effect=fake_build) as build:
            first = binding._cached_default_image()
            second = binding._cached_default_image()

        assert first == second
        build.assert_called_once()
        assert first.endswith(binding._FREEDOS_IMAGE_NAME)

    def test_zero_configuration_layers_the_system_rather_than_using_it(self):
        # Every guest session shares one built image, so none of them
        # may write into it: the drive is layered, and the work drive
        # lands beside it as the guest's second disk — D:.
        backend = binding.suite_backend(self.exe)
        with mock.patch.object(binding, "_cached_default_image",
                               return_value="SYSTEM.QCOW2"):
            document, key = backend._blueprint("work")

        drives = document[0]["drives"]
        assert drives["hdd0"]["materialize"] == "difference"
        assert drives["hdd0"]["location"] == {"local": "SYSTEM.QCOW2"}
        assert document[0]["boot"] == ["hdd0"]
        # The slot, which authoring decides; what the guest calls it is
        # read off the created machine and belongs to integration.
        assert key == "hdd1"
        assert drives["hdd1"]["name"] == binding._WORK_MEDIA_NAME

    def test_runs_suite_through_reliquary(self):
        expected = tuple(EMPTY_RUN_OUTPUT.splitlines())
        with self._fake_machine(return_value=expected) as guest_exec:
            backend = binding.suite_backend(self.exe, boot_image=self.image)
            backend.start_guest()
            try:
                assert backend.run_all() == []
            finally:
                backend.stop_guest()
        guest_exec.assert_called_once_with(
            mock.ANY, "C:\\SUITE.EXE -v",
            machine="testaferro-0", timeout=mock.ANY)

    def test_the_command_line_spells_every_argv_token(self):
        """The framework hands over tokens and this binding spells the
        DOS command line, so the expectation is written out rather
        than rebuilt from the argv builder — an expectation composed
        the way the code composes cannot see a wrong composition. A
        string treated as a token sequence joins character by
        character, asking the guest for '- v' instead.
        """
        expected = tuple(RUN_ONE_OUTPUT.splitlines())
        with self._fake_machine(return_value=expected) as guest_exec:
            backend = binding.suite_backend(self.exe,
                                            boot_image=self.image)
            backend.start_guest()
            try:
                assert backend.run_test("Vring", "Wraps").passed
            finally:
                backend.stop_guest()
        guest_exec.assert_called_once_with(
            mock.ANY, "C:\\SUITE.EXE -v -sg Vring -sn Wraps",
            machine="testaferro-0", timeout=mock.ANY)

    def test_the_nearest_speaker_sets_the_guest_command_timeout(self):
        # The call speaks about this run and a declaration about the
        # environment, so the call wins; absent both, the default.
        declared = environments.EnvironmentSpec({}, timeout=7)

        assert binding.suite_backend(
            self.exe, boot_image=self.image, timeout=3)._timeout == 3
        assert binding.suite_backend(
            self.exe, machine_config=declared)._timeout == 7
        assert binding.suite_backend(
            self.exe, machine_config=declared, timeout=3)._timeout == 3
        assert (binding.suite_backend(
                    self.exe, boot_image=self.image)._timeout
                == binding._DEFAULT_TIMEOUT)

    def test_enumerator_forwards_to_suite_backend(self):
        with self._fake_machine() as guest_exec:
            backend = binding.suite_backend(
                self.exe,
                enumerator=lambda: cpputest.parse_list("Vring.Wraps"))
            ids = backend.list_tests()
        assert [str(i) for i in ids] == ["Vring.Wraps"]
        guest_exec.assert_not_called()


    def test_reliquary_materializes_the_authored_blueprint(self):
        """The blueprint is reliquary's to validate, so let it: every
        test here creates the machine for real, and this one says so."""
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        with self._fake_machine() as guest_exec:
            backend.start_guest()
            try:
                assert backend._machine == "testaferro-0"
            finally:
                backend.stop_guest()
        guest_exec.assert_not_called()


@requires_reliquary
class SetupCommandTests(_BindingFixture):
    """Harness prep (F9): `setup=` commands run in the guest before
    any test, once per guest session."""

    def test_setup_commands_run_in_order_before_any_test(self):
        calls = []

        def fake_exec(session, command, *, machine=None, timeout=None,
                      blueprint=None, check=False):
            calls.append((command, check))
            if command == "C:\\SUITE.EXE -v":
                return tuple(EMPTY_RUN_OUTPUT.splitlines())
            return ()

        backend = binding.suite_backend(
            self.exe, boot_image=self.image,
            setup=["DRIVER.COM /install", "OTHER.COM /go"])

        with self._fake_machine(exec_side_effect=fake_exec):
            backend.start_guest()
            try:
                backend.run_all()
            finally:
                backend.stop_guest()

        # check=True asks reliquary whether each setup command
        # succeeded; the suite's own run asks no such thing, matching
        # every other guest exchange this binding performs.
        assert calls == [
            ("DRIVER.COM /install", True),
            ("OTHER.COM /go", True),
            ("C:\\SUITE.EXE -v", False),
        ]

    def test_setup_runs_again_each_new_guest_session(self):
        # Once per guest session (D15), an enumeration boot included:
        # a suite whose TSR must be resident needs it resident to
        # enumerate too.
        calls = []

        def fake_exec(session, command, *, machine=None, timeout=None,
                      blueprint=None, check=False):
            calls.append(command)
            return ()

        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        setup=["DRIVER.COM /install"])

        with self._fake_machine(exec_side_effect=fake_exec):
            backend.start_guest()
            backend.stop_guest()
            backend.start_guest()
            backend.stop_guest()

        assert calls == ["DRIVER.COM /install", "DRIVER.COM /install"]

    def test_a_failing_setup_command_ends_the_session_and_names_it(self):
        # Failure is the provider's to detect (exec(check=True)); this
        # binding turns that refusal into the same GuestOutputError
        # shape every guest exchange fails in, naming the command.
        def fake_exec(session, command, *, machine=None, timeout=None,
                      blueprint=None, check=False):
            raise reliquary_dist.RunFailure(
                f"command signalled failure: {command}")

        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        setup=["DRIVER.COM /install"])

        with self._fake_machine(exec_side_effect=fake_exec):
            with pytest.raises(GuestOutputError) as caught:
                backend.start_guest()

        assert "DRIVER.COM /install" in str(caught.value)
        assert caught.value.argv == ("DRIVER.COM /install",)
        # the session was ended, not left half-started
        assert backend._home is None
        assert backend not in binding._running

    def test_a_second_setup_command_never_runs_after_the_first_fails(self):
        calls = []

        def fake_exec(session, command, *, machine=None, timeout=None,
                      blueprint=None, check=False):
            calls.append(command)
            raise reliquary_dist.RunFailure(
                f"command signalled failure: {command}")

        backend = binding.suite_backend(
            self.exe, boot_image=self.image,
            setup=["DRIVER.COM /install", "OTHER.COM /go"])

        with self._fake_machine(exec_side_effect=fake_exec):
            with pytest.raises(GuestOutputError):
                backend.start_guest()

        assert calls == ["DRIVER.COM /install"]

    def test_the_nearest_speaker_sets_setup_commands(self):
        # The call speaks about this run and a declaration about the
        # environment, so the call wins; absent both, none at all.
        declared = environments.EnvironmentSpec({}, setup=["FROM.ENV /go"])

        assert (binding.suite_backend(
                    self.exe, boot_image=self.image,
                    setup=["FROM.CALL /go"])._setup
                == ("FROM.CALL /go",))
        assert (binding.suite_backend(
                    self.exe, machine_config=declared)._setup
                == ("FROM.ENV /go",))
        assert (binding.suite_backend(
                    self.exe, machine_config=declared,
                    setup=["FROM.CALL /go"])._setup
                == ("FROM.CALL /go",))
        assert (binding.suite_backend(
                    self.exe, boot_image=self.image)._setup
                == ())

    def test_a_suite_declaring_no_setup_runs_exactly_as_before(self):
        expected = tuple(EMPTY_RUN_OUTPUT.splitlines())
        with self._fake_machine(return_value=expected) as guest_exec:
            backend = binding.suite_backend(self.exe, boot_image=self.image)
            backend.start_guest()
            try:
                assert backend.run_all() == []
            finally:
                backend.stop_guest()
        guest_exec.assert_called_once_with(
            mock.ANY, "C:\\SUITE.EXE -v",
            machine="testaferro-0", timeout=mock.ANY)


@requires_reliquary
class GuestSessionTests(_BindingFixture):
    """guest_session(): the same provisioning suite_backend() draws
    on, reached with no suite executable to stage or place, and no
    framework adapter for output that was never going to exist (U10,
    F18).
    """

    def test_no_suite_executable_is_staged(self):
        session = binding.guest_session(boot_image=self.image)

        with self._fake_machine():
            with session:
                work = pathlib.Path(session._home) / "work"
                assert list(work.iterdir()) == []

    def test_files_are_staged_with_no_executable_beside_them(self):
        fixture = self.tempdir / "DRIVER.COM"
        fixture.write_bytes(b"driver bytes")
        session = binding.guest_session(boot_image=self.image,
                                        files=[str(fixture)])

        with self._fake_machine():
            with session:
                work = pathlib.Path(session._home) / "work"
                assert ([path.name for path in work.iterdir()]
                        == ["DRIVER.COM"])
                assert (work / "DRIVER.COM").read_bytes() == b"driver bytes"

    def test_zero_configuration_layers_the_default_system(self):
        # The same zero-configuration guest guest_suite() gives every
        # suite, reached with no exe at all.
        session = binding.guest_session()
        with mock.patch.object(binding, "_cached_default_image",
                               return_value="SYSTEM.QCOW2"):
            document, key = session._blueprint("work")

        drives = document[0]["drives"]
        assert drives["hdd0"]["materialize"] == "difference"
        assert drives["hdd0"]["location"] == {"local": "SYSTEM.QCOW2"}
        assert key == "hdd1"

    def test_exec_returns_the_sessions_own_rows_unjoined(self):
        # Mirrors reliquary.Session.exec()'s own contract (F18): the
        # rows come back exactly as reliquary returned them, never
        # joined into text the way a suite's framework adapter needs.
        rows = ("row one", "row two")
        with self._fake_machine(return_value=rows) as guest_exec:
            with binding.guest_session(boot_image=self.image) as guest:
                result = guest.exec("DIR")

        assert result == rows
        guest_exec.assert_called_once_with(
            mock.ANY, "DIR", machine="testaferro-0",
            timeout=binding._DEFAULT_TIMEOUT, check=False)

    def test_exec_timeout_overrides_the_sessions_own_for_one_call(self):
        with self._fake_machine(return_value=()) as guest_exec:
            with binding.guest_session(boot_image=self.image) as guest:
                guest.exec("DIR", timeout=5)

        guest_exec.assert_called_once_with(
            mock.ANY, "DIR", machine="testaferro-0", timeout=5, check=False)

    def test_exec_check_true_raises_on_a_failing_command(self):
        def fake_exec(session, command, *, machine=None, timeout=None,
                      blueprint=None, check=False):
            if check:
                raise reliquary_dist.RunFailure(
                    f"command signalled failure: {command}")
            return ()

        with self._fake_machine(exec_side_effect=fake_exec):
            with binding.guest_session(boot_image=self.image) as guest:
                with pytest.raises(reliquary_dist.RunFailure):
                    guest.exec("DRIVER.COM /install", check=True)

    def test_exec_refuses_outside_a_guest_session(self):
        session = binding.guest_session(boot_image=self.image)

        with pytest.raises(RuntimeError, match="no guest session"):
            session.exec("DIR")

    def test_the_session_sweeps_on_exit_even_after_an_exception(self):
        with self._fake_machine():
            session = binding.guest_session(boot_image=self.image)
            with pytest.raises(ValueError):
                with session:
                    home = session._home
                    raise ValueError("boom")

        assert session._home is None
        assert not os.path.exists(home)
        assert session not in binding._running

    def test_a_stopped_session_is_no_longer_tracked(self):
        with self._fake_machine():
            with binding.guest_session(boot_image=self.image) as guest:
                assert guest in binding._running

        assert guest not in binding._running

    def test_machine_config_platform_is_validated(self):
        declared = environments.EnvironmentSpec({"platform": "os2"})

        with pytest.raises(ValueError, match="DOS machine"):
            binding.guest_session(machine_config=declared)

    def test_boot_image_and_machine_config_cannot_be_combined(self):
        declared = environments.EnvironmentSpec({})

        with pytest.raises(TypeError, match="cannot be combined"):
            binding.guest_session(boot_image=self.image,
                                  machine_config=declared)


@requires_reliquary
class WorkDrivePlacementTests:
    """Slot choice — pure declaration arithmetic, so every case is
    worth stating.

    Slot choice is all Testaferro decides; what letter DOS gives that
    slot is `_letter_map`, exercised below — computed deterministically
    from the declaration rather than read back (0.1.0a2 removed the
    provider's own answer, D108).
    """

    def test_takes_the_first_disk_of_an_empty_machine(self):
        assert binding._work_slot({}) == "hdd0"

    def test_a_floppy_does_not_occupy_a_disk_slot(self):
        assert binding._work_slot({"floppy0": {}}) == "hdd0"

    def test_a_cdrom_does_not_occupy_a_disk_slot(self):
        assert binding._work_slot({"cdrom0": {}}) == "hdd0"

    def test_follows_a_declared_system_disk(self):
        assert binding._work_slot({"hdd0": {}}) == "hdd1"

    def test_follows_several_declared_disks(self):
        assert binding._work_slot({"hdd0": {}, "hdd1": {}}) == "hdd2"

    def test_fills_a_gap_rather_than_appending(self):
        # hdd1 declared, hdd0 free: the work drive lands first.
        assert binding._work_slot({"hdd1": {}}) == "hdd0"

    def test_undigited_disk_key_counts_as_slot_zero(self):
        assert binding._work_slot({"hdd": {}}) == "hdd1"

    def test_a_full_machine_fails_closed_naming_the_reason(self):
        drives = {f"hdd{slot}": {} for slot in range(4)}

        with pytest.raises(ValueError, match="free slot"):
            binding._work_slot(drives)


@requires_reliquary
class PlacedLetterTests:
    """What the guest is told, and where it comes from.

    Pure declaration arithmetic now (0.1.0a2, D108): there is no
    report left to ask, so `_letter_map` computes every drive's letter
    from the `drives` mapping alone, never a machine or a session.
    """

    def test_the_only_hard_disk_is_c(self):
        assert binding._letter_map({"hdd0": {}}) == {"C": "hdd0"}

    def test_a_second_hard_disk_follows_the_first(self):
        assert (binding._letter_map({"hdd0": {}, "hdd1": {}})
                == {"C": "hdd0", "D": "hdd1"})

    def test_position_counts_rather_than_the_slot_number(self):
        # hdd0 and hdd2 declared, hdd1 free: hdd2 is still the
        # machine's *second* hard disk, so it is D — one letter per
        # hdd slot present, in order, never per number.
        assert (binding._letter_map({"hdd0": {}, "hdd2": {}})
                == {"C": "hdd0", "D": "hdd2"})

    def test_floppies_take_a_and_b_ahead_of_any_hard_disk(self):
        assert (binding._letter_map(
                    {"floppy0": {}, "floppy1": {}, "hdd0": {}})
                == {"A": "floppy0", "B": "floppy1", "C": "hdd0"})

    def test_a_cdrom_takes_no_letter_at_all(self):
        # Testaferro never declares one for a runtime guest today
        # (only the install script attaches one, temporarily); this
        # pins that a stray cdrom key does not shift hard-disk
        # lettering the way one loaded as a driver could.
        assert (binding._letter_map({"hdd0": {}, "cdrom0": {}})
                == {"C": "hdd0"})


@requires_reliquary
class DeclaredPlacementTests(_BindingFixture):
    """A declared address, through the real session flow.

    The staging call is stubbed because this fixture's machine has no
    FAT volume to write into; everything around it — when the address
    is settled, whether a default is computed, what a refusal does —
    is the real path.
    """

    def _staging(self, put_side_effect=None):
        """Stub the at-rest seam and the volume it resolves against.

        `_resolve_volume` is Testaferro's own, and it is stubbed here
        rather than the calls beneath it because this fixture's
        machine has no volume for a real one to find. What each
        resolution *does* is proved in `VolumeResolutionTests`.
        """
        return _patched(
            mock.patch.object(binding, "_resolve_volume",
                              return_value=("disk.qcow2", 0, "HARNESS")),
            mock.patch.object(binding.at_rest, "put_tree",
                              side_effect=put_side_effect))

    def test_a_declared_location_is_staged_against_and_never_defaulted(self):
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        location="E:\\HARNESS")

        with self._fake_machine(), self._staging() as put, \
                mock.patch.object(binding, "_default_location") as default:
            backend.start_guest()
            try:
                assert backend.location == "E:\\HARNESS"
            finally:
                backend.stop_guest()

        # A default answers "where should this go" — a question the
        # declaration already answered, so it is never computed.
        default.assert_not_called()
        # The letter is split off before the write: at rest there are
        # no letters, only a volume and a path inside it (D23).
        assert put.call_args.args[2] == "HARNESS"

    def test_a_declared_location_that_refuses_does_not_fall_back(self):
        # The consumer named that address; smoothing it over with a
        # drive of Testaferro's own would hide the one thing they can
        # act on. The refusal survives.
        refusal = at_rest.AtRestError(
            "invalid fat disk image: directory 'HARNESS' not found")
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        location="E:\\HARNESS")

        with self._fake_machine(), self._staging(put_side_effect=refusal):
            with pytest.raises(at_rest.AtRestError) as caught:
                backend.start_guest()

        assert "'HARNESS' not found" in str(caught.value)

    def test_a_letter_the_machine_does_not_have_refuses(self):
        """The resolution's own refusal, not the write's.

        This machine has A: (the boot floppy) and C: (Testaferro's
        own work drive, `_letter_map` computed) and nothing else, so
        E: is refused before any boot — the consumer named that
        address and is the only one who can correct it.
        """
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        location="E:\\HARNESS")

        with self._fake_machine():
            with pytest.raises(ValueError) as caught:
                backend.start_guest()

        assert "no E:" in str(caught.value)

    def test_the_command_spells_the_address_that_was_staged_against(self):
        expected = tuple(EMPTY_RUN_OUTPUT.splitlines())
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        location="E:\\HARNESS")

        with self._fake_machine(return_value=expected) as guest_exec, \
                self._staging():
            backend.start_guest()
            try:
                backend.run_all()
            finally:
                backend.stop_guest()

        assert guest_exec.call_args.args[1].startswith(
            "E:\\HARNESS\\SUITE.EXE")

    def test_the_location_refuses_before_a_guest_session(self):
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        with pytest.raises(RuntimeError, match="has not been placed"):
            backend.location


@requires_reliquary
class PlacementTests:
    """Where a run lands when nobody said (F4): Testaferro's own work
    drive, always, at whatever letter `_letter_map` computes for it.
    """

    def test_the_zero_configuration_guest_defaults_to_its_work_drive(self):
        # hdd0 is the system disk, hdd1 the work drive — a second hard
        # disk, so D:, matching a real boot exactly (see _letter_map).
        assert (binding._default_location(
                    {"hdd0": {}, "hdd1": {}}, work_key="hdd1")
                == "D:\\")

    def test_a_lone_work_drive_defaults_to_c(self):
        # No system disk declared at all: the work drive is the
        # machine's only hard disk, so C:.
        assert (binding._default_location({"hdd1": {}}, work_key="hdd1")
                == "C:\\")


@requires_reliquary
class VolumeResolutionTests:
    """A guest address to the image and volume it names (F16, D23).

    At rest there are no drive letters, so an address has to be
    resolved to a volume before a byte can be written. One computation
    now for every drive, Testaferro's own or a `machine_config`
    template's alike (`_letter_map`, D108) — there is no split between
    a guaranteed answer and a looked-up one any more.
    """

    def _session(self, **paths):
        session = mock.Mock(spec=reliquary_dist.Session)
        session.list_machines.return_value = [{"id": "m", "drives": {
            key: {"path": path} for key, path in paths.items()}}]
        return session

    def test_the_system_disk_resolves(self):
        session = self._session(hdd0="sys.qcow2")

        assert (binding._resolve_volume("C:\\TESTS", "m", session,
                                        {"hdd0": {}})
                == ("sys.qcow2", 0, "TESTS"))

    def test_a_letter_the_machine_does_not_have_refuses(self):
        session = self._session(hdd0="sys.qcow2")

        with pytest.raises(ValueError) as caught:
            binding._resolve_volume("D:\\TESTS", "m", session,
                                    {"hdd0": {}})

        assert "no D:" in str(caught.value)

    def test_a_boot_floppy_resolves(self):
        # A:'s letter is DOS's own fixed rule: assigned by controller
        # position, never by content.
        session = self._session(floppy0="boot.img")

        assert (binding._resolve_volume("A:\\TESTS", "m", session,
                                        {"floppy0": {}})
                == ("boot.img", 0, "TESTS"))

    def test_a_declared_hard_disk_resolves_too(self):
        # The capability 0.1.0a2 took away and _letter_map gives back:
        # a machine_config's own declared disk resolves exactly like
        # Testaferro's own, since the same deterministic computation
        # now covers both. hdd1 is the *second* hard disk here, so D:.
        session = self._session(hdd0="sys.qcow2", hdd1="data.qcow2")

        assert (binding._resolve_volume("D:\\HARNESS", "m", session,
                                        {"hdd0": {}, "hdd1": {}})
                == ("data.qcow2", 0, "HARNESS"))

    def test_an_address_without_a_letter_is_refused(self):
        with pytest.raises(at_rest.AtRestError):
            binding._resolve_volume("HARNESS", "m", None, {"hdd0": {}})


@requires_reliquary
class BlueprintAcceptanceTests(_BindingFixture):
    """Documents Testaferro authors are ones **reliquary accepts**.

    `BlueprintAuthoringTests` below reads back the dict Testaferro
    composed, which proves Testaferro consistent with itself and
    nothing more: a document reliquary rejects passes it. This suite
    hands each document to `create_machine(dry_run=True)` — 0.1.0.dev5's
    preflight, which resolves media, assigns drives and validates the
    whole thing **having built none of it**.

    That is what puts the **zero-configuration** document in reach of
    this tier for the first time. Its system disk is materialized
    `difference`, so a real create reaches for qcow2 tooling and the
    case had to live in integration (P10); a dry create reads the
    declaration and never touches an image, so a few bytes of
    placeholder stand in for the built system. What this catches is
    the failure the authoring tests structurally cannot: reliquary's
    schema moving under a document Testaferro still composes happily.

    Letters are deliberately absent here. `_letter_map` is pure
    declaration arithmetic now (0.1.0a2 deleted the provider's own
    drive report, D108) and is proved on its own in
    `PlacedLetterTests`, never against a dry plan.
    """

    def _dry_plan(self, document):
        """Reliquary's own plan for a document Testaferro authored."""
        home = os.path.join(self.tempdir, "acceptance")
        blueprints = os.path.join(home, "blueprints")
        os.makedirs(blueprints, exist_ok=True)
        path = os.path.join(blueprints, binding._BLUEPRINT_NAME + ".rlqb")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        session = binding._open_session(home, blueprints)
        outcome = session.create_machine(binding._BLUEPRINT_NAME,
                                         dry_run=True)
        assert outcome.operation == "create-machine"
        return outcome.plan

    def _placeholder(self, name, content=b"stand-in for a built image"):
        path = os.path.join(self.tempdir, name)
        with open(path, "wb") as handle:
            handle.write(content)
        return path

    def _drive(self, plan, key):
        for entry in plan["drives"]:
            if entry["key"] == key:
                return entry
        pytest.fail(f"the plan places no drive {key}: {plan['drives']}")

    def test_zero_configuration_document_is_one_reliquary_accepts(self):
        # The case that could not be unit-tested before: a layered
        # system disk, validated without materializing one.
        system = self._placeholder("SYSTEM.QCOW2")
        work = os.path.join(self.tempdir, "work")
        os.makedirs(work, exist_ok=True)
        backend = binding.suite_backend(self.exe)
        with mock.patch.object(binding, "_cached_default_image",
                               return_value=system):
            document, key = backend._blueprint(work)

        plan = self._dry_plan(document)

        assert plan["platform"] == "dos"
        assert plan["boot"] == ["hdd0"]
        system_disk = self._drive(plan, "hdd0")
        assert system_disk["materialize"] == "difference"
        assert system_disk["base"] == system
        # The work drive is the one Testaferro appended, at the slot
        # `_work_slot` chose, served from the staged directory itself.
        staged = self._drive(plan, key)
        assert (staged["medium"], staged["slot"]) == ("hdd", 1)
        assert staged["materialize"] == "use"
        assert staged["path"] == work

    def test_a_declared_environment_is_carried_through_intact(self):
        # A tester's own machine spec reaches reliquary as written —
        # `platform` among it, which is the provider's word (P2).
        system = self._placeholder("DECLARED.QCOW2")
        work = os.path.join(self.tempdir, "declared-work")
        os.makedirs(work, exist_ok=True)
        template = environments.EnvironmentSpec({
            "memory": "64M",
            "drives": {"hdd0": {"name": "system",
                                "location": {"local": system}}},
            "boot": ["hdd0"]})
        backend = binding.suite_backend(self.exe, machine_config=template)

        document, key = backend._blueprint(work)
        plan = self._dry_plan(document)

        assert plan["memory"] == 64
        assert plan["boot"] == ["hdd0"]
        assert self._drive(plan, key)["path"] == work

    def test_a_document_naming_absent_media_is_refused_before_anything_runs(self):
        # The preflight earns its place only if it refuses: the boot
        # image names a file nobody staged, and this is where that is
        # found — not in a guest that will not boot.
        backend = binding.suite_backend(self.exe)
        document, _ = backend._blueprint(
            os.path.join(self.tempdir, "work"),
            os.path.join(self.tempdir, "NOT-STAGED.IMG"))

        with pytest.raises(reliquary_dist.PreflightError) as caught:
            self._dry_plan(document)

        assert "NOT-STAGED.IMG" in str(caught.value)


@requires_reliquary
class BlueprintAuthoringTests(_BindingFixture):
    """The document Testaferro composes, without materializing it."""

    def _document(self, backend, boot=None):
        # `_blueprint` authors over locations that are already staged,
        # so a boot image reaches it as a path rather than being
        # copied out of the backend here.
        document, key = backend._blueprint("/work", boot)
        return document[0], document[1:], key

    def test_zero_configuration_boots_the_chosen_image(self):
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        machine, media, key = self._document(backend, "/guest/boot.img")

        assert machine["type"] == "machine"
        assert machine["platform"] == "dos"
        assert machine["boot"] == ["floppy0"]
        # The staged copy, not the tester's own file (P5).
        assert (machine["drives"]["floppy0"]["location"]
                == {"local": "/guest/boot.img"})
        assert machine["drives"]["hdd0"]["location"] == {"local": "/work"}
        assert (media, key) == ([], "hdd0")

    def test_a_declared_environment_keeps_its_own_boot_arrangement(self):
        template = environments.EnvironmentSpec({
            "memory": "64M",
            "drives": {"hdd0": {"name": "system",
                                "location": {"local": str(self.image)}}},
            "boot": ["hdd0"]})
        backend = binding.suite_backend(self.exe, machine_config=template)

        machine, _, key = self._document(backend)

        # No boot floppy is invented, and the work drive steps aside.
        assert "floppy0" not in machine["drives"]
        assert machine["boot"] == ["hdd0"]
        assert machine["memory"] == "64M"
        assert (machine["drives"]["hdd1"]["location"]
                == {"local": "/work"})
        assert key == "hdd1"

    def test_media_declared_beside_the_machine_is_carried_through(self):
        spec = {"type": "media", "name": "extra", "location": "x.img"}
        template = environments.EnvironmentSpec(
            {"drives": {"floppy0": {"media": "extra"}}}, [spec])
        backend = binding.suite_backend(self.exe, machine_config=template)

        _, media, _ = self._document(backend)

        assert media == [spec]


@requires_reliquary
class SessionLifecycleTests(_BindingFixture):
    """testaferro.start()/stop(): one image choice shared by many
    suites, swept away together."""

    @pytest.fixture(autouse=True)
    def _stop_binding(self):
        yield
        binding.stop()

    def _run_suite(self, backend):
        return self._guest_homes_seen(backend)[0]

    def test_the_runs_image_is_staged_once_and_shared_by_suites(self):
        binding.start(boot_image=self.image)
        with mock.patch.object(binding, "_cached_default_image") as cached:
            first = self._run_suite(binding.suite_backend(self.exe))
            second = self._run_suite(binding.suite_backend(self.exe))
        cached.assert_not_called()
        assert (first[1], second[1]) == (b"custom dos", b"custom dos")
        assert first[0] != second[0]

    def test_start_does_not_stage_or_download_by_itself(self):
        with mock.patch.object(binding, "_cached_default_image") as cached:
            binding.start()
        cached.assert_not_called()

    def test_stop_sweeps_run_homes_but_keeps_the_built_system(self):
        # The run's own area goes; what an install paid for stays.
        # A boot image is declared here so the case tests sweeping
        # rather than the default path, which is no longer this
        # tier's to walk (P10): a layered system drive materializes
        # through an external image tool, and the system itself
        # materializes through a guest install.
        cached = pathlib.Path(cache.cache_root()) / binding._FREEDOS_IMAGE_NAME
        cached.parent.mkdir(parents=True, exist_ok=True)
        created = not cached.exists()
        if created:
            cached.write_bytes(b"not a real system")
        try:
            binding.start(boot_image=self.image)
            home, image = self._run_suite(binding.suite_backend(self.exe))
            assert image == b"custom dos"

            binding.stop()
            assert not os.path.exists(os.path.dirname(home))
            assert cached.exists()
        finally:
            if created:
                cached.unlink()

    def test_kept_guest_homes_survive_the_sweep_and_are_named(self):
        # The exploration option: looking at what the guest was given
        # is the whole point, so the directory has to still be there.
        cache.keep_guest_homes(True)
        try:
            binding.start(boot_image=self.image)
            home, _ = self._run_suite(binding.suite_backend(self.exe))

            binding.stop()

            assert os.path.exists(home)
            assert home in cache.kept_guest_homes()
        finally:
            cache._kept.clear()
            cache.keep_guest_homes(False)

    def test_stop_clear_downloads_removes_the_built_system(self):
        # What it drops is now an install rather than a download, so
        # the next zero-configuration run pays minutes to rebuild it.
        cached = pathlib.Path(cache.cache_root()) / binding._FREEDOS_IMAGE_NAME
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(b"not a real system")

        binding.stop(clear_downloads=True)
        assert not cached.exists()

    def test_suite_boot_image_overrides_the_runs_image(self):
        other = self.tempdir / "other.img"
        other.write_bytes(b"other dos")
        binding.start(boot_image=self.image)

        _, image = self._run_suite(
            binding.suite_backend(self.exe, boot_image=other))
        assert image == b"other dos"

    def test_stop_stops_a_machine_the_caller_left_running(self):
        # A machine outlives the call that booted it, so a run
        # closing while one is up must stop it before sweeping the
        # home it is running from.
        binding.start(boot_image=self.image)
        backend = binding.suite_backend(self.exe)

        with self._fake_machine():
            backend.start_guest()
            home = backend._home
            binding.stop()

        assert backend._home is None
        assert not os.path.exists(home)
        assert backend not in binding._running

    def test_a_stopped_guest_is_no_longer_tracked(self):
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        with self._fake_machine():
            backend.start_guest()
            assert backend in binding._running
            backend.stop_guest()

        assert backend not in binding._running

    def test_start_twice_raises_and_stop_is_reentrant(self):
        binding.start()
        with pytest.raises(RuntimeError, match="already"):
            binding.start()
        binding.stop()
        binding.stop()

    def test_forgotten_stop_is_swept_at_interpreter_exit(self):
        env = dict(os.environ,
                   LOCALAPPDATA=str(self.tempdir),      # Windows
                   XDG_CACHE_HOME=str(self.tempdir))    # elsewhere
        result = subprocess.run(
            [sys.executable, "-c",
             "import testaferro\n"
             "from testaferro import reliquary as binding\n"
             "testaferro.start()\n"
             "print(binding._run_area['dir'])\n"],
            env=env, capture_output=True, text=True, check=True)
        run_dir = result.stdout.strip().splitlines()[-1]

        assert run_dir
        assert not os.path.exists(run_dir)

    def test_package_level_start_stop_delegate(self):
        import testaferro
        with mock.patch.object(binding, "start") as start, \
                mock.patch.object(binding, "stop") as stop:
            testaferro.start(boot_image=self.image)
            testaferro.stop(clear_downloads=True)
        start.assert_called_once_with(boot_image=self.image)
        stop.assert_called_once_with(clear_downloads=True)


@requires_reliquary
class LogicalLinesTests:
    """The guest's 80-column console hard-wraps any longer line into
    two screen rows, split wherever column 80 fell — mid-token
    included — and the capture then drops blank rows and right-trims
    the rest. `_logical_lines()` undoes the wrap where the rows still
    carry the evidence: a row of exactly the console width continues
    on the next row. What it cannot undo is stated here as tests,
    because both limits shaped the grammar's failure-count check.
    """

    def test_joins_a_full_width_row_to_its_successor(self):
        # 87 characters: the virtio-dos failure header that was
        # silently reported as a pass. Column 80 falls mid-name.
        header = ("src\\rng_test.cpp:97: error: Failure in "
                  "TEST(Transport, PoolHoldsConsoleQueuesBesideRng)")
        assert (binding._logical_lines([header[:80], header[80:]])
                == [header])

    def test_joins_across_multiple_full_rows(self):
        line = "x" * 165
        assert (binding._logical_lines([line[:80], line[80:160], line[160:]])
                == [line])

    def test_short_rows_pass_through(self):
        rows = ["TEST(Vring, Wraps) - 0 ms",
                "OK (2 tests, 1 ran, 1 checks, 0 ignored, "
                "1 filtered out, 0 ms)"]
        assert binding._logical_lines(rows) == rows

    def test_a_wrap_on_a_space_is_not_healed(self):
        # When column 80 lands on a space, the capture right-trims
        # the first row below full width and the evidence of the wrap
        # is gone: these rows are indistinguishable from two short
        # lines, so they stay split. The grammar's failure-count
        # check is what keeps this limit loud instead of silent.
        first = "a" * 70   # was "a"*70 + " " * 10 on screen
        second = "continuation"
        assert binding._logical_lines([first, second]) == [first, second]

    def test_a_natural_full_width_line_joins_its_successor(self):
        # A line of exactly 80 characters leaves a blank row behind
        # it on a teletype console, and the capture drops blank rows
        # — so it is indistinguishable from a wrap and joins. The
        # damage is a swallowed next line, which the grammar reports
        # as a missing test or summary rather than absorbing quietly.
        rows = ["b" * 80, "next line"]
        assert binding._logical_lines(rows) == ["b" * 80 + "next line"]

    def test_wrapped_failure_header_parses_as_a_failure(self):
        # The original false pass, end to end: rows as the capture
        # delivered them (header split mid-token, blank rows gone),
        # through the transport's reconstruction, into the grammar.
        header = ("src\\rng_test.cpp:97: error: Failure in "
                  "TEST(Transport, PoolHoldsConsoleQueuesBesideRng)")
        rows = [
            "TEST(Transport, PoolHoldsConsoleQueuesBesideRng)",
            header[:80],
            header[80:],
            "        expected <0 0x0>",
            "        but was  <6 0x6>",
            " - 1 ms",
            "Errors (1 failures, 1 tests, 1 ran, 1 checks, 0 ignored, "
            "0 filtered out, 1 ms)",
        ]
        text = "\n".join(binding._logical_lines(rows)) + "\n"
        outcomes = cpputest.parse_run(text)
        assert ([(o.group, o.name, o.passed) for o in outcomes]
                == [("Transport", "PoolHoldsConsoleQueuesBesideRng", False)])

    def test_wrapped_enumeration_rejoins(self):
        # The same wrap broke '-ln' enumeration first: one long line
        # of space-separated ids, split mid-token at column 80.
        line = ("Rng.TwoRequestsReturnDifferentRealRandomBytes "
                "Rng.DriverIsInstalled "
                "Transport.PoolHoldsConsoleQueuesBesideRng")
        ids = cpputest.parse_list(
            "\n".join(binding._logical_lines([line[:80], line[80:]])))
        assert [str(i) for i in ids] == line.split()


def _machine_home(name):
    return os.path.join(cache.cache_root(), "machines", name)


@requires_reliquary
class PersistentMachineTests(_BindingFixture):
    """A declaration naming ``persist=`` keeps its machine between
    guest sessions (F2, U8): the home lives under ``machines/<name>``
    in Testaferro's cache, ``stop_guest()`` stops without sweeping,
    and the next session boots the same machine rather than authoring
    a new one. Every case declares a boot image so creation stays on
    the cheap side of P10's line.
    """

    @pytest.fixture(autouse=True)
    def _release(self):
        yield
        binding._stop_running_machines()
        binding._holders.clear()

    def _machine_ids(self, home):
        session = binding._open_session(
            home, os.path.join(home, "blueprints"))
        return [state["id"] for state in session.list_machines()]

    def test_the_home_is_named_kept_and_reused(self):
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        persist="hw-harness")

        with self._fake_machine():
            backend.start_guest()
            home = backend._home
            assert home == _machine_home("hw-harness")
            first = self._machine_ids(home)
            backend.stop_guest()

            assert os.path.isdir(home)
            assert self._machine_ids(home) == first

            again = binding.suite_backend(self.exe, boot_image=self.image,
                                          persist="hw-harness")
            again.start_guest()
            assert again._home == home
            assert self._machine_ids(home) == first
            assert again.location == "C:\\"
            again.stop_guest()

    def test_the_work_drive_is_restaged_each_session(self):
        # D: is Testaferro's staging and is rebuilt per guest session;
        # what persists is the machine's own disks, not the set that
        # was staged last time.
        stale = self.tempdir / "OLD.DAT"
        stale.write_bytes(b"old")
        first = binding.suite_backend(self.exe, boot_image=self.image,
                                      persist="hw-harness",
                                      files=[str(stale)])
        with self._fake_machine():
            first.start_guest()
            work = pathlib.Path(first._home) / "work"
            assert (work / "OLD.DAT").exists()
            first.stop_guest()

            second = binding.suite_backend(self.exe, boot_image=self.image,
                                           persist="hw-harness")
            second.start_guest()
            assert sorted(p.name for p in work.iterdir()) == ["SUITE.EXE"]
            second.stop_guest()

    def test_a_second_holder_in_this_process_takes_over(self):
        # Two suites naming one persistent machine in one run: the
        # machine serves one guest session at a time, so the later
        # one closes the earlier holder's session cleanly and boots
        # the same disks for itself.
        first = binding.suite_backend(self.exe, boot_image=self.image,
                                      persist="hw-harness")
        second = binding.suite_backend(self.exe, boot_image=self.image,
                                       persist="hw-harness")
        with self._fake_machine():
            first.start_guest()
            second.start_guest()

            assert first._home is None
            assert first not in binding._running
            assert second in binding._running
            second.stop_guest()

    def test_a_machine_recorded_running_elsewhere_is_refused(self):
        # Another process — or a run that died — holds it: refused
        # naming the verb that frees it, never stopped from under
        # whoever has it.
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        persist="hw-harness")
        with self._fake_machine():
            backend.start_guest()
            backend.stop_guest()

            real = reliquary_dist.Session.load_machine_state

            def running(session, machine_id):
                state = real(session, machine_id)
                state["phase"] = "running"
                return state

            with mock.patch.object(reliquary_dist.Session,
                                   "load_machine_state", autospec=True,
                                   side_effect=running):
                with pytest.raises(RuntimeError,
                                   match="testaferro shutdown hw-harness"):
                    backend.start_guest()
            assert backend._home is None

    def test_persistent_machines_are_listed_by_name_with_their_phase(self):
        assert binding.persistent_machines() == ()
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        persist="hw-harness")
        with self._fake_machine():
            backend.start_guest()
            backend.stop_guest()

        [found] = binding.persistent_machines()
        assert found.name == "hw-harness"
        assert found.phase == "ready"
        assert found.home == _machine_home("hw-harness")

    def test_destroy_removes_the_machine_and_its_home(self):
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        persist="hw-harness")
        with self._fake_machine():
            backend.start_guest()
            home = backend._home
            backend.stop_guest()

            binding.destroy("hw-harness")

        assert not os.path.exists(home)
        assert binding.persistent_machines() == ()

    def test_destroy_and_shutdown_refuse_an_unknown_name(self):
        with pytest.raises(LookupError, match="no persistent machine"):
            binding.destroy("nobody")
        with pytest.raises(LookupError, match="no persistent machine"):
            binding.shutdown("nobody")

    def test_shutdown_of_a_stopped_machine_is_a_no_op(self):
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        persist="hw-harness")
        with self._fake_machine():
            backend.start_guest()
            backend.stop_guest()

            assert binding.shutdown("hw-harness") is False


@requires_reliquary
class CacheCleaningTests(_BindingFixture):
    """``clean()`` sweeps what killed runs left behind and nothing a
    live one is using (F2): stale run and guest homes go, a home whose
    machine is recorded running stays, and the installed system goes
    only when asked for by name.
    """

    def _stale_guest(self, *parts):
        home = pathlib.Path(cache.cache_root()).joinpath(*parts)
        (home / "blueprints").mkdir(parents=True)
        return home

    def test_stale_homes_are_swept_and_reported(self):
        run = self._stale_guest("runs", "run-dead", "guests", "guest-x")
        lone = self._stale_guest("guests", "guest-y")

        removed = binding.clean()

        assert not run.exists()
        assert not lone.exists()
        assert sorted(removed) == sorted([
            str(pathlib.Path(cache.cache_root()) / "runs" / "run-dead"),
            str(lone)])

    def test_a_home_with_a_running_machine_is_left_alone(self):
        run = self._stale_guest("runs", "run-live", "guests", "guest-x")
        with mock.patch.object(
                reliquary_dist.Session, "list_machines", autospec=True,
                return_value=[{"id": "m", "phase": "running"}]):
            removed = binding.clean()

        assert run.exists()
        assert removed == ()

    def test_the_system_disk_goes_only_when_asked(self):
        cached = (pathlib.Path(cache.cache_root())
                  / binding._FREEDOS_IMAGE_NAME)
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(b"not a real system")
        (cached.parent / (cached.name + ".abc.part")).write_bytes(b"")

        binding.clean()
        assert cached.exists()

        removed = binding.clean(system=True)
        assert not cached.exists()
        assert not list(cached.parent.glob("*.part"))
        assert str(cached) in removed

    def test_a_persistent_machine_is_never_cleaned(self):
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        persist="hw-harness")
        with self._fake_machine():
            backend.start_guest()
            home = backend._home
            backend.stop_guest()
        binding._holders.clear()

        binding.clean(system=True)

        assert os.path.isdir(home)
