# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Unit tests for the QEMU/Windows 95 binding, driven through a fake
quemados95 injected into sys.modules — the binding's contract with
the runner is exercised without the real (optional) package."""

import importlib
import importlib.util
import os
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

from testaferro import cache

from test_binfmt import new_format_exe_bytes, plain_dos_exe_bytes

QUEMADOS_AVAILABLE = importlib.util.find_spec("quemados") is not None

EMPTY_RUN_OUTPUT = (
    "OK (2 tests, 0 ran, 0 checks, 0 ignored, 2 filtered out, 0 ms)\n")

PE_X86 = b"PE\0\0" + (0x014C).to_bytes(2, "little")

# set by setUpModule: the fake runner and the binding built on it
quemados95 = None
qemu95 = None


def _fake_quemados95():
    """A quemados95 stand-in honoring the contract the binding's
    docstring records: home management, install() building
    dist/hdd.img from the media (content echoes media and key so
    tests can tell installs apart), and a run hook tests patch."""
    module = types.ModuleType("quemados95")
    module._home = None

    def set_home(path):
        module._home = os.path.abspath(path)

    def home():
        return module._home

    def dist_dir():
        return os.path.join(module._home, "dist")

    def hdd_image():
        return os.path.join(dist_dir(), "hdd.img")

    def install(media=None, media_url=None, media_sha256=None,
                product_key=None):
        if media is None and media_url is None:
            raise ValueError("install media is required")
        if media is not None:
            with open(media, "rb") as source:
                content = source.read()
        else:
            content = media_url.encode()
        os.makedirs(dist_dir(), exist_ok=True)
        with open(hdd_image(), "wb") as image:
            image.write(b"installed:" + content + b":"
                        + (product_key or "").encode())

    def run_guest_program(exe_path, args=""):
        raise NotImplementedError("tests patch run_guest_program")

    module.set_home = set_home
    module.home = home
    module.dist_dir = dist_dir
    module.hdd_image = hdd_image
    module.install = install
    module.run_guest_program = run_guest_program
    return module


def setUpModule():
    global quemados95, qemu95
    quemados95 = _fake_quemados95()
    sys.modules["quemados95"] = quemados95
    qemu95 = importlib.import_module("testaferro.qemu95")


def tearDownModule():
    # leave no trace: other test modules probe for the absence of
    # quemados95 (the missing-runner error path)
    sys.modules.pop("testaferro.qemu95", None)
    sys.modules.pop("quemados95", None)
    import testaferro
    if hasattr(testaferro, "qemu95"):
        del testaferro.qemu95


class Qemu95DispatchTests(unittest.TestCase):
    """The guard on qemu95.suite_backend; the per-format naming
    matrix lives with the classifier in test_binfmt."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

    def _exe(self, content):
        path = pathlib.Path(self.tempdir.name) / "SUITE.EXE"
        path.write_bytes(content)
        return path

    def test_accepts_windows_pe_x86_executable(self):
        exe = self._exe(new_format_exe_bytes(PE_X86))

        self.assertIsNotNone(qemu95.suite_backend(exe))

    def test_accepts_dos_mz_for_compatibility_testing(self):
        exe = self._exe(plain_dos_exe_bytes())

        self.assertIsNotNone(qemu95.suite_backend(exe))

    def test_rejects_pe_on_another_architecture(self):
        machine = (0x8664).to_bytes(2, "little")
        exe = self._exe(new_format_exe_bytes(b"PE\0\0" + machine))

        with self.assertRaisesRegex(ValueError,
                                    r"Windows x64 \(PE\).*cannot run"):
            qemu95.suite_backend(exe)

    def test_missing_executable_raises_at_dispatch(self):
        with self.assertRaises(FileNotFoundError):
            qemu95.suite_backend(
                pathlib.Path(self.tempdir.name) / "MISSING.EXE")


