# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for named reliquary-backed test-machine declarations."""

import unittest

from testaferro import machines


class MachineConfigurationTests(unittest.TestCase):
    def setUp(self):
        machines._clear_for_tests()
        self.addCleanup(machines._clear_for_tests)

    def test_constructs_a_dos_machine_from_options(self):
        config = machines.configure("freedos", memory=32)

        self.assertEqual(config.platform, "dos")
        self.assertEqual(config.memory, 32)
        self.assertEqual(machines.select(inferred="dos"),
                         ("freedos", config))

    def test_template_supplies_the_platform(self):
        template = machines.MachineSpec({"platform": "win9x"})
        config = machines.configure("win98", machine_config=template)

        self.assertIs(config, template)
        self.assertEqual(machines.select(name="win98"),
                         ("win98", template))

    def test_explicit_platform_fills_a_template_that_omits_it(self):
        config = machines.configure(
            "win98", platform="win9x",
            machine_config={"memory": 32})

        self.assertEqual(config.platform, "win9x")

    def test_explicit_platform_must_match_template(self):
        template = machines.MachineSpec({"platform": "dos"})

        with self.assertRaisesRegex(ValueError, "declares platform"):
            machines.configure("win98", platform="win9x",
                               machine_config=template)

    def test_platform_selection_reports_ambiguity(self):
        machines.configure("freedos", platform="dos")
        machines.configure("msdos", platform="dos")

        with self.assertRaisesRegex(ValueError, "multiple.*freedos.*msdos"):
            machines.select(platform="dos")

    def test_no_configuration_keeps_the_implicit_dos_machine(self):
        self.assertIsNone(machines.select(inferred="dos"))

    def test_configured_machines_disable_the_implicit_default(self):
        machines.configure("win98", platform="win9x")

        with self.assertRaisesRegex(ValueError, "no configured test machine"):
            machines.select(inferred="dos")

    def test_media_is_declared_beside_the_machine_not_inside_it(self):
        spec = {"type": "media", "name": "boot", "location": "boot.img"}
        config = machines.configure(
            "freedos", media=[spec], drives={"floppy0": {"media": "boot"}})

        # A machine spec has no `media` field — reliquary's schema is
        # closed — so it belongs beside the machine in the document.
        self.assertNotIn("media", config.fields)
        self.assertEqual(config.media, (spec,))
        self.assertEqual(config.document("freedos")[1], spec)

    def test_a_lone_media_spec_is_the_list_of_one(self):
        spec = {"type": "media", "name": "boot", "location": "boot.img"}
        config = machines.configure("freedos", media=spec)

        self.assertEqual(config.media, (spec,))

    def test_machine_names_accumulate_without_replacement(self):
        machines.configure("freedos")

        with self.assertRaisesRegex(ValueError, "already configured"):
            machines.configure("freedos")


if __name__ == "__main__":
    unittest.main()
