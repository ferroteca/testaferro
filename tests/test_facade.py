# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the facade's batching broker and public pytest surface."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from testaferro.backend import Backend, TestId, TestOutcome
from testaferro.facade import ResultBroker

from test_binfmt import plain_dos_exe_bytes


class FakeBackend(Backend):
    def __init__(self, outcomes):
        self._outcomes = outcomes
        self.calls = []

    def start_guest(self):
        self.calls.append(("start_guest",))

    def stop_guest(self):
        self.calls.append(("stop_guest",))

    def list_tests(self):
        return [TestId(o.group, o.name) for o in self._outcomes]

    def run_test(self, group, name):
        self.calls.append(("run_test", group, name))
        for outcome in self._outcomes:
            if (outcome.group, outcome.name) == (group, name):
                return outcome
        raise LookupError(f"target did not run test {group}.{name}")

    def run_all(self):
        self.calls.append(("run_all",))
        return self._outcomes


OUTCOMES = [
    TestOutcome("Vring", "Wraps", passed=True),
    TestOutcome("Vring", "Fails", passed=False,
                file="vring_test.cpp", line=42, message="expected <1>"),
]

PYTEST_AVAILABLE = importlib.util.find_spec("pytest") is not None
RELIQUARY_AVAILABLE = importlib.util.find_spec("reliquary") is not None


