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

## F9 — In-guest harness prep

Serves **U7**. Two levels, both declared, both optional. The
per-boot level's design is settled in
[design/in-guest-prep.md](design/in-guest-prep.md); the provider
changes it rests on are argued separately, as a downstream proposal
to reliquary —
[design/reliquary-proposal.md](design/reliquary-proposal.md) — so
this feature waits on the first of those changes and on the
deliberate pin move it implies (D4).

- **Per-boot prep**: two declarations, each with the keyword and
  INI spellings every declaration has (P16), and neither a
  blueprint field — like `provider` and `timeout` they are
  testaferro's own words, said beside the machine spec, never
  inside it.

  `files=` — host paths staged onto the work drive beside the
  suite, before boot. The staging D5 already does, extended from
  one file to a list; the snapshot-before-boot invariant holds
  exactly, and landing on the work drive is what lets a setup
  command name a staged file with no path and no letter.

  `setup=` — commands run in the guest in the order given, once
  per **guest session** (D15) — every guest session, an
  enumeration boot included, since a suite that needs its TSR to
  run needs it to enumerate too — after the readiness wait,
  before anything else. Ordering within the list is the caller's.
  A setup command that fails ends the session and reports once,
  in the existing `GuestOutputError` shape: the command sent and
  the screen that came back.

  Failure is the provider's to detect, never testaferro's to
  parse: the downstream proposal asks reliquary's `exec()` to
  report each command's success (guest-side mechanics belong to
  reliquary, D2), and a consumer's setup programs owe an honest
  exit code in return. **Weighed and declined:** pre-boot validation of
  `setup` commands against the staged files and a shell-builtin
  list. The builtin list is a vocabulary testaferro would have to
  keep on the shell's behalf — the kind of mirror `_work_drive()`
  just paid to delete — and the staged-file check refuses
  legitimate commands naming programs on the system disk, a
  tester's floppy, or `PATH`. Keeping `files` and `setup`
  agreeing is the caller's own obligation, and a typo surfaces as
  a loud setup failure rather than a pre-boot refusal.

- **Boot-level support**: a device driver or installed component
  that must exist before the guest OS finishes booting. No
  post-boot step can add it: it rides a tester-authored boot image
  (U3) or a provisioned platform — a full machine document whose
  scripts bake a disk, the provider owning the in-guest install
  work (D2), viable per-run only where the machine persists (U8,
  F2).

The sibling fact — the *machine* exposing the device a driver
under test drives — is deliberately not this feature. It is a
machine fact, declared in the environment and passed through
untouched exactly as every blueprint field is (D4), so it becomes
expressible the day reliquary ships the `devices` vocabulary the
downstream proposal argues, with no testaferro change at all.

The prep vocabulary is new declaration surface and lands through
the interface-change rule; one declaration, three spellings, so it
touches the embedding API, the declaration, and `testaferro.ini`
together (the first, second and third interfaces).

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
