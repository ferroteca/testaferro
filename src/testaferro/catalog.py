# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""The standard environments Testaferro curates, reachable by name.

Between having nothing to declare and declaring an environment of
one's own sits a name: ``environment="freedos"`` selects an
environment Testaferro itself authors and maintains — today's
zero-configuration guest made nameable — and ``environment="dosbox-x"``
its sibling on the second provider. An environment name resolves
against the project's own declarations first and against this catalog
second (D10).

**What Testaferro offers, Testaferro authors** (P17). Every entry
here is a complete declaration written in this file, spelled exactly
as a ``testaferro.ini`` section or a ``testaferro.config()`` call
spells one (P16) — the provider beside the provider's own document,
in that provider's own vocabulary, carried through untouched exactly
as a declaration is (P3). No entry names a file outside this module,
none is a name resolved out of reliquary's codex, and none is read
from the user's reliquary home (D6): a test run depends only on state
Testaferro authored or the project checked in.

``freedos`` declares nothing but its platform, and that is the point:
the DOS binding fills in the memory default and boots the FreeDOS
image it downloads once and caches, so naming this environment and
naming none run the same guest.

``dosbox-x`` is the same idea one provider over, with one authored
section (F21): a suite is run for its answer, not for its timing, so
the CPU runs as fast as the host allows. A suite that cares about
real-mode timing belongs on the default provider (D27), and a project
wanting DOSBox-X's own default for ``cycles`` declares an environment
without the section — what the catalog authors is its own, never a
ceiling on what a declaration may say.
"""

from __future__ import annotations

import types


STANDARD = types.MappingProxyType({
    "freedos": {"platform": "dos"},
    "dosbox-x": {"provider": "dosbox-x", "cpu": {"cycles": "max"}},
})
