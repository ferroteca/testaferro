<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# Proposed features

> **Status:** drafted, not pledged. **Nothing is worked from here.**
> Large capability the project may want, each carrying whatever
> design is already settled about it — migrated from the retired
> `ROADMAP.md` when Testaferro adopted the planning model (D7). A
> feature arrives in `pledged/FEATURES.md` by being moved there, and
> the commit that moves it is the record of the pledge.

Each feature carries an **F-number**: the handle a dependency, a
commit or a decision points at. F-numbers are the handles of *work*,
so they **evaporate on delivery** — the item stops existing, its
number retires unreused, and gaps in the sequence are history rather
than a promise. **The numbers carry no order and no date**; F1 was
merely the first issued, and is already a gap.

**A feature must fit in one sprint**, and the bound bites at
**the pledge**, not here. Large, shapeless capability is welcome in
this file; cutting it into implementable pieces is part of what
pledging it means, and a split retires the parent's number for a
fresh one per piece. Entries flagged below as too large must be cut
at the pledge.

**Three numbers here are retired by split**, which is what the sprint
bound does at the pledge: the parent goes and each piece takes a
fresh one, because sub-numbering would build a hierarchy and
hierarchy is how a feature list turns into a schedule.

- **F1** (D9): the backend-resolution seam became F7, the
  command-line surface became the plugin, F8, and the `run` verb
  died with the wrapper it named — a lifecycle CLI survives inside
  F2, whose verbs are not test runs. Both pieces were pledged and
  both have since been delivered, so both numbers have evaporated
  in their turn.
- **F10**, the test-environment vocabulary: too large as written, so
  pledging it meant cutting it. The noun at the consumer surface
  became **F11** and the provider axis became **F12**; both have since
  been delivered and both numbers have evaporated with them, which is
  the cut working — two bounded pushes where the parent was one
  shapeless one. The binding rename it also carried had already
  landed on its own (D16).
- **F6**, the integration tier: too large as written, and it grew a
  dependency the project did not have. Its own text named its first
  slice, and that slice was **F13** — one real suite, one real
  machine, one real failure — **delivered, its number evaporated with
  it**. What F6 could not carry became **F14** (CppUTest's own
  output) and **F15** (the remaining journeys), the latter still
  below.

**F14 retired without ever being separate work.** It was issued to
hold an open question — whether CppUTest builds for a DOS target at
all — which turned out to be answered upstream, in CppUTest's own
`platforms/Dos`. With that settled there was nothing left in F14 that
F13 was not already doing, so it was absorbed and its number retires
unreused like any other. A number is a handle for work; where the work
turns out not to exist apart, neither does the handle.

A gap in the numbering here is where one of them went.

**F9 and F18 have left this file too**, each pledged alongside its
use case — F9 with U7, F18 with U10 — not retired, not split at the
time, just moved. F18 lives in
[../pledged/FEATURES.md](../pledged/FEATURES.md) now; F9 has since
delivered and retired, arming U7 with it.

## F2 — Persistent machines and the lifecycle verbs

Serves **U8**. A test machine that opts out of the sweep: its disks
persist when the session ends, because shutting down is not
destroying. The cycle is the pytest session — the machine boots
when the first suite needs it, serves every test that names it
while up, and shuts down at session end — and the next session
boots the same disks with the harness still in place. Destroying is
explicit: `testaferro shutdown`, `testaferro destroy`, plus cache
management, as verbs of a small lifecycle CLI — the one
command-line surface D9 leaves standing, carried by a
`[project.scripts]` console entry that does not exist today.
Persistence is also what makes provisioned platforms viable (U7,
F9): an install-recipe machine document implies provisioning and
reuse rather than a fresh machine per session.

Note the tension with **P5**: a machine surviving a session is state
Testaferro created and did not sweep. Pledging this feature means
saying exactly what remains, where, and how a user gets rid of it —
U8 already demands it be enumerable and removable.

## F3 — Intra-suite sharding

Serves **U5**, and the parallelism item with real payoff. A middle
backend operation between `run_all()` and `run_test()` — "run this
subset in one boot": CppUTest filter argv can select several tests
per invocation, so a worker holding part of a suite boots once
rather than once per test. That makes `--dist load` efficient on a
single suite (roughly N× wall clock for N workers) and softens
`-k`-narrowed selections in serial runs too.

Touches `ResultBroker`, the `Backend` seam, and the CppUTest argv
builders — so it changes an enumerated interface (the `Backend` ABC)
and takes the argued route regardless of its size.

## F5 — A second guest platform binding

A guest OS beyond DOS surfacing through the facade: a platform name,
its binary formats and default boot media in `binfmt`, and a thin
binding module. Waits entirely on reliquary — install media,
unattended setup and platform-specific completion detection are its
work, not Testaferro's (D2). This entry is shapeless until a
specific platform is named, and cutting it means naming one.

## F15 — The remaining journeys, proven

The end-to-end coverage the first integration slice deliberately
left: **U3**'s declared environments booting for real — a
`testaferro.ini` beside a project selecting a machine that actually
comes up — and **U5**'s parallelism, where every xdist worker collects
and so every worker wants a guest. Each is a journey a consumer takes,
and neither can be armed on unit tests (P10 says why: nearly all of
this project's behaviour can only be proved by booting a guest).

> **Now measurable, and worth cutting on that basis.** The tier
> exists and its five cases take about a minute, most of it one boot;
> what an integration test costs is no longer a guess. That is what
> decides whether this is one feature or four.
