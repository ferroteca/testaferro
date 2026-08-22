# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""The Backend seam: what the pytest facade needs from any remote
test target.

Any target that can list its tests and run one or all of them plugs
into the same facade, however it carries those operations out
underneath. The guest hooks default to no-ops because one-shot
backends (e.g. a SuiteBackend whose runner boots per operation) have
no guest session to manage.

"Guest session" rather than "session": pytest owns that word for the
whole run, and Testaferro would otherwise say it of three different
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


@dataclass(frozen=True)
class Availability:
    """One external dependency a binding needs, found on this host or
    not: a reliquary backend such as QEMU, or the DOSBox-X binary.

    Availability only, never a choice: what a binding *could* run
    with here, reported so a tester can see what is installed before
    declaring anything. `provider` is the binding that needs it;
    `backend` is the dependency's own name, spelled as its provider
    spells it and passed through uninterpreted; `executable` is what
    was found; `detail` says where, or why not.
    """

    provider: str
    backend: str
    available: bool
    executable: str | None = None
    version: str | None = None
    detail: str = ""


class GuestOutputError(Exception):
    """The guest answered, and no framework adapter could read it.

    Carries both halves of the exchange — the argv tokens the guest
    was asked for, and the text it showed in reply — so an entry point
    can report what actually happened out there instead of a traceback
    through the courier. The adapter supplies `reason` and nothing
    else: a grammar knows why it refused, and whoever performed the
    exchange knows what the exchange was.
    """

    def __init__(self, reason, argv=(), output=""):
        super().__init__(reason)
        self.reason = reason
        self.argv = tuple(argv)
        self.output = output


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

    def run_some(self, group, names) -> "list[TestOutcome]":
        """Run several tests of one group, in the group's own order
        of `names`. The middle operation between run_all() and
        run_test(), used by the facade when a narrowed selection
        still holds several tests of a group (F3): one exchange with
        the target where there would otherwise be one per test.

        Not abstract, so a prebuilt backend written to the five
        operations keeps working unchanged — this default is one
        run_test() per name, which is exactly what the facade did
        before the operation existed (D29). A backend for which a
        subset *is* cheaper overrides it. Raises LookupError if the
        target did not run one of them.
        """
        return [self.run_test(group, name) for name in names]

    def stop_guest(self):
        """Tear down cleanly. Must be safe to call after a failed or
        partial start_guest()."""
