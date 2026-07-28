# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""The pytest facade: surface a guest suite's tests as pytest items.

A consumer's test module hands over a reference to its suite
executable (public entry point: testaferro.guest_suite):

    test_guest_case = testaferro.guest_suite(HERE / "SUITE.EXE")

The executable is interrogated to select the matching platform binding
(currently: DOS programs, run under QEMU); a provably unsupported
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

from .backend import TestId
from .items import failure_text, item_id
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
               platform=None, machine=None, **machine_options):
    """Return a pytest test function with one parameterized item per
    test in the referenced suite. Assign it to a test_-prefixed
    module attribute:

        test_guest_case = testaferro.guest_suite(HERE / "SUITE.EXE")

    `target` is a path to the suite executable (interrogated to pick
    the guest backend) or a prebuilt Backend. The keyword options
    apply to the path form only: `framework` overrides the framework
    adapter, `enumerator` supplies a faster host-side source of the
    test list, `platform` chooses an OS platform when the executable's
    own format should not decide, and `machine` names a test machine —
    one declared with testaferro.config() or testaferro.ini (searched
    upward from this call site), or one of the standard environments
    testaferro curates, such as "freedos". Any further keyword is
    machine-specific and validated by the selected binding: today,
    `boot_image=` or `machine_config=` for DOS.

    Enumeration (backend.list_tests()) happens in its own session at
    import/collection time. A second session starts lazily when the
    first selected item runs and is cleaned up when pytest finishes.

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
    options.update(machine_options)
    if isinstance(target, (str, os.PathLike)):
        search_from = (None if call_site is None
                       else os.path.dirname(call_site[0]))
        backend = resolve_backend(target, platform=platform,
                                  machine=machine,
                                  search_from=search_from, **options)
    else:
        given = sorted(options)
        if platform is not None:
            given.append("platform")
        if machine is not None:
            given.append("machine")
        if given:
            raise TypeError(
                "keyword options apply only when passing an "
                "executable path; a prebuilt Backend carries its own "
                "configuration: " + ", ".join(given))
        backend = target

    try:
        backend.start_session()
        ids = list(backend.list_tests())
    finally:
        backend.stop_session()
    broker = ResultBroker(backend, ids)
    execution_session_started = False

    def start_execution_session(config):
        nonlocal execution_session_started
        if execution_session_started:
            return
        try:
            backend.start_session()
            config.add_cleanup(backend.stop_session)
        except BaseException:
            backend.stop_session()
            raise
        execution_session_started = True

    @pytest.mark.parametrize("guest_test", ids, ids=item_id)
    def run_guest_test(guest_test, request):
        start_execution_session(request.config)
        try:
            outcome = broker.outcome(guest_test,
                                     _selected_ids(request, broker))
        except LookupError as error:
            pytest.fail(str(error), pytrace=False)
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
