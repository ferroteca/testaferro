# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Tests for the pytest collection plugin.

Each case runs pytest for real, in a subprocess, over a tree written
for it: the plugin's whole subject is what pytest does with a file,
so nothing short of pytest itself proves it. The guest binding is
replaced from the tree's own conftest — the fake is installed in
``sys.modules`` before resolution imports it — so these stay unit
tests by the cost rule (P10): no hypervisor, and no reliquary either.
"""

import importlib.util
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

from test_binfmt import new_format_exe_bytes, plain_dos_exe_bytes

PYTEST_AVAILABLE = importlib.util.find_spec("pytest") is not None

# Stands in for the provider binding, recording what it was asked for.
CONFTEST = '''
import os
import sys
import tempfile
import types

import testaferro
from testaferro import cache
from testaferro.backend import TestId, TestOutcome

EVENTS = {events!r}
HOMES = {homes!r}


def record(event):
    with open(EVENTS, "a", encoding="utf-8") as stream:
        stream.write(event + "\\n")


class RecordingBackend:
    def __init__(self, exe_path, enumerator=None, **options):
        self.exe_path = exe_path
        self.enumerator = enumerator
        self.home = None

    def start_guest(self):
        record("start")
        # A guest home is what a real binding makes here, and handing
        # it back to the core is what decides whether it survives.
        self.home = tempfile.mkdtemp(prefix="guest-", dir=HOMES)

    def stop_guest(self):
        record("stop")
        if self.home is not None:
            cache.release_guest_home(self.home)
            self.home = None

    def list_tests(self):
        # SuiteBackend's own rule: a supplied enumerator replaces
        # asking the guest.
        if self.enumerator is not None:
            record("enumerate")
            return self.enumerator()
        record("list")
        return [TestId("Vring", "Wraps"), TestId("Vring", "Fails")]

    def run_all(self):
        record("run_all")
        return [TestOutcome("Vring", "Wraps", True),
                TestOutcome("Vring", "Fails", False,
                            "vring_test.cpp", 42, "expected <1>")]

    def run_test(self, group, name):
        record("run_test:" + group + ":" + name)
        return TestOutcome(group, name, True)


def suite_backend(exe_path, **options):
    record("resolve:" + ",".join(sorted(options)))
    return RecordingBackend(exe_path, **options)


fake = types.ModuleType("testaferro.reliquary")
fake.suite_backend = suite_backend
# A binding says which platforms it serves; resolution asks before it
# hands anything over, so a stand-in has to answer too.
fake.PLATFORMS = ("dos",)
sys.modules["testaferro.reliquary"] = fake
testaferro.reliquary = fake
'''


# A binding whose guest answers with something no adapter can read.
# A real SuiteBackend over the real CppUTest adapter, so what is
# exercised is the grammar refusing and the report that follows.
UNREADABLE_CONFTEST = '''
import sys
import types

import testaferro
from testaferro import cpputest
from testaferro.suite import SuiteBackend

ENUMERATES = {enumerates!r}


def run(exe_path, args):
    if ENUMERATES and "-ln" in args:
        return "Vring.Wraps Vring.Fails\\r\\n"
    return "Bad command or file name\\r\\n"


def suite_backend(exe_path, enumerator=None, **options):
    # `enumerator` has to reach the composition or a declared twin is
    # silently ignored and the guest answers instead.
    return SuiteBackend(exe_path, run=run, framework=cpputest,
                        enumerator=enumerator)


fake = types.ModuleType("testaferro.reliquary")
fake.suite_backend = suite_backend
fake.PLATFORMS = ("dos",)
sys.modules["testaferro.reliquary"] = fake
testaferro.reliquary = fake
'''


class _PytestTreeCase(unittest.TestCase):
    """A throwaway project tree, with pytest run against it for real.

    A collection plugin's whole subject is what pytest does with a
    file, so a case here is a real pytest run in a subprocess. The
    tree's own conftest is what each subclass supplies, and every one
    of them puts a fake binding in `sys.modules` before resolution
    imports it — so no guest starts and no reliquary loads (P10).
    """

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.events = self.root / "events.txt"
        # pytest.ini makes this tree its own rootdir, so a
        # testaferro.ini written beside it is the one found.
        self.write("pytest.ini", "[pytest]\n")
        self.homes = self.root / "homes"
        self.homes.mkdir()

    def write(self, name, content):
        path = self.root / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def suite(self, name="SUITE.EXE", content=None):
        return self.write(name, plain_dos_exe_bytes()
                          if content is None else content)

    def pytest(self, *args, cache=False):
        # The cache plugin is off by default so no run leaves state
        # for the next; `--lf` is the one thing that needs it, and
        # asks for it.
        cache_args = [] if cache else ["-p", "no:cacheprovider"]
        result = subprocess.run(
            [sys.executable, "-m", "pytest", *cache_args, "-q", *args],
            cwd=str(self.root), capture_output=True, text=True,
            check=False)
        return result

    def recorded(self):
        if not self.events.exists():
            return []
        return self.events.read_text(encoding="utf-8").splitlines()


@unittest.skipUnless(PYTEST_AVAILABLE, "pytest is not installed")
class PluginTests(_PytestTreeCase):
    def setUp(self):
        super().setUp()
        self.write("conftest.py",
                   CONFTEST.format(events=str(self.events),
                                   homes=str(self.homes)))

    # --- claiming -----------------------------------------------

    def test_a_named_executable_is_claimed_and_its_tests_are_items(self):
        self.suite()

        result = self.pytest("SUITE.EXE", "--collect-only")

        self.assertIn("SUITE.EXE::Vring-Wraps", result.stdout)
        self.assertIn("SUITE.EXE::Vring-Fails", result.stdout)

    def test_a_scan_claims_nothing_that_was_not_opted_in(self):
        # Installation is activation, so this is the guarantee that
        # landing in a venv changes no existing run.
        self.suite()

        result = self.pytest()

        self.assertNotIn("Vring", result.stdout)
        self.assertEqual(self.recorded(), [])

    def test_a_scan_claims_what_a_pytest_ini_mask_opts_in(self):
        self.write("pytest.ini", "[pytest]\ntestaferro-suites = *.EXE\n")
        self.suite()

        result = self.pytest("--collect-only")

        self.assertIn("SUITE.EXE::Vring-Wraps", result.stdout)

    def test_a_scan_claims_what_a_command_line_mask_opts_in(self):
        # The mask has a command-line spelling as well as an ini one,
        # so a mask can be tried before it is written down (P16).
        self.suite()

        result = self.pytest("--collect-only",
                             "--testaferro-suites=*.EXE")

        self.assertIn("SUITE.EXE::Vring-Wraps", result.stdout)

    def test_command_line_masks_add_to_the_ini_rather_than_replace(self):
        # A mask names files rather than choosing between them.
        self.write("pytest.ini", "[pytest]\ntestaferro-suites = *.EXE\n")
        self.suite()
        self.write("OTHER.COM", plain_dos_exe_bytes())

        result = self.pytest("--collect-only",
                             "--testaferro-suites=*.COM")

        self.assertIn("SUITE.EXE::Vring-Wraps", result.stdout)
        self.assertIn("OTHER.COM::Vring-Wraps", result.stdout)

    def test_the_timeout_option_reaches_the_binding(self):
        self.suite()

        self.pytest("SUITE.EXE", "--collect-only",
                    "--testaferro-timeout=5")

        self.assertIn("resolve:timeout", self.recorded())

    def test_the_setup_option_reaches_the_binding(self):
        self.suite()

        self.pytest("SUITE.EXE", "--collect-only",
                    "--testaferro-setup=DRIVER.COM /install")

        self.assertIn("resolve:setup", self.recorded())

    def test_a_non_numeric_timeout_is_refused(self):
        self.suite()

        result = self.pytest("SUITE.EXE", "--collect-only",
                             "--testaferro-timeout=soon")

        self.assertIn("takes a number of seconds",
                      result.stdout + result.stderr)
        self.assertNotIn("Vring", result.stdout)

    def test_the_provider_option_is_read_and_not_passed_onward(self):
        # The third spelling of `provider` (P16). It selects the
        # binding, so the seam consumes it: a binding is never told
        # which binding it is.
        self.suite()

        self.pytest("SUITE.EXE", "--collect-only",
                    "--testaferro-provider=reliquary")

        self.assertIn("resolve:", self.recorded())
        self.assertNotIn("provider", self.recorded())

    def test_an_unknown_provider_is_refused_from_the_command_line(self):
        self.suite()

        result = self.pytest("SUITE.EXE", "--collect-only",
                             "--testaferro-provider=vagrant")

        self.assertIn("unknown provider 'vagrant'",
                      result.stdout + result.stderr)
        self.assertNotIn("Vring", result.stdout)

    def test_the_provider_has_a_pytest_ini_spelling_too(self):
        self.write("pytest.ini",
                   "[pytest]\ntestaferro-provider = vagrant\n")
        self.suite()

        result = self.pytest("SUITE.EXE", "--collect-only")

        self.assertIn("unknown provider 'vagrant'",
                      result.stdout + result.stderr)

    def test_a_scan_claims_what_a_declaration_opts_in(self):
        self.write("testaferro.ini",
                   "[msdos]\nsuites = SUITE*.EXE\nmemory = 64\n")
        self.suite()

        result = self.pytest("--collect-only")

        self.assertIn("SUITE.EXE::Vring-Wraps", result.stdout)
        # and it runs in the environment that claimed it
        self.assertIn("resolve:machine_config", self.recorded())

    def test_a_headerless_image_is_never_claimed_from_a_scan(self):
        # Raw .com-style code proves nothing about being a program at
        # all, so a mask alone must not make a scan claim it.
        self.write("pytest.ini", "[pytest]\ntestaferro-suites = *.COM\n")
        self.write("SUITE.COM", b"\xb4\x09\xba\x00\x01\xcd\x21\xc3")

        scanned = self.pytest("--collect-only")
        named = self.pytest("SUITE.COM", "--collect-only")

        self.assertNotIn("Vring", scanned.stdout)
        self.assertIn("SUITE.COM::Vring-Wraps", named.stdout)

    def test_a_named_file_that_is_not_a_program_is_left_alone(self):
        # binfmt's "dos" for a headerless file means *nothing proves
        # otherwise*, which is just as true of a test module as of a
        # .com image. Reading it as proof claims pytest's own files
        # and boots a guest to run them.
        self.write("test_host.py", "def test_host():\n    assert True\n")
        self.write("notes.txt", "not a program\n")

        module = self.pytest("test_host.py")
        text = self.pytest("notes.txt", "--collect-only")

        self.assertIn("1 passed", module.stdout)
        self.assertNotIn("Vring", module.stdout)
        self.assertNotIn("Vring", text.stdout)
        self.assertEqual(self.recorded(), [])

    def test_a_host_format_is_claimed_only_by_declaration(self):
        machine = (0x014C).to_bytes(2, "little")
        self.suite("HOST.EXE",
                   new_format_exe_bytes(b"PE\0\0" + machine))

        unclaimed = self.pytest("HOST.EXE", "--collect-only")
        declared = self.pytest("HOST.EXE", "--collect-only",
                               "--testaferro-environment=freedos")

        self.assertNotIn("Vring", unclaimed.stdout)
        self.assertIn("HOST.EXE::Vring-Wraps", declared.stdout)

    def test_two_environments_claiming_one_file_is_an_error(self):
        self.write("testaferro.ini",
                   "[msdos]\nsuites = *.EXE\n\n"
                   "[freedos2]\nsuites = SUITE.EXE\n")
        self.suite()

        result = self.pytest("--collect-only")

        self.assertIn("claimed by more than one test environment",
                      result.stdout + result.stderr)

    # --- running ------------------------------------------------

    def test_the_whole_suite_batches_and_a_failure_reads_as_the_guests(self):
        self.suite()

        result = self.pytest("SUITE.EXE")

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("1 failed, 1 passed", result.stdout)
        self.assertIn("guest test failed: vring_test.cpp:42: "
                      "expected <1>", result.stdout)
        # the guest's report, not a traceback into Testaferro
        self.assertNotIn("Traceback", result.stdout)
        self.assertNotIn("in runtest", result.stdout)
        self.assertEqual(self.recorded(), [
            "resolve:", "start", "list", "stop",
            "start", "run_all", "stop",
        ])

    def test_a_narrowed_selection_runs_only_what_was_selected(self):
        self.suite()

        result = self.pytest("SUITE.EXE::Vring-Wraps")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("1 passed", result.stdout)
        self.assertIn("run_test:Vring:Wraps", self.recorded())
        self.assertNotIn("run_all", self.recorded())

    def test_exitfirst_stops_the_session_at_a_guest_failure(self):
        # `-x` is pytest's own and needs no help from Testaferro —
        # which is the claim, so it is worth proving rather than
        # assuming (U4). Two suites, so stopping is visible: the
        # first one's failure has to keep the second from running at
        # all.
        self.write("pytest.ini",
                   "[pytest]\ntestaferro-suites = *.EXE *.COM\n")
        self.suite()
        self.suite("OTHER.COM")

        result = self.pytest("-x")

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("stopping after 1 failures", result.stdout)
        # both suites were enumerated; only one was ever run
        self.assertEqual(self.recorded().count("list"), 2)
        self.assertEqual(self.recorded().count("run_all"), 1)

    def test_last_failed_reruns_only_the_guest_test_that_failed(self):
        # `--lf` keys on node ids, so it works exactly because the
        # ids are pytest's own and Testaferro produces them (U4).
        self.suite()

        first = self.pytest("SUITE.EXE", cache=True)
        self.assertIn("1 failed, 1 passed", first.stdout)
        before = len(self.recorded())

        again = self.pytest("SUITE.EXE", "--lf", cache=True)

        # One item selected and one deselected: `--lf` picked the
        # guest test that failed, by its node id. Whether it passes on
        # the rerun is the fake's business — this stand-in always
        # passes a single run_test — and not what is under test.
        self.assertIn("1 deselected", again.stdout)
        rerun = self.recorded()[before:]
        # narrowed to one item, so the broker asks for that one test
        # rather than batching the suite it did not select
        self.assertIn("run_test:Vring:Fails", rerun)
        self.assertNotIn("run_all", rerun)

    def test_a_guest_home_is_swept_unless_asked_for(self):
        self.suite()

        self.pytest("SUITE.EXE")

        self.assertEqual(list(self.homes.iterdir()), [])

    def test_the_keep_option_keeps_what_the_guest_was_given(self):
        self.suite()

        result = self.pytest("SUITE.EXE", "--testaferro-keep-guest-home")

        kept = list(self.homes.iterdir())
        self.assertTrue(kept)
        self.assertIn("guest homes kept", result.stdout)
        for home in kept:
            self.assertIn(home.name, result.stdout)

    # --- enumeration --------------------------------------------

    def test_a_guest_read_list_says_it_may_be_short(self):
        self.suite()

        result = self.pytest("SUITE.EXE", "--collect-only")

        self.assertIn("may be short", result.stdout)
        self.assertIn("GuestEnumerationWarning", result.stdout)

    def test_a_host_built_twin_enumerates_without_booting_a_guest(self):
        self.suite()
        twin = self._twin("Vring.Wraps Vring.Fails")

        result = self.pytest("SUITE.EXE", "--collect-only",
                             f"--testaferro-enumerator={twin.name}")

        self.assertIn("SUITE.EXE::Vring-Wraps", result.stdout)
        self.assertNotIn("may be short", result.stdout)
        # the twin's whole case: enumerated, with no guest started
        # around it, so no guest booted to be asked
        self.assertEqual(self.recorded(),
                         ["resolve:enumerator", "enumerate"])

    def test_a_missing_twin_falls_back_to_the_guest(self):
        self.suite()

        result = self.pytest(
            "SUITE.EXE", "--collect-only",
            "--testaferro-enumerator=build/{stem}-host.exe")

        self.assertIn("SUITE.EXE::Vring-Wraps", result.stdout)
        self.assertIn("list", self.recorded())

    def _twin(self, listing):
        """A host-built twin: an executable answering the framework's
        list argv with the same test list."""
        if os.name == "nt":
            return self.write("twin.cmd", f"@echo {listing}\n")
        twin = self.write("twin.sh", f"#!/bin/sh\necho '{listing}'\n")
        twin.chmod(twin.stat().st_mode | stat.S_IEXEC)
        return twin


@unittest.skipUnless(PYTEST_AVAILABLE, "pytest is not installed")
class UnreadableGuestOutputTests(_PytestTreeCase):
    """What a trial looks like when the guest answers unusably (U4).

    Trying a suite is exactly when things go wrong, so the report is
    what the guest showed — never a traceback into Testaferro, which
    would describe the courier instead of what happened. Both moments
    are covered because they are different pytest mechanisms: a
    collector reports an error, an item reports a failure.
    """

    def _binding(self, enumerates):
        self.write("conftest.py",
                   UNREADABLE_CONFTEST.format(enumerates=enumerates))
        self.suite()

    def _assert_reads_as_the_guests(self, output):
        self.assertIn("guest output not understood", output)
        self.assertIn("what the guest showed on its screen", output)
        self.assertIn("Bad command or file name", output)
        # The whole point: nothing of Testaferro's own machinery in
        # what the developer is asked to read.
        for frame in ("cpputest.py", "suite.py", "plugin.py",
                      "ValueError", "Traceback"):
            self.assertNotIn(frame, output)

    def test_an_unreadable_enumeration_reports_the_guests_screen(self):
        self._binding(enumerates=False)

        result = self.pytest("SUITE.EXE")

        self._assert_reads_as_the_guests(result.stdout)
        self.assertIn("ran the guest suite with: -ln", result.stdout)

    def test_an_unreadable_run_reports_the_guests_screen(self):
        # Enumeration works here, so the guest is only found wanting
        # once a test runs — a different pytest mechanism, same rule.
        self._binding(enumerates=True)

        result = self.pytest("SUITE.EXE", "-W", "ignore::UserWarning")

        self._assert_reads_as_the_guests(result.stdout)
        self.assertIn("ran the guest suite with: -v", result.stdout)

    def test_the_reason_survives_into_the_short_summary(self):
        # pytest quotes only a report's first line there, which is why
        # the reason leads and the exchange follows.
        self._binding(enumerates=True)

        result = self.pytest("SUITE.EXE", "-W", "ignore::UserWarning")

        summary = [line for line in result.stdout.splitlines()
                   if line.startswith("FAILED ")]
        self.assertTrue(summary, result.stdout)
        for line in summary:
            self.assertIn("guest output not understood", line)

    def test_a_twin_that_prints_nonsense_names_the_twin(self):
        # The host-built twin is a host program, so there is no guest
        # screen to show — but it must not fail as a traceback either.
        self._binding(enumerates=True)
        self._twin("not a test list at all")

        result = self.pytest(
            "SUITE.EXE", "--testaferro-enumerator=" + self._twin_name())

        self.assertIn("did not print a test list", result.stdout)
        self.assertNotIn("Traceback", result.stdout)

    def _twin(self, listing):
        if os.name == "nt":
            return self.write("twin.cmd", f"@echo {listing}\n")
        twin = self.write("twin.sh", f"#!/bin/sh\necho '{listing}'\n")
        twin.chmod(twin.stat().st_mode | stat.S_IEXEC)
        return twin

    def _twin_name(self):
        return "twin.cmd" if os.name == "nt" else "twin.sh"


if __name__ == "__main__":
    unittest.main()
