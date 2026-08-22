# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""The integration tier: the tests that boot a real guest.

**Nothing here runs unless asked for.** P10 forbids the unit tier
starting a guest, and this is the other side of that line rather than
an exception to it — `TESTAFERRO_INTEGRATION` in the environment is
the asking, and without it every case below skips. That keeps the
default `unittest discover -s tests` exactly as cheap as it was,
whether or not discovery ever learns to recurse in here.

What these prove is the half of Testaferro no unit test can reach: a
machine that actually boots, an executable that actually arrives on a
drive the guest can name, output a real screen actually carried back,
and a failure that happened somewhere else surfacing here with the
guest's own file and line on it. The suite they run is Testaferro's
own (see `guest/`), and it fails one test on purpose, because a run
where everything passes proves only that output was parsed.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SUITE = HERE / "guest" / "SUITE.EXE"

ASKED = bool(os.environ.get("TESTAFERRO_INTEGRATION"))

requires_guest = pytest.mark.skipif(
    not ASKED, reason="set TESTAFERRO_INTEGRATION=1 to boot a real guest")
requires_suite = pytest.mark.skipif(
    not SUITE.is_file(), reason=f"{SUITE.name} is not built — see guest/makefile")


@requires_guest
@requires_suite
class GuestSessionTests:
    """One guest session, several questions asked of it.

    A session per assertion would be honest and slow; a real consumer
    boots once and asks repeatedly, so this does too, and the shared
    guest is torn down in tearDownClass however the cases go.
    """

    @pytest.fixture(autouse=True, scope="class")
    def _setup(self, request):
        from testaferro import reliquary as binding

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
        # The whole point of the courier: what comes back is where the
        # guest says it went wrong, not where Testaferro was standing.
        outcome = self.backend.run_test("Guest", "Fails")

        assert not outcome.passed
        assert "SUITE" in outcome.file.upper()
        assert outcome.line > 0
        assert outcome.message.strip()

    def test_one_test_can_be_run_on_its_own(self):
        outcome = self.backend.run_test("Guest", "Runs")

        assert outcome.passed

    def test_the_suite_lands_on_a_vvfat_sibling_of_the_system_disk(self):
        """The letter this binding now computes rather than reads,
        proved against the boot it is computed for.

        Zero configuration boots Testaferro's own FreeDOS on `hdd0`;
        the work drive is always a sibling on `hdd1`, live-served over
        vvfat — one hard disk after the system disk, so `D:` — with
        nothing written into it at rest, since `_gather()` already put
        the suite there before the machine existed. Everything above
        this in the class has already run off that placement; this
        states it, against a real boot rather than a computation.
        """
        assert self.backend.location == "D:\\"

        blueprint = Path(self.backend._home) / "blueprints"
        document = json.loads(
            (blueprint / "testaferro.rlqb").read_text(encoding="utf-8"))
        drives = document[0]["drives"]

        assert sorted(drives) == ["hdd0", "hdd1"]
        assert drives["hdd0"]["materialize"] == "difference"
        assert drives["hdd1"]["materialize"] == "use"

    def test_the_guest_reads_the_suite_back_from_where_it_was_staged(self):
        # The staging is real on the guest's side of the glass: DOS
        # itself lists the file at the address Testaferro reports.
        rows = self.backend._session.exec(
            f"DIR {self.backend.location}",
            machine=self.backend._machine, timeout=60)

        assert "SUITE" in "\n".join(rows).upper()


