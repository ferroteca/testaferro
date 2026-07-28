# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Executable-format classification for platform dispatch.

`classify()` reads an executable's header and reports which platform
could run it, without importing any runner:

- ``Format("dos", ...)`` — a plain MZ program, or a headerless image
  (`.com`-style raw code carries nothing to prove, so it passes
  through for the guest itself to judge);
- ``Format(None, ...)`` — a provably unsupported binary: PE,
  NE/LX/LE, ELF, Mach-O (including universal).

`kind` always carries the human-readable format-and-architecture
name ('a Windows x64 (PE)', 'an ELF x86-64 (Linux/BSD)', ...) for
error messages, and a future platform extends the classification by
claiming formats currently mapped to None. Stdlib-only: the facade's
dispatch and each platform binding's own guard share it without
pulling in a runner.
"""

from __future__ import annotations

import collections

Format = collections.namedtuple("Format", ["platform", "kind"])

_DOS_MZ = Format("dos", "a DOS MZ")
# The one verdict with nothing behind it: no header, so nothing is
# proven either way and the guest judges. A caller that must tell
# "proven DOS" from "nothing to prove" — a collection scan deciding
# whether to claim a file nobody named — compares against this
# singleton by identity.
HEADERLESS = Format("dos", "a headerless (.com-style)")

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
    """The Format of the newer-format header an extended MZ file
    points at through e_lfanew, or None when none is recognized
    there. DOS runs none of these."""
    if found.startswith(b"PE\0\0"):
        arch = (_PE_MACHINES.get(int.from_bytes(found[4:6], "little"))
                if len(found) >= 6 else None)
        return Format(None, f"a Windows {arch} (PE)" if arch
                      else "a Windows (PE)")
    for signature, kind in ((b"NE", "a 16-bit Windows or OS/2 (NE)"),
                            (b"LX", "an OS/2 (LX)"),
                            (b"LE", "a linear (LE)")):
        if found.startswith(signature):
            return Format(None, kind)
    return None


def classify(exe_path):
    """The Format of the referenced executable: which platform could
    run it (`platform`) and its human-readable kind. Raises
    FileNotFoundError for a missing file; attaches no meaning beyond
    the header — a "dos" verdict means "nothing proves otherwise"."""
    with open(exe_path, "rb") as f:
        header = f.read(0x40)
        if header[:4] == b"\x7fELF":
            return Format(None, _elf_format(header))
        if header[:4] in (b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf",
                          b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe",
                          b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"):
            kind = _macho_format(header)
            return HEADERLESS if kind is None else Format(None, kind)
        if header[:2] != b"MZ":
            return HEADERLESS
        if len(header) < 0x40:
            return _DOS_MZ
        if int.from_bytes(header[0x18:0x1A], "little") < 0x40:
            return _DOS_MZ
        f.seek(int.from_bytes(header[0x3C:0x40], "little"))
        found = f.read(8)
    return _mz_extension_format(found) or _DOS_MZ
