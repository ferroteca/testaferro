# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Tests for the DOSBox-X provider binding, everything short of a run.

The binding is batch-shaped: each guest operation is one DOSBox-X
invocation authored as a conf and read back from a redirected file.
That leaves almost everything unit-testable as pure text — the conf,
the command spelling, the placement — and P10 draws the line at the
invocation itself: DOSBox-X starting a DOS is a guest starting,
however fast, so nothing here launches it. `subprocess.run` is
stubbed wherever an operation would, and the real launch belongs to
`tests/integration/test_dosbox_x.py`.
"""

import os
import subprocess
from unittest import mock

import pytest

from testaferro import cache, dosbox_x as binding
from testaferro.backend import GuestOutputError

from helpers import new_format_exe_bytes, plain_dos_exe_bytes


class _BindingFixture:
    """Shared setup: a DOS exe, a private cache, and DOSBox-X 'found'
    without being looked for."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.tempdir = tmp_path
        self.exe = tmp_path / "SUITE.EXE"
        self.exe.write_bytes(plain_dos_exe_bytes())
        patches = [
            mock.patch.object(cache, "cache_root",
                              return_value=str(tmp_path / "cache")),
            mock.patch.object(binding, "_find_executable",
                              return_value=r"X:\dosbox-x.exe"),
        ]
        for patch in patches:
            patch.start()
        yield
        for patch in patches:
            patch.stop()

class SuiteDispatchTests(_BindingFixture):
    def test_rejects_a_provably_foreign_executable(self):
        machine = (0x014C).to_bytes(2, "little")
        exe = self.tempdir / "HOST.EXE"
        exe.write_bytes(new_format_exe_bytes(b"PE\0\0" + machine))

        with pytest.raises(ValueError, match=r"Windows x86 \(PE\)"):
            binding.suite_backend(exe)

    def test_accepts_headerless_image_like_a_com_program(self):
        exe = self.tempdir / "TOOL.COM"
        exe.write_bytes(b"\xb4\x09\xba\x00\x01\xcd\x21\xc3")

        assert binding.suite_backend(exe) is not None

    def test_missing_executable_raises_at_dispatch(self):
        with pytest.raises(FileNotFoundError):
            binding.suite_backend(self.tempdir / "MISSING.EXE")

    def test_a_non_dos_machine_config_is_refused(self):
        with pytest.raises(ValueError, match="needs a DOS machine"):
            binding.suite_backend(self.exe,
                                  machine_config={"platform": "os2"})

    def test_another_providers_document_is_refused_naming_its_fields(self):
        # A dosbox-x environment's fields are conf sections (F21). A
        # field that is not one — a blueprint's `memory`, `boot` — is
        # another provider's vocabulary (P3), refused by name rather
        # than quietly dropped.
        with pytest.raises(ValueError) as caught:
            binding.suite_backend(self.exe, machine_config={
                "platform": "dos", "memory": "32M", "boot": ["hdd0"],
                "cpu": {"cycles": "max"}})

        assert "boot, memory" in str(caught.value)
        assert "cpu" not in str(caught.value)

    def test_blueprint_media_beside_the_machine_are_refused(self):
        from testaferro.environments import EnvironmentSpec

        spec = EnvironmentSpec({"platform": "dos"},
                               media=[{"name": "boot", "location": "x"}])

        with pytest.raises(ValueError, match="media belong to another"):
            binding.suite_backend(self.exe, machine_config=spec)

    def test_a_declaration_of_testaferros_own_words_is_accepted(self):
        from testaferro.environments import EnvironmentSpec

        spec = EnvironmentSpec({"platform": "dos"}, timeout=5,
                               location="D:\\TESTS",
                               program="{location}\\RUN.EXE",
                               setup=("DRIVER.COM /install",))

        backend = binding.suite_backend(self.exe, machine_config=spec)

        assert backend._timeout == 5
        assert backend.location == "D:\\TESTS"
        assert backend._setup == ("DRIVER.COM /install",)

    def test_declared_sections_are_carried_in_declaration_order(self):
        # Each field beside Testaferro's own words is a conf section,
        # carried as authored (P2, P3): nothing is read, and the order
        # the tester wrote is the order DOSBox-X sees.
        from testaferro.environments import EnvironmentSpec

        spec = EnvironmentSpec({"platform": "dos",
                                "dosbox": {"machine": "vga"},
                                "cpu": {"cycles": "max", "core": "auto"}})

        backend = binding.suite_backend(self.exe, machine_config=spec)

        assert backend._sections == (
            ("dosbox", {"machine": "vga"}),
            ("cpu", {"cycles": "max", "core": "auto"}))

    def test_a_declared_autoexec_is_refused_with_the_reason(self):
        # [autoexec] is the batch shape itself — the one section
        # Testaferro writes — so a declaration supplying its own is
        # refused naming that and the spelling that does exist.
        with pytest.raises(ValueError) as caught:
            binding.suite_backend(self.exe, machine_config={
                "platform": "dos", "autoexec": {"DRIVER.COM": None}})

        assert "cannot declare [autoexec]" in str(caught.value)
        assert "setup=" in str(caught.value)

    def test_a_boot_image_is_refused_with_the_reason(self):
        # DOSBox-X can BOOT a floppy image, but a booted DOS runs no
        # [autoexec], and that section is the batch shape's only way
        # of running the suite — refused naming that (F21).
        with pytest.raises(ValueError, match="runs no \\[autoexec\\]"):
            binding.suite_backend(self.exe,
                                  boot_image=str(self.tempdir / "a.img"))

    def test_guest_sessions_are_refused_with_the_reason(self):
        # U10's open question, answered (D27): the batch model holds
        # no guest state between invocations, so a scripted
        # interaction has nothing to build on here — refused naming
        # the reason and the provider that serves it.
        with pytest.raises(ValueError, match="runs suites only"):
            binding.guest_session()


