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

## F3 — Intra-suite sharding

Serves **U5** (drafted). A middle backend operation between
`run_all()` and `run_test()` — "run this subset in one boot": CppUTest
filter argv can select several tests per invocation, so a worker
holding part of a suite boots once rather than once per test. That
makes `--dist load` efficient on a single suite (roughly N× wall clock
for N workers) and softens `-k`-narrowed selections in serial runs
too.

Touches `ResultBroker`, the `Backend` seam, and the CppUTest argv
builders — so it changes an enumerated interface (the `Backend` ABC)
and takes the argued route regardless of its size.

**Pledged citing a drafted use case, not paired with it.** U7+F9 and
U10+F18 were each pledged together because the use case's own text
named the feature as a hard prerequisite — neither could arm without
the other. U5 names no such requirement on F3: it describes several
suites booting concurrently, each suite's items staying together on
one worker, and says nothing about splitting one suite's items across
workers. What F3 delivers is the sharding optimization U5 calls "the
parallelism item with real payoff," a real gain on its own terms and
not the whole of U5's route — the cross-worker suite-isolation journey
still owed there is [F15](../proposed/FEATURES.md)'s to prove, not cut
yet. The general rule covers a demand pledged alone: a pledged item
may cite a use case "still drafted under `proposed/`"
([README.md](../README.md)), and nothing here requires U5's own
pledge to follow.
