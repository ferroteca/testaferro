# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""CppUTest framework adapter.

Knows CppUTest and nothing else: the argv that makes a suite
executable enumerate or run tests, and the grammar of the resulting
output. How and where the executable runs — the guest-OS aspect — is
deliberately not this module's business; the
two aspects compose in a SuiteBackend (testaferro.suite) or directly
at the call site:

    log = run_guest_program(exe, args=cpputest.run_all_argv())
    results = cpputest.parse(log)

**Every argv builder returns a sequence of tokens, never a command
line.** Spelling one is the executing side's business — a DOS guest
takes a single string, a host subprocess takes a list — and only
that side knows which. Handing over a string instead would make an
adapter that has never seen a command line decide how one is
quoted, and leaves each caller to guess whether to split it back.

Output grammars follow CppUTest v4.0's own source (TestOutput.cpp,
TestRegistry.cpp): eclipse-style failure locations (the default),
'-ln' space-separated 'Group.Name' enumeration.
"""

from __future__ import annotations

import re

from .backend import TestId, TestOutcome

# Suite argv for each backend operation, as token sequences.
# VERBOSE_ARGS produces the run output parse()/parse_run()
# understand; LIST_ARGS produces the enumeration parse_list()
# understands.
VERBOSE_ARGS = ("-v",)
LIST_ARGS = ("-ln",)

# CppUTest verbose (-v) output. Test ids are 'Group.Name', matching
# the executable's own -ln enumeration format.
_RAN = re.compile(r"^(?:IGNORE_)?TEST\((\w+), (\w+)\)", re.M)
# Eclipse-style failure header: '<file>:<line>: error: Failure in
# TEST(<group>, <name>)'. When the failure is outside the test file,
# a second '<file>:<line>: error:' location line follows with the
# actual failure site; the tab-indented message lines come last.
_FAILED = re.compile(
    r"^(.*):(\d+): error: Failure in TEST\((\w+), (\w+)\)$", re.M)
_LOCATION = re.compile(r"^(.*):(\d+): error:$")
_SUMMARY = re.compile(r"^(?:OK|Errors) \(.*\)", re.M)
_LIST_ID = re.compile(r"(\w+)\.(\w+)$")
# The per-test timing line CppUTest writes once a test is done. It is
# what actually follows a failure's message, and the blank line
# between them is the thing a transport is free to lose.
_TIMING = re.compile(r"^\s*-\s+\d+\s*ms\s*$")


def list_argv():
    """Suite argv that enumerates tests in parse_list()'s format."""
    return LIST_ARGS


def run_all_argv():
    """Suite argv that runs every test in parse_run()'s format."""
    return VERBOSE_ARGS


def run_one_argv(group, name):
    """Suite argv that runs exactly one test in parse_run()'s
    format ('-sg'/'-sn' are CppUTest's strict-match filters)."""
    return VERBOSE_ARGS + ("-sg", group, "-sn", name)


def parse_list(text):
    """Parse '-ln' enumeration output: space-separated 'Group.Name'
    tokens. Returns a list of TestId.

    Raises ValueError naming the token it choked on, and not the text
    it was given: the caller passed that in and still has it, and
    whoever obtained it is the one who can say where it came from.
    """
    text = text.replace("\r\n", "\n")
    ids = []
    for token in text.split():
        match = _LIST_ID.fullmatch(token)
        if not match:
            raise ValueError(
                f"{token!r} is not a CppUTest 'Group.Name' test id, so "
                "this is not a '-ln' test list")
        ids.append(TestId(*match.groups()))
    return ids


def _ends_message(line):
    """Whether this line is the end of a failure's message.

    CppUTest writes a blank line after the message and then the test's
    timing line, so a blank line is the natural terminator — and it is
    the one thing a transport may not deliver. A guest screen read
    back row by row has its blank rows dropped, which left the message
    running on into the next test and the summary. So the message ends
    at the blank line **or at whatever CppUTest writes next**: the
    timing line, the next test's header, another failure, or the
    summary. Each of those is in the framework's own output, not in
    any sample (P9).
    """
    return (not line.strip()
            or bool(_TIMING.match(line))
            or bool(_RAN.match(line))
            or bool(_FAILED.match(line))
            or bool(_LOCATION.match(line))
            or bool(_SUMMARY.match(line)))


def _dedented(message):
    """Message lines with their common indent removed.

    CppUTest indents each message line with a tab. A guest console
    renders that tab as spaces, so stripping tabs specifically finds
    nothing to strip on a real screen. Removing the *common* leading
    whitespace handles both, and unlike stripping each line it leaves
    the deeper indentation alone — which matters, because a
    difference report points at a column with a caret and a caret that
    has moved is worse than one that is indented.
    """
    filled = [line for line in message if line.strip()]
    if not filled:
        return message
    indents = [len(line) - len(line.lstrip()) for line in filled]
    common = min(indents)
    return [line[common:] if line.strip() else line for line in message]


def _failures(text):
    """Map 'Group.Name' -> (file, line, message) for each failure
    block in verbose output."""
    lines = text.splitlines()
    failures = {}
    for match in _FAILED.finditer(text):
        file, line, group, name = match.groups()
        rest = lines[text.count("\n", 0, match.start()) + 1:]
        if rest and _LOCATION.match(rest[0]):
            # Failure outside the test file: the second location
            # line carries the actual failure site.
            file, line = _LOCATION.match(rest[0]).groups()
            rest = rest[1:]
        message = []
        for text_line in rest:
            if _ends_message(text_line):
                break
            message.append(text_line)
        failures[f"{group}.{name}"] = (
            file, int(line), "\n".join(_dedented(message)).rstrip())
    return failures


def parse_run(text):
    """Parse verbose (-v) run output into a list of TestOutcome, in
    output order. Raises ValueError when the output carries no
    CppUTest summary line (the run died before finishing) — naming
    what was missing rather than repeating the text the caller
    supplied. DOS logs arrive with CRLF line endings; both endings are
    accepted."""
    text = text.replace("\r\n", "\n")
    if not _SUMMARY.search(text):
        raise ValueError(
            "no CppUTest summary line ('OK (...)' or 'Errors (...)'), "
            "so the suite did not run to completion")
    failures = _failures(text)
    outcomes = []
    for group, name in _RAN.findall(text):
        file, line, message = failures.get(f"{group}.{name}", ("", 0, ""))
        outcomes.append(TestOutcome(
            group=group, name=name,
            passed=f"{group}.{name}" not in failures,
            file=file, line=line, message=message))
    return outcomes


def parse(text):
    """Normalize CppUTest verbose output: return a dict with "ran" and
    "failed" (sets of 'Group.Name' ids) and "summary" (the OK/Errors
    line)."""
    outcomes = parse_run(text)
    return {
        "ran": {f"{o.group}.{o.name}" for o in outcomes},
        "failed": {f"{o.group}.{o.name}" for o in outcomes
                   if not o.passed},
        "summary": _SUMMARY.search(text).group(0),
    }
