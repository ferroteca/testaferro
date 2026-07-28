# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Unit tests for SuiteBackend, the runner x framework composition."""

import unittest

from testaferro import cpputest
from testaferro.backend import TestId, TestOutcome
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


class ScriptedFramework:
    """Stands in for the framework aspect: the five callables P4 says
    an adapter supplies, in an argv spelling and an output grammar
    nothing in testaferro knows. Deliberately unlike CppUTest's, so a
    composition reaching for the real adapter rather than the one it
    was handed fails here instead of passing by coincidence.

    A real adapter is a module of functions (P4). This is an object,
    and works because the seam only ever does attribute lookup — which
    is the whole of what makes the axis pluggable.
    """

    def list_argv(self):
        return ("--enumerate",)

    def run_all_argv(self):
        return ("--run-all",)

    def run_one_argv(self, group, name):
        return ("--run", f"{group}/{name}")

    def parse_list(self, text):
        return [TestId(*line.split("/")) for line in text.split()]

    def parse_run(self, text):
        outcomes = []
        for line in text.splitlines():
            verdict, _, test = line.partition(" ")
            group, _, name = test.partition("/")
            outcomes.append(TestOutcome(group, name, verdict == "PASS"))
        return outcomes


class SuiteBackendTests(unittest.TestCase):
    def test_any_adapter_drives_the_framework_seam(self):
        # The composition names no framework: whatever it was handed
        # builds the argv and reads the output back, and CppUTest's
        # spellings appear nowhere in this case (P4, U6).
        run = ScriptedRunner({
            ("--enumerate",): "Vring/Wraps Vring/Fails\n",
            ("--run-all",): "PASS Vring/Wraps\nFAIL Vring/Fails\n",
            ("--run", "Vring/Wraps"): "PASS Vring/Wraps\n",
        })
        backend = SuiteBackend("SUITE.EXE", run=run,
                               framework=ScriptedFramework())

        self.assertEqual([str(i) for i in backend.list_tests()],
                         ["Vring.Wraps", "Vring.Fails"])
        self.assertEqual(
            [(o.group, o.name, o.passed) for o in backend.run_all()],
            [("Vring", "Wraps", True), ("Vring", "Fails", False)])
        self.assertTrue(backend.run_test("Vring", "Wraps").passed)
        self.assertEqual(run.calls, [
            ("SUITE.EXE", ("--enumerate",)),
            ("SUITE.EXE", ("--run-all",)),
            ("SUITE.EXE", ("--run", "Vring/Wraps")),
        ])

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
