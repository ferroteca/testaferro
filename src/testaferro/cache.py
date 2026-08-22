# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Testaferro's durable filespace, shared by the guest bindings.

Also where a finished guest home is handed back, because whether one
is swept or kept is Testaferro's own policy rather than any one
binding's: `release_guest_home()` is the single place that decides,
and the exploration option that flips it (`keep_guest_homes()`) is
asked here by whoever reports it. Nothing in this module knows which
guest made the directory, which is what lets the pytest plugin read
the answer without importing a binding — or a provider.
"""

from __future__ import annotations

import os
import shutil

# Exploration: keep guest homes rather than sweeping them, because
# looking at what the guest was given is the whole point of asking.
_keep = False
_kept = []


def keep_guest_homes(enabled=True):
    """Preserve guest homes rather than sweeping them. Set before any
    guest starts; what was kept is reported by kept_guest_homes()."""
    global _keep
    _keep = bool(enabled)


def keeping_guest_homes():
    """Whether homes are being kept, asked *before* one is released.

    `release_guest_home()` answers the same question by acting on it,
    which is too late for a binding that must do work to make a kept
    home worth having — retrieving what a run left inside a drive
    image, which can only happen while the machine still exists.
    """
    return _keep


def kept_guest_homes():
    """Every guest home preserved so far, in the order made."""
    return tuple(_kept)


def release_guest_home(path):
    """Give back a finished guest home: swept, or kept when the tester
    asked to see it. Returns whether it was kept.

    A kept home is a directory and never a running guest — the machine
    that made it is stopped before any of this, on every exit path — so
    this trades disk for evidence and nothing else.
    """
    if not _keep:
        shutil.rmtree(path, ignore_errors=True)
        return False
    _kept.append(path)
    return True


def cache_root():
    """Testaferro's own filespace: each guest binding's image cache
    plus its disposable guest homes.

    The layout says which span made what (D15): `runs/run-*/` is one
    Testaferro run — `start()` to `stop()`, one staged image shared by
    many suites — and `guests/guest-*/` inside it is one guest
    session's home. A guest belonging to no run sits in `guests/` at
    this level instead. Stale directories from killed processes can
    be deleted freely — `testaferro clean` does exactly that.

    `machines/<name>/` is the one thing here that is **not**
    disposable: a persistent machine a declaration asked for by name
    (`persist=`, F2, U8), kept between runs on purpose and removed
    only by `testaferro destroy <name>`.
    """
    if os.name == "nt":
        base = (os.environ.get("LOCALAPPDATA")
                or os.path.join(os.path.expanduser("~"),
                                "AppData", "Local"))
    else:
        base = (os.environ.get("XDG_CACHE_HOME")
                or os.path.join(os.path.expanduser("~"), ".cache"))
    return os.path.join(base, "testaferro")


def machines_root():
    """Where persistent machines live, one directory per name.

    Kept apart from the run and guest areas so that a sweep of what
    runs leave behind can never take a machine a tester asked to keep
    (P5): everything else under the cache root is disposable, and
    this directory alone is not.
    """
    return os.path.join(cache_root(), "machines")
