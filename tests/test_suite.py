# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Unit tests for SuiteBackend, the runner x framework composition."""

import unittest

from testaferro import cpputest
from testaferro.suite import SuiteBackend

LIST_OUTPUT = "Vring.Wraps Vring.Fails\n"
RUN_ALL_OUTPUT = (
    "TEST(Vring, Wraps) - 0 ms\n"
    "TEST(Vring, Fails)\n"
    "vring_test.cpp:42: error: Failure in TEST(Vring, Fails)\n"
    "\texpected <1>\n"
    "\n"
    " - 1 ms\n"
    "Errors (1 failures, 2 tests, 2 ran, 2 checks, 0 ignored, "
    "0 filtered out, 1 ms)\n")
RUN_ONE_OUTPUT = (
    "TEST(Vring, Wraps) - 0 ms\n"
    "OK (2 tests, 1 ran, 1 checks, 0 ignored, 1 filtered out, 0 ms)\n")
EMPTY_RUN_OUTPUT = (
    "OK (2 tests, 0 ran, 0 checks, 0 ignored, 2 filtered out, 0 ms)\n")


class ScriptedRunner:
    """Stands in for the guest-OS aspect: returns canned suite output
    per argv, recording each call. Keyed by the argv token tuple the
    framework builds, which is what a real runner receives."""

    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = []

    def __call__(self, exe_path, args):
        self.calls.append((exe_path, args))
        return self.outputs[args]


class SuiteBackendTests(unittest.TestCase):
    def test_operations_compose_runner_and_framework(self):
        run = ScriptedRunner({
            ("-ln",): LIST_OUTPUT,
            ("-v",): RUN_ALL_OUTPUT,
            ("-v", "-sg", "Vring", "-sn", "Wraps"): RUN_ONE_OUTPUT,
        })
        backend = SuiteBackend("SUITE.EXE", run=run, framework=cpputest)

        ids = backend.list_tests()
        self.assertEqual([str(i) for i in ids],
                         ["Vring.Wraps", "Vring.Fails"])

        outcomes = backend.run_all()
        self.assertEqual([(o.group, o.name, o.passed) for o in outcomes],
                         [("Vring", "Wraps", True),
                          ("Vring", "Fails", False)])

        outcome = backend.run_test("Vring", "Wraps")
        self.assertTrue(outcome.passed)
        # Written out rather than rebuilt from the argv builders: the
        # seam's contract is that argv reaches the runner as the
        # tokens the framework named, and an expectation composed the
        # way the code composes cannot see a wrong composition.
        self.assertEqual(run.calls, [
            ("SUITE.EXE", ("-ln",)),
            ("SUITE.EXE", ("-v",)),
            ("SUITE.EXE", ("-v", "-sg", "Vring", "-sn", "Wraps")),
        ])

    def test_run_test_raises_when_target_did_not_run_it(self):
        run = ScriptedRunner(
            {("-v", "-sg", "Vring", "-sn", "Gone"): EMPTY_RUN_OUTPUT})
        backend = SuiteBackend("SUITE.EXE", run=run, framework=cpputest)

        with self.assertRaisesRegex(LookupError, "Vring.Gone"):
            backend.run_test("Vring", "Gone")

    def test_enumerator_overrides_guest_enumeration(self):
        # e.g. a host-built twin executable enumerating faster than a
        # guest boot; run operations still go through the runner.
        run = ScriptedRunner({})
        backend = SuiteBackend(
            "SUITE.EXE", run=run, framework=cpputest,
            enumerator=lambda: cpputest.parse_list("Vring.Wraps"))

        self.assertEqual([str(i) for i in backend.list_tests()],
                         ["Vring.Wraps"])
        self.assertEqual(run.calls, [])


if __name__ == "__main__":
    unittest.main()
