# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Unit tests for the reliquary provider binding: executable
interrogation and the testaferro-managed reliquary home.

`binding` is testaferro.reliquary; the bare "reliquary." strings
patched below are the provider distribution it drives.
"""

import contextlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from testaferro import cache, cpputest

from test_binfmt import new_format_exe_bytes, plain_dos_exe_bytes

RELIQUARY_AVAILABLE = importlib.util.find_spec("reliquary") is not None

if RELIQUARY_AVAILABLE:
    import reliquary as reliquary_dist
    from testaferro import environments
    from testaferro import reliquary as binding

_no_install = None


def setUpModule():
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
    global _no_install
    if not RELIQUARY_AVAILABLE:
        return
    _no_install = mock.patch.object(
        binding, "_build_default_image",
        side_effect=AssertionError(
            "the unit tier may not install a guest system: stub "
            "_cached_default_image() in this test (P10)"))
    _no_install.start()


def tearDownModule():
    if _no_install is not None:
        _no_install.stop()


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


@unittest.skipUnless(RELIQUARY_AVAILABLE, "reliquary is not installed")
class SuiteBackendDispatchTests(unittest.TestCase):
    """The guard on suite_backend(); the per-format naming matrix
    lives with the classifier in test_binfmt."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

    def _exe(self, content):
        path = pathlib.Path(self.tempdir.name) / "SUITE.EXE"
        path.write_bytes(content)
        return path

    def test_rejects_windows_pe_executable(self):
        exe = self._exe(new_format_exe_bytes(b"PE\0\0"))

        with self.assertRaisesRegex(ValueError, r"Windows \(PE\)"):
            binding.suite_backend(exe)

    def test_rejects_pe_x86_naming_the_architecture(self):
        machine = (0x014C).to_bytes(2, "little")
        exe = self._exe(new_format_exe_bytes(b"PE\0\0" + machine))

        with self.assertRaisesRegex(ValueError, r"Windows x86 \(PE\)"):
            binding.suite_backend(exe)

    def test_accepts_headerless_image_like_a_com_program(self):
        # .com-style raw 8086 code has no magic at all — nothing to
        # prove, so it must pass through for the guest to judge
        exe = self._exe(b"\xb4\x09\xba\x00\x01\xcd\x21\xc3")

        self.assertIsNotNone(binding.suite_backend(exe))

    def test_missing_executable_raises_at_dispatch(self):
        with self.assertRaises(FileNotFoundError):
            binding.suite_backend(
                pathlib.Path(self.tempdir.name) / "MISSING.EXE")


