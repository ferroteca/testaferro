# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Unit tests for executable-format classification."""

import pathlib
import tempfile
import unittest

from testaferro import binfmt


def new_format_exe_bytes(signature):
    """An MZ image whose relocation table at 0x40+ marks a
    newer-format header (PE/NE/...) at e_lfanew."""
    header = bytearray(0x40)
    header[0:2] = b"MZ"
    header[0x18:0x1A] = (0x40).to_bytes(2, "little")  # e_lfarlc
    header[0x3C:0x40] = (0x40).to_bytes(4, "little")  # e_lfanew
    return bytes(header) + signature


def plain_dos_exe_bytes():
    # e_lfarlc below 0x40: original MZ layout, no newer header.
    header = bytearray(0x40)
    header[0:2] = b"MZ"
    header[0x18:0x1A] = (0x1C).to_bytes(2, "little")
    return bytes(header)


class ClassifyTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

    def _classify(self, content):
        path = pathlib.Path(self.tempdir.name) / "SUITE.EXE"
        path.write_bytes(content)
        return binfmt.classify(path)

    def test_plain_mz_is_a_dos_program(self):
        fmt = self._classify(plain_dos_exe_bytes())

        self.assertEqual(fmt.platform, "dos")
        self.assertIn("MZ", fmt.kind)

    def test_headerless_image_like_a_com_program_is_dos(self):
        # .com-style raw 8086 code has no magic at all — nothing to
        # prove, so it must pass through for the guest to judge
        fmt = self._classify(b"\xb4\x09\xba\x00\x01\xcd\x21\xc3")

        self.assertEqual(fmt.platform, "dos")

    def test_pe_x86_is_unsupported(self):
        machine = (0x014C).to_bytes(2, "little")
        fmt = self._classify(new_format_exe_bytes(b"PE\0\0" + machine))

        self.assertEqual(fmt, (None, "a Windows x86 (PE)"))

    def test_pe_without_architecture_is_unsupported(self):
        fmt = self._classify(new_format_exe_bytes(b"PE\0\0"))

        self.assertEqual(fmt, (None, "a Windows (PE)"))

    def test_pe_x64_is_unsupported(self):
        machine = (0x8664).to_bytes(2, "little")
        fmt = self._classify(new_format_exe_bytes(b"PE\0\0" + machine))

        self.assertEqual(fmt, (None, "a Windows x64 (PE)"))

    def test_win16_ne_is_unsupported(self):
        fmt = self._classify(new_format_exe_bytes(b"NE\0\0"))

        self.assertEqual(fmt.platform, None)
        self.assertIn("(NE)", fmt.kind)

    def test_linux_bsd_elf_is_unsupported(self):
        header = bytearray(0x40)
        header[0:4] = b"\x7fELF"
        header[4] = 2                                   # 64-bit
        header[5] = 1                                   # little-endian
        header[0x12:0x14] = (0x3E).to_bytes(2, "little")  # x86-64
        fmt = self._classify(bytes(header))

        self.assertEqual(fmt, (None, "an ELF x86-64 (Linux/BSD)"))

    def test_elf_arm64_is_unsupported(self):
        header = bytearray(0x40)
        header[0:4] = b"\x7fELF"
        header[4] = 2
        header[5] = 1
        header[0x12:0x14] = (0xB7).to_bytes(2, "little")  # aarch64
        fmt = self._classify(bytes(header))

        self.assertEqual(fmt, (None, "an ELF ARM64 (Linux/BSD)"))

    def test_macos_macho_is_unsupported(self):
        # little-endian 64-bit Mach-O, cputype arm64
        header = (b"\xcf\xfa\xed\xfe"
                  + (0x0100000C).to_bytes(4, "little"))
        fmt = self._classify(header + bytes(0x40 - len(header)))

        self.assertEqual(fmt, (None, "a macOS ARM64 (Mach-O)"))

    def test_macos_universal_binary_is_unsupported(self):
        # fat header: big-endian magic + tiny arch count (a Java
        # class file shares the magic but never a small count there)
        header = b"\xca\xfe\xba\xbe" + (2).to_bytes(4, "big")
        fmt = self._classify(header + bytes(0x40 - len(header)))

        self.assertEqual(fmt, (None, "a macOS universal (Mach-O)"))

    def test_fat_magic_with_large_count_field_passes_through(self):
        # cafebabe + a value far too large for a universal binary's
        # arch count: not provably Mach-O, so the guest judges
        header = b"\xca\xfe\xba\xbe" + (0x00010000).to_bytes(4, "big")
        fmt = self._classify(header + bytes(0x40 - len(header)))

        self.assertEqual(fmt.platform, "dos")

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            binfmt.classify(
                pathlib.Path(self.tempdir.name) / "MISSING.EXE")


if __name__ == "__main__":
    unittest.main()
