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

## F11 — The environment noun at the consumer surface

Serves **P2** (in pledged/ARCHITECTURE.md, D18) and **U9**
(drafted). testaferro's guest-facing vocabulary becomes one noun in
the code: `environment=` replaces `machine=` at `guest_suite()`, in
`testaferro.ini`'s sections, and in the plugin's option and ini key.
`machines.py` becomes `environments.py` and `MachineSpec` becomes
`EnvironmentSpec`, because *machine* stops being testaferro's word —
`catalog.py` already holds standard environments and needs only its
prose. `config()` keeps its name: P2 governs the vocabulary a suite
writes, and a function that declares one is not itself part of it.

**`platform=` leaves the consumer surface, and this is not a
capability loss** — worth stating, because the removal will read like
one. It does two jobs today: choosing among declared machines, and
overriding what the executable's format inferred. Naming an
environment covers both. What it does *not* do is disappear from
`testaferro.ini`, where it stays a blueprint field passing through
untouched (P2, P3): what changes is whose word it is, not whether a
tester may write it. Format inference survives whole, internally —
an executable with nothing declared still selects a standard
environment (P8).

Reaches the first three enumerated interfaces and renames the second
and third of them. It also moves a clause a **pledged** use case
leans on: U4 cites U3's "selects the same machine", so that wording
travels with the vocabulary — the cost D13 recorded and D18 incurred
deliberately.

> **This sits at the top of the sprint bound**, not comfortably
> inside it: a rename across four surfaces plus tests and docs. If it
> proves larger once picked up, cut it again rather than letting it
> sprawl — the bound is the rule, not this entry's guess at it.

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

Needs F11 delivered first, the declaration being what a `provider=`
hangs on. That is an ordinary sideways reference and says nothing
about when either is picked up.
