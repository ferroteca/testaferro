# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Test placement, shared across the provider bindings.

`files=`, `location=`, `program=` and `setup=` are Testaferro's own
words (F4, F9), never a provider document's fields — so the mechanics
behind them belong to no one binding. This module holds what every
binding does with them the same way: the nearest-speaker override
rule, the host-side gathering of the staged set, and the resolution
of `program=` against a settled location. What a *location* means —
which drives exist, what letter the staged set answers to — stays
each binding's own, because only the binding knows what it serves.

Derived from the two concrete bindings rather than designed ahead of
them (D1, D11): this module exists because `testaferro.dosbox_x`
arrived and did these three things exactly as `testaferro.reliquary`
already did, which is the event those decisions were waiting on.
Anything the second binding did *differently* stayed out.
"""

from __future__ import annotations

import os
import shutil

# What `program=` may say before the location is known. `{stem}` and
# `{name}` in the enumerator template are the precedent; this joins
# that vocabulary rather than inventing a second one (F4).
LOCATION_PLACEHOLDER = "location"


def nearest(given, declaration, name, default=None):
    """This call, then the declaration, then the default.

    The same rule for every placement word, so a consumer never has
    to remember which options overrule a declaration. `declaration`
    is the environment's own spec, or None when the run declared no
    environment; an empty tuple counts as unsaid exactly as None
    does, both being the shape "nothing was declared" takes.
    """
    declared = (None if declaration is None
                else getattr(declaration, name, None))
    return next((value for value in (given, declared)
                 if value not in (None, ())), default)


def gather(target, files, exe_path=None):
    """Collect the staged set into one host directory.

    The suite executable, when there is one — a scripted guest
    interaction names none — plus each `files=` entry beside it. A
    named directory contributes its contents rather than itself,
    which is what makes `files=["fixtures"]` land the fixtures where
    a guest program will look for them instead of one directory
    deeper.
    """
    if exe_path is not None:
        shutil.copy2(exe_path,
                     os.path.join(target, os.path.basename(exe_path)))
    for source in files:
        if os.path.isdir(source):
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, os.path.join(
                target, os.path.basename(source)))


def resolve_program(program, location, exe_name):
    """The guest address of what to run, defaulted or declared.

    Defaulted it is the staged executable under the location, which
    is the whole of the one-liner case. Declared it is the consumer's
    own address, with `{location}` substituted — the location is
    settled by now whether they stated it or the binding chose it,
    and that is precisely what makes one placeholder enough.
    """
    if program is None:
        return join(location, exe_name)
    try:
        return program.format(**{LOCATION_PLACEHOLDER: location})
    except KeyError as error:
        raise ValueError(
            f"program={program!r} names {{{error.args[0]}}}, which "
            f"testaferro does not substitute; it knows "
            f"{{{LOCATION_PLACEHOLDER}}}") from None


def join(location, name):
    """Join a guest directory address to a name, DOS-style."""
    return location.rstrip("\\") + "\\" + name
