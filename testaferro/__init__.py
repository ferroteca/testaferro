# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""testaferro: a pytest facade for remote (e.g. QEMU-guest) unit
tests.

A suite compiled for and running on a remote target surfaces as
ordinary pytest tests on the host. Hand guest_suite() a reference to
the suite executable:

    from pathlib import Path

    import testaferro

    test_guest_case = testaferro.guest_suite(
        Path(__file__).parent / "SUITE.EXE")

The executable is interrogated to select its platform (DOS programs
run in a QEMU guest; anything else is rejected), the
framework adapter defaults to testaferro.cpputest (`framework=`
overrides), and the runner's working state lives in
testaferro-managed disposable directories. Named test machines are
declared with config(); a prebuilt Backend remains the custom escape
hatch for callers that need a different execution mechanism.

For many suites (and future parallel runs), open a session so the
boot image is specified once and all per-run state is swept together
— in pytest, from the consumer's conftest.py:

    import testaferro

    testaferro.start()              # or start(boot_image=...)

    def pytest_unconfigure(config):
        testaferro.stop()
"""

# eager: the facade's own imports are stdlib-only (pytest is loaded
# lazily inside it). start/stop delegate lazily instead, because
# importing testaferro.qemu pulls in relict.
from .facade import guest_suite  # noqa: F401


def config(machine, platform=None, **options):
    """Declare a named relict test machine.

    ``platform`` is optional when the supplied ``machine_config`` or
    ``template`` declares it. Without a template, remaining options
    construct relict.MachineConfig directly. The declaration is reused
    as a template; each guest session receives a fresh materialization.
    """
    from .machines import configure
    return configure(machine, platform=platform, **options)


def start(boot_image=None):
    """Open a guest-test session: one boot-image choice (or the
    downloaded default) serving every suite until stop(). Costs
    nothing until a guest actually runs; an atexit failsafe sweeps
    the session if stop() is never called."""
    from . import qemu
    qemu.start(boot_image=boot_image)


def stop(clear_downloads=False):
    """Close the session, sweeping its staged image and all per-run
    state; safe without an active session. `clear_downloads=True`
    also drops the cached default boot image."""
    from . import qemu
    qemu.stop(clear_downloads=clear_downloads)
