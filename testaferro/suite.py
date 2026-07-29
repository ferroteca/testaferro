# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""SuiteBackend: internal execution × framework composition.

The reliquary-backed platform binding supplies the execution callable;
the framework adapter exposes list_argv/run_all_argv/run_one_argv and
parse_list/parse_run (e.g. testaferro.cpputest). Neither aspect knows
the other exists. The callable remains an internal testing and
composition seam, not a public runner contract.

    backend = SuiteBackend("VRING16.EXE",
                           run=run_guest_program,
                           framework=cpputest)

**Argv crosses this seam as a token sequence**, and passes through
untouched: `run(exe_path, args)` receives what the builder returned —
`("-v", "-sg", "Vring", "-sn", "Wraps")` — and the callable decides
how those tokens reach the program, because only it knows what does
the executing. This module joins nothing and quotes nothing; a
composition that flattened the tokens on the way past would be
guessing at a command line for a runner it deliberately knows
nothing about.

The optional `enumerator` replaces guest enumeration with a faster
source of the same list — e.g. a host-built twin executable — without
changing where the tests actually run.
"""

from __future__ import annotations

from .backend import Backend, GuestOutputError, TestId, TestOutcome


class SuiteBackend(Backend):
    def __init__(self, exe_path, run, framework, enumerator=None):
        self._exe = exe_path
        self._run = run
        self._framework = framework
        self._enumerator = enumerator

    def list_tests(self) -> "list[TestId]":
        if self._enumerator is not None:
            return self._enumerator()
        argv = self._framework.list_argv()
        return self._parse(self._framework.parse_list, argv)

    def run_test(self, group, name) -> TestOutcome:
        argv = self._framework.run_one_argv(group, name)
        outcomes = self._parse(self._framework.parse_run, argv)
        for outcome in outcomes:
            if (outcome.group, outcome.name) == (group, name):
                return outcome
        raise LookupError(
            f"target did not run test {group}.{name} "
            "(host and target test lists out of sync?)")

    def run_all(self) -> "list[TestOutcome]":
        argv = self._framework.run_all_argv()
        return self._parse(self._framework.parse_run, argv)

    def _parse(self, grammar, argv):
        """Perform one exchange and read it, or say what was exchanged.

        This is the only place both halves are in hand at once — the
        argv that went out and the text that came back — so it is
        where an adapter's refusal becomes something an entry point
        can report. The grammar says why it refused and nothing about
        provenance; it never saw the guest, and D17's reasoning cuts
        the same way here as it does for quoting.
        """
        output = self._run(self._exe, argv)
        try:
            return grammar(output)
        except ValueError as error:
            raise GuestOutputError(str(error), argv, output) from None
