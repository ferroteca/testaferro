# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Unit tests for the QEMU backend: executable interrogation and the
testaferro-managed quemados home."""

import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from testaferro import cpputest

QUEMADOS_AVAILABLE = importlib.util.find_spec("quemados") is not None

if QUEMADOS_AVAILABLE:
    from testaferro import qemu
    from testaferro.qemu import QemuSuiteBackend

EMPTY_RUN_OUTPUT = (
    "OK (2 tests, 0 ran, 0 checks, 0 ignored, 2 filtered out, 0 ms)\n")


def _new_format_exe_bytes(signature):
    """An MZ image whose relocation table at 0x40+ marks a
    newer-format header (PE/NE/...) at e_lfanew."""
    header = bytearray(0x40)
    header[0:2] = b"MZ"
    header[0x18:0x1A] = (0x40).to_bytes(2, "little")  # e_lfarlc
    header[0x3C:0x40] = (0x40).to_bytes(4, "little")  # e_lfanew
    return bytes(header) + signature


def _plain_dos_exe_bytes():
    # e_lfarlc below 0x40: original MZ layout, no newer header.
    header = bytearray(0x40)
    header[0:2] = b"MZ"
    header[0x18:0x1A] = (0x1C).to_bytes(2, "little")
    return bytes(header)


@unittest.skipUnless(QUEMADOS_AVAILABLE, "quemados is not installed")
class SuiteBackendDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

    def _exe(self, content):
        path = pathlib.Path(self.tempdir.name) / "SUITE.EXE"
        path.write_bytes(content)
        return path

    def test_rejects_win32_pe_executable(self):
        exe = self._exe(_new_format_exe_bytes(b"PE\0\0"))

        with self.assertRaisesRegex(ValueError, r"Win32 \(PE\)"):
            qemu.suite_backend(exe)

    def test_rejects_win16_ne_executable(self):
        exe = self._exe(_new_format_exe_bytes(b"NE\0\0"))

        with self.assertRaisesRegex(ValueError, r"\(NE\)"):
            qemu.suite_backend(exe)

    def test_missing_executable_raises_at_dispatch(self):
        with self.assertRaises(FileNotFoundError):
            qemu.suite_backend(
                pathlib.Path(self.tempdir.name) / "MISSING.EXE")


class _QemuFixture(unittest.TestCase):
    """Shared setup: a DOS exe, a custom image, and a private cache."""

    def setUp(self):
        import quemados
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        root = pathlib.Path(self.tempdir.name)
        self.exe = root / "SUITE.EXE"
        self.exe.write_bytes(_plain_dos_exe_bytes())
        self.image = root / "custom.img"
        self.image.write_bytes(b"custom dos")
        cache = mock.patch.object(qemu, "_cache_root",
                                  return_value=str(root / "cache"))
        cache.start()
        self.addCleanup(cache.stop)
        self.quemados_home_before = quemados._home

    def _guest_homes_seen(self, backend, calls=1):
        """Run the backend, returning the quemados home (and boot
        image bytes) observed during each guest run."""
        import quemados
        seen = []

        def fake_run(exe_path, args):
            with open(quemados.boot_image(), "rb") as image:
                seen.append((quemados.home(), image.read()))
            return EMPTY_RUN_OUTPUT

        with mock.patch("quemados.run_guest_program",
                        side_effect=fake_run):
            for _ in range(calls):
                backend.run_all()
        return seen

@unittest.skipUnless(QUEMADOS_AVAILABLE, "quemados is not installed")
class QemuSuiteBackendTests(_QemuFixture):
    """Backend behavior inside a provisioned facade session."""

    def test_session_runs_in_fresh_home_with_caller_boot_image(self):
        import quemados
        backend = qemu.suite_backend(self.exe, boot_image=self.image)

        backend.start_session()
        try:
            [(home, image)] = self._guest_homes_seen(backend)
            self.assertTrue(home.startswith(
                os.path.join(qemu._cache_root(), "runs")))
            self.assertEqual(image, b"custom dos")
            self.assertEqual(quemados._home, self.quemados_home_before)
        finally:
            backend.stop_session()
        self.assertFalse(os.path.exists(home))

    def test_each_session_gets_its_own_home(self):
        backend = qemu.suite_backend(self.exe, boot_image=self.image)
        homes = []
        for _ in range(2):
            backend.start_session()
            try:
                [(home, _)] = self._guest_homes_seen(backend)
                homes.append(home)
            finally:
                backend.stop_session()
        self.assertNotEqual(homes[0], homes[1])

    def test_default_boot_image_downloads_once_then_caches(self):
        import quemados

        def fake_download():
            os.makedirs(quemados.dist_dir(), exist_ok=True)
            with open(quemados.boot_image(), "wb") as image:
                image.write(b"freedos")

        backend = qemu.suite_backend(self.exe)
        images = []
        with mock.patch("quemados.download",
                        side_effect=fake_download) as download:
            for _ in range(2):
                backend.start_session()
                try:
                    [(_, image)] = self._guest_homes_seen(backend)
                    images.append(image)
                finally:
                    backend.stop_session()
        self.assertEqual(images, [b"freedos", b"freedos"])
        download.assert_called_once()

    def test_runs_suite_through_quemados(self):
        with mock.patch("quemados.run_guest_program",
                        return_value=EMPTY_RUN_OUTPUT) as run:
            backend = qemu.suite_backend(self.exe, boot_image=self.image)
            backend.start_session()
            try:
                self.assertEqual(backend.run_all(), [])
            finally:
                backend.stop_session()
        run.assert_called_once_with(str(self.exe),
                                    cpputest.run_all_argv())

    def test_enumerator_forwards_to_suite_backend(self):
        with mock.patch("quemados.run_guest_program") as run:
            backend = qemu.suite_backend(
                self.exe,
                enumerator=lambda: cpputest.parse_list("Vring.Wraps"))
            ids = backend.list_tests()
        self.assertEqual([str(i) for i in ids], ["Vring.Wraps"])
        run.assert_not_called()


@unittest.skipUnless(QUEMADOS_AVAILABLE, "quemados is not installed")
class SessionLifecycleTests(_QemuFixture):
    """testaferro.start()/stop(): one image choice shared by many
    suites, swept away together."""

    def setUp(self):
        super().setUp()
        self.addCleanup(qemu.stop)

    def _run_suite(self, backend):
        backend.start_session()
        try:
            return self._guest_homes_seen(backend)[0]
        finally:
            backend.stop_session()

    def test_session_image_is_staged_once_and_shared_by_suites(self):
        qemu.start(boot_image=self.image)
        with mock.patch.object(qemu, "_cached_default_image") as cached:
            first = self._run_suite(qemu.suite_backend(self.exe))
            second = self._run_suite(qemu.suite_backend(self.exe))
        cached.assert_not_called()
        self.assertEqual((first[1], second[1]),
                         (b"custom dos", b"custom dos"))
        self.assertNotEqual(first[0], second[0])

    def test_start_does_not_stage_or_download_by_itself(self):
        with mock.patch.object(qemu, "_cached_default_image") as cached:
            qemu.start()
        cached.assert_not_called()

    def test_stop_sweeps_run_homes_but_keeps_download_cache(self):
        cached = pathlib.Path(qemu._cache_root()) / "boot.img"
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(b"freedos")
        qemu.start()
        home, image = self._run_suite(qemu.suite_backend(self.exe))
        self.assertEqual(image, b"freedos")

        qemu.stop()
        self.assertFalse(os.path.exists(os.path.dirname(home)))
        self.assertTrue(cached.exists())

    def test_stop_clear_downloads_removes_cached_image(self):
        cached = pathlib.Path(qemu._cache_root()) / "boot.img"
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(b"freedos")

        qemu.stop(clear_downloads=True)
        self.assertFalse(cached.exists())

    def test_suite_boot_image_overrides_session_image(self):
        other = pathlib.Path(self.tempdir.name) / "other.img"
        other.write_bytes(b"other dos")
        qemu.start(boot_image=self.image)

        _, image = self._run_suite(
            qemu.suite_backend(self.exe, boot_image=other))
        self.assertEqual(image, b"other dos")

    def test_start_twice_raises_and_stop_is_reentrant(self):
        qemu.start()
        with self.assertRaisesRegex(RuntimeError, "already"):
            qemu.start()
        qemu.stop()
        qemu.stop()

    def test_forgotten_stop_is_swept_at_interpreter_exit(self):
        env = dict(os.environ,
                   LOCALAPPDATA=self.tempdir.name,      # Windows
                   XDG_CACHE_HOME=self.tempdir.name)    # elsewhere
        result = subprocess.run(
            [sys.executable, "-c",
             "import testaferro\n"
             "from testaferro import qemu\n"
             "testaferro.start()\n"
             "print(qemu._session['dir'])\n"],
            env=env, capture_output=True, text=True, check=True)
        session_dir = result.stdout.strip().splitlines()[-1]

        self.assertTrue(session_dir)
        self.assertFalse(os.path.exists(session_dir))

    def test_package_level_start_stop_delegate(self):
        import testaferro
        with mock.patch.object(qemu, "start") as start, \
                mock.patch.object(qemu, "stop") as stop:
            testaferro.start(boot_image=self.image)
            testaferro.stop(clear_downloads=True)
        start.assert_called_once_with(boot_image=self.image)
        stop.assert_called_once_with(clear_downloads=True)


if __name__ == "__main__":
    unittest.main()
