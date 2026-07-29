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

## F13 — The first end-to-end run

Serves **U4** (pledged), and U1, U2 and U3 behind it. **One real
suite, booting one real machine, reporting one real failure.** No
guest has run since the migration to the blueprint model (D4), so
nothing this project says about a guest has ever been observed. The
feature adds no capability — it converts claims into evidence, which
is why its absence is what keeps root `USE-CASES.md` from existing at
all.

**One feature and not two**, because a guest suite with nothing to run
it and a tier with nothing to run are each meaningless alone. Its work
items therefore carry the one ordering that binds: the suite, the
tier, then the run.

Three things were left to decide at the pledge, and are decided here.

**The suite is authored, not built with CppUTest.** A small DOS
program that answers `-ln` with a CppUTest-shaped test list and `-v`
with CppUTest-shaped verbose output, failing one test on purpose so a
real failure has something to be. Building CppUTest itself for a
16-bit DOS target is a separate question with its own feasibility
risk, and it is **F14** — pledging it now would pledge something
nobody can yet size. What the authored suite cannot prove is stated
plainly rather than glossed: it proves the machinery end to end, and
it does not discharge what P9 names as its own cost, since a grammar
answering to a fixture testaferro wrote is answering to itself.

**The tier is stdlib `unittest`, under `tests/integration/`, skipped
unless asked for.** Tests here are stdlib `unittest` and that
constraint is not spent on this; `skipUnless` on an environment
variable is how the existing suite already gates on reliquary and
pytest being installed, so the tier is that mechanism one step
further. The unit run therefore stays exactly as cheap as P10 requires
it to be, and stays cheap by default rather than by discipline. Root
[AGENTS.md](../../AGENTS.md) mentions `pytest -m integration`; that
describes a *consuming* project's run and is not this tier, and the
wording is corrected with this work.

**A checked-in binary is covered in `REUSE.toml`.** It cannot carry an
SPDX header, and the licensing rule admits exactly that case. The
suite's source and its build recipe are checked in beside it, so the
binary is reproducible rather than magical, and P12 holds throughout:
this is testaferro's own fixture and names no consuming project.

**What the run must show** is the whole point, so it is enumerated:
the guest boots from the cached image, the work drive carries the
executable in at the letter testaferro named, `-ln` comes back and
parses, a run comes back and parses, one test passes and one fails,
and the failure surfaces as the guest's own file, line and assertion.
Anything it shows that testaferro did not expect is the feature
earning its keep — the screen-capture questions raised while D19 was
being built (whether `parse_list`'s strictness survives real capture,
and whether an 80-column wrap corrupts an id before it fails) can be
answered no other way.
