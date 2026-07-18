# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""The QEMU/DOS guest binding.

`suite_backend()` guards the door with `binfmt.classify()`: a DOS
program — plain MZ or a headerless/.com image — yields a
QemuSuiteBackend; anything else is rejected before any guest work,
with the format and architecture named. The framework adapter
defaults to testaferro.cpputest.

QemuSuiteBackend manages a configured relict Runner on the caller's
behalf. Each facade session runs in a fresh, disposable relict home
under testaferro's cache directory (LOCALAPPDATA or XDG_CACHE_HOME).
Named machine templates are copied into that home so mutable drives
never leak between runs; zero configuration is seeded from the
caller-supplied `boot_image` or a cached FreeDOS image.
"""

from __future__ import annotations

import atexit
import dataclasses
import os
import shutil
import tempfile

import relict

from . import binfmt
from . import cache
from . import cpputest
from .suite import SuiteBackend


def suite_backend(exe_path, framework=cpputest, enumerator=None,
                  boot_image=None, machine_config=None):
    """Interrogate the referenced suite executable and return the
    backend matching its format — a QemuSuiteBackend for a DOS
    program. Raises FileNotFoundError for a missing file and
    ValueError for a provably non-DOS executable (e.g. the suite's
    host build passed by mistake)."""
    exe_path = os.fspath(exe_path)
    fmt = binfmt.classify(exe_path)
    if fmt.platform != "dos":
        raise ValueError(
            f"{os.path.basename(exe_path)} is {fmt.kind} executable; "
            "only DOS guest suites are supported")
    if machine_config is not None:
        from .machines import _coerce_machine_config

        machine_config = _coerce_machine_config(machine_config)
        if machine_config.platform != "dos":
            raise ValueError(
                "the QEMU/DOS binding requires a DOS machine config, "
                f"not {machine_config.platform!r}")
    if boot_image is not None and machine_config is not None:
        raise TypeError("boot_image and machine_config cannot be combined")
    return QemuSuiteBackend(exe_path, framework=framework,
                            enumerator=enumerator,
                            boot_image=boot_image,
                            machine_config=machine_config)


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
    through relict.download() (FreeDOS) on first use."""
    cached = os.path.join(cache.cache_root(), "boot.img")
    if not os.path.exists(cached):
        os.makedirs(cache.cache_root(), exist_ok=True)
        with tempfile.TemporaryDirectory(
                prefix="download-", dir=cache.cache_root()) as home:
            relict.download(home=home)
            shutil.copy(
                os.path.join(relict.drives_dir(home), "floppy.img"),
                cached + ".part")
        os.replace(cached + ".part", cached)
    return cached


class QemuSuiteBackend(SuiteBackend):
    def __init__(self, exe_path, framework=cpputest, enumerator=None,
                 boot_image=None, machine_config=None):
        self._boot_image = (None if boot_image is None
                            else os.fspath(boot_image))
        self._home = None
        self._runner = None
        self._machine_config = machine_config
        super().__init__(os.fspath(exe_path), run=self._run_in_guest,
                         framework=framework, enumerator=enumerator)

    def start_session(self):
        area = _session["dir"] if _session else cache.cache_root()
        runs = os.path.join(area, "runs")
        os.makedirs(runs, exist_ok=True)
        self._home = tempfile.mkdtemp(prefix="run-", dir=runs)
        drives = os.path.join(self._home, "drives")
        os.makedirs(drives)
        config = self._materialize_config(drives)
        self._runner = relict.Runner(self._home, config)

    def stop_session(self):
        if self._home is not None:
            shutil.rmtree(self._home, ignore_errors=True)
            self._home = None
            self._runner = None

    def _run_in_guest(self, exe_path, args):
        if self._home is None:
            raise RuntimeError("no active session: guest runs happen "
                               "between start_session and stop_session")
        return self._runner.run(exe_path, args)

    def _materialize_config(self, drives):
        """Copy a machine template into this backend session's home.

        Relict mounts configured drive sources in place. Testaferro
        deliberately copies them so a machine declaration is a template,
        never mutable state shared by two guest runs.
        """
        config = self._machine_config or relict.MachineConfig()
        options = {}
        bootable = False
        for key, declaration in config.drives.items():
            source = declaration["source"]
            drive_options = dict(declaration["options"])
            if source is not None:
                target = _materialized_drive_path(drives, key, source)
                if os.path.isdir(source):
                    shutil.copytree(source, target)
                else:
                    shutil.copy2(source, target)
                    bootable = True
            if drive_options:
                options[key] = {"options": drive_options}
        if not bootable:
            source = self._boot_image or (
                _session_image() if _session else _cached_default_image())
            shutil.copy2(source, os.path.join(drives, "floppy.img"))
        return dataclasses.replace(config, drives=options)


def _materialized_drive_path(drives, key, source):
    """The private-home declaration path for one configured source."""
    if os.path.isdir(source):
        return os.path.join(drives, key)
    extension = os.path.splitext(source)[1]
    return os.path.join(drives, key + extension)
