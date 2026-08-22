# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Tests for the facade's batching broker and public pytest surface."""

from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import mock

import pytest

from testaferro.backend import TestId, TestOutcome
from testaferro.facade import ResultBroker

from helpers import (FakeBackend, OUTCOMES, plain_dos_exe_bytes,
                      requires_pytest, requires_reliquary)


@requires_pytest
class GuestSuiteTargetTests:
    """What guest_suite() does with the target it is handed. Resolving
    a path to a backend is the seam's own (test_resolution); what is
    tested here is the facade's half — that a path goes through it,
    that the call site is where the search starts, and that a prebuilt
    Backend takes no options."""

    def _exe(self, tmp_path, content):
        path = tmp_path / "SUITE.EXE"
        path.write_bytes(content)
        return path

    @requires_reliquary
    def test_path_target_resolves_backend_from_executable(self, tmp_path):
        import testaferro

        def enumerator():
            return [TestId("Vring", "Wraps")]

        exe = self._exe(tmp_path, plain_dos_exe_bytes())
        with mock.patch("testaferro.reliquary.suite_backend",
                        return_value=FakeBackend(OUTCOMES)) as factory:
            suite = testaferro.guest_suite(exe, enumerator=enumerator)
        factory.assert_called_once_with(exe, enumerator=enumerator)
        assert callable(suite)

    @requires_reliquary
    def test_guest_suite_searches_for_ini_from_the_call_site(
            self, tmp_path, clean_environments):
        import testaferro

        def enumerator():
            return [TestId("Vring", "Wraps")]

        exe = self._exe(tmp_path, plain_dos_exe_bytes())
        with mock.patch("testaferro.environments.load_config") as load:
            with mock.patch("testaferro.reliquary.suite_backend",
                            return_value=FakeBackend(OUTCOMES)):
                testaferro.guest_suite(exe, enumerator=enumerator)
        load.assert_called_once()
        assert (Path(load.call_args.kwargs["search_from"]).resolve()
                == Path(__file__).resolve().parent)

    @requires_reliquary
    def test_a_host_side_enumerator_starts_no_guest(self, tmp_path):
        # The list comes from the host, so starting a guest here would
        # boot a machine and ask it nothing — the cost the twin exists
        # to avoid, and what the collection plugin already avoids.
        import testaferro

        backend = FakeBackend(OUTCOMES)
        exe = self._exe(tmp_path, plain_dos_exe_bytes())
        with mock.patch("testaferro.reliquary.suite_backend",
                        return_value=backend):
            testaferro.guest_suite(
                exe, enumerator=lambda: [TestId("Vring", "Wraps")])

        assert backend.calls == []

    def test_a_prebuilt_backend_still_gets_its_guest(self):
        # It may be what makes list_tests() work, and a prebuilt
        # backend cannot carry an enumerator to say otherwise.
        import testaferro

        backend = FakeBackend(OUTCOMES)
        testaferro.guest_suite(backend)

        assert backend.calls == [("start_guest",), ("stop_guest",)]

    def test_backend_target_rejects_path_only_options(self):
        import testaferro

        with pytest.raises(TypeError, match="executable path"):
            testaferro.guest_suite(FakeBackend(OUTCOMES),
                                  boot_image="OTHER.IMG")

    def test_backend_target_rejects_an_environment_selector(self):
        import testaferro

        with pytest.raises(TypeError, match="environment"):
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

        assert suite.__code__.co_filename == __file__
        assert suite.__code__.co_firstlineno == call_line


