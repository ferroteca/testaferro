# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Unit tests for the interim CppUTest framework aspect."""

import unittest

from testaferro import cpputest


# Verbose output as CppUTest v4.0 actually prints it (eclipse-style
# locations, the default): TestOutput.cpp emits failures as
# '<file>:<line>: error: Failure in TEST(<group>, <name>)' followed by
# tab-indented message lines and a blank line.
FAILING_RUN = (
    "TEST(Vring, Wraps) - 0 ms\n"
    "TEST(Vring, Fails)\n"
    "vring_test.cpp:42: error: Failure in TEST(Vring, Fails)\n"
    "\texpected <1 0x1>\n"
    "\tbut was  <2 0x2>\n"
    "\n"
    " - 1 ms\n"
    "IGNORE_TEST(Vring, Slow) - 0 ms\n"
    "\n"
    "Errors (1 failures, 3 tests, 3 ran, 4 checks, 1 ignored, "
    "0 filtered out, 1 ms)\n")


class ParseTests(unittest.TestCase):
    def test_parse_normalizes_results(self):
        self.assertEqual(cpputest.parse(FAILING_RUN), {
            "ran": {"Vring.Wraps", "Vring.Fails", "Vring.Slow"},
            "failed": {"Vring.Fails"},
            "summary": ("Errors (1 failures, 3 tests, 3 ran, 4 checks, "
                        "1 ignored, 0 filtered out, 1 ms)"),
        })

    def test_parse_requires_summary(self):
        with self.assertRaisesRegex(ValueError, "no CppUTest summary"):
            cpputest.parse("TEST(Math, Adds)\n")


class ParseRunTests(unittest.TestCase):
    def test_outcomes_carry_failure_location_and_message(self):
        outcomes = {(o.group, o.name): o
                    for o in cpputest.parse_run(FAILING_RUN)}

        self.assertEqual(len(outcomes), 3)
        self.assertTrue(outcomes[("Vring", "Wraps")].passed)
        self.assertTrue(outcomes[("Vring", "Slow")].passed)
        failed = outcomes[("Vring", "Fails")]
        self.assertFalse(failed.passed)
        self.assertEqual(failed.file, "vring_test.cpp")
        self.assertEqual(failed.line, 42)
        self.assertEqual(failed.message,
                         "expected <1 0x1>\nbut was  <2 0x2>")

    def test_failure_outside_test_file_uses_failure_site(self):
        # TestOutput.cpp prints a second location line (the actual
        # failure site) when the failure is outside the test file.
        output = ("TEST(Vring, Helper)\n"
                  "vring_test.cpp:10: error: "
                  "Failure in TEST(Vring, Helper)\n"
                  "helpers.cpp:99: error:\n"
                  "\tCHECK(x) failed\n"
                  "\n"
                  " - 0 ms\n"
                  "Errors (1 failures, 1 tests, 1 ran, 1 checks, "
                  "0 ignored, 0 filtered out, 0 ms)\n")

        outcome, = cpputest.parse_run(output)
        self.assertFalse(outcome.passed)
        self.assertEqual(outcome.file, "helpers.cpp")
        self.assertEqual(outcome.line, 99)
        self.assertEqual(outcome.message, "CHECK(x) failed")

    def test_accepts_dos_crlf_line_endings(self):
        outcomes = cpputest.parse_run(FAILING_RUN.replace("\n", "\r\n"))
        self.assertEqual([o.passed for o in outcomes],
                         [True, False, True])


class ListTests(unittest.TestCase):
    def test_parse_list_returns_test_ids(self):
        ids = cpputest.parse_list("Vring.Wraps Vring.Fails\r\n")
        self.assertEqual([(i.group, i.name) for i in ids],
                         [("Vring", "Wraps"), ("Vring", "Fails")])
        self.assertEqual(str(ids[0]), "Vring.Wraps")

    def test_parse_list_rejects_non_enumeration_output(self):
        with self.assertRaisesRegex(ValueError, "not a CppUTest"):
            cpputest.parse_list("Bad command or file name\n")


class ArgvTests(unittest.TestCase):
    def test_argv_builders(self):
        self.assertEqual(cpputest.list_argv(), "-ln")
        self.assertEqual(cpputest.run_all_argv(), "-v")
        self.assertEqual(cpputest.run_one_argv("Vring", "Wraps"),
                         "-v -sg Vring -sn Wraps")


if __name__ == "__main__":
    unittest.main()
