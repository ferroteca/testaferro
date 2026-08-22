# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Shared fixtures no single test module owns.

Not itself a test module (pytest only collects `test_*.py`), so
these are ordinary imports (`from helpers import ...`) rather than
fixtures — plain data and a fake `Backend`, reused wherever a case
needs an executable's bytes or a guest that never boots.
"""

import importlib.util

import pytest

from testaferro.backend import Backend, TestId, TestOutcome

PYTEST_AVAILABLE = importlib.util.find_spec("pytest") is not None
RELIQUARY_AVAILABLE = importlib.util.find_spec("reliquary") is not None
REMANENCE_AVAILABLE = importlib.util.find_spec("remanence") is not None

requires_pytest = pytest.mark.skipif(
    not PYTEST_AVAILABLE, reason="pytest is not installed")
requires_reliquary = pytest.mark.skipif(
    not RELIQUARY_AVAILABLE, reason="reliquary is not installed")
requires_remanence = pytest.mark.skipif(
    not REMANENCE_AVAILABLE, reason="remanence is not installed")


def new_format_exe_bytes(signature):
    """An MZ image whose relocation table at 0x40+ marks a newer-
    format header (PE/NE/...) at e_lfanew."""
    header = bytearray(0x40)
    header[0:2] = b"MZ"
    header[0x18:0x1A] = (0x40).to_bytes(2, "little")  # e_lfarlc
    header[0x3C:0x40] = (0x40).to_bytes(4, "little")  # e_lfanew
    return bytes(header) + signature


def plain_dos_exe_bytes():
    # e_lfarlc below 0x40: original MZ layout, no newer header.
    header = bytearray(0x40)
    header[0:2] = b"MZ"
    header[0x18:0x1A] = (0x1C).to_bytes(2, "little")
    return bytes(header)


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

    def run_some(self, group, names):
        self.calls.append(("run_some", group, tuple(names)))
        return [o for o in self._outcomes
                if o.group == group and o.name in names]

    def run_all(self):
        self.calls.append(("run_all",))
        return self._outcomes


OUTCOMES = [
    TestOutcome("Vring", "Wraps", passed=True),
    TestOutcome("Vring", "Fails", passed=False,
                file="vring_test.cpp", line=42, message="expected <1>"),
]