class ResultBrokerTests:
    def test_full_selection_batches_one_run_all(self):
        backend = FakeBackend(OUTCOMES)
        ids = [TestId("Vring", "Wraps"), TestId("Vring", "Fails")]
        broker = ResultBroker(backend, ids)

        assert broker.outcome(ids[0], ids).passed
        assert not broker.outcome(ids[1], ids).passed
        assert backend.calls == [("run_all",)]

    def test_narrowed_selection_runs_tests_individually(self):
        backend = FakeBackend(OUTCOMES)
        ids = [TestId("Vring", "Wraps"), TestId("Vring", "Fails")]
        broker = ResultBroker(backend, ids)
        selected = [ids[1]]

        outcome = broker.outcome(ids[1], selected)
        assert not outcome.passed
        # Memoized: a second lookup must not re-run the guest.
        broker.outcome(ids[1], selected)
        assert backend.calls == [("run_test", "Vring", "Fails")]

    def test_a_narrowed_selection_is_batched_per_group(self):
        # Several selected tests of one group go out in one exchange;
        # a second group is a second exchange, because CppUTest's
        # filters cross-multiply across groups (D24). A lone selected
        # test keeps the single-test operation.
        outcomes = [TestOutcome("Vring", "Wraps", True),
                    TestOutcome("Vring", "Fails", False),
                    TestOutcome("Vring", "Empties", True),
                    TestOutcome("Ring", "Alone", True),
                    TestOutcome("Ring", "Skipped", True)]
        backend = FakeBackend(outcomes)
        ids = [TestId(o.group, o.name) for o in outcomes]
        broker = ResultBroker(backend, ids)
        selected = [ids[0], ids[1], ids[3]]

        assert broker.outcome(ids[0], selected).passed
        assert not broker.outcome(ids[1], selected).passed
        assert broker.outcome(ids[3], selected).passed
        assert backend.calls == [
            ("run_some", "Vring", ("Wraps", "Fails")),
            ("run_test", "Ring", "Alone"),
        ]

    def test_a_batched_group_missing_one_raises_lookup_error(self):
        backend = FakeBackend(OUTCOMES[:1])
        ids = [TestId("Vring", "Wraps"), TestId("Vring", "Gone"),
               TestId("Vring", "Unselected")]
        broker = ResultBroker(backend, ids)

        assert broker.outcome(ids[0], ids[:2]).passed
        with pytest.raises(LookupError, match="Vring.Gone"):
            broker.outcome(ids[1], ids[:2])
        assert backend.calls == [("run_some", "Vring", ("Wraps", "Gone"))]

    def test_test_id_components_are_preserved(self):
        outcome = TestOutcome("namespace.group", "case", passed=True)
        backend = FakeBackend([outcome])
        test_id = TestId(outcome.group, outcome.name)
        broker = ResultBroker(backend, [test_id])

        assert broker.outcome(test_id, []).passed
        assert backend.calls == [("run_test", "namespace.group", "case")]

    def test_missing_outcome_in_batch_raises_lookup_error(self):
        backend = FakeBackend(OUTCOMES[:1])
        ids = [TestId("Vring", "Wraps"), TestId("Vring", "Gone")]
        broker = ResultBroker(backend, ids)

        with pytest.raises(LookupError, match="Vring.Gone"):
            broker.outcome(ids[1], ids)


@requires_pytest
class GuestSuiteTests:
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

        assert "test_guest_case[namespace.group-Passes]" in result.stdout
        assert "test_guest_case[Group-Fails]" in result.stdout

    def test_full_suite_batches_and_balances_guest_sessions(self):
        result, events = self._run_pytest()

        assert result.returncode == 1, result.stdout + result.stderr
        assert ("guest test failed: guest.cpp:42: expected <1>"
                in result.stdout)
        assert events == [
            "start", "list", "stop", "start", "run_all", "stop",
        ]

    def test_narrowed_selection_preserves_id_and_balances_guests(self):
        result, events = self._run_pytest("-k", "Passes")

        assert result.returncode == 0, result.stdout + result.stderr
        assert "1 passed, 1 deselected" in result.stdout
        assert events == [
            "start", "list", "stop", "start",
            "run_test:namespace.group:Passes", "stop",
        ]


@requires_pytest
class UnreadableGuestOutputTests:
    """The facade's half of U4's promise (the plugin's is in
    test_plugin): when the guest answers unusably, the consumer reads
    the guest's screen rather than a traceback through their own
    module and this one. Enumeration here happens while that module
    is importing, which is why it is a separate mechanism from the
    plugin's collector."""

    def _run_pytest(self, enumerates):
        with tempfile.TemporaryDirectory(
                dir=Path(__file__).parent) as directory:
            module = Path(directory) / "test_guest.py"
            module.write_text(
                "import testaferro\n"
                "from testaferro import cpputest\n"
                "from testaferro.suite import SuiteBackend\n"
                "\n"
                f"ENUMERATES = {enumerates!r}\n"
                "\n"
                "def run(exe_path, args):\n"
                "    if ENUMERATES and '-ln' in args:\n"
                "        return 'Vring.Wraps Vring.Fails\\r\\n'\n"
                "    return 'Bad command or file name\\r\\n'\n"
                "\n"
                "test_guest_case = testaferro.guest_suite(\n"
                "    SuiteBackend('SUITE.EXE', run=run,\n"
                "                 framework=cpputest))\n",
                encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-m", "pytest", "-q",
                 "-p", "no:cacheprovider", str(module)],
                capture_output=True, text=True, check=False)

    def _assert_reads_as_the_guests(self, output):
        assert "guest output not understood" in output
        assert "what the guest showed on its screen" in output
        assert "Bad command or file name" in output
        for frame in ("cpputest.py", "suite.py", "facade.py",
                      "ValueError", "Traceback"):
            assert frame not in output

    def test_an_unreadable_enumeration_reports_the_guests_screen(self):
        result = self._run_pytest(enumerates=False)

        self._assert_reads_as_the_guests(result.stdout)
        assert "ran the guest suite with: -ln" in result.stdout

    def test_an_unreadable_run_reports_the_guests_screen(self):
        result = self._run_pytest(enumerates=True)

        self._assert_reads_as_the_guests(result.stdout)
        assert "ran the guest suite with: -v" in result.stdout
