# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""The backend-resolution seam: an executable plus options becomes a
Backend.

Every entry point resolves through here, so the rules are stated once
and answer the same way whoever asked: which project declarations are
in scope, what the executable's own format says, which named test
environment is selected — project declarations first, then the
standard catalog (D10) — which binding runs it, and whether the
options given are ones that binding accepts. What comes back is a
`Backend`; everything above it (pytest items, batching, reporting) is
the entry point's own business.

`platform` is nothing a consumer says (P2): it reaches here as a
blueprint field on the selected environment, or as what the
executable's own format inferred, and it is read only to pick the
binding.

The seam is entry-point-neutral, and `search_from` is where that
shows. It is the directory the upward search for `testaferro.ini`
starts from, and each entry point computes it in its own vocabulary:
the embedding facade from its caller's stack frame, a collection
plugin from the file it collected. Nothing here can know how the
caller was reached, so nothing here tries.

Failing before a guest boots is the rule (P7): a provably foreign
binary, an ambiguous environment selection and an option the selected
binding does not take are all refused here, naming what was found and
what the choices were.
"""

from __future__ import annotations

import importlib
import os

from . import binfmt

# platform name -> the provider binding that runs it (a sibling
# module, imported only when resolution selects it). A binding is
# named for its provider, never for what that provider drives
# underneath (D16); reliquary is the only one built (P1, D11).
_PLATFORM_PROVIDERS = {"dos": "reliquary"}


def resolve_backend(target, environment=None, search_from=None,
                    **options):
    """Build the suite backend for an executable path.

    `target` is the suite executable. `environment` names a test
    environment — one the project declared with `testaferro.config()`
    or `testaferro.ini`, or one of the standard environments
    testaferro curates; `search_from` is the directory the search for
    a project `testaferro.ini` starts from (default: the current
    directory). Every further keyword is passed to the selected
    binding, which owns validating it: `framework` and `enumerator`
    today, plus that environment's own options.
    """
    # lazily: environments pulls in reliquary, and this is the first
    # point that actually needs it.
    from . import environments

    environments.load_config(search_from=search_from)
    fmt = binfmt.classify(target)
    if fmt.platform is None and environment is None:
        raise ValueError(
            f"{os.path.basename(os.fspath(target))} is "
            f"{fmt.kind} executable; no test environment here runs it")
    selected = environments.select(environment, fmt.platform)
    if selected is not None:
        name, machine_config = selected
        if "machine_config" in options:
            raise TypeError("machine_config cannot be combined with a "
                            "named environment")
        selected_platform = machine_config.platform
        options["machine_config"] = machine_config
    else:
        name, selected_platform = None, fmt.platform
    if selected_platform not in _PLATFORM_PROVIDERS:
        # The platform is a blueprint field the tester wrote, or what
        # the format inferred — never an option anyone typed — so the
        # refusal names whichever it was.
        source = (f"test environment {name!r} declares platform"
                  if name is not None else "the executable's format is")
        raise ValueError(
            f"{source} {selected_platform!r}, which no binding here "
            "runs; supported: "
            + ", ".join(sorted(_PLATFORM_PROVIDERS)))
    binding = importlib.import_module(
        "." + _PLATFORM_PROVIDERS[selected_platform], __package__)
    try:
        return binding.suite_backend(target, **options)
    except TypeError as error:
        if "unexpected keyword argument" not in str(error):
            raise
        raise TypeError(f"{error} — options are environment-specific; "
                        f"the selected environment runs on "
                        f"{selected_platform!r}") from None