@requires_guest
@requires_suite
class SetupCommandTests:
    """Harness prep (F9), against a real boot: `setup=` commands
    actually run in the guest, actually before any test, and a real
    failure actually surfaces as `GuestOutputError` rather than as
    every later test failing mysteriously.

    Each case boots its own guest — unlike `GuestSessionTests`' shared
    session — because what is under test here is `start_guest()`
    itself, including the one that never finishes starting.
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from testaferro import reliquary as binding
        from testaferro.backend import GuestOutputError

        self.binding = binding
        self.GuestOutputError = GuestOutputError
        self.backend = None

        yield

        if self.backend is not None:
            self.backend.stop_guest()

    def test_a_setup_command_runs_before_the_guest_is_asked_for_anything(self):
        # Zero configuration lands the work drive at D: (see
        # GuestSessionTests.test_the_suite_lands_on_a_vvfat_sibling_
        # of_the_system_disk), so a setup command can write evidence
        # there and this reads it back afterward — proof the command
        # ran *during* start_guest(), not proof by inspecting Python.
        self.backend = self.binding.suite_backend(
            str(SUITE), setup=["ECHO ready>D:\\SETUP.MRK"])

        self.backend.start_guest()

        rows = self.backend._session.exec(
            "TYPE D:\\SETUP.MRK", machine=self.backend._machine, timeout=60)
        assert "ready" in "\n".join(rows)

    def test_a_failing_setup_command_ends_the_session_before_any_test_runs(self):
        # No new fixture needed: the suite already stages itself onto
        # the work drive, and CppUTest's runner returns its failure
        # count, so running the deliberately-failing case as a setup
        # command is a real program, on a real guest, actually
        # signalling failure — the exact channel `exec(check=True)`
        # exists to read.
        self.backend = self.binding.suite_backend(
            str(SUITE), setup=["D:\\SUITE.EXE -sg Guest -sn Fails"])

        with pytest.raises(self.GuestOutputError) as caught:
            self.backend.start_guest()

        assert "D:\\SUITE.EXE -sg Guest -sn Fails" in str(caught.value)
        # ended, not left half up: stop_guest() already ran once
        # (inside start_guest()'s own failure handling), so tearDown's
        # second call has to be a no-op rather than an error.
        assert self.backend._home is None

    def test_a_suite_declaring_no_setup_still_boots_and_runs(self):
        # The one-liner path stays exactly as it was: no setup
        # declared, no extra guest exchange, same green run
        # GuestSessionTests already proves in detail.
        self.backend = self.binding.suite_backend(str(SUITE))

        self.backend.start_guest()

        assert self.backend.run_test("Guest", "Runs").passed


@requires_guest
@requires_suite
class ScriptedGuestSessionTests:
    """U10, against a real boot: a scripted guest interaction reaches
    the same provisioning guest_suite() gives every suite, with no
    suite executable, no framework adapter, and nothing for one to
    parse — just guest.exec(), called directly, as many times as the
    script needs.
    """

    def test_staged_files_are_reachable_and_exec_reads_the_answer_back(self):
        from testaferro import reliquary as binding

        with binding.guest_session(files=[str(SUITE)]) as guest:
            rows = guest.exec(f"DIR {guest.location}")
            assert "SUITE" in "\n".join(rows).upper()

            rows = guest.exec(
                f"{guest.location}SUITE.EXE -sg Guest -sn Runs")
            assert "OK" in "\n".join(rows)

    def test_the_public_entry_point_opens_the_same_kind_of_session(self):
        import testaferro

        with testaferro.guest_session(files=[str(SUITE)]) as guest:
            assert guest.location
            rows = guest.exec(f"DIR {guest.location}")
            assert "SUITE" in "\n".join(rows).upper()


@requires_guest
@requires_suite
class NamedStandardEnvironmentTests:
    """U9, against a real boot: `environment="freedos"` resolves
    through the same seam every entry point shares
    (`resolution.resolve_backend`/`resolve_guest_session`), reaching
    the standard catalog's own document rather than only the
    zero-configuration default's inference landing on the same disk
    unnamed. `environments.select()` and the catalog it feeds are
    already unit-tested (F19) — what only a real boot can show is
    that the named path actually runs a guest, the same bar U4, U7
    and U10 each cleared (P10).
    """

    def test_the_named_environment_resolves_and_boots_for_real(self):
        from testaferro.resolution import resolve_backend

        backend = resolve_backend(str(SUITE), environment="freedos")
        backend.start_guest()
        try:
            outcomes = {(o.group, o.name): o for o in backend.run_all()}
        finally:
            backend.stop_guest()

        assert outcomes[("Guest", "Runs")].passed
        assert not outcomes[("Guest", "Fails")].passed

    def test_the_public_facade_names_it_the_same_way(self):
        import testaferro

        with testaferro.guest_session(
                environment="freedos", files=[str(SUITE)]) as guest:
            rows = guest.exec(
                f"{guest.location}SUITE.EXE -sg Guest -sn Runs")
            assert "OK" in "\n".join(rows)


@requires_guest
@requires_suite
class GuestCollectionTests:
    """U4's own command, run for real: `pytest <suite>.EXE`.

    The plugin path rather than the seam — a real pytest process, the
    real auto-loaded plugin, and a guest at the end of it, which is
    the journey a developer trying a suite actually takes.
    """

    def test_pytest_collects_and_runs_the_guest_suite(self):
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "no:cacheprovider",
             "-v", str(SUITE)],
            capture_output=True, text=True, check=False, cwd=str(HERE))
        output = result.stdout + result.stderr

        assert "SUITE.EXE::Guest-Runs" in output, output
        assert "SUITE.EXE::Guest-Fails" in output, output
        # One deliberate failure, and the rest passing: a run that is
        # all green would not show the failure path works at all.
        assert result.returncode == 1, output
        assert "1 failed" in output

    def test_a_project_ini_claims_the_suite_and_its_environment_boots(self):
        """U4's declaration clause, proved by a guest rather than a
        stub.

        A `testaferro.ini` beside the project is what makes the trial
        and the embedded run the same execution: it says which files
        are guest suites and which environment runs them, and nothing
        about the suite has to be named on the command line. Unit
        tests prove the file is found and the environment selected;
        only a boot proves the environment it selected actually runs
        the suite.
        """
        with tempfile.TemporaryDirectory() as project:
            root = Path(project)
            shutil.copy2(SUITE, root / SUITE.name)
            # One section, one environment: declaring only a platform
            # is what the standard catalog's own entry does, so this
            # runs on Testaferro's installed system exactly as naming
            # nothing would (P8).
            (root / "testaferro.ini").write_text(
                "[project-dos]\nplatform = dos\nsuites = *.EXE\n",
                encoding="utf-8")
            (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-p", "no:cacheprovider",
                 "-v"],
                capture_output=True, text=True, check=False, cwd=str(root))
            output = result.stdout + result.stderr

        # Claimed by the declaration's mask, with no file named on the
        # command line at all, and run in the environment it declared.
        assert "SUITE.EXE::Guest-Runs" in output, output
        assert "SUITE.EXE::Guest-Fails" in output, output
        assert "1 failed" in output


requires_xdist = pytest.mark.skipif(
    importlib.util.find_spec("xdist") is None,
    reason="pytest-xdist is not installed — run the tier with "
           "`uv run --with pytest-xdist pytest tests/integration`")


@requires_guest
@requires_suite
@requires_xdist
class ParallelTreeTests:
    """U5's journey: a whole tree of guest suites, run in parallel.

    The same `pytest -n auto --dist loadfile` the README advises, run
    for real over a project holding two suites: each worker collects
    — so each worker boots its own enumeration guest — and each suite
    lands whole on one worker, boots one execution guest there, and
    runs its items batched. The two suites run on different workers
    at the same time; the proof of that is in xdist's own per-item
    worker tags rather than in any clock, since a suite kept whole on
    one worker and two workers each holding one suite is exactly
    what `loadfile` means, and what the batching needs.

    pytest-xdist is a consumer's tool and not a dependency of this
    package (AGENTS.md, prior art); the tier borrows it for the run
    with `uv run --with pytest-xdist`, and this class skips without
    it rather than failing.
    """

    def test_two_suites_boot_on_two_workers_each_staying_whole(self):
        with tempfile.TemporaryDirectory() as project:
            root = Path(project)
            for name in ("ALPHA.EXE", "BRAVO.EXE"):
                shutil.copy2(SUITE, root / name)
            (root / "testaferro.ini").write_text(
                "[project-dos]\nplatform = dos\nsuites = *.EXE\n",
                encoding="utf-8")
            (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-p", "no:cacheprovider",
                 "-v", "-n", "2", "--dist", "loadfile"],
                capture_output=True, text=True, check=False, cwd=str(root))
            output = result.stdout + result.stderr

        # xdist tags every reported item with the worker that ran it:
        # "[gw0] [ 25%] PASSED ALPHA.EXE::Guest-Runs".
        placements = {}
        for worker, suite in re.findall(
                r"\[(gw\d+)\] \[\s*\d+%\] \w+ (\w+\.EXE)::", output):
            placements.setdefault(suite, set()).add(worker)
        assert set(placements) == {"ALPHA.EXE", "BRAVO.EXE"}, output
        # Each suite whole on one worker (the batching survives) ...
        assert all(len(workers) == 1 for workers in placements.values()), \
            placements
        # ... and the two suites on different workers (the tree was
        # actually run in parallel rather than queued on one).
        assert placements["ALPHA.EXE"] != placements["BRAVO.EXE"], placements
        # Both suites ran to their deliberate failure, and both guests
        # came down cleanly enough for pytest to report normally.
        assert "2 failed" in output, output
        assert result.returncode == 1, output
