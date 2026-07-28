<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: BSD-3-Clause
-->

# Proposed features

> **Status:** drafted, not pledged. **Nothing is worked from here.**
> Large capability the project may want, each carrying whatever
> design is already settled about it — migrated from the retired
> `ROADMAP.md` when testaferro adopted the planning model (D7). A
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

**F1 is retired by split** (D9): the backend-resolution seam became
F7, the command-line surface became the plugin, F8, and the `run`
verb died with the wrapper it named — a lifecycle CLI survives
inside F2, whose verbs are not test runs. Both pieces were pledged
and both have since been delivered, so both numbers have evaporated
and nothing is pledged today: `pledged/FEATURES.md` will reappear
with the next promotion. A gap in the numbering here is where one
went.

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
testaferro created and did not sweep. Pledging this feature means
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

## F4 — A specified insertion point

Replaces the testaferro-supplied hostdir work drive (D5) with an
explicit insertion point in the declaration — a slot plus a guest
directory, e.g. `hdd0:\TESTS\`.

Waits on reliquary maturity, and the blocker is concrete: writing
into an image drive would be testaferro's own offline work, since
reliquary blesses writes to a stopped machine's `drives/` but
provides no FAT writer, and `insert_media()` covers only floppy and
cdrom slots, never `hdd`. A FAT-writing dependency is what this
feature costs today, which P11 is exactly the rule for weighing.

## F5 — A second guest platform binding

A guest OS beyond DOS surfacing through the facade: a platform name,
its binary formats and default boot media in `binfmt`, and a thin
binding module. Waits entirely on reliquary — install media,
unattended setup and platform-specific completion detection are its
work, not testaferro's (D2). This entry is shapeless until a
specific platform is named, and cutting it means naming one.

## F6 — The integration tier

The verification testaferro does not have. There is **no integration
suite**, so no guest has run since the migration to the blueprint
model (D4), and U1, U2, U3 and U5 cannot be armed on the strength of
unit tests alone (P10 says why: nearly all of this project's
behaviour can only be proved by booting a guest).

> **Too large as written**, and it grows a dependency the project
> does not have: an actual guest test suite to run. Cut at the
> pledge — the first sprint's worth is one real suite booting one
> real machine and reporting one real failure.

What it is for is worth stating plainly, because it is unusual for a
feature: this one does not add capability, it converts claims into
in-force ones. Until it exists, root `USE-CASES.md` stays empty of
everything it would otherwise be ready to carry.

## F9 — In-guest harness prep

Serves **U7**. Two levels, both declared, both optional:

- **Per-boot prep**: the declaration stages named host files onto
  the work drive beside the suite — the snapshot-before-boot
  invariant holds (D5) — and runs setup commands in the guest
  after boot, before any test: TSRs, environment, the harness's
  own prep tool.
- **Boot-level support**: a device driver or installed component
  that must exist before the guest OS finishes booting. No
  post-boot step can add it: it rides a tester-authored boot image
  (U3) or a provisioned platform — a full machine document whose
  scripts bake a disk, the provider owning the in-guest install
  work (D2), viable per-run only where the machine persists (U8,
  F2).

The prep vocabulary is new declaration surface (the second
interface) and lands through the interface-change rule.

## F10 — The test-environment vocabulary

Serves **P1** and **P2** as amended in
[ARCHITECTURE.md](ARCHITECTURE.md), and **U9**. testaferro's
guest-facing vocabulary becomes one noun. A **test environment** is
what a suite runs in: a standard one testaferro authors and names
(`freedos`), or a custom one the tester declares as a choice of
provider plus all the configuration that provider requires.
`platform=` and `machine=` collapse into one way of naming one, and
`platform` goes back to being what it always was — a field in an
authored blueprint, reliquary's word, passing through untouched
(P3). `provider=` enters the declaration, which D11 already says the
tester names and nothing currently spells; the binding table keys by
provider rather than by OS family; and `testaferro/qemu.py` takes
the name of what it actually binds, since it drives reliquary and
never QEMU. That last part answers the open question asking whether
the module should be named for its *platform* instead — which the
amended vocabulary decides differently, so the question retires with
the adjudication rather than on its own terms.

Reaches four of the six enumerated interfaces — the embedding API,
the declaration, `testaferro.ini`, and the plugin's options and ini
keys, which are a second presentation of the first two — and renames
the second and third of them. It also moves a clause a **pledged**
use case leans on: U4 cites U3's "selects the same machine", so the
wording travels with the vocabulary, which is the cost D13 recorded
for reshaping what U4 rests on.

> **Too large as written**, and it cannot be picked up first: the
> amendment is the argument (INTERFACES.md), so P1 and P2 have to
> win and be pledged before this is. Cut at the pledge — the first
> sprint's worth is the noun and the resolution path it names, with
> the provider axis and the binding rename following it.
