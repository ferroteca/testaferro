# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Conformance checks a runner package runs in its own test suite.

Usage, in the runner's tests::

    import unittest

    from testaferro_runner_api import conformance

    class MyRunnerConformance(conformance.RunnerContract,
                              unittest.TestCase):
        def make_machine(self):
            return MyRunner(MyRunnerConfig())

The checks are structural — protocol shape, explicit-location
signatures, platform naming, config lineage. They boot nothing, so
they run without an emulator, media, or network; behavioral
verification stays in the runner's own tests."""

from __future__ import annotations

import inspect

from . import PLATFORMS, Runner


class RunnerContract:
    """Mixin of structural conformance checks. Subclass together
    with unittest.TestCase and implement make_machine()."""

    def make_machine(self):
        """Return a test machine: the runner class constructed with
        a representative instance of its config type."""
        raise NotImplementedError(
            "conformance subclasses implement make_machine()")

    def test_machine_satisfies_the_runner_protocol(self):
        self.assertIsInstance(self.make_machine(), Runner)

    def test_platform_is_defined_by_the_spec(self):
        self.assertIn(self.make_machine().platform, PLATFORMS)

    def test_config_matches_the_platform(self):
        machine = self.make_machine()
        self.assertIn(machine.platform, PLATFORMS)
        self.assertIsInstance(machine.config,
                              PLATFORMS[machine.platform])

    def test_operations_take_explicit_locations(self):
        # the spec's concurrency guarantee hangs on these
        # parameters: no process-global home, no hidden state
        machine = self.make_machine()
        self.assertEqual(
            list(inspect.signature(machine.provision).parameters),
            ["dist_dir"])
        self.assertEqual(
            list(inspect.signature(machine.run).parameters),
            ["exe_path", "args", "home"])
