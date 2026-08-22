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

**F3 has left this file too**, the long way round: pledged, withdrawn
the same day when its batching turned out to need a sixth
framework-adapter callable P4 did not allow (D24), and pledged again
once P4 was amended to admit an optional one (D29) — pledged and
delivered in one change, as F20 and F22 were. Its number is retired
with it.

A gap in the numbering here is where one of them went.

**F9 and F18 have left this file too**, each pledged alongside its
use case — F9 with U7, F18 with U10 — not retired, not split at the
time, just moved. Both have since delivered and retired, arming U7
and U10 with them. **F2 left last**, pledged and delivered in one
change (D30); U8 armed the same day once its one short clause was
amended to say what F2 built (D31).

## F5 — A second guest platform binding

A guest OS beyond DOS surfacing through the facade: a platform name,
its binary formats and default boot media in `binfmt`, and a thin
binding module. Waits entirely on reliquary — install media,
unattended setup and platform-specific completion detection are its
work, not Testaferro's (D2). This entry is shapeless until a
specific platform is named, and cutting it means naming one.
