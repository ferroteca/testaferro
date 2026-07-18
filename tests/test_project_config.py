# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the per-project testaferro.ini machine file."""

import json
import os
import tempfile
import unittest

import relict

from testaferro import machines


class ProjectConfigTests(unittest.TestCase):
    def setUp(self):
        machines._clear_for_tests()
        self.addCleanup(machines._clear_for_tests)
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = self._temp.name

    def _write(self, relative, text):
        path = os.path.join(self.root, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_loads_one_section_per_machine(self):
        image = self._write("images/msdos.img", "fake")
        ini = self._write(
            "testaferro.ini",
            "[msdos]\n"
            "boot_image = images/msdos.img\n"
            "memory = 32\n")

        loaded = machines.load_config(ini)

        self.assertEqual(loaded, os.path.abspath(ini))
        config = machines.configured()["msdos"]
        self.assertEqual(config.platform, "dos")
        self.assertEqual(config.memory, 32)
        self.assertEqual(config.drives["floppy_0"]["source"],
                         os.path.abspath(image))

    def test_search_walks_upward_from_start(self):
        self._write(
            "testaferro.ini",
            "[freedos]\n"
            "memory = 24\n")
        nested = os.path.join(self.root, "tests", "guest")
        os.makedirs(nested)

        loaded = machines.load_config(search_from=nested)

        self.assertEqual(os.path.basename(loaded), "testaferro.ini")
        self.assertEqual(machines.configured()["freedos"].memory, 24)

    def test_fruitless_search_is_a_noop(self):
        loaded = machines.load_config(search_from=self.root)

        self.assertIsNone(loaded)
        self.assertEqual(machines.configured(), {})

    def test_machine_config_path_resolves_from_the_ini_directory(self):
        document = {
            "version": 1,
            "platform": "dos",
            "memory": 48,
        }
        self._write("machines/custom.json", json.dumps(document))
        ini = self._write(
            "testaferro.ini",
            "[custom]\n"
            "machine_config = machines/custom.json\n")

        machines.load_config(ini)

        self.assertEqual(machines.configured()["custom"].memory, 48)

    def test_json_valued_machine_fields(self):
        ini = self._write(
            "testaferro.ini",
            "[tuned]\n"
            "qemu_args = [\"-cpu\", \"486\"]\n"
            "machine = {\"type\": \"pc\", \"accel\": \"tcg\"}\n")

        machines.load_config(ini)
        config = machines.configured()["tuned"]

        self.assertEqual(config.qemu_args, ("-cpu", "486"))
        self.assertEqual(config.machine["type"], "pc")

    def test_duplicate_name_with_configure_fails_closed(self):
        ini = self._write("testaferro.ini", "[freedos]\nmemory = 16\n")
        machines.configure("freedos", memory=32)

        with self.assertRaisesRegex(ValueError, "already configured"):
            machines.load_config(ini)

    def test_repeated_load_of_same_path_is_idempotent(self):
        ini = self._write("testaferro.ini", "[freedos]\nmemory = 16\n")

        first = machines.load_config(ini)
        second = machines.load_config(ini)

        self.assertEqual(first, second)
        self.assertEqual(list(machines.configured()), ["freedos"])

    def test_second_distinct_load_is_rejected(self):
        first = self._write("a.ini", "[one]\nmemory = 16\n")
        second = self._write("b.ini", "[two]\nmemory = 32\n")
        machines.load_config(first)

        with self.assertRaisesRegex(RuntimeError, "already loaded"):
            machines.load_config(second)

    def test_explicit_platform_in_section(self):
        template = relict.MachineConfig(platform="win9x", memory=64)
        # File form: platform alone constructs a MachineConfig.
        ini = self._write(
            "testaferro.ini",
            "[win98]\n"
            "platform = win9x\n"
            "memory = 64\n")

        machines.load_config(ini)

        config = machines.configured()["win98"]
        self.assertEqual(config.platform, template.platform)
        self.assertEqual(config.memory, 64)


if __name__ == "__main__":
    unittest.main()
