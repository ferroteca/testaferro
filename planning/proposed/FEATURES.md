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

## F20 — DOSBox-X as a second execution provider

Serves **P1**, and is the event three entries defer to rather than
refuse: D1 reconsiders a runner seam "only if a second actual runner
appears", D11 leaves construction "waiting on a second concrete
provider", and D16 declines a `providers/` package until "the day a
second binding exists". Each names this as the trigger. The work is a
binding module for DOSBox-X, its `PLATFORMS` declaring `dos`, and
`provider=` accepting a second value — the axis P1 already describes,
exercised for the first time.

**The argument is cost, and P10 is where it lands.** The tiers are
split on expense rather than coverage, and nearly everything
Testaferro does can only be proved by booting a guest — so integration
carries most of the real coverage, at roughly fifteen seconds for a
single boot. DOSBox-X does not boot: it starts a DOS in about a
second, serves a host directory as a drive with no image at all, and
needs no install. If that holds, the tier's cost curve changes shape
and work currently priced out of being tested becomes cheap. **That is
a claim to measure before pledging, not to assert** — and measuring it
is itself cheap now that the tier exists to measure against.

**The shape is batch, not interactive, and that is the whole design.**
Reliquary's model is a machine that stays up with an `exec()` per
operation against it. DOSBox-X has no such channel and should not be
given one: each `Backend` operation becomes one DOSBox-X invocation
whose generated conf mounts the work directory in `[autoexec]`, runs
the argv, redirects to a file on it, and exits. The host then reads
the file. Three consequences, every one of them a simplification:

- **The screen transport disappears.** A redirected file is CppUTest's
  own bytes, blank lines and tabs intact, so the mangling the grammar
  had to learn to tolerate (P9, and the defect that taught it) is not
  exercised at all. A second provider reading the same framework
  through a clean channel is also the best check available that the
  grammar is right about *CppUTest* rather than right about
  reliquary's screen.
- **Readiness does not apply.** `[autoexec]` runs after DOS is up by
  construction, so the invariant whose absence made every run's first
  command come back as the boot's own output has nothing to guard.
- **Nothing is written at rest.** A mounted host directory is the work
  drive, so `at_rest`, remanence and the letter map stay reliquary's
  business and none of this binding's.

**What the pledge costs is not the binding.** Three things land with
it:

- **P1 is amended**, in force at the root, on two clauses: "reliquary
  is the only supported one" stops being true, and the note that
  `start()`/`stop()` reach `reliquary.py` by name stops being a
  declared stop-short and becomes a divergence — P1 already calls it
  "the first place to look the day a second binding lands". Neither is
  a reversal; both are the entry catching up to code that moved.
- **The seam is derived, not designed.** D1 and D11 both hold that a
  richer provider interface comes from the concrete implementations
  once there are two, so this is where that judgement finally gets
  made: what `_GuestLifecycle` holds that is genuinely reliquary's,
  and what belongs above it, is answerable for the first time.
- **Inference does not become a choice** (P8). Two providers serve
  `dos`, so the platform-to-provider mapping stops being a function.
  The default stays reliquary and DOSBox-X is reached by declaring it,
  so zero configuration keeps meaning exactly one thing.

**The open question that may cut this in half is U10.**
`guest_session()` is in force: a script runs guest commands one at a
time and reads each answer back, with guest state persisting between
them. The batch model has no answer for that, and relaunching per
command discards the very state a session exists to hold. Either the
binding refuses guest sessions and says so — a provider serving some
entry points and not others, which nothing in the architecture
currently contemplates — or DOSBox-X gets an interactive channel after
all and the simplicity above is spent buying it. **Answer this before
pledging**; it decides whether this is one piece or two.

**Licensing needs a new entry, and that is new in itself.** Testaferro
would invoke an external emulator *itself*, where today QEMU is
reliquary's to invoke and the arm's-length analysis deliberately lives
there. DOSBox-X is **believed GPL-2.0-or-later and unverified** —
verify against the upstream tag before pledging, as the prior-art rule
requires at the version in question. Invoked as a separate process it
is tier 2 and adds no runtime dependency, so P11's cap holds;
bundling it into either build artifact would demote it and must not
happen. A `dosbox` standard environment would also be the catalog's
first entry with nothing to author (P17), DOSBox-X bringing its own
DOS — either a pleasant degenerate case or a sign the catalog's shape
quietly assumes a document.

**Too large as written**, and the cut lines are the three questions
above: the measurement, the suite-running binding, and U10's answer.
One naming detail waits at the pledge — a binding is named for the
provider it binds (D16), and `dosbox-x` is not a Python identifier, so
`provider="dosbox-x"` resolving to a `dosbox_x` module wants the same
hyphen normalization the declaration keys already use, or a different
name.
