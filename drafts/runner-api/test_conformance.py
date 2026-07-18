# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the conformance kit: a conforming runner passes every
check; characteristic defects fail the check that guards them."""

import unittest

import testaferro_runner_api as api
from testaferro_runner_api import conformance

from test_api import FakeMachine


class FakeMachineConformance(conformance.RunnerContract,
                             unittest.TestCase):
    """The kit, used exactly as a runner package would use it."""

    def make_machine(self):
        return FakeMachine()


def _failures(machine):
    """Run the contract against one machine, returning the names of
    failing checks."""

    class Case(conformance.RunnerContract, unittest.TestCase):
        def make_machine(self):
            return machine

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Case)
    result = unittest.TestResult()
    suite.run(result)
    return sorted(test.id().rsplit(".", 1)[-1]
                  for test, _ in result.failures + result.errors)


class DefectDetectionTests(unittest.TestCase):
    def test_global_home_shaped_run_fails_the_signature_check(self):
        class GlobalHomeMachine(FakeMachine):
            def run(self, exe_path, args):  # no explicit home
                return ""

        self.assertIn("test_operations_take_explicit_locations",
                      _failures(GlobalHomeMachine()))

    def test_undefined_platform_fails_the_platform_check(self):
        class UndefinedPlatformMachine(FakeMachine):
            platform = "os2"

        self.assertIn("test_platform_is_defined_by_the_spec",
                      _failures(UndefinedPlatformMachine()))

    def test_foreign_config_fails_the_config_check(self):
        class ForeignConfigMachine(FakeMachine):
            def __init__(self):
                super().__init__()
                self.config = {"boot_image": None}

        self.assertIn("test_config_matches_the_platform",
                      _failures(ForeignConfigMachine()))

    def test_generic_config_fails_the_config_check(self):
        # a dos machine's config must be the dos platform's type,
        # not the bare generic config
        class GenericConfigMachine(FakeMachine):
            def __init__(self):
                super().__init__()
                self.config = api.RunnerConfig()

        self.assertIn("test_config_matches_the_platform",
                      _failures(GenericConfigMachine()))

    def test_missing_operation_fails_the_protocol_check(self):
        class NoProvisionMachine(FakeMachine):
            provision = None

        self.assertIn("test_machine_satisfies_the_runner_protocol",
                      _failures(NoProvisionMachine()))


if __name__ == "__main__":
    unittest.main()