class _BindingFixture(unittest.TestCase):
    """Shared setup: a DOS exe, a custom image, and a private cache."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        root = pathlib.Path(self.tempdir.name)
        self.exe = root / "SUITE.EXE"
        self.exe.write_bytes(plain_dos_exe_bytes())
        self.image = root / "custom.img"
        self.image.write_bytes(b"custom dos")
        cache_patch = mock.patch.object(
            cache, "cache_root", return_value=str(root / "cache"))
        cache_patch.start()
        self.addCleanup(cache_patch.stop)

    def _blueprint(self, home):
        """The machine spec testaferro authored for one run home."""
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
        do (P10). What is under test here is testaferro's own
        bookkeeping, which a floppy exercises just as well.
        """
        seen = []

        def fake_exec(command, *, machine=None, context=None, timeout=None):
            home = context.home_dir
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
        testaferro authored, resolves its media and materializes the
        drives, all of which is cheap and hypervisor-free. Booting is
        not — `start_machine` starts a guest for real (P10) — so every
        call that needs a running machine is stubbed and nothing else.

        **`execute_script` is one of them, and not obviously.** A
        script's `machine` header is a precondition reliquary
        *establishes*: the readiness script says `running`, so running
        one against a machine this fixture never really started starts
        it for real. Stubbing `start_machine` alone is not enough, and
        the way that announces itself is a unit run booting QEMU.

        Creation stays cheap only while every drive's media is `use`
        (attached in place). A blueprint declaring a blank (`size`)
        makes reliquary reach for an external image tool, which belongs
        in an integration test instead.
        """
        return _patched(
            mock.patch("reliquary.start_machine"),
            mock.patch("reliquary.stop_machine"),
            mock.patch("reliquary.execute_script"),
            mock.patch("reliquary.get_machine_var", return_value="yes"),
            mock.patch("reliquary.exec", side_effect=exec_side_effect,
                       **exec_kwargs))

@unittest.skipUnless(RELIQUARY_AVAILABLE, "reliquary is not installed")
class ReliquarySuiteBackendTests(_BindingFixture):
    """Backend behavior within one guest session."""

    def test_a_guest_runs_in_a_fresh_home_with_the_caller_boot_image(self):
        # No run open, so the guest home sits at the cache root rather
        # than inside a run's area (D15).
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        [(home, image)] = self._guest_homes_seen(backend)

        self.assertTrue(home.startswith(
            os.path.join(cache.cache_root(), "guests")))
        self.assertEqual(image, b"custom dos")
        self.assertFalse(os.path.exists(home))

    def test_each_guest_session_gets_its_own_home(self):
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        homes = [self._guest_homes_seen(backend)[0][0] for _ in range(2)]

        self.assertNotEqual(homes[0], homes[1])

    def test_machine_template_becomes_this_guests_blueprint(self):
        source = pathlib.Path(self.tempdir.name) / "msdos.img"
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
                self.assertEqual(drives["floppy0"]["location"]["local"],
                                 str(source))
                self.assertEqual(template.drives["floppy0"]["location"],
                                 {"local": str(source)})
            finally:
                backend.stop_guest()

    def test_a_machine_with_no_writable_room_falls_back_to_a_work_drive(self):
        """The fallback F4 left standing, and this fixture is it.

        The declared boot image here is ten bytes of text, not a FAT
        volume, so reliquary refuses to stage into it at rest — which
        is exactly the "machine offering no writable room" the design
        keeps the directory-source drive for. testaferro appends one,
        recreates, and stages there instead, so the run still happens.
        A *declared* location would have surfaced the refusal rather
        than falling back; only a defaulted one may.
        """
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        with self._fake_machine():
            backend.start_guest()
            try:
                home = backend._home
                drives = self._blueprint(home)["drives"]
                work = drives["hdd0"]["location"]["local"]
                self.assertEqual(work, os.path.join(home, "work"))
                staged = pathlib.Path(work) / "SUITE.EXE"
                self.assertEqual(staged.read_bytes(), self.exe.read_bytes())
                # The appended drive is served whole, so the set is at
                # its root rather than in a directory under it.
                self.assertEqual(backend.location, "C:\\")
            finally:
                backend.stop_guest()

    def test_files_are_staged_beside_the_suite(self):
        fixture = pathlib.Path(self.tempdir.name) / "DATA.TXT"
        fixture.write_bytes(b"fixture bytes")
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        files=[str(fixture)])

        with self._fake_machine():
            backend.start_guest()
            try:
                work = pathlib.Path(backend._home) / "work"
                self.assertEqual((work / "SUITE.EXE").read_bytes(),
                                 self.exe.read_bytes())
                self.assertEqual((work / "DATA.TXT").read_bytes(),
                                 b"fixture bytes")
            finally:
                backend.stop_guest()

    def test_a_declared_directory_contributes_its_contents(self):
        # `files=["fixtures"]` lands the fixtures where a guest program
        # looks for them, not one directory deeper.
        tree = pathlib.Path(self.tempdir.name) / "fixtures"
        tree.mkdir()
        (tree / "CASE.DAT").write_bytes(b"case")
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        files=[str(tree)])

        with self._fake_machine():
            backend.start_guest()
            try:
                work = pathlib.Path(backend._home) / "work"
                self.assertEqual((work / "CASE.DAT").read_bytes(), b"case")
            finally:
                backend.stop_guest()

    def test_the_testers_boot_image_is_read_and_never_written(self):
        # P5's promise, and it was not kept: the image was attached in
        # place, so a guest writing to A: — which DOS does for reasons
        # of its own — edited the file its tester handed over. What
        # boots is testaferro's copy inside the guest's own home.
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        with self._fake_machine():
            backend.start_guest()
            try:
                booted = self._blueprint(
                    backend._home)["drives"]["floppy0"]["location"]["local"]
                home = backend._home
            finally:
                backend.stop_guest()

        self.assertNotEqual(pathlib.Path(booted), pathlib.Path(self.image))
        self.assertEqual(pathlib.Path(booted).parent, pathlib.Path(home))
        # and it is a copy, not an empty placeholder
        self.assertEqual(pathlib.Path(self.image).read_bytes(), b"custom dos")

    def test_two_guest_sessions_do_not_share_a_writable_floppy(self):
        # One run, two suites: each gets its own copy, so neither can
        # hand the other a floppy it has changed.
        binding.start(boot_image=self.image)
        self.addCleanup(binding.stop)
        booted = []

        for _ in range(2):
            backend = binding.suite_backend(self.exe)
            with self._fake_machine():
                backend.start_guest()
                try:
                    booted.append(self._blueprint(backend._home)
                                  ["drives"]["floppy0"]["location"]["local"])
                finally:
                    backend.stop_guest()

        self.assertNotEqual(booted[0], booted[1])

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

        self.assertEqual(first, second)
        build.assert_called_once()
        self.assertTrue(first.endswith(binding._FREEDOS_IMAGE_NAME))

    def test_zero_configuration_layers_the_system_rather_than_using_it(self):
        # Every guest session shares one built image, so none of them
        # may write into it: the drive is layered, and the work drive
        # lands beside it as the guest's second disk — D:.
        backend = binding.suite_backend(self.exe)
        with mock.patch.object(binding, "_cached_default_image",
                               return_value="SYSTEM.QCOW2"):
            document, key = backend._blueprint("work")

        drives = document[0]["drives"]
        self.assertEqual(drives["hdd0"]["materialize"], "difference")
        self.assertEqual(drives["hdd0"]["location"], {"local": "SYSTEM.QCOW2"})
        self.assertEqual(document[0]["boot"], ["hdd0"])
        # The slot, which authoring decides; what the guest calls it is
        # read off the created machine and belongs to integration.
        self.assertEqual(key, "hdd1")
        self.assertEqual(drives["hdd1"]["name"], binding._WORK_MEDIA_NAME)

    def test_runs_suite_through_reliquary(self):
        expected = tuple(EMPTY_RUN_OUTPUT.splitlines())
        with self._fake_machine(return_value=expected) as guest_exec:
            backend = binding.suite_backend(self.exe, boot_image=self.image)
            backend.start_guest()
            try:
                self.assertEqual(backend.run_all(), [])
            finally:
                backend.stop_guest()
        guest_exec.assert_called_once_with(
            "C:\\SUITE.EXE -v",
            machine="testaferro-0", context=mock.ANY, timeout=mock.ANY)

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
                self.assertTrue(backend.run_test("Vring", "Wraps").passed)
            finally:
                backend.stop_guest()
        guest_exec.assert_called_once_with(
            "C:\\SUITE.EXE -v -sg Vring -sn Wraps",
            machine="testaferro-0", context=mock.ANY, timeout=mock.ANY)

    def test_the_nearest_speaker_sets_the_guest_command_timeout(self):
        # The call speaks about this run and a declaration about the
        # environment, so the call wins; absent both, the default.
        declared = environments.EnvironmentSpec({}, timeout=7)

        self.assertEqual(
            binding.suite_backend(self.exe, boot_image=self.image,
                                  timeout=3)._timeout, 3)
        self.assertEqual(
            binding.suite_backend(self.exe,
                                  machine_config=declared)._timeout, 7)
        self.assertEqual(
            binding.suite_backend(self.exe, machine_config=declared,
                                  timeout=3)._timeout, 3)
        self.assertEqual(
            binding.suite_backend(self.exe,
                                  boot_image=self.image)._timeout,
            binding._DEFAULT_TIMEOUT)

    def test_enumerator_forwards_to_suite_backend(self):
        with self._fake_machine() as guest_exec:
            backend = binding.suite_backend(
                self.exe,
                enumerator=lambda: cpputest.parse_list("Vring.Wraps"))
            ids = backend.list_tests()
        self.assertEqual([str(i) for i in ids], ["Vring.Wraps"])
        guest_exec.assert_not_called()


    def test_reliquary_materializes_the_authored_blueprint(self):
        """The blueprint is reliquary's to validate, so let it: every
        test here creates the machine for real, and this one says so."""
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        with self._fake_machine() as guest_exec:
            backend.start_guest()
            try:
                self.assertEqual(backend._machine, "testaferro-0")
            finally:
                backend.stop_guest()
        guest_exec.assert_not_called()


@unittest.skipUnless(RELIQUARY_AVAILABLE, "reliquary is not installed")
class WorkDrivePlacementTests(unittest.TestCase):
    """Slot choice — pure declaration arithmetic, so every case is
    worth stating.

    **The letters left this suite with 0.1.0.dev6.** Slot choice is
    all testaferro decides; the letter is read off a created machine
    (`_placed_letter`, exercised below against a real report), so
    asserting one from declared drives alone would be reinstating the
    inference the pin move retired.
    """

    def test_takes_the_first_disk_of_an_empty_machine(self):
        self.assertEqual(binding._work_slot({}), "hdd0")

    def test_a_floppy_does_not_occupy_a_disk_slot(self):
        self.assertEqual(binding._work_slot({"floppy0": {}}), "hdd0")

    def test_a_cdrom_does_not_occupy_a_disk_slot(self):
        self.assertEqual(binding._work_slot({"cdrom0": {}}), "hdd0")

    def test_follows_a_declared_system_disk(self):
        self.assertEqual(binding._work_slot({"hdd0": {}}), "hdd1")

    def test_follows_several_declared_disks(self):
        self.assertEqual(binding._work_slot({"hdd0": {}, "hdd1": {}}),
                         "hdd2")

    def test_fills_a_gap_rather_than_appending(self):
        # hdd1 declared, hdd0 free: the work drive lands first.
        self.assertEqual(binding._work_slot({"hdd1": {}}), "hdd0")

    def test_undigited_disk_key_counts_as_slot_zero(self):
        self.assertEqual(binding._work_slot({"hdd": {}}), "hdd1")

    def test_a_full_machine_fails_closed_naming_the_reason(self):
        drives = {f"hdd{slot}": {} for slot in range(4)}

        with self.assertRaisesRegex(ValueError, "free slot"):
            binding._work_slot(drives)


@unittest.skipUnless(RELIQUARY_AVAILABLE, "reliquary is not installed")
class PlacedLetterTests(unittest.TestCase):
    """What the guest is told, and where it comes from."""

    def test_the_letter_is_the_one_reliquary_reported(self):
        # Not a rule testaferro keeps a copy of: the report is the
        # only source, so a letter it does not carry is not invented.
        report = {"mapping": {"letters": {
            "A": {"drive": "floppy0", "volume": 0},
            "C": {"drive": "hdd0", "volume": 0},
            "D": {"drive": "hdd1", "volume": 0}}}}

        with mock.patch("reliquary.describe_drives", return_value=report):
            self.assertEqual(
                binding._placed_letter("hdd1", "machine", None), "D")

    def test_a_second_volume_does_not_confuse_the_lookup(self):
        # The case the old inference could not survive: a disk holding
        # two volumes takes two letters, so the work drive behind it
        # sits further along than one-letter-per-disk would place it.
        report = {"mapping": {"letters": {
            "C": {"drive": "hdd0", "volume": 0},
            "D": {"drive": "hdd0", "volume": 1},
            "E": {"drive": "hdd1", "volume": 0}}}}

        with mock.patch("reliquary.describe_drives", return_value=report):
            self.assertEqual(
                binding._placed_letter("hdd1", "machine", None), "E")

    def test_an_unplaced_drive_is_refused_carrying_reliquarys_reason(self):
        # The specific refusal survives the indirection: whoever reads
        # this learns which disk blocked it and why, which a summary
        # ("no letter") would throw away.
        report = {"mapping": {
            "letters": {"A": {"drive": "floppy0", "volume": 0}},
            "undetermined": [
                {"drive": "hdd1", "id": "drive.no-at-rest-access",
                 "reason": "drive hdd0 is a drive image, and the qemu "
                           "adapter cannot read one at rest"}]}}

        with mock.patch("reliquary.describe_drives", return_value=report):
            with self.assertRaises(ValueError) as caught:
                binding._placed_letter("hdd1", "machine", None)

        self.assertIn("cannot read one at rest", str(caught.exception))
        self.assertIn("drive.no-at-rest-access", str(caught.exception))

    def test_a_drive_the_report_never_mentions_fails_closed(self):
        with mock.patch("reliquary.describe_drives",
                        return_value={"mapping": {"letters": {}}}):
            with self.assertRaisesRegex(ValueError, "no letter and no refusal"):
                binding._placed_letter("hdd1", "machine", None)


@unittest.skipUnless(RELIQUARY_AVAILABLE, "reliquary is not installed")
class DeclaredPlacementTests(_BindingFixture):
    """A declared address, through the real session flow.

    `put_files` is stubbed because this fixture's machine has no FAT
    volume to write into; everything around it — when the address is
    settled, whether the map is consulted, what a refusal does — is
    the real path.
    """

    def test_a_declared_location_is_staged_against_and_never_defaulted(self):
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        location="E:\\HARNESS")

        with self._fake_machine(), \
                mock.patch("reliquary.put_files") as put, \
                mock.patch("reliquary.describe_drives") as describe:
            backend.start_guest()
            try:
                self.assertEqual(backend.location, "E:\\HARNESS")
            finally:
                backend.stop_guest()

        self.assertEqual(put.call_args.args[1], "E:\\HARNESS")
        # The map answers "where should this go" — a question already
        # answered, so it is never asked.
        describe.assert_not_called()

    def test_a_declared_location_that_refuses_does_not_fall_back(self):
        # The consumer named that address; smoothing it over with a
        # drive of testaferro's own would hide the one thing they can
        # act on. The refusal is reliquary's own, and it survives.
        refusal = reliquary_dist.PreflightError(
            "E:\\HARNESS: the machine declares no drive at E:",
            rule_id="drive.letter-not-declared")
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        location="E:\\HARNESS")

        with self._fake_machine(), \
                mock.patch("reliquary.put_files", side_effect=refusal):
            with self.assertRaises(reliquary_dist.PreflightError) as caught:
                backend.start_guest()

        self.assertIn("no drive at E:", str(caught.exception))

    def test_the_command_spells_the_address_that_was_staged_against(self):
        expected = tuple(EMPTY_RUN_OUTPUT.splitlines())
        backend = binding.suite_backend(self.exe, boot_image=self.image,
                                        location="E:\\HARNESS")

        with self._fake_machine(return_value=expected) as guest_exec, \
                mock.patch("reliquary.put_files"):
            backend.start_guest()
            try:
                backend.run_all()
            finally:
                backend.stop_guest()

        self.assertTrue(
            guest_exec.call_args.args[0].startswith("E:\\HARNESS\\SUITE.EXE"))

    def test_the_location_refuses_before_a_guest_session(self):
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        with self.assertRaisesRegex(RuntimeError, "has not been placed"):
            backend.location


@unittest.skipUnless(RELIQUARY_AVAILABLE, "reliquary is not installed")
class PlacementTests(unittest.TestCase):
    """Where a run lands, and how that address is spelled (F4).

    The primary path — staging at rest into a drive the machine
    already has — needs a machine with a real FAT volume, which is an
    image this tier may not build (P10). So the provider's two calls
    are stubbed here and the *policy over them* is what is tested:
    which letter is chosen, what is done with a declared one, and
    which failures may fall back. `tests/integration/` proves the same
    policy against a booted guest.
    """

    def _report(self, *letters):
        return {"mapping": {"letters": {
            letter: {"drive": f"hdd{index}", "volume": 0}
            for index, letter in enumerate(letters)}}}

    def test_the_default_location_is_the_last_letter(self):
        # Last rather than first: the system disk is what a machine
        # declares first, and a default must not scatter a stranger's
        # files across somebody's C:\ root.
        with mock.patch("reliquary.describe_drives",
                        return_value=self._report("C", "D")):
            self.assertEqual(binding._default_location("m", None),
                             "D:\\TESTS")

    def test_a_single_drive_machine_takes_that_drive(self):
        with mock.patch("reliquary.describe_drives",
                        return_value=self._report("C")):
            self.assertEqual(binding._default_location("m", None),
                             "C:\\TESTS")

    def test_undetermined_letters_refuse_rather_than_default(self):
        report = {"mapping": {"letters": {}, "undetermined": [
            {"drive": "hdd0", "id": "drive.no-at-rest-access",
             "reason": "the qemu adapter cannot read one at rest"}]}}

        with mock.patch("reliquary.describe_drives", return_value=report):
            with self.assertRaises(ValueError) as caught:
                binding._default_location("m", None)

        # Reliquary's own words, and the way out named.
        self.assertIn("cannot read one at rest", str(caught.exception))
        self.assertIn("location=", str(caught.exception))

    def test_the_program_defaults_to_the_staged_executable(self):
        self.assertEqual(
            binding._resolve_program(None, "D:\\TESTS", "SUITE.EXE"),
            "D:\\TESTS\\SUITE.EXE")

    def test_a_root_location_does_not_double_its_separator(self):
        self.assertEqual(
            binding._resolve_program(None, "C:\\", "SUITE.EXE"),
            "C:\\SUITE.EXE")

    def test_a_declared_program_substitutes_the_location(self):
        self.assertEqual(
            binding._resolve_program("{location}\\RUNNER.EXE", "D:\\TESTS",
                                     "SUITE.EXE"),
            "D:\\TESTS\\RUNNER.EXE")

    def test_a_declared_program_may_name_no_placeholder_at_all(self):
        self.assertEqual(
            binding._resolve_program("C:\\TOOLS\\RUN.EXE", "D:\\TESTS",
                                     "SUITE.EXE"),
            "C:\\TOOLS\\RUN.EXE")

    def test_an_unknown_placeholder_is_refused_naming_the_known_one(self):
        with self.assertRaises(ValueError) as caught:
            binding._resolve_program("{drive}\\RUN.EXE", "D:\\TESTS",
                                     "SUITE.EXE")

        self.assertIn("{drive}", str(caught.exception))
        self.assertIn("{location}", str(caught.exception))


@unittest.skipUnless(RELIQUARY_AVAILABLE, "reliquary is not installed")
class BlueprintAcceptanceTests(_BindingFixture):
    """Documents testaferro authors are ones **reliquary accepts**.

    `BlueprintAuthoringTests` below reads back the dict testaferro
    composed, which proves testaferro consistent with itself and
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
    schema moving under a document testaferro still composes happily.

    Letters are deliberately absent here. The drive report is
    created-only by the provider's own ruling (D83 there) — a dry run
    describes what *would* be built — so `_placed_letter` is proved
    against a real machine in `_BindingFixture` and against reports in
    `PlacedLetterTests`, never here.
    """

    def _dry_plan(self, document):
        """Reliquary's own plan for a document testaferro authored."""
        home = os.path.join(self.tempdir.name, "acceptance")
        blueprints = os.path.join(home, "blueprints")
        os.makedirs(blueprints, exist_ok=True)
        path = os.path.join(blueprints, binding._BLUEPRINT_NAME + ".rlqb")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        outcome = reliquary_dist.create_machine(
            binding._BLUEPRINT_NAME,
            context=binding._context(home, blueprints), dry_run=True)
        self.assertEqual(outcome.operation, "create-machine")
        return outcome.plan

    def _placeholder(self, name, content=b"stand-in for a built image"):
        path = os.path.join(self.tempdir.name, name)
        with open(path, "wb") as handle:
            handle.write(content)
        return path

    def _drive(self, plan, key):
        for entry in plan["drives"]:
            if entry["key"] == key:
                return entry
        self.fail(f"the plan places no drive {key}: {plan['drives']}")

    def test_zero_configuration_document_is_one_reliquary_accepts(self):
        # The case that could not be unit-tested before: a layered
        # system disk, validated without materializing one.
        system = self._placeholder("SYSTEM.QCOW2")
        work = os.path.join(self.tempdir.name, "work")
        os.makedirs(work, exist_ok=True)
        backend = binding.suite_backend(self.exe)
        with mock.patch.object(binding, "_cached_default_image",
                               return_value=system):
            document, key = backend._blueprint(work)

        plan = self._dry_plan(document)

        self.assertEqual(plan["platform"], "dos")
        self.assertEqual(plan["boot"], ["hdd0"])
        system_disk = self._drive(plan, "hdd0")
        self.assertEqual(system_disk["materialize"], "difference")
        self.assertEqual(system_disk["base"], system)
        # The work drive is the one testaferro appended, at the slot
        # `_work_slot` chose, served from the staged directory itself.
        staged = self._drive(plan, key)
        self.assertEqual((staged["medium"], staged["slot"]), ("hdd", 1))
        self.assertEqual(staged["materialize"], "use")
        self.assertEqual(staged["path"], work)

    def test_a_declared_environment_is_carried_through_intact(self):
        # A tester's own machine spec reaches reliquary as written —
        # `platform` among it, which is the provider's word (P2).
        system = self._placeholder("DECLARED.QCOW2")
        work = os.path.join(self.tempdir.name, "declared-work")
        os.makedirs(work, exist_ok=True)
        template = environments.EnvironmentSpec({
            "memory": "64M",
            "drives": {"hdd0": {"name": "system",
                                "location": {"local": system}}},
            "boot": ["hdd0"]})
        backend = binding.suite_backend(self.exe, machine_config=template)

        document, key = backend._blueprint(work)
        plan = self._dry_plan(document)

        self.assertEqual(plan["memory"], 64)
        self.assertEqual(plan["boot"], ["hdd0"])
        self.assertEqual(self._drive(plan, key)["path"], work)

    def test_a_document_naming_absent_media_is_refused_before_anything_runs(self):
        # The preflight earns its place only if it refuses: the boot
        # image names a file nobody staged, and this is where that is
        # found — not in a guest that will not boot.
        backend = binding.suite_backend(self.exe)
        document, _ = backend._blueprint(
            os.path.join(self.tempdir.name, "work"),
            os.path.join(self.tempdir.name, "NOT-STAGED.IMG"))

        with self.assertRaises(reliquary_dist.PreflightError) as caught:
            self._dry_plan(document)

        self.assertIn("NOT-STAGED.IMG", str(caught.exception))


