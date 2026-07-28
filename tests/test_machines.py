# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for named reliquary-backed test-machine declarations."""

import unittest

from testaferro import catalog, machines


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


class StandardCatalogTests(unittest.TestCase):
    """A machine name resolves to the project's declarations first and
    the standard catalog second (D10)."""

    def setUp(self):
        machines._clear_for_tests()
        self.addCleanup(machines._clear_for_tests)

    def test_a_standard_name_resolves_with_nothing_declared(self):
        name, config = machines.select(name="freedos")

        self.assertEqual(name, "freedos")
        self.assertEqual(config.platform, "dos")

    def test_the_standard_machine_is_one_shared_declaration(self):
        self.assertIs(machines.select(name="freedos")[1],
                      machines.select(name="freedos")[1])

    def test_the_standard_machine_declares_only_its_platform(self):
        # What makes naming it identical to naming nothing: the DOS
        # binding supplies the memory default and the cached image.
        _, config = machines.select(name="freedos")

        self.assertEqual(dict(config.fields), {"platform": "dos"})
        self.assertEqual(config.media, ())

    def test_a_declaration_shadows_the_standard_name(self):
        declared = machines.configure("freedos", memory=64)

        self.assertEqual(machines.select(name="freedos"),
                         ("freedos", declared))

    def test_the_catalog_is_reached_by_name_never_by_inference(self):
        # Zero configuration stays zero configuration (P8): an
        # inferred platform selects among declarations only.
        self.assertIsNone(machines.select(inferred="dos"))

    def test_a_standard_machine_answers_a_platform_mismatch(self):
        with self.assertRaisesRegex(ValueError, "has platform 'dos'"):
            machines.select(name="freedos", platform="win9x")

    def test_every_standard_document_is_testaferros_own(self):
        # A standard environment is fully owned: its document names
        # no blueprint and no medium testaferro did not author beside
        # it, so nothing resolves from reliquary's codex or from the
        # user's reliquary home (D6, D10).
        for name, document in catalog.STANDARD.items():
            declared = {spec.get("name") for spec in document
                        if spec.get("type") != "machine"}
            for spec in document:
                self.assertIn(spec.get("type"), ("machine", "media"), name)
                if spec.get("type") != "machine":
                    self.assertTrue(
                        spec.get("location") or spec.get("path"),
                        f"{name}: medium {spec.get('name')!r} locates "
                        "nothing testaferro authored")
                    continue
                for slot, drive in (spec.get("drives") or {}).items():
                    located = (isinstance(drive, dict)
                               and (drive.get("location")
                                    or drive.get("media") in declared))
                    self.assertTrue(
                        located,
                        f"{name}: drive {slot!r} reaches for media "
                        "declared somewhere testaferro does not own")

    def test_an_unknown_name_lists_both_sources(self):
        machines.configure("win98", platform="win9x")

        with self.assertRaisesRegex(
                ValueError,
                r"unknown test machine 'msdos'.*"
                r"configured: win98.*standard: freedos"):
            machines.select(name="msdos")


if __name__ == "__main__":
    unittest.main()