class PlacementTests(_BindingFixture):
    """The location settles at construction: one drive, this
    binding's own constant, no machine to read anything off."""

    def test_the_default_location_is_the_work_drive_root(self):
        # D:, the letter the default provider's work drive takes, so
        # an address declared for one provider holds on the other
        # (F21, D28).
        backend = binding.suite_backend(self.exe)

        assert backend.location == "D:\\"

    def test_a_declared_location_maps_to_a_work_subdirectory(self):
        backend = binding.suite_backend(self.exe, location="D:\\TESTS")
        backend.start_guest()
        try:
            staged = os.path.join(backend._work, "TESTS", "SUITE.EXE")
            assert os.path.isfile(staged)
        finally:
            backend.stop_guest()

    def test_a_location_on_another_drive_is_refused_naming_this_one(self):
        with pytest.raises(ValueError) as caught:
            binding.suite_backend(self.exe, location="C:\\TESTS")

        assert "names drive C:" in str(caught.value)
        assert "D:" in str(caught.value)

    def test_files_are_gathered_beside_the_suite(self):
        data = self.tempdir / "DATA.BIN"
        data.write_bytes(b"data")
        backend = binding.suite_backend(self.exe, files=[str(data)])
        backend.start_guest()
        try:
            names = sorted(os.listdir(backend._work))
            assert names == ["DATA.BIN", "SUITE.EXE"]
        finally:
            backend.stop_guest()

    def test_the_guest_home_is_swept_on_stop(self):
        backend = binding.suite_backend(self.exe)
        backend.start_guest()
        home = backend._home

        backend.stop_guest()

        assert not os.path.exists(home)

    def test_a_missing_emulator_refuses_before_any_home_exists(self):
        backend = binding.suite_backend(self.exe)
        with mock.patch.object(
                binding, "_find_executable",
                side_effect=FileNotFoundError("dosbox-x was not found")):
            with pytest.raises(FileNotFoundError):
                backend.start_guest()

        assert backend._home is None


class DiscoveryTests:
    """Where DOSBox-X is looked for: PATH, then the installer's
    default, then the host's own Program Files."""

    def test_program_files_comes_from_the_host_not_a_literal(self):
        with mock.patch.dict(os.environ,
                             {"PROGRAMFILES": r"E:\Apps",
                              "PROGRAMFILES(X86)": r"E:\Apps32"}):
            locations = binding._windows_locations()

        assert locations == (r"C:\DOSBox-X\dosbox-x.exe",
                             r"E:\Apps\DOSBox-X\dosbox-x.exe",
                             r"E:\Apps32\DOSBox-X\dosbox-x.exe")

    def test_a_32_bit_host_naming_one_directory_twice_lists_it_once(self):
        with mock.patch.dict(os.environ,
                             {"PROGRAMFILES": r"E:\Apps",
                              "PROGRAMFILES(X86)": r"E:\Apps"}):
            locations = binding._windows_locations()

        assert locations == (r"C:\DOSBox-X\dosbox-x.exe",
                             r"E:\Apps\DOSBox-X\dosbox-x.exe")

    def test_without_program_files_only_the_installer_default_remains(self):
        with mock.patch.dict(os.environ, clear=True):
            locations = binding._windows_locations()

        assert locations == (r"C:\DOSBox-X\dosbox-x.exe",)

    def test_the_refusal_names_where_it_looked(self, tmp_path):
        with mock.patch.object(binding.shutil, "which", return_value=None), \
                mock.patch.object(binding.os.path, "isfile",
                                  return_value=False), \
                mock.patch.dict(os.environ,
                                {"PROGRAMFILES": str(tmp_path)}):
            with pytest.raises(FileNotFoundError) as caught:
                binding._find_executable()

        assert str(tmp_path) in str(caught.value)
        assert "PATH" in str(caught.value)


