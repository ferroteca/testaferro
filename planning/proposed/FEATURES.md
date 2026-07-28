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
than a promise. **The numbers carry no order and no date**; F1 is
merely the first issued.

**A feature must fit in one sprint**, and the bound bites at
**the pledge**, not here. Large, shapeless capability is welcome in
this file; cutting it into implementable pieces is part of what
pledging it means, and a split retires the parent's number for a
fresh one per piece. Two entries below are flagged as too large as
written.

## F1 — The command-line entry

Serves **U4**. A second entry point onto the same execution path:
`testaferro run tests/vring16.exe` tries a suite against a guest
without the developer first writing anything into their project.

> **Too large as written** — several sprints, and it must be cut at
> the pledge. The seam extraction, the `run` verb, and the
> exploration flags are three separable pieces at least.

Settled design:

- **The CLI runs pytest; it does not report for itself.** It
  resolves the backend, generates a one-line test module, and hands
  it to `pytest.main()`, forwarding whatever follows `--`. So the CLI
  exercises the embedded path rather than approximating it: `-k`,
  `-v`, `-x`, `--tb`, `--lf` and third-party plugins all come free,
  and there is no second reporter to drift. A hand-written
  pytest-alike reporter is **rejected on purpose** — divergence
  between what the CLI shows and what the consumer gets after
  embedding would defeat the CLI's only reason to exist.
- **The shared seam is backend resolution.**
  `facade._dispatched_backend()` — config search, platform
  validation, format classification, machine selection, binding
  import, option validation — moves into the core as the single place
  where "an executable plus options" becomes a `Backend`. Both entry
  points call it. Extracting it is the first work item, since today
  it is fused to the pytest entry point: it takes `search_from`,
  which `guest_suite()` computes from the caller's stack frame.
- Afterwards the entry points differ in three known places only:
  **config search origin** (the caller's file when embedded, the
  current directory from the CLI); **session lifecycle** (a consumer
  conftest calls `start()`/`stop()`, the CLI wraps its own run); and
  **enumeration** (embedded consumers usually pass a host-built twin
  as `enumerator=`, while the CLI enumerates in the guest unless
  given `--enumerate-with` — the lossier path, since agentless
  capture returns the visible screen and a long list loses its head).
- **Flag and keyword parity** is P16: `--machine` ↔ `machine=`,
  `--framework` ↔ `framework=`, `--boot-image` ↔ `boot_image=`,
  `--enumerate-with` ↔ `enumerator=`.
- **Deliberate asymmetry: exploration-only flags.** `--list`
  (enumerate and stop), `--keep` (leave the run home behind for
  inspection instead of sweeping it), and `--snippet` (print the test
  module to paste into the consumer project). `--snippet` is what
  makes the two entry points literally one path: the CLI's output is
  the embedded form.
- **One CLI, subcommands.** `run` is one verb of the same executable
  that carries F2's lifecycle verbs. A `[project.scripts]` console
  entry is needed; there is none today. P11's lazy-pytest rule
  becomes "confined to `facade.py` and the CLI module".

**Decide first:** what a machine name resolves to — the
zero-configuration image or a named reliquary blueprint
([../DECISIONS.md](../DECISIONS.md), Open questions).

## F2 — Persistent machines and the lifecycle verbs

Test machines that opt out of the sweep at `stop()`, keeping their
guests warm for reuse across pytest runs and shut down explicitly:
`testaferro shutdown`, plus cache management, as verbs of F1's
executable.

Depends on **F1** — the executable that would carry the verbs does
not exist yet. Also the shape that would make a named-blueprint
machine viable, since an install-recipe blueprint implies
provisioning and reuse rather than a fresh machine per session.

Note the tension with **P5**: a machine surviving a session is state
testaferro created and did not sweep. Pledging this feature means
saying exactly what remains, where, and how a user gets rid of it.

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
