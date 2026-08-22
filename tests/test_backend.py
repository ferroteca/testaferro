# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""The Backend ABC's own behaviour: what a prebuilt backend gets for
free, so that the escape hatch keeps its five operations to implement
(D29)."""

from __future__ import annotations

from testaferro.backend import Backend, TestId, TestOutcome


class FiveOperations(Backend):
    """A consumer's own backend, written to the ABC as documented:
    the five operations and nothing more."""

    def __init__(self):
        self.calls = []

    def list_tests(self):
        return [TestId("Vring", "Wraps"), TestId("Vring", "Fails")]

    def run_test(self, group, name):
        self.calls.append((group, name))
        return TestOutcome(group, name, name != "Fails")

    def run_all(self):
        return [self.run_test("Vring", "Wraps"),
                self.run_test("Vring", "Fails")]


class BackendDefaultsTests:
    def test_run_some_defaults_to_one_run_test_per_name(self):
        backend = FiveOperations()

        outcomes = backend.run_some("Vring", ["Wraps", "Fails"])

        assert [(o.name, o.passed) for o in outcomes] == [
            ("Wraps", True), ("Fails", False)]
        assert backend.calls == [("Vring", "Wraps"), ("Vring", "Fails")]
