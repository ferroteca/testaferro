# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Tests for named reliquary-backed test-environment declarations."""

import pytest

from testaferro import catalog, environments


class EnvironmentConfigurationTests:
    @pytest.fixture(autouse=True)
    def _setup(self, clean_environments):
        pass

    def test_constructs_a_dos_environment_from_options(self):
        config = environments.configure("freedos", memory=32)

        assert config.platform == "dos"
        assert config.memory == 32
        assert (environments.select(inferred="dos")
                == ("freedos", config))

    def test_template_supplies_the_platform(self):
        template = environments.EnvironmentSpec({"platform": "win9x"})
        config = environments.configure("win98", machine_config=template)

        assert config is template
        assert (environments.select(name="win98")
                == ("win98", template))

    def test_platform_is_a_blueprint_field_passing_through(self):
        # Not Testaferro's word (P2): it is written where every other
        # blueprint field is written, and read back the same way.
        config = environments.configure("win98", platform="win9x",
                                        memory=64)

        assert config.platform == "win9x"
        assert (dict(config.fields)
                == {"platform": "win9x", "memory": 64})

    def test_a_template_is_complete_so_fields_are_not_said_beside_it(self):
        # Including `platform`, which used to be the exception that
        # let Testaferro cross-check somebody else's document.
        template = environments.EnvironmentSpec({"platform": "dos"})

        with pytest.raises(TypeError, match="complete template"):
            environments.configure("win98", platform="win9x",
                                   machine_config=template)

    def test_provider_is_testaferros_own_word_not_a_blueprint_field(self):
        # The mirror image of `platform` above: reliquary's document
        # has no field for who is reading it, so this one is declared
        # beside the blueprint fields and never among them (P1, P3).
        config = environments.configure("msdos", provider="reliquary",
                                        memory=64)

        assert config.provider == "reliquary"
        assert (dict(config.fields)
                == {"platform": "dos", "memory": 64})
        assert "provider" not in config.document("msdos")[0]

    def test_an_unnamed_provider_stays_unsaid(self):
        # Defaulting is resolution's answer, said in one place; a
        # declaration reports what was written and nothing more.
        config = environments.configure("msdos", memory=64)

        assert config.provider is None

    def test_provider_is_said_beside_a_complete_template(self):
        # A template is the provider's own document, so it cannot name
        # the provider reading it — which is why this is one of the
        # keys admitted beside a template, as timeout and suites are.
        template = environments.EnvironmentSpec({"platform": "dos"})

        config = environments.configure("msdos", machine_config=template,
                                        provider="reliquary")

        assert config.provider == "reliquary"
        assert dict(config.fields) == {"platform": "dos"}
        assert template.provider is None

    def test_inference_reports_ambiguity(self):
        environments.configure("freedos", platform="dos")
        environments.configure("msdos", platform="dos")

        with pytest.raises(ValueError,
                           match="more than one.*freedos.*msdos"):
            environments.select(inferred="dos")

    def test_no_configuration_keeps_the_implicit_dos_environment(self):
        assert environments.select(inferred="dos") is None

    def test_configured_environments_disable_the_implicit_default(self):
        environments.configure("win98", platform="win9x")

        with pytest.raises(
                ValueError, match="no configured test environment runs dos"):
            environments.select(inferred="dos")

    def test_media_is_declared_beside_the_machine_not_inside_it(self):
        spec = {"type": "media", "name": "boot", "location": "boot.img"}
        config = environments.configure(
            "freedos", media=[spec], drives={"floppy0": {"media": "boot"}})

        # A machine spec has no `media` field — reliquary's schema is
        # closed — so it belongs beside the machine in the document.
        assert "media" not in config.fields
        assert config.media == (spec,)
        assert config.document("freedos")[1] == spec

    def test_a_lone_media_spec_is_the_list_of_one(self):
        spec = {"type": "media", "name": "boot", "location": "boot.img"}
        config = environments.configure("freedos", media=spec)

        assert config.media == (spec,)

    def test_environment_names_accumulate_without_replacement(self):
        environments.configure("freedos")

        with pytest.raises(ValueError, match="already configured"):
            environments.configure("freedos")

    def test_setup_commands_are_declared_in_order(self):
        # The same argument as files/location/program made a fourth
        # time (F9): reliquary's document has no field for what runs
        # in the guest before a test does.
        config = environments.configure(
            "msdos", setup=["DRIVER.COM /install", "OTHER.COM /go"])

        assert (config.setup
                == ("DRIVER.COM /install", "OTHER.COM /go"))
        assert "setup" not in config.fields

    def test_a_lone_setup_command_needs_no_list(self):
        config = environments.configure("msdos", setup="DRIVER.COM /install")

        assert config.setup == ("DRIVER.COM /install",)

    def test_setup_is_said_beside_a_complete_template(self):
        # A template is the provider's own document and cannot say
        # what runs before a test — this is one of the keys admitted
        # beside it, as timeout, suites and provider are.
        template = environments.EnvironmentSpec({"platform": "dos"})

        config = environments.configure(
            "msdos", machine_config=template, setup=["DRIVER.COM /install"])

        assert config.setup == ("DRIVER.COM /install",)
        assert template.setup == ()

    def test_an_undeclared_setup_stays_empty(self):
        config = environments.configure("msdos")

        assert config.setup == ()


