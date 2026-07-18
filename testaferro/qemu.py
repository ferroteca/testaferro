# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""The QEMU/DOS guest binding.

`suite_backend()` guards the door with `binfmt.classify()`: a DOS
program — plain MZ or a headerless/.com image — yields a
QemuSuiteBackend; anything else is rejected before any guest work,
with the format and architecture named. The framework adapter
defaults to testaferro.cpputest.

QemuSuiteBackend manages the quemados runner entirely on the caller's
behalf. Each facade session runs in a fresh, disposable quemados home
under testaferro's cache directory (LOCALAPPDATA or XDG_CACHE_HOME),
seeded with the caller's `boot_image` or with a cached copy of the
FreeDOS image quemados downloads on first use. The process-global
quemados home is set only for the duration of each guest run and then
restored, so co-resident direct quemados users are unaffected.

Only this module imports quemados; the generic SuiteBackend remains
the seam for composing any other runner callable.
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile

import quemados

from . import binfmt
from . import cache
from . import cpputest
from .suite import SuiteBackend


def suite_backend(exe_path, framework=cpputest, enumerator=None,
                  boot_image=None):
    """Interrogate the referenced suite executable and return the
    backend matching its format — a QemuSuiteBackend for a DOS
    program. Raises FileNotFoundError for a missing file and
    ValueError for a provably non-DOS executable (e.g. the suite's
    host build passed by mistake)."""
    exe_path = os.fspath(exe_path)
    fmt = binfmt.classify(exe_path)
    if fmt.guest != "dos":
        raise ValueError(
            f"{os.path.basename(exe_path)} is {fmt.kind} executable; "
            "only DOS guest suites are supported")
    return QemuSuiteBackend(exe_path, framework=framework,
                            enumerator=enumerator,
                            boot_image=boot_image)


# The active testaferro session opened by start(), or None: its
# disposable directory (holding the staged boot image and every run
# home) plus the recorded image choice, staged lazily on first use.
_session = None


def start(boot_image=None):
    """Open a testaferro session: one boot-image choice serving every
    suite until stop(). The image itself — `boot_image` or the cached
    default — is staged lazily on the first guest use, so calling
    this from a conftest costs nothing when no guest test runs. An
    atexit failsafe sweeps the session if stop() is never called."""
    global _session
    if _session is not None:
        raise RuntimeError("a testaferro session is already active")
    root = os.path.join(cache.cache_root(), "sessions")
    os.makedirs(root, exist_ok=True)
    _session = {
        "dir": tempfile.mkdtemp(prefix="session-", dir=root),
        "boot_image": (None if boot_image is None
                       else os.fspath(boot_image)),
    }
    # failsafe: sweep at interpreter exit if the caller never calls
    # stop(); an explicit stop() unregisters this again
    atexit.register(stop)


def stop(clear_downloads=False):
    """Close the session opened by start(), sweeping its whole area —
    staged image and every run home. Safe to call with no session
    active. `clear_downloads=True` also removes the cached default
    boot image, forcing a fresh download next time."""
    global _session
    atexit.unregister(stop)
    if _session is not None:
        shutil.rmtree(_session["dir"], ignore_errors=True)
        _session = None
    if clear_downloads:
        cached = os.path.join(cache.cache_root(), "boot.img")
        for path in (cached, cached + ".part"):
            if os.path.exists(path):
                os.remove(path)


def _session_image():
    """The active session's staged boot image, staging it on first
    use from the recorded choice or the cached default."""
    image = os.path.join(_session["dir"], "boot.img")
    if not os.path.exists(image):
        shutil.copy(_session["boot_image"] or _cached_default_image(),
                    image)
    return image


def _cached_default_image():
    """testaferro's cached copy of the default boot image, obtained
    through quemados.download() (FreeDOS) on first use."""
    cached = os.path.join(cache.cache_root(), "boot.img")
    if not os.path.exists(cached):
        os.makedirs(cache.cache_root(), exist_ok=True)
        with tempfile.TemporaryDirectory(
                prefix="download-", dir=cache.cache_root()) as home:
            previous = quemados._home
            quemados.set_home(home)
            try:
                quemados.download()
                shutil.copy(quemados.boot_image(), cached + ".part")
            finally:
                quemados._home = previous
        os.replace(cached + ".part", cached)
    return cached


class QemuSuiteBackend(SuiteBackend):
    def __init__(self, exe_path, framework=cpputest, enumerator=None,
                 boot_image=None):
        self._boot_image = (None if boot_image is None
                            else os.fspath(boot_image))
        self._home = None
        super().__init__(os.fspath(exe_path), run=self._run_in_guest,
                         framework=framework, enumerator=enumerator)

    def start_session(self):
        area = _session["dir"] if _session else cache.cache_root()
        runs = os.path.join(area, "runs")
        os.makedirs(runs, exist_ok=True)
        self._home = tempfile.mkdtemp(prefix="run-", dir=runs)
        dist = os.path.join(self._home, "dist")
        os.makedirs(dist)
        source = self._boot_image or (
            _session_image() if _session else _cached_default_image())
        shutil.copy(source, os.path.join(dist, "boot.img"))

    def stop_session(self):
        if self._home is not None:
            shutil.rmtree(self._home, ignore_errors=True)
            self._home = None

    def _run_in_guest(self, exe_path, args):
        if self._home is None:
            raise RuntimeError("no active session: guest runs happen "
                               "between start_session and stop_session")
        # save/restore the raw value (set_home cannot express None);
        # quemados's own tests bracket _home the same way
        previous = quemados._home
        quemados.set_home(self._home)
        try:
            return quemados.run_guest_program(exe_path, args)
        finally:
            quemados._home = previous
