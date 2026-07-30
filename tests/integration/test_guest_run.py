# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""The integration tier: the tests that boot a real guest.

**Nothing here runs unless asked for.** P10 forbids the unit tier
starting a guest, and this is the other side of that line rather than
an exception to it — `TESTAFERRO_INTEGRATION` in the environment is
the asking, and without it every case below skips. That keeps the
default `unittest discover -s tests` exactly as cheap as it was,
whether or not discovery ever learns to recurse in here.

What these prove is the half of testaferro no unit test can reach: a
machine that actually boots, an executable that actually arrives on a
drive the guest can name, output a real screen actually carried back,
and a failure that happened somewhere else surfacing here with the
guest's own file and line on it. The suite they run is testaferro's
own (see `guest/`), and it fails one test on purpose, because a run
where everything passes proves only that output was parsed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE = HERE / "guest" / "SUITE.EXE"

ASKED = bool(os.environ.get("TESTAFERRO_INTEGRATION"))

requires_guest = unittest.skipUnless(
    ASKED, "set TESTAFERRO_INTEGRATION=1 to boot a real guest")
requires_suite = unittest.skipUnless(
    SUITE.is_file(), f"{SUITE.name} is not built — see guest/makefile")


@requires_guest
@requires_suite
class GuestSessionTests(unittest.TestCase):
    """One guest session, several questions asked of it.

    A session per assertion would be honest and slow; a real consumer
    boots once and asks repeatedly, so this does too, and the shared
    guest is torn down in tearDownClass however the cases go.
    """

    @classmethod
    def setUpClass(cls):
        from testaferro import reliquary as binding

        cls.backend = binding.suite_backend(str(SUITE))
        cls.backend.start_guest()

    @classmethod
    def tearDownClass(cls):
        cls.backend.stop_guest()

    def test_the_guest_enumerates_its_own_tests(self):
        ids = [str(test_id) for test_id in self.backend.list_tests()]

        self.assertIn("Guest.Runs", ids)
        self.assertIn("Guest.Fails", ids)
        self.assertIn("Guest.RunsToo", ids)

    def test_a_whole_run_comes_back_and_parses(self):
        outcomes = {(o.group, o.name): o for o in self.backend.run_all()}

        self.assertTrue(outcomes[("Guest", "Runs")].passed)
        self.assertTrue(outcomes[("Guest", "RunsToo")].passed)
        self.assertFalse(outcomes[("Guest", "Fails")].passed)

    def test_a_failure_carries_the_guests_own_file_and_line(self):
        # The whole point of the courier: what comes back is where the
        # guest says it went wrong, not where testaferro was standing.
        outcome = self.backend.run_test("Guest", "Fails")

        self.assertFalse(outcome.passed)
        self.assertIn("SUITE", outcome.file.upper())
        self.assertGreater(outcome.line, 0)
        self.assertTrue(outcome.message.strip())

    def test_one_test_can_be_run_on_its_own(self):
        outcome = self.backend.run_test("Guest", "Runs")

        self.assertTrue(outcome.passed)

    def test_the_suite_is_staged_at_rest_with_no_work_drive(self):
        """F4's primary path, which only a guest can prove.

        Zero configuration boots testaferro's own FreeDOS, whose disk
        is the only one the machine has — so the default location is a
        directory on it, staged into the drive *image* between create
        and start, with no drive appended. Everything above this in
        the class has already run off that placement; this states it.
        """
        self.assertEqual(self.backend.location, "C:\\TESTS")

        blueprint = Path(self.backend._home) / "blueprints"
        document = json.loads(
            (blueprint / "testaferro.rlqb").read_text(encoding="utf-8"))
        drives = document[0]["drives"]

        # One disk, the system's own: the work drive D5 supplied is
        # gone rather than merely unused.
        self.assertEqual(sorted(drives), ["hdd0"])
        self.assertEqual(drives["hdd0"]["materialize"], "difference")

    def test_the_guest_reads_the_suite_back_from_where_it_was_staged(self):
        # The staging is real on the guest's side of the glass: DOS
        # itself lists the file at the address testaferro reports.
        import reliquary

        rows = reliquary.exec(f"DIR {self.backend.location}",
                              machine=self.backend._machine,
                              context=self.backend._ctx, timeout=60)

        self.assertIn("SUITE", "\n".join(rows).upper())


@requires_guest
@requires_suite
class GuestCollectionTests(unittest.TestCase):
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

        self.assertIn("SUITE.EXE::Guest-Runs", output, output)
        self.assertIn("SUITE.EXE::Guest-Fails", output, output)
        # One deliberate failure, and the rest passing: a run that is
        # all green would not show the failure path works at all.
        self.assertEqual(result.returncode, 1, output)
        self.assertIn("1 failed", output)

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
            # runs on testaferro's installed system exactly as naming
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
        self.assertIn("SUITE.EXE::Guest-Runs", output, output)
        self.assertIn("SUITE.EXE::Guest-Fails", output, output)
        self.assertIn("1 failed", output)


if __name__ == "__main__":
    unittest.main()
