# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
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

**A subset of one group is one exchange where the adapter allows it**
(F3, D29). `run_some(group, names)` asks the adapter for its optional
sixth callable, `run_some_argv(group, names)`; an adapter supplying
only P4's five gets one exchange per name, which is what every
subset used to cost. The names are cut to fit the executing side's
own `argv_budget` — a DOS program sees at most 125 characters of
arguments, and whoever types the line knows what else is on it — so
a large subset is several exchanges rather than a truncated one.
This module still joins nothing: the budget is measured the way the
executing side will spend it, one separating space per token, and
the tokens cross as tokens.
"""

from __future__ import annotations

from .backend import Backend, GuestOutputError, TestId, TestOutcome


class SuiteBackend(Backend):
    def __init__(self, exe_path, run, framework, enumerator=None,
                 argv_budget=None):
        self._exe = exe_path
        self._run = run
        self._framework = framework
        self._enumerator = enumerator
        # Characters of argv the executing side can carry in one
        # exchange: an int, a zero-argument callable answering at run
        # time (the line a binding types is only known once the guest
        # is placed), or None for no limit.
        self._argv_budget = argv_budget

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

    def run_some(self, group, names) -> "list[TestOutcome]":
        names = list(names)
        builder = getattr(self._framework, "run_some_argv", None)
        if builder is None:
            return Backend.run_some(self, group, names)
        wanted = {}
        for chunk in self._chunks(builder, group, names):
            outcomes = self._parse(self._framework.parse_run,
                                   builder(group, chunk))
            for outcome in outcomes:
                wanted.setdefault((outcome.group, outcome.name), outcome)
        results = []
        for name in names:
            if (group, name) not in wanted:
                raise LookupError(
                    f"target did not run test {group}.{name} "
                    "(host and target test lists out of sync?)")
            results.append(wanted[(group, name)])
        return results

    def _chunks(self, builder, group, names):
        """Cut `names` into runs whose argv fits the budget.

        Greedy and in order: a name goes into the current chunk while
        the argv for the chunk plus that name still fits, else it
        opens the next one. A name that does not fit on its own goes
        out alone regardless — the single-test argv would be no
        shorter, and the executing side is the one to refuse it.
        """
        budget = self._argv_budget
        if callable(budget):
            budget = budget()
        if budget is None:
            yield names
            return
        chunk = []
        for name in names:
            if chunk and _spent(builder(group, chunk + [name])) > budget:
                yield chunk
                chunk = []
            chunk.append(name)
        if chunk:
            yield chunk

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


def _spent(argv):
    """Characters an argv costs on a command line: the tokens and one
    separating space between each — measured, not spelled, since the
    spelling is the executing side's."""
    return sum(len(token) for token in argv) + max(len(argv) - 1, 0)
