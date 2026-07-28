# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""The Backend seam: what the pytest facade needs from any remote
test target.

Any target that can list its tests and run one or all of them plugs
into the same facade, however it carries those operations out
underneath. The guest hooks default to no-ops because one-shot
backends (e.g. a SuiteBackend whose runner boots per operation) have
no guest session to manage.

"Guest session" rather than "session": pytest owns that word for the
whole run, and testaferro would otherwise say it of three different
spans (D15). Here it means one guest up and able to answer — from
start_guest() to stop_guest().
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class TestId:
    __test__ = False        # not a test case, despite the name

    group: str
    name: str

    def __str__(self):
        return f"{self.group}.{self.name}"


@dataclass
class TestOutcome:
    __test__ = False        # not a test case, despite the name

    group: str
    name: str
    passed: bool
    file: str = ""
    line: int = 0
    message: str = ""


class Backend(ABC):
    def start_guest(self):
        """Boot or attach to the remote target. Ready to accept
        list/run calls immediately after this returns."""

    @abstractmethod
    def list_tests(self) -> "list[TestId]":
        ...

    @abstractmethod
    def run_test(self, group, name) -> TestOutcome:
        """Run one test. Raises LookupError if the target did not
        run it (e.g. host and target test lists diverged)."""

    @abstractmethod
    def run_all(self) -> "list[TestOutcome]":
        """Used by the facade's batching logic when no host-side
        filter is active - a single bulk operation is expected to be
        cheaper than many individual run_test() calls, however the
        backend chooses to implement that."""

    def stop_guest(self):
        """Tear down cleanly. Must be safe to call after a failed or
        partial start_guest()."""