@unittest.skipUnless(RELIQUARY_AVAILABLE, "reliquary is not installed")
class BlueprintAuthoringTests(_BindingFixture):
    """The document testaferro composes, without materializing it."""

    def _document(self, backend, boot=None):
        # `_blueprint` authors over locations that are already staged,
        # so a boot image reaches it as a path rather than being
        # copied out of the backend here.
        document, key = backend._blueprint("/work", boot)
        return document[0], document[1:], key

    def test_zero_configuration_boots_the_chosen_image(self):
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        machine, media, key = self._document(backend, "/guest/boot.img")

        self.assertEqual(machine["type"], "machine")
        self.assertEqual(machine["platform"], "dos")
        self.assertEqual(machine["boot"], ["floppy0"])
        # The staged copy, not the tester's own file (P5).
        self.assertEqual(machine["drives"]["floppy0"]["location"],
                         {"local": "/guest/boot.img"})
        self.assertEqual(machine["drives"]["hdd0"]["location"],
                         {"local": "/work"})
        self.assertEqual((media, key), ([], "hdd0"))

    def test_a_declared_environment_keeps_its_own_boot_arrangement(self):
        template = environments.EnvironmentSpec({
            "memory": "64M",
            "drives": {"hdd0": {"name": "system",
                                "location": {"local": str(self.image)}}},
            "boot": ["hdd0"]})
        backend = binding.suite_backend(self.exe, machine_config=template)

        machine, _, key = self._document(backend)

        # No boot floppy is invented, and the work drive steps aside.
        self.assertNotIn("floppy0", machine["drives"])
        self.assertEqual(machine["boot"], ["hdd0"])
        self.assertEqual(machine["memory"], "64M")
        self.assertEqual(machine["drives"]["hdd1"]["location"],
                         {"local": "/work"})
        self.assertEqual(key, "hdd1")

    def test_media_declared_beside_the_machine_is_carried_through(self):
        spec = {"type": "media", "name": "extra", "location": "x.img"}
        template = environments.EnvironmentSpec(
            {"drives": {"floppy0": {"media": "extra"}}}, [spec])
        backend = binding.suite_backend(self.exe, machine_config=template)

        _, media, _ = self._document(backend)

        self.assertEqual(media, [spec])