class ConfAuthoringTests:
    """The conf one invocation runs, as pure text (P10)."""

    def test_the_autoexec_mounts_runs_and_exits(self):
        text = binding._conf(r"C:\cache\guests\g1\work",
                             ["SUITE.EXE -v > D:\\TSTFERRO.OUT"])

        assert text == (
            "[autoexec]\n"
            "@echo off\n"
            'mount d "C:\\cache\\guests\\g1\\work"\n'
            "D:\n"
            "SUITE.EXE -v > D:\\TSTFERRO.OUT\n"
            "exit\n")

    def test_setup_commands_precede_the_program_in_order(self):
        text = binding._conf("work", ["FIRST.COM", "SECOND.COM",
                                      "RUN.EXE > D:\\TSTFERRO.OUT"])

        lines = text.splitlines()
        assert lines.index("FIRST.COM") < lines.index("SECOND.COM")
        assert lines.index("SECOND.COM") < lines.index(
            "RUN.EXE > D:\\TSTFERRO.OUT")

    def test_declared_sections_precede_the_autoexec_as_authored(self):
        # The tester's sections go in ahead of Testaferro's own, each
        # key spelled as DOSBox-X spells it — a truth value as the
        # conf's `true`, everything else as written (F21).
        text = binding._conf("work", ["RUN.EXE > D:\\TSTFERRO.OUT"],
                             sections=(("cpu", {"cycles": "max"}),
                                       ("render", {"aspect": True,
                                                   "scaler": "none"})))

        assert text == (
            "[cpu]\n"
            "cycles=max\n"
            "\n"
            "[render]\n"
            "aspect=true\n"
            "scaler=none\n"
            "\n"
            "[autoexec]\n"
            "@echo off\n"
            'mount d "work"\n'
            "D:\n"
            "RUN.EXE > D:\\TSTFERRO.OUT\n"
            "exit\n")


class DocumentTests(_BindingFixture):
    """A whole `.conf` is DOSBox-X's own document, opened by this
    binding (F21): the declaration keeps the path, the provider reads
    the format."""

    def _conf_file(self, text):
        path = self.tempdir / "harness.conf"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_a_conf_document_reads_as_sections(self):
        path = self._conf_file(
            "# DOSBox-X's own INI, comments and all\n"
            "[dosbox]\n"
            "machine = vga\n"
            "memsize = 16\n"
            "\n"
            "[cpu]\n"
            "cycles = max\n")

        spec = binding.read_document(path)

        assert spec.platform == "dos"
        assert spec.dosbox == {"machine": "vga", "memsize": "16"}
        assert spec.cpu == {"cycles": "max"}

    def test_keys_and_values_are_carried_as_authored(self):
        # Nothing case-folded, nothing interpolated: `%` and mixed
        # case are DOSBox-X's to read (P3).
        path = self._conf_file("[sdl]\nOutput = OpenGL\ntitle = 100%\n")

        spec = binding.read_document(path)

        assert spec.sdl == {"Output": "OpenGL", "title": "100%"}

    def test_a_document_with_its_own_autoexec_is_refused_on_reading(self):
        path = self._conf_file("[cpu]\ncycles = max\n"
                               "[autoexec]\nDRIVER.COM /install\n")

        with pytest.raises(ValueError, match="cannot declare \\[autoexec\\]"):
            binding.read_document(path)

    def test_a_document_path_reaches_the_generated_conf(self):
        path = self._conf_file("[cpu]\ncycles = max\n")
        backend = binding.suite_backend(self.exe, machine_config=path)

        assert backend._sections == (("cpu", {"cycles": "max"}),)


