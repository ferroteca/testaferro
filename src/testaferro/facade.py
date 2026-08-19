# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""The pytest facade: surface a guest suite's tests as pytest items.

A consumer's test module hands over a reference to its suite
executable (public entry point: testaferro.guest_suite):

    test_guest_case = testaferro.guest_suite(HERE / "SUITE.EXE")

The executable is interrogated to select the matching binding
(currently: DOS programs, run by reliquary); a provably unsupported
binary is rejected with a clear error. That resolution is the core's
and is shared with every other entry point (testaferro.resolution);
what this module adds is what only a call from a test module can
supply — the call site, which is both where the project's
testaferro.ini search starts and where the generated items report
their source. Alternatively a prebuilt Backend may be passed in place
of the path — the custom execution escape hatch and test seam for
this facade.

Each of the suite's tests becomes one pytest item, so pytest's own
selection (-k, node ids) drives what actually runs remotely. When the
whole suite is selected, the facade batches everything into a single
run_all(); a narrowed selection falls back to individual run_test()
calls. Remote failures are replayed with the
guest side's original file/line/message rather than a traceback into
this facade.
"""

from __future__ import annotations

import os

from .backend import GuestOutputError, TestId
from .items import failure_text, guest_output_text, item_id
from .resolution import resolve_backend


class ResultBroker:
    """Lazily fetch outcomes for one suite, deciding between one
    batched run_all() and per-test run_test() calls from how much of
    the suite pytest actually selected. pytest-free on purpose."""

    def __init__(self, backend, ids):
        self._backend = backend
        self._ids = list(ids)
        self._batch = None
        self._single = {}

    def outcome(self, test_id, selected_ids):
        if set(selected_ids) == set(self._ids):
            if self._batch is None:
                self._batch = {TestId(o.group, o.name): o
                               for o in self._backend.run_all()}
            if test_id not in self._batch:
                raise LookupError(
                    f"target did not run test {test_id} "
                    "(host and target test lists out of sync?)")
            return self._batch[test_id]
        if test_id not in self._single:
            self._single[test_id] = self._backend.run_test(
                test_id.group, test_id.name)
        return self._single[test_id]


def guest_suite(target, framework=None, enumerator=None,
               environment=None, provider=None, **environment_options):
    """Return a pytest test function with one parameterized item per
    test in the referenced suite. Assign it to a test_-prefixed
    module attribute:

        test_guest_case = testaferro.guest_suite(HERE / "SUITE.EXE")

    `target` is a path to the suite executable (interrogated to pick
    the guest backend) or a prebuilt Backend. The keyword options
    apply to the path form only: `framework` overrides the framework
    adapter, `enumerator` supplies a faster host-side source of the
    test list, and `environment` names the test environment the suite
    runs in — one declared with testaferro.config() or testaferro.ini
    (searched upward from this call site), or one of the standard
    environments Testaferro curates, such as "freedos". Naming none
    lets the executable's own format select one. `provider` names what
    runs the guest for an environment declared inline here —
    "reliquary" today, the default and the only one built — and a
    named environment carries its own, so the two do not combine. Any
    further keyword is environment-specific and validated by the
    selected binding: today, `boot_image=` or `machine_config=` for
    DOS, plus the placement declarations `files=`, `location=` and
    `program=` — what is staged into the guest, the guest address it
    lands at, and what to run there. All three default, so a lone
    suite executable still needs none of them, and where a run landed
    is readable afterwards as the backend's `location`. `setup=` is
    harness prep (F9): commands run in the guest, in order, once per
    guest session before any test — a TSR or driver made resident
    ahead of the framework, rather than an unrepeatable setup test. A
    suite that declares none runs exactly as before.

    Enumeration (backend.list_tests()) happens at import/collection
    time, in a guest session of its own — unless `enumerator` supplies
    the list from the host, in which case no guest is started, because
    none is needed. A second guest session, for execution, starts
    lazily when the first selected item runs and is stopped when
    pytest finishes.

    The returned function is re-homed to the caller's file and call
    line, so IDE per-item actions that key on source location (run
    one item, jump to source) resolve to the consumer's module
    rather than this facade.
    """
    import inspect

    import pytest

    frame = inspect.currentframe()
    caller = None if frame is None else frame.f_back
    call_site = (None if caller is None else
                 (caller.f_code.co_filename, caller.f_lineno))
    del frame, caller

    options = {name: value
               for name, value in (("framework", framework),
                                   ("enumerator", enumerator))
               if value is not None}
    options.update(environment_options)
    if isinstance(target, (str, os.PathLike)):
        search_from = (None if call_site is None
                       else os.path.dirname(call_site[0]))
        backend = resolve_backend(target, environment=environment,
                                  provider=provider,
                                  search_from=search_from, **options)
    else:
        given = sorted(options)
        for name, value in (("environment", environment),
                            ("provider", provider)):
            if value is not None:
                given.append(name)
        if given:
            raise TypeError(
                "keyword options apply only when passing an "
                "executable path; a prebuilt Backend carries its own "
                "configuration: " + ", ".join(given))
        backend = target

    if enumerator is None:
        try:
            try:
                backend.start_guest()
                ids = list(backend.list_tests())
            finally:
                backend.stop_guest()
        except GuestOutputError as error:
            # This runs while the consumer's module is importing, so
            # an escaped exception reports as a traceback through
            # their module and this one. `pytrace=False` leaves the
            # guest's own words and nothing else.
            pytest.fail(guest_output_text(error), pytrace=False)
    else:
        # A host-side enumerator answers without the guest, so starting
        # one here would boot a machine and ask it nothing. Safe to
        # skip only because `enumerator` reaches this point on the path
        # form alone — a prebuilt Backend rejects it above, and its own
        # start_guest() may well be what makes list_tests() work.
        ids = list(backend.list_tests())
    broker = ResultBroker(backend, ids)
    execution_guest_started = False

    def start_execution_guest(config):
        nonlocal execution_guest_started
        if execution_guest_started:
            return
        try:
            backend.start_guest()
            config.add_cleanup(backend.stop_guest)
        except BaseException:
            backend.stop_guest()
            raise
        execution_guest_started = True

    @pytest.mark.parametrize("guest_test", ids, ids=item_id)
    def run_guest_test(guest_test, request):
        start_execution_guest(request.config)
        try:
            outcome = broker.outcome(guest_test,
                                     _selected_ids(request, broker))
        except LookupError as error:
            pytest.fail(str(error), pytrace=False)
        except GuestOutputError as error:
            pytest.fail(guest_output_text(error), pytrace=False)
        if not outcome.passed:
            pytest.fail(failure_text(outcome), pytrace=False)

    if call_site is not None:
        run_guest_test.__code__ = run_guest_test.__code__.replace(
            co_filename=call_site[0], co_firstlineno=call_site[1])
    run_guest_test._testaferro_broker = broker
    return run_guest_test


def _selected_ids(request, broker):
    """The suite's test ids that survived pytest's selection —
    exactly the items pytest is going to run this session."""
    return [item.callspec.params["guest_test"]
            for item in request.session.items
            if getattr(item.function, "_testaferro_broker", None)
            is broker]
