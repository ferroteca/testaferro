# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Unit tests for the interim CppUTest framework aspect."""

import pytest

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


class ParseTests:
    def test_parse_normalizes_results(self):
        assert cpputest.parse(FAILING_RUN) == {
            "ran": {"Vring.Wraps", "Vring.Fails", "Vring.Slow"},
            "failed": {"Vring.Fails"},
            "summary": ("Errors (1 failures, 3 tests, 3 ran, 4 checks, "
                        "1 ignored, 0 filtered out, 1 ms)"),
        }

    def test_parse_requires_summary(self):
        with pytest.raises(ValueError, match="no CppUTest summary"):
            cpputest.parse("TEST(Math, Adds)\n")

    def test_a_refusal_says_why_without_quoting_back_the_text(self):
        # The caller passed the text in and still holds it; whoever
        # obtained it is the one who can say where it came from, and
        # is the one who reports it. A grammar states its own reason.
        with pytest.raises(ValueError) as caught:
            cpputest.parse_run("Bad command or file name\n")

        assert "Bad command or file name" not in str(caught.value)
        assert "summary line" in str(caught.value)

    def test_a_list_refusal_names_the_token_it_choked_on(self):
        with pytest.raises(ValueError) as caught:
            cpputest.parse_list("Vring.Wraps NotAnId Vring.Fails")

        assert "'NotAnId'" in str(caught.value)


class ParseRunTests:
    def test_outcomes_carry_failure_location_and_message(self):
        outcomes = {(o.group, o.name): o
                    for o in cpputest.parse_run(FAILING_RUN)}

        assert len(outcomes) == 3
        assert outcomes[("Vring", "Wraps")].passed
        assert outcomes[("Vring", "Slow")].passed
        failed = outcomes[("Vring", "Fails")]
        assert not failed.passed
        assert failed.file == "vring_test.cpp"
        assert failed.line == 42
        assert failed.message == "expected <1 0x1>\nbut was  <2 0x2>"

    def test_a_message_ends_where_the_next_thing_begins(self):
        # Without a blank line to stop at, the message used to run on
        # through the timing line, the next test and the summary — so
        # a guest's one-line failure arrived carrying the whole rest
        # of the run. It ends at whatever CppUTest writes next.
        outcomes = {(o.group, o.name): o
                    for o in cpputest.parse_run(FAILING_RUN_FROM_A_SCREEN)}

        failed = outcomes[("Vring", "Fails")]
        assert failed.file == "vring_test.cpp"
        assert failed.line == 42
        assert "ms" not in failed.message
        assert "Errors (" not in failed.message
        assert "IGNORE_TEST" not in failed.message

    def test_a_screen_rendered_indent_is_removed_but_alignment_is_not(self):
        # The tab CppUTest writes arrives as spaces, so the common
        # indent goes; the caret under a difference report is deeper
        # than that and has to stay where it was pointing.
        outcomes = {(o.group, o.name): o
                    for o in cpputest.parse_run(FAILING_RUN_FROM_A_SCREEN)}

        lines = outcomes[("Vring", "Fails")].message.splitlines()
        assert lines[0] == "expected <1 0x1>"
        assert lines[1] == "but was  <2 0x2>"
        caret = lines[-1]
        difference = lines[-2]
        assert caret.strip() == "^"
        assert caret.index("^") == difference.index(
            "2", difference.index("<"))

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
        assert not outcome.passed
        assert outcome.file == "helpers.cpp"
        assert outcome.line == 99
        assert outcome.message == "CHECK(x) failed"

    def test_accepts_dos_crlf_line_endings(self):
        outcomes = cpputest.parse_run(FAILING_RUN.replace("\n", "\r\n"))
        assert [o.passed for o in outcomes] == [True, False, True]


class FailureCountTests:
    """The summary's own failure count, cross-checked against the
    failure blocks actually parsed. The count is CppUTest's
    (TestResult.cpp prints it), so a block the transport mangled
    beyond the grammar's reach — a header wrapped on a space, say —
    surfaces as a refusal instead of as a passing test. Failing
    loud is the point: the alternative was a silent false pass.
    """

    def test_a_missing_failure_block_is_refused_not_passed(self):
        # Summary says one failure; no block parsed. Before the
        # check, this text reported every test as passing.
        mangled = (
            "TEST(Vring, Fails)\n"
            "vring_test.cpp:42: error: Failure in\n"
            "TEST(Vring, Fails)\n"
            "        but was  <2 0x2>\n"
            " - 1 ms\n"
            "Errors (1 failures, 1 tests, 1 ran, 1 checks, 0 ignored, "
            "0 filtered out, 1 ms)\n")
        with pytest.raises(ValueError, match="1 failure"):
            cpputest.parse_run(mangled)

    def test_two_failure_blocks_in_one_test_match_the_stated_count(self):
        # With non-fatal checks a single test reports several failure
        # blocks; the count compares blocks, not failed tests.
        text = (
            "TEST(Vring, Fails)\n"
            "vring_test.cpp:42: error: Failure in TEST(Vring, Fails)\n"
            "        expected <1 0x1>\n"
            "vring_test.cpp:43: error: Failure in TEST(Vring, Fails)\n"
            "        expected <2 0x2>\n"
            " - 1 ms\n"
            "Errors (2 failures, 1 tests, 1 ran, 2 checks, 0 ignored, "
            "0 filtered out, 1 ms)\n")
        outcomes = cpputest.parse_run(text)
        assert [o.passed for o in outcomes] == [False]


class ListTests:
    def test_parse_list_returns_test_ids(self):
        ids = cpputest.parse_list("Vring.Wraps Vring.Fails\r\n")
        assert ([(i.group, i.name) for i in ids]
                == [("Vring", "Wraps"), ("Vring", "Fails")])
        assert str(ids[0]) == "Vring.Wraps"

    def test_parse_list_rejects_non_enumeration_output(self):
        with pytest.raises(ValueError, match="not a CppUTest"):
            cpputest.parse_list("Bad command or file name\n")


class ArgvTests:
    def test_argv_builders(self):
        assert cpputest.list_argv() == ("-ln",)
        assert cpputest.run_all_argv() == ("-v",)
        assert (cpputest.run_one_argv("Vring", "Wraps")
                == ("-v", "-sg", "Vring", "-sn", "Wraps"))
        # One strict group filter and one strict name filter per
        # wanted test: CppUTest runs a test when it matches *any*
        # group filter and *any* name filter, so a single `-sg`
        # scopes every `-sn` to that group and nothing else runs
        # (D24, D29).
        assert (cpputest.run_some_argv("Vring", ["Wraps", "Empties"])
                == ("-v", "-sg", "Vring", "-sn", "Wraps",
                    "-sn", "Empties"))

    def test_argv_is_tokens_and_not_a_command_line(self):
        """A string is a sequence too, which is what made the flaw
        silent: every caller iterating one gets characters. So say
        what a builder returns, not merely what it equals."""
        for argv in (cpputest.list_argv(), cpputest.run_all_argv(),
                     cpputest.run_one_argv("Vring", "Wraps"),
                     cpputest.run_some_argv("Vring", ["Wraps", "Empties"])):
            assert not isinstance(argv, str)
            for token in argv:
                assert " " not in token
