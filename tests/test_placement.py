# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Tests for the placement vocabulary the provider bindings share.

`placement` holds what every binding does with `files=`, `location=`,
`program=` and `setup=` the same way (F4, F9): the nearest-speaker
override rule, host-side gathering of the staged set, and `program=`
resolution against a settled location. The program-resolution cases
here moved from the reliquary binding's tests when the module did —
each binding's own tests keep only what that binding does with the
shared answers.
"""

from types import SimpleNamespace

import pytest

from testaferro import placement


class NearestSpeakerTests:
    """This call, then the declaration, then the default — one rule
    for every placement word, whoever the binding is."""

    def test_the_call_wins_over_the_declaration(self):
        declaration = SimpleNamespace(timeout=30)

        assert placement.nearest(5, declaration, "timeout", 120) == 5

    def test_the_declaration_wins_over_the_default(self):
        declaration = SimpleNamespace(timeout=30)

        assert placement.nearest(None, declaration, "timeout", 120) == 30

    def test_the_default_answers_when_nobody_said(self):
        assert placement.nearest(None, None, "timeout", 120) == 120

    def test_an_empty_tuple_counts_as_unsaid(self):
        # `files=()` is the shape "nothing was declared" takes, on the
        # call and on the declaration alike.
        declaration = SimpleNamespace(files=())

        assert placement.nearest((), declaration, "files", None) is None

    def test_a_declaration_without_the_word_counts_as_unsaid(self):
        assert placement.nearest(None, SimpleNamespace(), "files",
                                 ()) == ()


class GatherTests:
    """The staged set, collected into one host directory."""

    def test_the_executable_lands_under_its_own_name(self, tmp_path):
        exe = tmp_path / "SUITE.EXE"
        exe.write_bytes(b"MZ")
        target = tmp_path / "work"
        target.mkdir()

        placement.gather(target, (), exe_path=str(exe))

        assert (target / "SUITE.EXE").read_bytes() == b"MZ"

    def test_files_land_beside_the_executable(self, tmp_path):
        exe = tmp_path / "SUITE.EXE"
        exe.write_bytes(b"MZ")
        data = tmp_path / "DATA.BIN"
        data.write_bytes(b"data")
        target = tmp_path / "work"
        target.mkdir()

        placement.gather(target, (str(data),), exe_path=str(exe))

        assert sorted(p.name for p in target.iterdir()) == [
            "DATA.BIN", "SUITE.EXE"]

    def test_a_directory_contributes_its_contents_not_itself(self, tmp_path):
        fixtures = tmp_path / "fixtures"
        fixtures.mkdir()
        (fixtures / "A.TXT").write_text("a")
        target = tmp_path / "work"
        target.mkdir()

        placement.gather(target, (str(fixtures),))

        assert (target / "A.TXT").read_text() == "a"
        assert not (target / "fixtures").exists()

    def test_no_executable_stages_files_alone(self, tmp_path):
        data = tmp_path / "DRIVER.COM"
        data.write_bytes(b"drv")
        target = tmp_path / "work"
        target.mkdir()

        placement.gather(target, (str(data),))

        assert [p.name for p in target.iterdir()] == ["DRIVER.COM"]


class ProgramResolutionTests:
    """The guest address of what to run, defaulted or declared."""

    def test_the_program_defaults_to_the_staged_executable(self):
        assert (placement.resolve_program(None, "D:\\TESTS", "SUITE.EXE")
                == "D:\\TESTS\\SUITE.EXE")

    def test_a_root_location_does_not_double_its_separator(self):
        assert (placement.resolve_program(None, "C:\\", "SUITE.EXE")
                == "C:\\SUITE.EXE")

    def test_a_declared_program_substitutes_the_location(self):
        assert (placement.resolve_program(
                    "{location}\\RUNNER.EXE", "D:\\TESTS", "SUITE.EXE")
                == "D:\\TESTS\\RUNNER.EXE")

    def test_a_declared_program_may_name_no_placeholder_at_all(self):
        assert (placement.resolve_program(
                    "C:\\TOOLS\\RUN.EXE", "D:\\TESTS", "SUITE.EXE")
                == "C:\\TOOLS\\RUN.EXE")

    def test_an_unknown_placeholder_is_refused_naming_the_known_one(self):
        with pytest.raises(ValueError) as caught:
            placement.resolve_program("{drive}\\RUN.EXE", "D:\\TESTS",
                                      "SUITE.EXE")

        assert "{drive}" in str(caught.value)
        assert "{location}" in str(caught.value)
