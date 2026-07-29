# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""The backend-resolution seam: an executable plus options becomes a
Backend.

Every entry point resolves through here, so the rules are stated once
and answer the same way whoever asked: which project declarations are
in scope, what the executable's own format says, which named test
environment is selected — project declarations first, then the
standard catalog (D10) — which provider runs it, and whether the
options given are ones that provider's binding accepts. What comes
back is a `Backend`; everything above it (pytest items, batching,
reporting) is the entry point's own business.

**Dispatch keys by provider, and the provider is declared** (P1, P2,
D11). An environment names one or takes the default, reliquary being
the only binding built; that name selects the sibling module of the
same name, because a binding is named for the provider it binds
(D16). A name outside `_PROVIDERS` is refused rather than imported.

`platform` is nothing a consumer says (P2): it reaches here as a
blueprint field on the selected environment, or as what the
executable's own format inferred. It no longer picks anything — what
happens to it now is a check against the platforms the selected
binding says it serves, so a provider that cannot run this guest is
refused before it is asked to.

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

# The providers testaferro binds, spelled as a declaration spells
# them. A binding is named for its provider (D16), so a name here is
# also the sibling module that implements it — imported only once
# resolution has selected it, and never derived from anything a
# consumer typed that is not in this set.
_PROVIDERS = frozenset({"reliquary"})
# What runs a guest when no environment named anything (P1, D11).
_DEFAULT_PROVIDER = "reliquary"


def resolve_backend(target, environment=None, provider=None,
                    search_from=None, **options):
    """Build the suite backend for an executable path.

    `target` is the suite executable. `environment` names a test
    environment — one the project declared with `testaferro.config()`
    or `testaferro.ini`, or one of the standard environments
    testaferro curates. `provider` names what runs the guest, for an
    environment declared inline here rather than by name; a named
    environment carries its own, so the two cannot be combined.
    `search_from` is the directory the search for a project
    `testaferro.ini` starts from (default: the current directory).
    Every further keyword is passed to the selected binding, which
    owns validating it: `framework` and `enumerator` today, plus that
    environment's own options.
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
        if provider is not None:
            raise TypeError(
                f"provider cannot be combined with a named environment; "
                f"{name!r} names its own provider, or takes the default")
        selected_platform = machine_config.platform
        selected_provider = machine_config.provider
        options["machine_config"] = machine_config
    else:
        name, selected_platform = None, fmt.platform
        selected_provider = environments._provider(provider)
    selected_provider = selected_provider or _DEFAULT_PROVIDER
    if selected_provider not in _PROVIDERS:
        raise ValueError(
            f"unknown provider {selected_provider!r}; testaferro binds: "
            + ", ".join(sorted(_PROVIDERS)))
    binding = importlib.import_module("." + selected_provider, __package__)
    if selected_platform not in binding.PLATFORMS:
        # The platform is a blueprint field the tester wrote, or what
        # the format inferred — never an option anyone typed — so the
        # refusal names whichever it was. Which platforms are runnable
        # is the binding's own answer, not a table kept here: a
        # provider knows what it serves and testaferro does not.
        source = (f"test environment {name!r} declares platform"
                  if name is not None else "the executable's format is")
        raise ValueError(
            f"{source} {selected_platform!r}, which the "
            f"{selected_provider!r} provider does not run; it runs: "
            + ", ".join(binding.PLATFORMS))
    try:
        return binding.suite_backend(target, **options)
    except TypeError as error:
        if "unexpected keyword argument" not in str(error):
            raise
        raise TypeError(f"{error} — options are environment-specific; "
                        f"this environment runs {selected_platform!r} "
                        f"on {selected_provider!r}") from None