@unittest.skipUnless(PYTEST_AVAILABLE, "pytest is not installed")
class GuestSuiteTargetTests(unittest.TestCase):
    """What guest_suite() does with the target it is handed. Resolving
    a path to a backend is the seam's own (test_resolution); what is
    tested here is the facade's half — that a path goes through it,
    that the call site is where the search starts, and that a prebuilt
    Backend takes no options."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

    def _exe(self, content):
        path = Path(self.tempdir.name) / "SUITE.EXE"
        path.write_bytes(content)
        return path

    @unittest.skipUnless(RELIQUARY_AVAILABLE, "reliquary is not installed")
    def test_path_target_resolves_backend_from_executable(self):
        from unittest import mock

        import testaferro

        def enumerator():
            return [TestId("Vring", "Wraps")]

        exe = self._exe(plain_dos_exe_bytes())
        with mock.patch("testaferro.reliquary.suite_backend",
                        return_value=FakeBackend(OUTCOMES)) as factory:
            suite = testaferro.guest_suite(exe, enumerator=enumerator)
        factory.assert_called_once_with(exe, enumerator=enumerator)
        self.assertTrue(callable(suite))

    @unittest.skipUnless(RELIQUARY_AVAILABLE, "reliquary is not installed")
    def test_guest_suite_searches_for_ini_from_the_call_site(self):
        from unittest import mock

        import testaferro
        from testaferro import environments

        environments._clear_for_tests()
        self.addCleanup(environments._clear_for_tests)

        def enumerator():
            return [TestId("Vring", "Wraps")]

        exe = self._exe(plain_dos_exe_bytes())
        with mock.patch("testaferro.environments.load_config") as load:
            with mock.patch("testaferro.reliquary.suite_backend",
                            return_value=FakeBackend(OUTCOMES)):
                testaferro.guest_suite(exe, enumerator=enumerator)
        load.assert_called_once()
        self.assertEqual(
            Path(load.call_args.kwargs["search_from"]).resolve(),
            Path(__file__).resolve().parent)

    @unittest.skipUnless(RELIQUARY_AVAILABLE, "reliquary is not installed")
    def test_a_host_side_enumerator_starts_no_guest(self):
        # The list comes from the host, so starting a guest here would
        # boot a machine and ask it nothing — the cost the twin exists
        # to avoid, and what the collection plugin already avoids.
        from unittest import mock

        import testaferro

        backend = FakeBackend(OUTCOMES)
        exe = self._exe(plain_dos_exe_bytes())
        with mock.patch("testaferro.reliquary.suite_backend",
                        return_value=backend):
            testaferro.guest_suite(
                exe, enumerator=lambda: [TestId("Vring", "Wraps")])

        self.assertEqual(backend.calls, [])

    def test_a_prebuilt_backend_still_gets_its_guest(self):
        # It may be what makes list_tests() work, and a prebuilt
        # backend cannot carry an enumerator to say otherwise.
        import testaferro

        backend = FakeBackend(OUTCOMES)
        testaferro.guest_suite(backend)

        self.assertEqual(backend.calls,
                         [("start_guest",), ("stop_guest",)])

    def test_backend_target_rejects_path_only_options(self):
        import testaferro

        with self.assertRaisesRegex(TypeError, "executable path"):
            testaferro.guest_suite(FakeBackend(OUTCOMES),
                                  boot_image="OTHER.IMG")

    def test_backend_target_rejects_an_environment_selector(self):
        import testaferro

        with self.assertRaisesRegex(TypeError, "environment"):
            testaferro.guest_suite(FakeBackend(OUTCOMES),
                                  environment="freedos")

    def test_items_report_the_guest_suite_call_site_as_source(self):
        # IDE per-item actions (run-one, jump-to-source) resolve the
        # test function via its code object; it must point at the
        # caller's module and call line, not at the facade.
        import inspect

        import testaferro

        call_line = inspect.currentframe().f_lineno + 1
        suite = testaferro.guest_suite(FakeBackend(OUTCOMES))

        self.assertEqual(suite.__code__.co_filename, __file__)
        self.assertEqual(suite.__code__.co_firstlineno, call_line)



class ResultBrokerTests(unittest.TestCase):
    def test_full_selection_batches_one_run_all(self):
        backend = FakeBackend(OUTCOMES)
        ids = [TestId("Vring", "Wraps"), TestId("Vring", "Fails")]
        broker = ResultBroker(backend, ids)

        self.assertTrue(broker.outcome(ids[0], ids).passed)
        self.assertFalse(broker.outcome(ids[1], ids).passed)
        self.assertEqual(backend.calls, [("run_all",)])

    def test_narrowed_selection_runs_tests_individually(self):
        backend = FakeBackend(OUTCOMES)
        ids = [TestId("Vring", "Wraps"), TestId("Vring", "Fails")]
        broker = ResultBroker(backend, ids)
        selected = [ids[1]]

        outcome = broker.outcome(ids[1], selected)
        self.assertFalse(outcome.passed)
        # Memoized: a second lookup must not re-run the guest.
        broker.outcome(ids[1], selected)
        self.assertEqual(backend.calls, [("run_test", "Vring", "Fails")])

    def test_test_id_components_are_preserved(self):
        outcome = TestOutcome("namespace.group", "case", passed=True)
        backend = FakeBackend([outcome])
        test_id = TestId(outcome.group, outcome.name)
        broker = ResultBroker(backend, [test_id])

        self.assertTrue(broker.outcome(test_id, []).passed)
        self.assertEqual(
            backend.calls,
            [("run_test", "namespace.group", "case")])

    def test_missing_outcome_in_batch_raises_lookup_error(self):
        backend = FakeBackend(OUTCOMES[:1])
        ids = [TestId("Vring", "Wraps"), TestId("Vring", "Gone")]
        broker = ResultBroker(backend, ids)

        with self.assertRaisesRegex(LookupError, "Vring.Gone"):
            broker.outcome(ids[1], ids)


@unittest.skipUnless(PYTEST_AVAILABLE, "pytest is not installed")
class GuestSuiteTests(unittest.TestCase):
    def _run_pytest(self, *args):
        with tempfile.TemporaryDirectory(
                dir=Path(__file__).parent) as directory:
            events = Path(directory) / "events.txt"
            test_module = Path(directory) / "test_guest.py"
            test_module.write_text(
                "import testaferro\n"
                "from testaferro.backend import TestId, TestOutcome\n"
                "\n"
                f"events = {str(events)!r}\n"
                "\n"
                "class RecordingBackend:\n"
                "    def record(self, event):\n"
                "        with open(events, 'a') as stream:\n"
                "            stream.write(event + '\\n')\n"
                "\n"
                "    def start_guest(self):\n"
                "        self.record('start')\n"
                "\n"
                "    def stop_guest(self):\n"
                "        self.record('stop')\n"
                "\n"
                "    def list_tests(self):\n"
                "        self.record('list')\n"
                "        return [TestId('namespace.group', 'Passes'),\n"
                "                TestId('Group', 'Fails')]\n"
                "\n"
                "    def run_all(self):\n"
                "        self.record('run_all')\n"
                "        return [TestOutcome(\n"
                "                    'namespace.group', 'Passes', True),\n"
                "                TestOutcome(\n"
                "                    'Group', 'Fails', False,\n"
                "                    'guest.cpp', 42, 'expected <1>')]\n"
                "\n"
                "    def run_test(self, group, name):\n"
                "        self.record(f'run_test:{group}:{name}')\n"
                "        return TestOutcome(group, name, True)\n"
                "\n"
                "test_guest_case = testaferro.guest_suite("
                "RecordingBackend())\n",
                encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", str(test_module),
                 *args],
                capture_output=True, text=True, check=False)
            recorded = events.read_text(encoding="utf-8").splitlines()
        return result, recorded

    def test_item_ids_join_group_and_name_with_a_dash(self):
        # not str(TestId): a dot inside a parametrize id breaks
        # IDE tree->target mapping (dots are hierarchy separators
        # there), turning run-this-item into run-the-whole-file
        result, _ = self._run_pytest("--collect-only")

        self.assertIn("test_guest_case[namespace.group-Passes]",
                      result.stdout)
        self.assertIn("test_guest_case[Group-Fails]", result.stdout)

    def test_full_suite_batches_and_balances_guest_sessions(self):
        result, events = self._run_pytest()

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(
            "guest test failed: guest.cpp:42: expected <1>",
            result.stdout)
        self.assertEqual(events, [
            "start", "list", "stop", "start", "run_all", "stop",
        ])

    def test_narrowed_selection_preserves_id_and_balances_guests(self):
        result, events = self._run_pytest("-k", "Passes")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1 passed, 1 deselected", result.stdout)
        self.assertEqual(events, [
            "start", "list", "stop", "start",
            "run_test:namespace.group:Passes", "stop",
        ])


if __name__ == "__main__":
    unittest.main()
