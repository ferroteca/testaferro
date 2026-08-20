# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Unit tests for executable-format classification."""

import pytest

from testaferro import binfmt

from helpers import new_format_exe_bytes, plain_dos_exe_bytes


class ClassifyTests:
    def _classify(self, tmp_path, content):
        path = tmp_path / "SUITE.EXE"
        path.write_bytes(content)
        return binfmt.classify(path)

    def test_plain_mz_is_a_dos_program(self, tmp_path):
        fmt = self._classify(tmp_path, plain_dos_exe_bytes())

        assert fmt.platform == "dos"
        assert "MZ" in fmt.kind

    def test_headerless_image_like_a_com_program_is_dos(self, tmp_path):
        # .com-style raw 8086 code has no magic at all — nothing to
        # prove, so it must pass through for the guest to judge
        fmt = self._classify(tmp_path, b"\xb4\x09\xba\x00\x01\xcd\x21\xc3")

        assert fmt.platform == "dos"

    def test_pe_x86_is_unsupported(self, tmp_path):
        machine = (0x014C).to_bytes(2, "little")
        fmt = self._classify(
            tmp_path, new_format_exe_bytes(b"PE\0\0" + machine))

        assert fmt == (None, "a Windows x86 (PE)")

    def test_pe_without_architecture_is_unsupported(self, tmp_path):
        fmt = self._classify(tmp_path, new_format_exe_bytes(b"PE\0\0"))

        assert fmt == (None, "a Windows (PE)")

    def test_pe_x64_is_unsupported(self, tmp_path):
        machine = (0x8664).to_bytes(2, "little")
        fmt = self._classify(
            tmp_path, new_format_exe_bytes(b"PE\0\0" + machine))

        assert fmt == (None, "a Windows x64 (PE)")

    def test_win16_ne_is_unsupported(self, tmp_path):
        fmt = self._classify(tmp_path, new_format_exe_bytes(b"NE\0\0"))

        assert fmt.platform is None
        assert "(NE)" in fmt.kind

    def test_linux_bsd_elf_is_unsupported(self, tmp_path):
        header = bytearray(0x40)
        header[0:4] = b"\x7fELF"
        header[4] = 2                                   # 64-bit
        header[5] = 1                                   # little-endian
        header[0x12:0x14] = (0x3E).to_bytes(2, "little")  # x86-64
        fmt = self._classify(tmp_path, bytes(header))

        assert fmt == (None, "an ELF x86-64 (Linux/BSD)")

    def test_elf_arm64_is_unsupported(self, tmp_path):
        header = bytearray(0x40)
        header[0:4] = b"\x7fELF"
        header[4] = 2
        header[5] = 1
        header[0x12:0x14] = (0xB7).to_bytes(2, "little")  # aarch64
        fmt = self._classify(tmp_path, bytes(header))

        assert fmt == (None, "an ELF ARM64 (Linux/BSD)")

    def test_macos_macho_is_unsupported(self, tmp_path):
        # little-endian 64-bit Mach-O, cputype arm64
        header = (b"\xcf\xfa\xed\xfe"
                  + (0x0100000C).to_bytes(4, "little"))
        fmt = self._classify(
            tmp_path, header + bytes(0x40 - len(header)))

        assert fmt == (None, "a macOS ARM64 (Mach-O)")

    def test_macos_universal_binary_is_unsupported(self, tmp_path):
        # fat header: big-endian magic + tiny arch count (a Java
        # class file shares the magic but never a small count there)
        header = b"\xca\xfe\xba\xbe" + (2).to_bytes(4, "big")
        fmt = self._classify(
            tmp_path, header + bytes(0x40 - len(header)))

        assert fmt == (None, "a macOS universal (Mach-O)")

    def test_fat_magic_with_large_count_field_passes_through(self, tmp_path):
        # cafebabe + a value far too large for a universal binary's
        # arch count: not provably Mach-O, so the guest judges
        header = b"\xca\xfe\xba\xbe" + (0x00010000).to_bytes(4, "big")
        fmt = self._classify(
            tmp_path, header + bytes(0x40 - len(header)))

        assert fmt.platform == "dos"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            binfmt.classify(tmp_path / "MISSING.EXE")