class _Qemu95Fixture(unittest.TestCase):
    """Shared setup: a Win95 exe, fake install media, and a private
    cache."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        root = pathlib.Path(self.tempdir.name)
        self.exe = root / "SUITE.EXE"
        self.exe.write_bytes(new_format_exe_bytes(PE_X86))
        self.iso = root / "win95.iso"
        self.iso.write_bytes(b"win95 media")
        cache_patch = mock.patch.object(
            cache, "cache_root", return_value=str(root / "cache"))
        cache_patch.start()
        self.addCleanup(cache_patch.stop)
        self.quemados95_home_before = quemados95._home
        self.addCleanup(qemu95.stop)

    def _guest_homes_seen(self, backend, calls=1):
        """Run the backend, returning the quemados95 home (and
        hard-disk image bytes) observed during each guest run."""
        seen = []

        def fake_run(exe_path, args):
            with open(quemados95.hdd_image(), "rb") as image:
                seen.append((quemados95.home(), image.read()))
            return EMPTY_RUN_OUTPUT

        with mock.patch.object(quemados95, "run_guest_program",
                               side_effect=fake_run):
            for _ in range(calls):
                backend.run_all()
        return seen


class Qemu95SuiteBackendTests(_Qemu95Fixture):
    """Backend behavior inside a provisioned facade session."""

    def test_session_runs_in_fresh_home_with_installed_image(self):
        backend = qemu95.suite_backend(self.exe,
                                       install_media=self.iso,
                                       product_key="KEY-123")

        backend.start_session()
        try:
            [(home, image)] = self._guest_homes_seen(backend)
            self.assertTrue(home.startswith(os.path.join(
                cache.cache_root(), "win95", "runs")))
            self.assertEqual(image, b"installed:win95 media:KEY-123")
            self.assertEqual(quemados95._home,
                             self.quemados95_home_before)
        finally:
            backend.stop_session()
        self.assertFalse(os.path.exists(home))

    def test_install_happens_once_then_caches(self):
        backend = qemu95.suite_backend(self.exe,
                                       install_media=self.iso)
        original = quemados95.install
        images = []
        with mock.patch.object(quemados95, "install",
                               side_effect=original) as install:
            for _ in range(2):
                backend.start_session()
                try:
                    [(_, image)] = self._guest_homes_seen(backend)
                    images.append(image)
                finally:
                    backend.stop_session()
        self.assertEqual(images, [b"installed:win95 media:",
                                  b"installed:win95 media:"])
        install.assert_called_once()

    def test_media_url_is_accepted_in_place_of_a_local_iso(self):
        backend = qemu95.suite_backend(
            self.exe, media_url="https://example.test/win95.iso",
            media_sha256="ab" * 32)

        backend.start_session()
        try:
            [(_, image)] = self._guest_homes_seen(backend)
        finally:
            backend.stop_session()
        self.assertEqual(
            image, b"installed:https://example.test/win95.iso:")

    def test_media_url_requires_its_hash(self):
        with self.assertRaisesRegex(ValueError, "media_sha256"):
            qemu95.suite_backend(
                self.exe, media_url="https://example.test/win95.iso")
        with self.assertRaisesRegex(ValueError, "media_sha256"):
            qemu95.start(media_url="https://example.test/win95.iso")

    def test_media_hash_keys_the_cache_not_the_url(self):
        # same URL, different claimed content: two distinct installs
        url = "https://example.test/win95.iso"
        for sha256 in ("ab" * 32, "cd" * 32):
            backend = qemu95.suite_backend(self.exe, media_url=url,
                                           media_sha256=sha256)
            backend.start_session()
            try:
                self._guest_homes_seen(backend)
            finally:
                backend.stop_session()
        win95_cache = pathlib.Path(cache.cache_root()) / "win95"
        cached = [name for name in os.listdir(win95_cache)
                  if name.startswith("installed-")]
        self.assertEqual(len(cached), 2)

    def test_ready_hdd_image_is_used_without_any_install(self):
        ready = pathlib.Path(self.tempdir.name) / "ready.img"
        ready.write_bytes(b"ready image")
        backend = qemu95.suite_backend(self.exe, hdd_image=ready)

        with mock.patch.object(quemados95, "install") as install:
            backend.start_session()
            try:
                [(_, image)] = self._guest_homes_seen(backend)
            finally:
                backend.stop_session()
        self.assertEqual(image, b"ready image")
        install.assert_not_called()

    def test_ready_hdd_image_rejects_install_media_options(self):
        ready = pathlib.Path(self.tempdir.name) / "ready.img"
        ready.write_bytes(b"ready image")

        with self.assertRaisesRegex(ValueError, "hdd_image"):
            qemu95.suite_backend(self.exe, hdd_image=ready,
                                 install_media=self.iso)
        with self.assertRaisesRegex(ValueError, "hdd_image"):
            qemu95.start(hdd_image=ready, product_key="KEY")

    def test_product_key_shapes_the_cache_key(self):
        seen = []
        for key in ("KEY-A", "KEY-B"):
            backend = qemu95.suite_backend(self.exe,
                                           install_media=self.iso,
                                           product_key=key)
            backend.start_session()
            try:
                seen.append(self._guest_homes_seen(backend)[0][1])
            finally:
                backend.stop_session()
        self.assertNotEqual(seen[0], seen[1])
        win95_cache = pathlib.Path(cache.cache_root()) / "win95"
        cached = [name for name in os.listdir(win95_cache)
                  if name.startswith("installed-")]
        self.assertEqual(len(cached), 2)

    def test_media_is_required_without_a_session(self):
        backend = qemu95.suite_backend(self.exe)

        with self.assertRaisesRegex(ValueError, "install_media"):
            backend.start_session()


class Win95SessionLifecycleTests(_Qemu95Fixture):
    """qemu95.start()/stop(): one media choice shared by many
    suites, swept away together — the installed-image cache kept."""

    def _run_suite(self, backend):
        backend.start_session()
        try:
            return self._guest_homes_seen(backend)[0]
        finally:
            backend.stop_session()

    def test_session_media_serves_every_suite(self):
        qemu95.start(install_media=self.iso, product_key="KEY")

        first = self._run_suite(qemu95.suite_backend(self.exe))
        second = self._run_suite(qemu95.suite_backend(self.exe))
        self.assertEqual((first[1], second[1]),
                         (b"installed:win95 media:KEY",) * 2)
        self.assertNotEqual(first[0], second[0])

    def test_suite_media_overrides_session_media(self):
        other = pathlib.Path(self.tempdir.name) / "other.iso"
        other.write_bytes(b"other media")
        qemu95.start(install_media=self.iso)

        _, image = self._run_suite(
            qemu95.suite_backend(self.exe, install_media=other))
        self.assertEqual(image, b"installed:other media:")

    def test_session_ready_hdd_image_serves_every_suite(self):
        ready = pathlib.Path(self.tempdir.name) / "ready.img"
        ready.write_bytes(b"ready image")
        qemu95.start(hdd_image=ready)

        _, image = self._run_suite(qemu95.suite_backend(self.exe))
        self.assertEqual(image, b"ready image")

    def test_suite_ready_hdd_image_overrides_session_media(self):
        ready = pathlib.Path(self.tempdir.name) / "ready.img"
        ready.write_bytes(b"ready image")
        qemu95.start(install_media=self.iso)

        _, image = self._run_suite(
            qemu95.suite_backend(self.exe, hdd_image=ready))
        self.assertEqual(image, b"ready image")

    def test_stop_keeps_installed_cache_unless_cleared(self):
        qemu95.start(install_media=self.iso)
        home, _ = self._run_suite(qemu95.suite_backend(self.exe))
        win95_cache = pathlib.Path(cache.cache_root()) / "win95"
        [cached] = [name for name in os.listdir(win95_cache)
                    if name.startswith("installed-")]

        qemu95.stop()
        self.assertFalse(os.path.exists(os.path.dirname(home)))
        self.assertTrue((win95_cache / cached).exists())

        qemu95.stop(clear_downloads=True)
        self.assertFalse((win95_cache / cached).exists())

    def test_start_twice_raises_and_stop_is_reentrant(self):
        qemu95.start(install_media=self.iso)
        with self.assertRaisesRegex(RuntimeError, "already"):
            qemu95.start()
        qemu95.stop()
        qemu95.stop()

    @unittest.skipUnless(QUEMADOS_AVAILABLE,
                         "quemados is not installed")
    def test_package_stop_sweeps_win95_session_but_not_its_cache(self):
        import testaferro
        from testaferro import qemu

        with mock.patch.object(qemu, "stop") as dos_stop, \
                mock.patch.object(qemu95, "stop") as win95_stop:
            testaferro.stop(clear_downloads=True)
        dos_stop.assert_called_once_with(clear_downloads=True)
        win95_stop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
