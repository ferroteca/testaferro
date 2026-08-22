# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Testaferro: a pytest plugin for tests that run inside a guest.

A suite compiled for and running on a remote target surfaces as
ordinary pytest tests on the host. There are two ways in, and they
are the same execution underneath.

Point pytest at the executable — the plugin auto-loads with the
distribution, claims it, and collects its tests as
`tests/SUITE.EXE::Group-Name` items:

    pytest tests/SUITE.EXE

Or embed it, when programmatic control is wanted. Hand guest_suite()
a reference to the suite executable:

    from pathlib import Path

    import testaferro

    test_guest_case = testaferro.guest_suite(
        Path(__file__).parent / "SUITE.EXE")

The executable is interrogated to select its test environment (DOS
programs run in a guest reliquary provides; anything else is
rejected), the framework adapter defaults to testaferro.cpputest
(`framework=` overrides), and the runner's working state lives in
Testaferro-managed disposable directories. Named test environments
are declared with config() or an optional per-project testaferro.ini;
a prebuilt Backend remains the custom escape hatch for callers that
need a different execution mechanism.

A guest-driven test that is a linear script rather than a suite of
named cases reaches the same zero-configuration guest through a
lower-level door instead (U10):

    with testaferro.guest_session() as guest:
        guest.exec("DRIVER.COM /install")
        guest.exec("RUNNER.EXE")

guest_suite() remains the right tool for anything shaped as a suite
of named tests; guest_session() is purely additive beside it.

For many suites (and future parallel runs), open a *run* so the boot
image is specified once and all the state it leaves behind is swept
together — in pytest, from the consumer's conftest.py:

    import testaferro

    testaferro.start()              # or start(boot_image=...)

    def pytest_unconfigure(config):
        testaferro.stop()
"""

# eager: the facade's own imports are stdlib-only (pytest is loaded
# lazily inside it). start/stop delegate lazily instead, because
# importing the provider binding pulls in reliquary.
from .facade import guest_suite  # noqa: F401

import inspect
import os


def guest_session(environment=None, provider=None, **options):
    """Open a guest session directly, for a guest-driven test that is
    a linear script rather than a suite of named cases (U10):

        with testaferro.guest_session() as guest:
            guest.exec("DRIVER.COM /install")
            guest.exec("RUNNER.EXE")

    The same zero-configuration guest `guest_suite()` gives every
    suite — the cached image, downloaded/installed once and reused,
    booting inside a fresh disposable overlay this session alone
    writes to — reached without a suite executable to interrogate or
    a framework adapter for output that was never going to exist.
    Entering boots the guest and returns the handle; leaving sweeps
    the session, whether the script's own assertions passed or one of
    them raised.

    `environment` names the test environment the guest runs in — one
    declared with testaferro.config() or testaferro.ini (searched
    upward from this call site), or one of the standard environments
    Testaferro curates. `provider` names what runs the guest for an
    environment declared inline here — "reliquary", the default and
    the one binding serving guest sessions — and a named environment
    carries its own, so the two do not combine. `files` is host paths staged onto the
    work drive before boot, the same placement vocabulary
    `guest_suite()` takes (U1); `machine_config` reaches the same
    declared or standard machine a suite would (U3, U9). Any further
    keyword is environment-specific, validated by the selected
    binding.

    The handle's `exec(command, timeout=None)` runs one guest command
    and reads its answer back, in the order the script itself decides
    rather than a suite's enumeration — nothing to enumerate, nothing
    for a framework adapter to parse.
    """
    from .resolution import resolve_guest_session

    frame = inspect.currentframe()
    caller = None if frame is None else frame.f_back
    search_from = (None if caller is None
                  else os.path.dirname(caller.f_code.co_filename))
    del frame, caller
    return resolve_guest_session(environment=environment, provider=provider,
                                 search_from=search_from, **options)


def config(name, **options):
    """Declare a named test environment, backed by the declared
    provider's own document.

    Without a ``machine_config`` / ``template``, the options are the
    provider's own fields — a blueprint's ``platform``, ``memory``,
    ``drives`` and friends for reliquary; conf sections such as
    ``cpu={"cycles": "max"}`` for ``provider="dosbox-x"`` — passed
    through untouched for the provider to validate. With one, the
    path is the provider's own document (a ``.rlqb``, or a ``.conf``)
    and that provider opens it. The declaration is reused as a template; each guest
    session receives a fresh materialization. The same declarations
    may be written in ``testaferro.ini`` (see ``load_config``).
    """
    from .environments import configure
    return configure(name, **options)


def load_config(path=None):
    """Load named test environments from a ``testaferro.ini``.

    With ``path``, read that file. With ``path`` omitted, search
    upward from the current directory. ``guest_suite()`` performs the
    same search from its call site automatically.
    """
    from .environments import load_config as load
    return load(path)


def start(boot_image=None):
    """Open a Testaferro run: one boot-image choice (or the
    downloaded default) serving every suite until stop(). Costs
    nothing until a guest actually runs; an atexit failsafe sweeps
    the run if stop() is never called."""
    from . import reliquary
    reliquary.start(boot_image=boot_image)


def stop(clear_downloads=False):
    """Close the run, sweeping its staged image and every guest home
    inside it; safe without an active run. `clear_downloads=True`
    also drops the cached default boot image."""
    from . import reliquary
    reliquary.stop(clear_downloads=clear_downloads)
