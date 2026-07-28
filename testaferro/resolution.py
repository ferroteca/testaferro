# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""The backend-resolution seam: an executable plus options becomes a
Backend.

Every entry point resolves through here, so the rules are stated once
and answer the same way whoever asked: which project declarations are
in scope, what the executable's own format says, which named machine
is selected — project declarations first, then the standard catalog
(D10) — which platform binding runs it, and whether the options given
are ones that binding accepts. What comes back is a `Backend`;
everything above it (pytest items, batching, reporting) is the entry
point's own business.

The seam is entry-point-neutral, and `search_from` is where that
shows. It is the directory the upward search for `testaferro.ini`
starts from, and each entry point computes it in its own vocabulary:
the embedding facade from its caller's stack frame, a collection
plugin from the file it collected. Nothing here can know how the
caller was reached, so nothing here tries.

Failing before a guest boots is the rule (P7): a provably foreign
binary, an ambiguous machine selection and an option the selected
binding does not take are all refused here, naming what was found and
what the choices were.
"""

from __future__ import annotations

import importlib
import os

from . import binfmt

# platform name -> binding module (a sibling of this one), imported
# only when resolution selects it. Platform names, never emulators:
# QEMU is the binding's business and appears in no consumer's
# vocabulary (P2, D3).
_PLATFORM_BINDINGS = {"dos": "qemu"}


def resolve_backend(target, platform=None, machine=None,
                    search_from=None, **options):
    """Build the suite backend for an executable path.

    `target` is the suite executable. `platform` names an OS platform
    for when the executable's own format should not decide; `machine`
    names a test machine — one the project declared with
    `testaferro.config()` or `testaferro.ini`, or one of the standard
    environments testaferro curates; `search_from` is the directory
    the search for a project `testaferro.ini` starts from (default:
    the current directory). Every further keyword is passed to the
    selected binding, which owns validating it: `framework` and
    `enumerator` today, plus that platform's own options.
    """
    # lazily: machines pulls in reliquary, and this is the first
    # point that actually needs it.
    from . import machines

    machines.load_config(search_from=search_from)
    if platform is not None:
        platform = str(platform).lower()
        if platform not in _PLATFORM_BINDINGS:
            raise ValueError(f"unsupported platform {platform!r}; "
                             "supported: "
                             + ", ".join(sorted(_PLATFORM_BINDINGS)))
    fmt = binfmt.classify(target)
    if fmt.platform is None and platform is None and machine is None:
        raise ValueError(
            f"{os.path.basename(os.fspath(target))} is "
            f"{fmt.kind} executable; no supported platform can run it")
    selected = machines.select(machine, platform, fmt.platform)
    if selected is not None:
        _, machine_config = selected
        if "machine_config" in options:
            raise TypeError(
                "machine_config cannot be combined with a named machine")
        selected_platform = machine_config.platform
        options["machine_config"] = machine_config
    else:
        selected_platform = platform if platform is not None else fmt.platform
    if selected_platform not in _PLATFORM_BINDINGS:
        raise ValueError(f"unsupported platform {selected_platform!r}; "
                         "supported: "
                         + ", ".join(sorted(_PLATFORM_BINDINGS)))
    binding = importlib.import_module(
        "." + _PLATFORM_BINDINGS[selected_platform], __package__)
    try:
        return binding.suite_backend(target, **options)
    except TypeError as error:
        if "unexpected keyword argument" not in str(error):
            raise
        raise TypeError(f"{error} — options are machine-specific; "
                        f"the selected platform is "
                        f"{selected_platform!r}") from None
