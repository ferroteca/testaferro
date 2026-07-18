# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""The QEMU/DOS guest backend, plus the executable interrogation that
selects it.

`suite_backend()` inspects the referenced suite executable: a DOS
program yields a QemuSuiteBackend; a provably non-DOS binary — a
Windows PE such as the suite's host build, a Linux/BSD ELF, a macOS
Mach-O (including universal), an NE/LX/LE, on any architecture — is
rejected before any guest work, with the format and architecture
named. The framework adapter defaults to testaferro.cpputest.

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

from . import cpputest
from .suite import SuiteBackend

# architecture names per format, keyed by each format's machine field
_ELF_MACHINES = {0x03: "x86", 0x28: "ARM", 0x3E: "x86-64",
                 0xB7: "ARM64", 0xF3: "RISC-V"}
_PE_MACHINES = {0x014C: "x86", 0x01C0: "ARM", 0x01C4: "ARM",
                0x8664: "x64", 0xAA64: "ARM64"}
_MACHO_CPUTYPES = {7: "x86", 0x01000007: "x86-64",
                   12: "ARM", 0x0100000C: "ARM64"}


def _elf_format(header):
    """Kind string for an ELF image (Linux and the BSDs; most carry
    the generic System V OS/ABI byte, so no OS is claimed)."""
    arch = None
    if len(header) >= 0x14:
        order = "little" if header[5] == 1 else "big"
        arch = _ELF_MACHINES.get(
            int.from_bytes(header[0x12:0x14], order))
    return (f"an ELF {arch} (Linux/BSD)" if arch
            else "an ELF (Linux/BSD)")


def _macho_format(header):
    """Kind string for a Mach-O image, or None when the magic is
    really something else's."""
    magic = header[:4]
    if magic in (b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"):
        # a universal binary's big-endian arch count is tiny; a Java
        # class file shares the magic but puts its version there
        if (len(header) >= 8
                and int.from_bytes(header[4:8], "big") < 0x40):
            return "a macOS universal (Mach-O)"
        return None
    order = "big" if magic[:2] == b"\xfe\xed" else "little"
    arch = (_MACHO_CPUTYPES.get(int.from_bytes(header[4:8], order))
            if len(header) >= 8 else None)
    return (f"a macOS {arch} (Mach-O)" if arch
            else "a macOS (Mach-O)")


def _mz_extension_format(found):
    """Kind string for the newer-format header an extended MZ file
    points at through e_lfanew. DOS cannot run any of these."""
    if found.startswith(b"PE\0\0"):
        arch = (_PE_MACHINES.get(int.from_bytes(found[4:6], "little"))
                if len(found) >= 6 else None)
        return (f"a Windows {arch} (PE)" if arch
                else "a Windows (PE)")
    for signature, kind in ((b"NE", "a 16-bit Windows or OS/2 (NE)"),
                            (b"LX", "an OS/2 (LX)"),
                            (b"LE", "a linear (LE)")):
        if found.startswith(signature):
            return kind
    return None


def _non_dos_format(exe_path):
    """The provable non-DOS format of an executable ('a Windows x64
    (PE)', 'an ELF x86-64 (Linux/BSD)', ...), or None when the file
    could be a DOS program — plain MZ layout, or no recognizable
    magic at all (a .com image is raw code with no header, so it can
    never be ruled out here)."""
    with open(exe_path, "rb") as f:
        header = f.read(0x40)
        if header[:4] == b"\x7fELF":
            return _elf_format(header)
        if header[:4] in (b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf",
                          b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe",
                          b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"):
            return _macho_format(header)
        if len(header) < 0x40 or header[:2] != b"MZ":
            return None
        if int.from_bytes(header[0x18:0x1A], "little") < 0x40:
            return None
        f.seek(int.from_bytes(header[0x3C:0x40], "little"))
        found = f.read(8)
    return _mz_extension_format(found)


def suite_backend(exe_path, framework=cpputest, enumerator=None,
                  boot_image=None):
    """Interrogate the referenced suite executable and return the
    backend matching its format — a QemuSuiteBackend for a DOS
    program. Raises FileNotFoundError for a missing file and
    ValueError for a provably non-DOS executable (e.g. the suite's
    host build passed by mistake)."""
    exe_path = os.fspath(exe_path)
    kind = _non_dos_format(exe_path)
    if kind is not None:
        raise ValueError(
            f"{os.path.basename(exe_path)} is {kind} executable; "
            "only DOS guest suites are supported")
    return QemuSuiteBackend(exe_path, framework=framework,
                            enumerator=enumerator,
                            boot_image=boot_image)


def _cache_root():
    """testaferro's own filespace: boot-image cache plus the
    disposable per-session quemados homes (under runs/; stale ones
    from killed processes can be deleted freely)."""
    if os.name == "nt":
        base = (os.environ.get("LOCALAPPDATA")
                or os.path.join(os.path.expanduser("~"),
                                "AppData", "Local"))
    else:
        base = (os.environ.get("XDG_CACHE_HOME")
                or os.path.join(os.path.expanduser("~"), ".cache"))
    return os.path.join(base, "testaferro")


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
    root = os.path.join(_cache_root(), "sessions")
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
        cached = os.path.join(_cache_root(), "boot.img")
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
    cached = os.path.join(_cache_root(), "boot.img")
    if not os.path.exists(cached):
        os.makedirs(_cache_root(), exist_ok=True)
        with tempfile.TemporaryDirectory(
                prefix="download-", dir=_cache_root()) as home:
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
        area = _session["dir"] if _session else _cache_root()
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
