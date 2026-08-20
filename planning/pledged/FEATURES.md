<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
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

## F19 — Prove the standard catalog resolves by name

Serves **U9**. `environments.select(name="freedos")` and the
resolution seam it feeds (`catalog.py`, D10) already run project
declarations first, then the standard catalog, and are unit-tested —
nothing here is unbuilt mechanism. What U9 still owes is proof: one
integration case that names `"freedos"` explicitly —
`environment="freedos"` (or a declaration's `machine="freedos"`) —
and boots a real guest through it, showing the named path resolves to
the standard catalog's own document rather than only the
zero-configuration default's inference reaching the same disk
unnamed.

No new machinery, no interface change: this is one case added beside
the integration tier F13 already delivered, in the same shape U4's
own trial journey was proven — a real guest boot, not a unit test
standing in for one (P10).
