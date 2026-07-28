# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
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
sys.modules["testaferro.reliquary"] = fake
testaferro.reliquary = fake
'''


@unittest.skipUnless(PYTEST_AVAILABLE, "pytest is not installed")
class PluginTests(unittest.TestCase):
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
        self.write("conftest.py",
                   CONFTEST.format(events=str(self.events),
                                   homes=str(self.homes)))

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

    def pytest(self, *args):
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "no:cacheprovider",
             "-q", *args],
            cwd=str(self.root), capture_output=True, text=True,
            check=False)
        return result

    def recorded(self):
        if not self.events.exists():
            return []
        return self.events.read_text(encoding="utf-8").splitlines()

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

    def test_a_scan_claims_what_a_declaration_opts_in(self):
        self.write("testaferro.ini",
                   "[msdos]\nsuites = SUITE*.EXE\nmemory = 64\n")
        self.suite()

        result = self.pytest("--collect-only")

        self.assertIn("SUITE.EXE::Vring-Wraps", result.stdout)
        # and it runs on the machine that claimed it
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
                               "--testaferro-platform=dos")

        self.assertNotIn("Vring", unclaimed.stdout)
        self.assertIn("HOST.EXE::Vring-Wraps", declared.stdout)

    def test_two_machines_claiming_one_file_is_an_error(self):
        self.write("testaferro.ini",
                   "[msdos]\nsuites = *.EXE\n\n"
                   "[freedos2]\nsuites = SUITE.EXE\n")
        self.suite()

        result = self.pytest("--collect-only")

        self.assertIn("claimed by more than one test machine",
                      result.stdout + result.stderr)

    # --- running ------------------------------------------------

    def test_the_whole_suite_batches_and_a_failure_reads_as_the_guests(self):
        self.suite()

        result = self.pytest("SUITE.EXE")

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("1 failed, 1 passed", result.stdout)
        self.assertIn("guest test failed: vring_test.cpp:42: "
                      "expected <1>", result.stdout)
        # the guest's report, not a traceback into testaferro
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


if __name__ == "__main__":
    unittest.main()