class StandardCatalogTests:
    """An environment name resolves to the project's declarations
    first and the standard catalog second (D10)."""

    @pytest.fixture(autouse=True)
    def _setup(self, clean_environments):
        pass

    def test_a_standard_name_resolves_with_nothing_declared(self):
        name, config = environments.select(name="freedos")

        assert name == "freedos"
        assert config.platform == "dos"

    def test_the_standard_environment_is_one_shared_declaration(self):
        assert (environments.select(name="freedos")[1]
                is environments.select(name="freedos")[1])

    def test_the_standard_environment_declares_only_its_platform(self):
        # What makes naming it identical to naming nothing: the DOS
        # binding supplies the memory default and the cached image.
        _, config = environments.select(name="freedos")

        assert dict(config.fields) == {"platform": "dos"}
        assert config.media == ()

    def test_a_declaration_shadows_the_standard_name(self):
        declared = environments.configure("freedos", memory=64)

        assert (environments.select(name="freedos")
                == ("freedos", declared))

    def test_the_catalog_is_reached_by_name_never_by_inference(self):
        # Zero configuration stays zero configuration (P8): an
        # inferred platform selects among declarations only.
        assert environments.select(inferred="dos") is None

    def test_every_standard_document_is_testaferros_own(self):
        # A standard environment is fully owned: its document names
        # no blueprint and no medium Testaferro did not author beside
        # it, so nothing resolves from reliquary's codex or from the
        # user's reliquary home (D6, D10).
        for name, document in catalog.STANDARD.items():
            declared = {spec.get("name") for spec in document
                        if spec.get("type") != "machine"}
            for spec in document:
                assert spec.get("type") in ("machine", "media"), name
                if spec.get("type") != "machine":
                    assert (
                        spec.get("location") or spec.get("path")), (
                        f"{name}: medium {spec.get('name')!r} locates "
                        "nothing testaferro authored")
                    continue
                for slot, drive in (spec.get("drives") or {}).items():
                    located = (isinstance(drive, dict)
                               and (drive.get("location")
                                    or drive.get("media") in declared))
                    assert located, (
                        f"{name}: drive {slot!r} reaches for media "
                        "declared somewhere testaferro does not own")

    def test_an_unknown_name_lists_both_sources(self):
        environments.configure("win98", platform="win9x")

        with pytest.raises(
                ValueError,
                match=(r"unknown test environment 'msdos'.*"
                       r"configured: win98.*standard: freedos")):
            environments.select(name="msdos")
