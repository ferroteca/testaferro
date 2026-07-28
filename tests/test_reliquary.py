# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
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
    from testaferro import environments
    from testaferro import reliquary as binding

EMPTY_RUN_OUTPUT = (
    "OK (2 tests, 0 ran, 0 checks, 0 ignored, 2 filtered out, 0 ms)\n")
RUN_ONE_OUTPUT = (
    "TEST(Vring, Wraps) - 0 ms\n"
    "OK (2 tests, 1 ran, 1 checks, 0 ignored, 1 filtered out, 0 ms)\n")


def _drive_state(key):
    """A blueprint drive key as reliquary records it on a machine."""
    medium = key.rstrip("0123456789")
    return {"medium": medium, "slot": int(key[len(medium):] or 0)}


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
        declaring its own home or boot drive fails loudly."""
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
        not — `start_machine` starts a guest for real (P10) — so the
        three calls that need a running machine are stubbed and
        nothing else.

        Creation stays cheap only while every drive's media is `use`
        (attached in place). A blueprint declaring a blank (`size`)
        makes reliquary reach for an external image tool, which belongs
        in an integration test instead.
        """
        return _patched(
            mock.patch("reliquary.start_machine"),
            mock.patch("reliquary.stop_machine"),
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

    def test_the_suite_executable_is_staged_on_a_work_drive(self):
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
                self.assertEqual(backend._letter, "C")
            finally:
                backend.stop_guest()

    def test_default_boot_image_downloads_once_then_caches(self):
        def fake_fetch_media(name, context):
            payload = os.path.join(context.home_dir, "payload.img")
            with open(payload, "wb") as image:
                image.write(b"freedos")
            return payload

        backend = binding.suite_backend(self.exe)
        with mock.patch("reliquary.fetch_media",
                        side_effect=fake_fetch_media) as fetch_media:
            images = [self._guest_homes_seen(backend)[0][1]
                      for _ in range(2)]
        self.assertEqual(images, [b"freedos", b"freedos"])
        fetch_media.assert_called_once()

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
    """Slot choice and the DOS letter that follows from it — pure
    declaration arithmetic, so every case is worth stating."""

    def test_takes_the_first_disk_of_an_empty_machine(self):
        self.assertEqual(binding._work_drive({}), ("hdd0", "C"))

    def test_a_floppy_does_not_occupy_a_disk_slot(self):
        self.assertEqual(binding._work_drive({"floppy0": {}}), ("hdd0", "C"))

    def test_a_cdrom_does_not_shift_the_letter(self):
        # CD-ROMs take the letters after the last disk, so a declared
        # cdrom leaves the work drive at C:.
        self.assertEqual(binding._work_drive({"cdrom0": {}}), ("hdd0", "C"))

    def test_follows_a_declared_system_disk(self):
        self.assertEqual(binding._work_drive({"hdd0": {}}), ("hdd1", "D"))

    def test_follows_several_declared_disks(self):
        self.assertEqual(binding._work_drive({"hdd0": {}, "hdd1": {}}),
                         ("hdd2", "E"))

    def test_fills_a_gap_and_letters_it_by_position(self):
        # hdd1 declared, hdd0 free: the work drive lands first and is
        # therefore C:, pushing the declared disk to D:.
        self.assertEqual(binding._work_drive({"hdd1": {}}), ("hdd0", "C"))

    def test_undigited_disk_key_counts_as_slot_zero(self):
        self.assertEqual(binding._work_drive({"hdd": {}}), ("hdd1", "D"))

    def test_a_full_machine_fails_closed_naming_the_reason(self):
        drives = {f"hdd{slot}": {} for slot in range(4)}

        with self.assertRaisesRegex(ValueError, "free slot"):
            binding._work_drive(drives)

    def test_the_letter_agrees_with_reliquarys_own_assignment(self):
        """Guard the duplication, as far as reliquary will vouch for it.

        `_work_drive` derives the guest letter from a rule reliquary
        owns, and since 0.1.0.dev3 reliquary answers for fewer drives
        than testaferro asks about: the first hard disk is C: and no
        later disk has a determined letter, because volume count is
        not a declared fact. Where it does answer, this copy must
        agree — the day that rule changes this fails here rather than
        by running a suite off the wrong drive. Where it does not,
        testaferro is assuming one volume per declared disk, and the
        least this can hold it to is that the assumed letter never
        collides with one reliquary has already placed.
        """
        from reliquary import platform_dos

        for declared in ({}, {"floppy0": {}}, {"floppy0": {}, "hdd0": {}},
                         {"hdd0": {}}, {"hdd1": {}}, {"hdd0": {}, "hdd1": {}},
                         {"cdrom0": {}}, {"hdd0": {}, "cdrom0": {}}):
            with self.subTest(declared=sorted(declared)):
                key, letter = binding._work_drive(declared)
                state = {name: _drive_state(name)
                         for name in (*declared, key)}
                determined = platform_dos.drive_letters(state)
                if key in platform_dos.undetermined_letters(state):
                    self.assertNotIn(letter, determined)
                else:
                    self.assertEqual(determined.get(letter), key)


@unittest.skipUnless(RELIQUARY_AVAILABLE, "reliquary is not installed")
class BlueprintAuthoringTests(_BindingFixture):
    """The document testaferro composes, without materializing it."""

    def _document(self, backend):
        document, letter = backend._blueprint("/work")
        return document[0], document[1:], letter

    def test_zero_configuration_boots_the_chosen_image(self):
        backend = binding.suite_backend(self.exe, boot_image=self.image)

        machine, media, letter = self._document(backend)

        self.assertEqual(machine["type"], "machine")
        self.assertEqual(machine["platform"], "dos")
        self.assertEqual(machine["boot"], ["floppy0"])
        self.assertEqual(machine["drives"]["floppy0"]["location"],
                         {"local": str(self.image)})
        self.assertEqual(machine["drives"]["hdd0"]["location"],
                         {"local": "/work"})
        self.assertEqual((media, letter), ([], "C"))

    def test_a_declared_environment_keeps_its_own_boot_arrangement(self):
        template = environments.EnvironmentSpec({
            "memory": "64M",
            "drives": {"hdd0": {"name": "system",
                                "location": {"local": str(self.image)}}},
            "boot": ["hdd0"]})
        backend = binding.suite_backend(self.exe, machine_config=template)

        machine, _, letter = self._document(backend)

        # No boot floppy is invented, and the work drive steps aside.
        self.assertNotIn("floppy0", machine["drives"])
        self.assertEqual(machine["boot"], ["hdd0"])
        self.assertEqual(machine["memory"], "64M")
        self.assertEqual(machine["drives"]["hdd1"]["location"],
                         {"local": "/work"})
        self.assertEqual(letter, "D")

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

    def test_stop_sweeps_run_homes_but_keeps_download_cache(self):
        cached = pathlib.Path(cache.cache_root()) / "boot.img"
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(b"freedos")
        binding.start()
        home, image = self._run_suite(binding.suite_backend(self.exe))
        self.assertEqual(image, b"freedos")

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

    def test_stop_clear_downloads_removes_cached_image(self):
        cached = pathlib.Path(cache.cache_root()) / "boot.img"
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(b"freedos")

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
