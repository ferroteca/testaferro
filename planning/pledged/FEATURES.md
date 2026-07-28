<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: BSD-3-Clause
-->

# Pledged features

> **Status:** pledged — owed by the project, and not yet delivered.
> The project will do these and says nothing about when: **the
> absence of order is uniform**, and whoever picks work up picks
> whatever they like. The one ordering that binds runs *inside* a
> feature — the work items delivering it have to be done to complete
> it.

**F-numbers are the handles of work, so they evaporate on delivery**:
the item stops existing, its number retires unreused, and gaps in the
sequence are history rather than a promise. **A feature here fits in
one sprint** — the bound bites at the pledge, which is why the large
and shapeless entries stay in
[../proposed/FEATURES.md](../proposed/FEATURES.md). Every entry cites
what demands it.

## F12 — The provider axis

Serves **P1** (in pledged/ARCHITECTURE.md, D18) and D11, which has
said since it was written that the tester declares the provider while
nothing spells it. `provider=` enters the declaration in all three
spellings (P16, now in force), dispatch keys by provider rather than
by OS family, and each binding validates the platforms it serves —
`_PLATFORM_PROVIDERS` becoming a provider lookup outright. Reliquary
stays the default and the only one built (P1), so an unknown provider
is refused by naming what exists.

**Naming the choice is not building the seam.** D1 refused a
structural runner contract and any abstraction built ahead of a
second concrete provider, and P1 carries that refusal verbatim; this
adds a declaration keyword, which D11 already blesses, and no layer
behind it. A second provider remains F5's problem and needs a
concrete one to exist first.

It needed F11 first, the declaration being what a `provider=` hangs
on; F11 has since been delivered and its number has evaporated, so
nothing stands in the way of picking this up.
