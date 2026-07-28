# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""testaferro: a pytest plugin for tests that run inside a guest.

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

The executable is interrogated to select its platform (DOS programs
run in a guest reliquary provides; anything else is rejected), the
framework adapter defaults to testaferro.cpputest (`framework=`
overrides), and the runner's working state lives in
testaferro-managed disposable directories. Named test machines are
declared with config() or an optional per-project testaferro.ini; a
prebuilt Backend remains the custom escape hatch for callers that
need a different execution mechanism.

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


def config(machine, platform=None, **options):
    """Declare a named reliquary test machine.

    ``platform`` is optional when the supplied ``machine_config`` or
    ``template`` declares it. Without a template, remaining options are
    the blueprint's own machine fields. The declaration is reused
    as a template; each guest session receives a fresh materialization.
    The same declarations may be written in ``testaferro.ini`` (see
    ``load_config``).
    """
    from .machines import configure
    return configure(machine, platform=platform, **options)


def load_config(path=None):
    """Load named machines from a ``testaferro.ini``.

    With ``path``, read that file. With ``path`` omitted, search
    upward from the current directory. ``guest_suite()`` performs the
    same search from its call site automatically.
    """
    from .machines import load_config as load
    return load(path)


def start(boot_image=None):
    """Open a testaferro run: one boot-image choice (or the
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
