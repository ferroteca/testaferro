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

**Four numbers here are retired by split**, which is what the sprint
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
  output) and **F15** (the remaining journeys), the latter since
  split in its turn, below.

**F14 retired without ever being separate work.** It was issued to
hold an open question — whether CppUTest builds for a DOS target at
all — which turned out to be answered upstream, in CppUTest's own
`platforms/Dos`. With that settled there was nothing left in F14 that
F13 was not already doing, so it was absorbed and its number retires
unreused like any other. A number is a handle for work; where the work
turns out not to exist apart, neither does the handle.

- **F15**, the remaining journeys: cut at the pledge to the one
  journey nothing had exercised, **U5**'s parallelism, which became
  **F22** — pledged and delivered in one change, the F20 precedent —
  and is gone in its turn. The other half, U3's declared environment
  booting for real, had already been run by the tier (a
  `testaferro.ini` beside a project, claiming a suite and booting the
  environment it names, in `tests/integration/test_guest_run.py`),
  so no work remained in it to carry a number; what U3 itself still
  owes is its own clauses, and it stays drafted here, unowed.

A gap in the numbering here is where one of them went.

**F9 and F18 have left this file too**, each pledged alongside its
use case — F9 with U7, F18 with U10 — not retired, not split at the
time, just moved. Both have since delivered and retired, arming U7
and U10 with them.

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

**Pledged and withdrawn the same day** (D24): CppUTest's own filter
model makes safe batching possible only through a group-scoped filter
argv, a sixth callable on the framework-adapter seam that contradicts
P4's own count — "`SuiteBackend` calls exactly those five." Reconsider
once P4 is amended to make room for one, or a shape is found that
does not need it; either is a pledge of its own, not a resumption of
this one.

## F5 — A second guest platform binding

A guest OS beyond DOS surfacing through the facade: a platform name,
its binary formats and default boot media in `binfmt`, and a thin
binding module. Waits entirely on reliquary — install media,
unattended setup and platform-specific completion detection are its
work, not Testaferro's (D2). This entry is shapeless until a
specific platform is named, and cutting it means naming one.