class GuestRunTests(_BindingFixture):
    """One exchange, with the invocation itself stubbed (P10)."""

    def _run(self, backend, args, side_effect=None, **run_kwargs):
        """Drive one _run_in_guest with subprocess.run stubbed."""
        backend.start_guest()
        try:
            with mock.patch.object(
                    binding.subprocess, "run", side_effect=side_effect,
                    **run_kwargs) as run:
                return backend._run_in_guest(str(self.exe), args), run
        finally:
            backend.stop_guest()

    def _completed(self, returncode=0, stderr=b""):
        return subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=b"", stderr=stderr)

    def test_one_invocation_per_operation_reading_the_redirected_file(self):
        backend = binding.suite_backend(self.exe)

        def fake_run(argv, **kwargs):
            # The redirected file arrives with the guest's own bytes:
            # CRLF line ends and the guest code page, both of which
            # the read normalizes.
            with open(os.path.join(backend._work, "TSTFERRO.OUT"),
                      "wb") as handle:
                handle.write(b"OK (3 tests)\r\n")
            return self._completed()

        text, run = self._run(backend, ("-v",), side_effect=fake_run)

        assert text == "OK (3 tests)\n"
        [argv] = run.call_args.args
        assert argv[0] == r"X:\dosbox-x.exe"
        assert argv[1] == "-conf"
        assert os.path.basename(argv[2]) == "testaferro.conf"
        assert "-silent" in argv
        assert "-nolog" in argv

    def test_the_command_is_spelled_off_the_settled_location(self):
        # The argv expectation is a literal, never rebuilt from the
        # builder under test (D17's lesson): the conf carries one DOS
        # command line, the staged executable at the settled address
        # with the tokens joined after it.
        backend = binding.suite_backend(self.exe)
        conf_seen = []

        def fake_run(argv, **kwargs):
            with open(argv[2], encoding="utf-8") as handle:
                conf_seen.append(handle.read())
            with open(os.path.join(backend._work, "TSTFERRO.OUT"),
                      "wb") as handle:
                handle.write(b"OK\r\n")
            return self._completed()

        self._run(backend, ("-sg", "Vring", "-sn", "Wraps"),
                  side_effect=fake_run)

        assert ("D:\\SUITE.EXE -sg Vring -sn Wraps > D:\\TSTFERRO.OUT"
                in conf_seen[0])

    def test_declared_sections_are_written_ahead_of_the_autoexec(self):
        backend = binding.suite_backend(
            self.exe, machine_config={"platform": "dos",
                                      "cpu": {"cycles": "max"}})
        conf_seen = []

        def fake_run(argv, **kwargs):
            with open(argv[2], encoding="utf-8") as handle:
                conf_seen.append(handle.read())
            with open(os.path.join(backend._work, "TSTFERRO.OUT"),
                      "wb") as handle:
                handle.write(b"OK\r\n")
            return self._completed()

        self._run(backend, ("-v",), side_effect=fake_run)

        lines = conf_seen[0].splitlines()
        assert lines.index("[cpu]") < lines.index("cycles=max")
        assert lines.index("cycles=max") < lines.index("[autoexec]")

    def test_setup_commands_run_in_every_invocation(self):
        # The batch spelling of "once per guest session": each
        # invocation is its own guest, and a TSR the suite needs
        # resident must be resident every time (F9, D15).
        backend = binding.suite_backend(
            self.exe, setup=["DRIVER.COM /install"])
        conf_seen = []

        def fake_run(argv, **kwargs):
            with open(argv[2], encoding="utf-8") as handle:
                conf_seen.append(handle.read())
            with open(os.path.join(backend._work, "TSTFERRO.OUT"),
                      "wb") as handle:
                handle.write(b"OK\r\n")
            return self._completed()

        self._run(backend, ("-v",), side_effect=fake_run)

        lines = conf_seen[0].splitlines()
        assert lines.index("DRIVER.COM /install") < lines.index(
            "D:\\SUITE.EXE -v > D:\\TSTFERRO.OUT")

    def test_a_declared_program_is_the_command_spelled(self):
        backend = binding.suite_backend(
            self.exe, program="{location}RUNNER.EXE")
        conf_seen = []

        def fake_run(argv, **kwargs):
            with open(argv[2], encoding="utf-8") as handle:
                conf_seen.append(handle.read())
            with open(os.path.join(backend._work, "TSTFERRO.OUT"),
                      "wb") as handle:
                handle.write(b"OK\r\n")
            return self._completed()

        self._run(backend, ("-v",), side_effect=fake_run)

        assert "D:\\RUNNER.EXE -v > D:\\TSTFERRO.OUT" in conf_seen[0]

    def test_a_run_that_leaves_no_output_fails_naming_the_channel(self):
        backend = binding.suite_backend(self.exe)

        with pytest.raises(GuestOutputError, match="no output"):
            self._run(backend, ("-v",),
                      return_value=self._completed())

    def test_a_timeout_fails_in_the_guest_exchange_shape(self):
        backend = binding.suite_backend(self.exe, timeout=1)

        with pytest.raises(GuestOutputError, match="within 1 seconds"):
            self._run(backend, ("-v",),
                      side_effect=subprocess.TimeoutExpired("dosbox-x", 1))

    def test_a_failed_invocation_names_the_exit_status(self):
        backend = binding.suite_backend(self.exe)

        with pytest.raises(GuestOutputError, match="status 3"):
            self._run(backend, ("-v",),
                      return_value=self._completed(returncode=3,
                                                   stderr=b"boom"))

    def test_a_run_outside_a_guest_session_is_refused(self):
        backend = binding.suite_backend(self.exe)

        with pytest.raises(RuntimeError, match="no guest session"):
            backend._run_in_guest(str(self.exe), ("-v",))
