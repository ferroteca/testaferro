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

The optional `enumerator` replaces guest enumeration with a faster
source of the same list — e.g. a host-built twin executable — without
changing where the tests actually run.
"""

from __future__ import annotations

from .backend import Backend, TestId, TestOutcome


class SuiteBackend(Backend):
    def __init__(self, exe_path, run, framework, enumerator=None):
        self._exe = exe_path
        self._run = run
        self._framework = framework
        self._enumerator = enumerator

    def list_tests(self) -> "list[TestId]":
        if self._enumerator is not None:
            return self._enumerator()
        return self._framework.parse_list(
            self._run(self._exe, self._framework.list_argv()))

    def run_test(self, group, name) -> TestOutcome:
        outcomes = self._framework.parse_run(
            self._run(self._exe,
                      self._framework.run_one_argv(group, name)))
        for outcome in outcomes:
            if (outcome.group, outcome.name) == (group, name):
                return outcome
        raise LookupError(
            f"target did not run test {group}.{name} "
            "(host and target test lists out of sync?)")

    def run_all(self) -> "list[TestOutcome]":
        return self._framework.parse_run(
            self._run(self._exe, self._framework.run_all_argv()))
