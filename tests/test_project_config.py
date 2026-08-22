# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Tests for the per-project testaferro.ini declaration file."""

import json
import os

import pytest

from testaferro import environments


class ProjectConfigTests:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, clean_environments):
        self.root = tmp_path

    def _write(self, relative, text):
        path = os.path.join(self.root, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_loads_one_section_per_environment(self):
        image = self._write("images/msdos.img", "fake")
        ini = self._write(
            "testaferro.ini",
            "[msdos]\n"
            "boot_image = images/msdos.img\n"
            "memory = 32\n")

        loaded = environments.load_config(ini)

        assert loaded == os.path.abspath(ini)
        config = environments.configured()["msdos"]
        assert config.platform == "dos"
        assert config.memory == 32
        assert (config.drives["floppy0"]["location"]["local"]
                == os.path.abspath(image))

    def test_search_walks_upward_from_start(self):
        self._write(
            "testaferro.ini",
            "[freedos]\n"
            "memory = 24\n")
        nested = os.path.join(self.root, "tests", "guest")
        os.makedirs(nested)

        loaded = environments.load_config(search_from=nested)

        assert os.path.basename(loaded) == "testaferro.ini"
        assert environments.configured()["freedos"].memory == 24

    def test_fruitless_search_is_a_noop(self):
        loaded = environments.load_config(search_from=self.root)

        assert loaded is None
        assert environments.configured() == {}

    def test_machine_config_path_resolves_from_the_ini_directory(self):
        document = {
            "type": "machine",
            "name": "custom",
            "platform": "dos",
            "memory": 48,
        }
        self._write("machines/custom.rlqb", json.dumps(document))
        ini = self._write(
            "testaferro.ini",
            "[custom]\n"
            "machine_config = machines/custom.rlqb\n")

        environments.load_config(ini)

        assert environments.configured()["custom"].memory == 48

    def test_json_valued_blueprint_fields(self):
        ini = self._write(
            "testaferro.ini",
            "[tuned]\n"
            "boot = [\"hdd0\"]\n"
            "backend_settings = {\"qemu\": {\"accel\": \"tcg\"}}\n")

        environments.load_config(ini)
        config = environments.configured()["tuned"]

        assert config.boot == ["hdd0"]
        assert config.backend_settings["qemu"]["accel"] == "tcg"

    def test_media_section_value_becomes_a_document_spec(self):
        ini = self._write(
            "testaferro.ini",
            "[freedos]\n"
            "drives = {\"floppy0\": {\"media\": \"boot\"}}\n"
            "media = [{\"name\": \"boot\", \"location\": \"boot.img\"}]\n")

        environments.load_config(ini)
        config = environments.configured()["freedos"]

        assert config.media == ({"name": "boot", "location": "boot.img"},)
        assert "media" not in config.fields

    def test_duplicate_name_with_configure_fails_closed(self):
        ini = self._write("testaferro.ini", "[freedos]\nmemory = 16\n")
        environments.configure("freedos", memory=32)

        with pytest.raises(ValueError, match="already configured"):
            environments.load_config(ini)

    def test_repeated_load_of_same_path_is_idempotent(self):
        ini = self._write("testaferro.ini", "[freedos]\nmemory = 16\n")

        first = environments.load_config(ini)
        second = environments.load_config(ini)

        assert first == second
        assert list(environments.configured()) == ["freedos"]

    def test_second_distinct_load_is_rejected(self):
        first = self._write("a.ini", "[one]\nmemory = 16\n")
        second = self._write("b.ini", "[two]\nmemory = 32\n")
        environments.load_config(first)

        with pytest.raises(RuntimeError, match="already loaded"):
            environments.load_config(second)

    def test_platform_stays_writable_as_a_blueprint_field(self):
        # It left the consumer surface without leaving the file: here
        # it is the provider's own word, passing through (P2, P3).
        ini = self._write(
            "testaferro.ini",
            "[win98]\n"
            "platform = win9x\n"
            "memory = 64\n")

        environments.load_config(ini)

        config = environments.configured()["win98"]
        assert config.platform == "win9x"
        assert config.memory == 64

    def test_provider_has_an_ini_spelling_like_every_keyword(self):
        # The declarative twin of config(provider=...): one vocabulary,
        # spelled here as it is spelled in Python (P16).
        ini = self._write(
            "testaferro.ini",
            "[msdos]\n"
            "provider = reliquary\n"
            "memory = 64\n")

        environments.load_config(ini)

        config = environments.configured()["msdos"]
        assert config.provider == "reliquary"
        assert dict(config.fields) == {"platform": "dos", "memory": 64}

    def test_placement_has_ini_spellings_like_every_keyword(self):
        # The declarative twin of config(files=/location=/program=),
        # and none of the three reaches the blueprint: reliquary's
        # document has no field for what a test run stages (F4, P16).
        ini = self._write(
            "testaferro.ini",
            "[msdos]\n"
            "memory = 64\n"
            "location = D:\\TESTDIR\n"
            "program = {location}\\RUNNER.EXE\n")

        environments.load_config(ini)

        config = environments.configured()["msdos"]
        assert config.location == "D:\\TESTDIR"
        assert config.program == "{location}\\RUNNER.EXE"
        assert dict(config.fields) == {"platform": "dos", "memory": 64}

    def test_staged_files_resolve_from_the_ini_directory(self):
        # `files` names host paths, so a relative one means beside the
        # declaration — the same rule every other path setting follows.
        first = self._write("fixtures/CASE.DAT", "case")
        second = self._write("fixtures/OTHER.DAT", "other")
        ini = self._write(
            "testaferro.ini",
            "[msdos]\n"
            "files = fixtures/CASE.DAT, fixtures/OTHER.DAT\n")

        environments.load_config(ini)

        config = environments.configured()["msdos"]
        assert config.files == (os.path.abspath(first),
                                 os.path.abspath(second))

    def test_a_lone_staged_file_needs_no_comma(self):
        path = self._write("fixtures/CASE.DAT", "case")
        ini = self._write(
            "testaferro.ini",
            "[msdos]\n"
            "files = fixtures/CASE.DAT\n")

        environments.load_config(ini)

        assert (environments.configured()["msdos"].files
                == (os.path.abspath(path),))

    def test_setup_has_an_ini_spelling_one_command_per_line(self):
        # The declarative twin of config(setup=[...]) (F9, P16): a
        # command routinely embeds a space of its own and sometimes a
        # comma, so it is split by line rather than files' comma rule.
        ini = self._write(
            "testaferro.ini",
            "[msdos]\n"
            "setup =\n"
            "    DRIVER.COM /install\n"
            "    OTHER.COM /go\n")

        environments.load_config(ini)

        config = environments.configured()["msdos"]
        assert config.setup == ("DRIVER.COM /install", "OTHER.COM /go")
        assert "setup" not in config.fields

    def test_persist_has_an_ini_spelling(self):
        # The declarative twin of config(persist="...") (F2, P16): a
        # name, kept as authored and never read as a number or JSON.
        ini = self._write(
            "testaferro.ini",
            "[harness]\n"
            "persist = hw-harness\n")

        environments.load_config(ini)

        config = environments.configured()["harness"]
        assert config.persist == "hw-harness"
        assert "persist" not in config.fields

    def test_a_lone_setup_command_needs_no_leading_newline(self):
        ini = self._write(
            "testaferro.ini",
            "[msdos]\n"
            "setup = DRIVER.COM /install\n")

        environments.load_config(ini)

        assert (environments.configured()["msdos"].setup
                == ("DRIVER.COM /install",))

    def test_a_dosbox_x_section_spells_conf_sections_as_json(self):
        # The structured-value rule already covering it (F21): a value
        # opening with a brace is JSON, so a conf section is written
        # under the environment's section with no new spelling.
        ini = self._write(
            "testaferro.ini",
            "[fast]\n"
            "provider = dosbox-x\n"
            "cpu = {\"cycles\": \"max\"}\n"
            "render = {\"aspect\": true}\n")

        environments.load_config(ini)

        config = environments.configured()["fast"]
        assert config.provider == "dosbox-x"
        assert config.cpu == {"cycles": "max"}
        assert config.render == {"aspect": True}

    def test_a_dosbox_x_conf_path_resolves_from_the_ini_directory(self):
        # The existing path rule, and the declared provider opening
        # its own document (F21): a .conf beside testaferro.ini is
        # read as DOSBox-X's INI, never as a blueprint.
        self._write("machines/harness.conf",
                    "[dosbox]\nmachine = vga\n[cpu]\ncycles = max\n")
        ini = self._write(
            "testaferro.ini",
            "[fast]\n"
            "provider = dosbox-x\n"
            "machine_config = machines/harness.conf\n")

        environments.load_config(ini)

        config = environments.configured()["fast"]
        assert config.provider == "dosbox-x"
        assert config.dosbox == {"machine": "vga"}
        assert config.cpu == {"cycles": "max"}
