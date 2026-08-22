# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""The integration tier for the DOSBox-X binding: real invocations.

Fast is not cheap in P10's sense: DOSBox-X starting a DOS is a guest
starting, however little it costs, so these cases sit on this side of
the line no matter that a whole run takes seconds. They skip without
`TESTAFERRO_INTEGRATION`, exactly as every guest run does, and skip
again when DOSBox-X itself is not installed — an external emulator is
not a dependency (P11), so its absence is a skipped proof rather than
a failed suite.

What only a real invocation can show: the generated conf actually
drives the emulator, the redirected file actually comes back as
CppUTest's own bytes — the clean channel that double-checks the
grammar is right about *CppUTest* rather than right about a screen
transport (P9, F20) — and a failure carries the guest's own file and
line through it.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SUITE = HERE / "guest" / "SUITE.EXE"

ASKED = bool(os.environ.get("TESTAFERRO_INTEGRATION"))


def _dosbox_available():
    try:
        from testaferro import dosbox_x

        dosbox_x._find_executable()
    except FileNotFoundError:
        return False
    return True


requires_guest = pytest.mark.skipif(
    not ASKED, reason="set TESTAFERRO_INTEGRATION=1 to run a real guest")
requires_suite = pytest.mark.skipif(
    not SUITE.is_file(),
    reason=f"{SUITE.name} is not built — see guest/makefile")
requires_dosbox = pytest.mark.skipif(
    ASKED and not _dosbox_available(),
    reason="dosbox-x is not installed")


@requires_guest
@requires_suite
@requires_dosbox
class DosboxSuiteTests:
    """One staged guest session, several invocations asked of it.

    Unlike the reliquary tier's shared boot, sharing costs nothing
    here — each operation is its own invocation regardless — but the
    staged home is shared the same way a real consumer's would be.
    """

    @pytest.fixture(autouse=True, scope="class")
    def _setup(self, request):
        from testaferro import dosbox_x as binding

        backend = binding.suite_backend(str(SUITE))
        backend.start_guest()
        request.cls.backend = backend

        yield

        backend.stop_guest()

    def test_the_guest_enumerates_its_own_tests(self):
        ids = [str(test_id) for test_id in self.backend.list_tests()]

        assert "Guest.Runs" in ids
        assert "Guest.Fails" in ids
        assert "Guest.RunsToo" in ids

    def test_a_whole_run_comes_back_and_parses(self):
        outcomes = {(o.group, o.name): o for o in self.backend.run_all()}

        assert outcomes[("Guest", "Runs")].passed
        assert outcomes[("Guest", "RunsToo")].passed
        assert not outcomes[("Guest", "Fails")].passed

    def test_a_failure_carries_the_guests_own_file_and_line(self):
        outcome = self.backend.run_test("Guest", "Fails")

        assert not outcome.passed
        assert "SUITE" in outcome.file.upper()
        assert outcome.line > 0
        assert outcome.message.strip()

    def test_one_test_can_be_run_on_its_own(self):
        outcome = self.backend.run_test("Guest", "Runs")

        assert outcome.passed


@requires_guest
@requires_suite
@requires_dosbox
class DosboxResolutionTests:
    """The declared second value on P1's axis, end to end: the same
    seam every entry point shares selects the dosbox-x binding and a
    real invocation answers through it."""

    @pytest.fixture(autouse=True)
    def _setup(self, clean_environments):
        pass

    def test_the_declared_provider_resolves_and_runs_for_real(self):
        from testaferro.resolution import resolve_backend

        backend = resolve_backend(str(SUITE), provider="dosbox-x")
        backend.start_guest()
        try:
            outcomes = {(o.group, o.name): o
                        for o in backend.run_all()}
        finally:
            backend.stop_guest()

        assert outcomes[("Guest", "Runs")].passed
        assert not outcomes[("Guest", "Fails")].passed

    def test_declared_conf_sections_reach_the_emulator_for_real(self):
        # A dosbox-x environment goes as deep as DOSBox-X does (F21,
        # P2): sections declared inline are written ahead of
        # [autoexec], and only a real invocation can show DOSBox-X
        # accepts the generated file — and that the work drive
        # mounted at D: with nothing at C: runs the suite.
        import testaferro
        from testaferro.resolution import resolve_backend

        testaferro.config("fast", provider="dosbox-x",
                          dosbox={"machine": "vga", "memsize": 16},
                          cpu={"cycles": "max"})
        backend = resolve_backend(str(SUITE), environment="fast")
        backend.start_guest()
        try:
            outcomes = {(o.group, o.name): o
                        for o in backend.run_all()}
        finally:
            backend.stop_guest()

        assert backend.location == "D:\\"
        assert outcomes[("Guest", "Runs")].passed
        assert not outcomes[("Guest", "Fails")].passed

    def test_a_conf_document_reaches_the_emulator_for_real(self, tmp_path):
        from testaferro.resolution import resolve_backend

        conf = tmp_path / "harness.conf"
        conf.write_text("# the tester's own DOSBox-X conf\n"
                        "[cpu]\ncycles = max\n", encoding="utf-8")
        backend = resolve_backend(str(SUITE), provider="dosbox-x",
                                  machine_config=str(conf))
        backend.start_guest()
        try:
            outcome = backend.run_test("Guest", "Runs")
        finally:
            backend.stop_guest()

        assert outcome.passed

    def test_the_standard_environment_resolves_and_runs_for_real(self):
        # The catalog's second entry, end to end (F21, P17).
        from testaferro.resolution import resolve_backend

        backend = resolve_backend(str(SUITE), environment="dosbox-x")
        backend.start_guest()
        try:
            outcome = backend.run_test("Guest", "Runs")
        finally:
            backend.stop_guest()

        assert outcome.passed