@unittest.skipUnless(RELIQUARY_AVAILABLE, "reliquary is not installed")
class SessionLifecycleTests(_BindingFixture):
    """testaferro.start()/stop(): one image choice shared by many
    suites, swept away together."""

    def setUp(self):
        super().setUp()
        self.addCleanup(binding.stop)

    def _run_suite(self, backend):
        return self._guest_homes_seen(backend)[0]

    def test_the_runs_image_is_staged_once_and_shared_by_suites(self):
        binding.start(boot_image=self.image)
        with mock.patch.object(binding, "_cached_default_image") as cached:
            first = self._run_suite(binding.suite_backend(self.exe))
            second = self._run_suite(binding.suite_backend(self.exe))
        cached.assert_not_called()
        self.assertEqual((first[1], second[1]),
                         (b"custom dos", b"custom dos"))
        self.assertNotEqual(first[0], second[0])

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
        if not cached.exists():
            cached.write_bytes(b"not a real system")
            self.addCleanup(cached.unlink)
        binding.start(boot_image=self.image)
        home, image = self._run_suite(binding.suite_backend(self.exe))
        self.assertEqual(image, b"custom dos")

        binding.stop()
        self.assertFalse(os.path.exists(os.path.dirname(home)))
        self.assertTrue(cached.exists())

    def test_kept_guest_homes_survive_the_sweep_and_are_named(self):
        # The exploration option: looking at what the guest was given
        # is the whole point, so the directory has to still be there.
        cache.keep_guest_homes(True)
        self.addCleanup(cache.keep_guest_homes, False)
        self.addCleanup(cache._kept.clear)
        binding.start(boot_image=self.image)
        home, _ = self._run_suite(binding.suite_backend(self.exe))

        binding.stop()

        self.assertTrue(os.path.exists(home))
        self.assertIn(home, cache.kept_guest_homes())

    def test_stop_clear_downloads_removes_the_built_system(self):
        # What it drops is now an install rather than a download, so
        # the next zero-configuration run pays minutes to rebuild it.
        cached = pathlib.Path(cache.cache_root()) / binding._FREEDOS_IMAGE_NAME
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(b"not a real system")

        binding.stop(clear_downloads=True)
        self.assertFalse(cached.exists())

    def test_suite_boot_image_overrides_the_runs_image(self):
        other = pathlib.Path(self.tempdir.name) / "other.img"
        other.write_bytes(b"other dos")
        binding.start(boot_image=self.image)

        _, image = self._run_suite(
            binding.suite_backend(self.exe, boot_image=other))
        self.assertEqual(image, b"other dos")

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

        self.assertIsNone(backend._home)
        self.assertFalse(os.path.exists(home))
        self.assertNotIn(backend, binding._running)

    def test_a_stopped_guest_is_no_longer_tracked(self):
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        with self._fake_machine():
            backend.start_guest()
            self.assertIn(backend, binding._running)
            backend.stop_guest()

        self.assertNotIn(backend, binding._running)

    def test_start_twice_raises_and_stop_is_reentrant(self):
        binding.start()
        with self.assertRaisesRegex(RuntimeError, "already"):
            binding.start()
        binding.stop()
        binding.stop()

    def test_forgotten_stop_is_swept_at_interpreter_exit(self):
        env = dict(os.environ,
                   LOCALAPPDATA=self.tempdir.name,      # Windows
                   XDG_CACHE_HOME=self.tempdir.name)    # elsewhere
        result = subprocess.run(
            [sys.executable, "-c",
             "import testaferro\n"
             "from testaferro import reliquary as binding\n"
             "testaferro.start()\n"
             "print(binding._run_area['dir'])\n"],
            env=env, capture_output=True, text=True, check=True)
        run_dir = result.stdout.strip().splitlines()[-1]

        self.assertTrue(run_dir)
        self.assertFalse(os.path.exists(run_dir))

    def test_package_level_start_stop_delegate(self):
        import testaferro
        with mock.patch.object(binding, "start") as start, \
                mock.patch.object(binding, "stop") as stop:
            testaferro.start(boot_image=self.image)
            testaferro.stop(clear_downloads=True)
        start.assert_called_once_with(boot_image=self.image)
        stop.assert_called_once_with(clear_downloads=True)


if __name__ == "__main__":
    unittest.main()
