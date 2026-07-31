# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""The standard environments testaferro curates, reachable by name.

Between having nothing to declare and declaring an environment of
one's own sits a name: ``environment="freedos"`` selects an
environment testaferro itself authors and maintains — today's
zero-configuration guest made nameable, with siblings arriving as
guests grow. An environment name resolves against the project's own
declarations first and against this catalog second (D10).

**What testaferro offers, testaferro authors** (P17, drafted). Every
entry here is a complete document written in this file — the machine,
the drives it declares, and the media those locate — in the provider's
own vocabulary (a reliquary blueprint today), carried through
untouched exactly as a declaration is (P3). No entry is a name
resolved out of reliquary's codex, and none is read from the user's
reliquary home (D6): a test run depends only on state testaferro
authored or the project checked in.

``freedos`` declares nothing but its platform, and that is the point:
the DOS binding fills in the memory default and boots the FreeDOS
image it downloads once and caches, so naming this environment and
naming none run the same guest.
"""

from __future__ import annotations

import types


STANDARD = types.MappingProxyType({
    "freedos": (
        {"type": "machine", "name": "freedos", "platform": "dos"},
    ),
})
