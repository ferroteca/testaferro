# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the backend-resolution seam.

Every case here calls resolve_backend() directly, with no pytest
entry point above it: the seam is what each entry point shares, so
its rules are proved where they live.
"""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from testaferro.backend import TestId

from test_binfmt import new_format_exe_bytes, plain_dos_exe_bytes
from test_facade import FakeBackend, OUTCOMES

RELIQUARY_AVAILABLE = importlib.util.find_spec("reliquary") is not None


@unittest.skipUnless(RELIQUARY_AVAILABLE, "reliquary is not installed")
class BackendResolutionTests(unittest.TestCase):
    def setUp(self):
        from testaferro import environments

        environments._clear_for_tests()
        self.addCleanup(environments._clear_for_tests)
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

    def _exe(self, content=None):
        path = Path(self.tempdir.name) / "SUITE.EXE"
        path.write_bytes(plain_dos_exe_bytes() if content is None
                         else content)
        return path

    def _resolved(self, *args, **kwargs):
        """Resolve, with the DOS binding standing in for a real guest,
        and report the options it was handed."""
        from testaferro.resolution import resolve_backend

        with mock.patch("testaferro.reliquary.suite_backend",
                        return_value=FakeBackend(OUTCOMES)) as factory:
            backend = resolve_backend(*args, **kwargs)
        return backend, factory

    def test_the_executables_format_selects_the_binding(self):
        def enumerator():
            return [TestId("Vring", "Wraps")]

        exe = self._exe()

        backend, factory = self._resolved(exe, enumerator=enumerator)

        factory.assert_called_once_with(exe, enumerator=enumerator)
        self.assertIsInstance(backend, FakeBackend)

    def test_declared_environment_supplies_its_configuration(self):
        import testaferro

        image = Path(self.tempdir.name) / "msdos.img"
        image.write_bytes(b"msdos")
        machine_config = testaferro.config("msdos", boot_image=image)
        exe = self._exe()

        _, factory = self._resolved(exe, environment="msdos")

        factory.assert_called_once_with(exe, machine_config=machine_config)

    def test_a_standard_name_resolves_from_the_catalog(self):
        # Nothing declared: "freedos" is testaferro's own, and it
        # carries only a platform, so the binding boots exactly what
        # zero configuration boots (D10, U9).
        from testaferro import catalog

        exe = self._exe()

        _, factory = self._resolved(exe, environment="freedos")

        machine_config = factory.call_args.kwargs["machine_config"]
        self.assertEqual(machine_config.platform, "dos")
        self.assertEqual(dict(machine_config.fields), {"platform": "dos"})
        self.assertIn("freedos", catalog.STANDARD)

    def test_a_declaration_wins_over_the_standard_name(self):
        import testaferro

        declared = testaferro.config("freedos", memory=64)
        exe = self._exe()

        _, factory = self._resolved(exe, environment="freedos")

        factory.assert_called_once_with(exe, machine_config=declared)

    def test_unknown_environment_names_both_sources(self):
        from testaferro.resolution import resolve_backend

        exe = self._exe()

        with self.assertRaisesRegex(
                ValueError,
                r"unknown test environment 'msdos'.*standard: freedos"):
            resolve_backend(exe, environment="msdos")

    def test_a_named_environment_rejects_a_second_template(self):
        import testaferro
        from testaferro import environments
        from testaferro.resolution import resolve_backend

        testaferro.config("freedos")
        exe = self._exe()

        with self.assertRaisesRegex(TypeError, "cannot be combined"):
            resolve_backend(exe, environment="freedos",
                            machine_config=environments.EnvironmentSpec({}))

    def test_the_ini_search_starts_where_the_caller_says(self):
        # The seam knows nothing about how it was reached: an entry
        # point names the directory, and the facade's call site is
        # only one way to arrive at one.
        exe = self._exe()

        with mock.patch("testaferro.environments.load_config") as load:
            self._resolved(exe, search_from=self.tempdir.name)

        self.assertEqual(load.call_args.kwargs["search_from"],
                         self.tempdir.name)

    def test_unsupported_format_is_rejected_before_any_guest(self):
        from testaferro.resolution import resolve_backend

        header = bytearray(0x40)
        header[0:4] = b"\x7fELF"
        header[4] = 2
        header[5] = 1
        header[0x12:0x14] = (0x3E).to_bytes(2, "little")

        with self.assertRaisesRegex(
                ValueError, r"ELF x86-64.*no test environment here runs"):
            resolve_backend(self._exe(bytes(header)))

    def test_pe_is_rejected_naming_format_and_architecture(self):
        from testaferro.resolution import resolve_backend

        machine = (0x014C).to_bytes(2, "little")
        exe = self._exe(new_format_exe_bytes(b"PE\0\0" + machine))

        with self.assertRaisesRegex(
                ValueError,
                r"Windows x86 \(PE\).*no test environment here runs"):
            resolve_backend(exe)

    def test_an_environment_no_binding_runs_is_rejected(self):
        # The platform reaching here is a blueprint field the tester
        # wrote (P3), so the refusal names the environment that
        # declared it rather than an option nobody typed.
        import testaferro
        from testaferro.resolution import resolve_backend

        testaferro.config("warp", platform="os2")

        with self.assertRaisesRegex(
                ValueError,
                r"test environment 'warp' declares platform 'os2'"):
            resolve_backend(self._exe(), environment="warp")

    def test_a_wrong_option_names_what_the_environment_runs_on(self):
        from testaferro.resolution import resolve_backend

        with self.assertRaisesRegex(
                TypeError, "selected environment runs on 'dos'"):
            resolve_backend(self._exe(), guest_image="OTHER.IMG")


if __name__ == "__main__":
    unittest.main()
