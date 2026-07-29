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

# The same run as a *guest transport* delivers it, and authored from
# what that transport does rather than pasted out of one (P9). Two
# things change on the way back from a guest screen, and neither is
# CppUTest behaving differently: blank rows are dropped, so the blank
# line after the message is gone; and the message's leading tab is
# rendered as spaces, so there is no tab left to strip. Both once made
# a failure's message swallow the rest of the run.
FAILING_RUN_FROM_A_SCREEN = (
    "TEST(Vring, Wraps) - 0 ms\n"
    "TEST(Vring, Fails)\n"
    "vring_test.cpp:42: error: Failure in TEST(Vring, Fails)\n"
    "        expected <1 0x1>\n"
    "        but was  <2 0x2>\n"
    "        difference starts at position 0 at: <          2  >\n"
    "                                                       ^\n"
    " - 1 ms\n"
    "IGNORE_TEST(Vring, Slow) - 0 ms\n"
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

    def test_a_refusal_says_why_without_quoting_back_the_text(self):
        # The caller passed the text in and still holds it; whoever
        # obtained it is the one who can say where it came from, and
        # is the one who reports it. A grammar states its own reason.
        with self.assertRaises(ValueError) as caught:
            cpputest.parse_run("Bad command or file name\n")

        self.assertNotIn("Bad command or file name", str(caught.exception))
        self.assertIn("summary line", str(caught.exception))

    def test_a_list_refusal_names_the_token_it_choked_on(self):
        with self.assertRaises(ValueError) as caught:
            cpputest.parse_list("Vring.Wraps NotAnId Vring.Fails")

        self.assertIn("'NotAnId'", str(caught.exception))


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

    def test_a_message_ends_where_the_next_thing_begins(self):
        # Without a blank line to stop at, the message used to run on
        # through the timing line, the next test and the summary — so
        # a guest's one-line failure arrived carrying the whole rest
        # of the run. It ends at whatever CppUTest writes next.
        outcomes = {(o.group, o.name): o
                    for o in cpputest.parse_run(FAILING_RUN_FROM_A_SCREEN)}

        failed = outcomes[("Vring", "Fails")]
        self.assertEqual(failed.file, "vring_test.cpp")
        self.assertEqual(failed.line, 42)
        self.assertNotIn("ms", failed.message)
        self.assertNotIn("Errors (", failed.message)
        self.assertNotIn("IGNORE_TEST", failed.message)

    def test_a_screen_rendered_indent_is_removed_but_alignment_is_not(self):
        # The tab CppUTest writes arrives as spaces, so the common
        # indent goes; the caret under a difference report is deeper
        # than that and has to stay where it was pointing.
        outcomes = {(o.group, o.name): o
                    for o in cpputest.parse_run(FAILING_RUN_FROM_A_SCREEN)}

        lines = outcomes[("Vring", "Fails")].message.splitlines()
        self.assertEqual(lines[0], "expected <1 0x1>")
        self.assertEqual(lines[1], "but was  <2 0x2>")
        caret = lines[-1]
        difference = lines[-2]
        self.assertEqual(caret.strip(), "^")
        self.assertEqual(caret.index("^"),
                         difference.index("2", difference.index("<")))

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
        self.assertEqual(cpputest.list_argv(), ("-ln",))
        self.assertEqual(cpputest.run_all_argv(), ("-v",))
        self.assertEqual(cpputest.run_one_argv("Vring", "Wraps"),
                         ("-v", "-sg", "Vring", "-sn", "Wraps"))

    def test_argv_is_tokens_and_not_a_command_line(self):
        """A string is a sequence too, which is what made the flaw
        silent: every caller iterating one gets characters. So say
        what a builder returns, not merely what it equals."""
        for argv in (cpputest.list_argv(), cpputest.run_all_argv(),
                     cpputest.run_one_argv("Vring", "Wraps")):
            self.assertNotIsInstance(argv, str)
            for token in argv:
                self.assertNotIn(" ", token)


if __name__ == "__main__":
    unittest.main()
