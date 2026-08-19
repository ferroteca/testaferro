<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# Proposed use cases

> **Status:** drafted, not pledged. **Nothing is worked from here.**
> These are the use cases as reconstructed from the project's own
> prose — [README.md](../../README.md), [AGENTS.md](../../AGENTS.md)
> and the retired `ROADMAP.md` — when testaferro adopted the planning
> model (D7). They are the decision surface *once pledged*; until
> then a citation of a U-number here names a draft, and should be
> read as weaker than citing an in-force entry. Numbering comes from
> one global U-sequence, never reused, and an entry keeps its number
> when it moves to `pledged/` and again when it reaches root
> `USE-CASES.md`.

**Pledging and delivery are different events.** An entry moves to
`pledged/` when the project undertakes it, and to
[root `USE-CASES.md`](../../USE-CASES.md) only when the code meets it
in full. Several entries below already describe working code, which
makes their route short but not automatic: root is an implementation
claim, and each entry has to be met clause by clause.

**A guest runs now**, so what these wait on has changed. The
integration tier exists and U4 has armed on the strength of it, but
one boot does not arm four journeys: U1, U2, U3 and U5 are exercised
in passing by that proof rather than met in full by it — U5's
parallelism is not exercised at all — so each still owes the clauses
nobody has asserted.

Reconstructed drafts, so read them for accuracy first: these are the
owner's use cases put into words by an agent, not dictated by him.
Reshape freely — a proposed use case may be changed in nature at
will; only an in-force one may not. Reshaping a clause a *pledged*
entry leans on is still allowed and no longer free: it re-opens what
that pledge rests on (D13).

**Entries that moved on have left this file**, and a gap in the
numbering here is where one went. There is one so far: U4 was pledged
by D13, waited on the pledged shelf for a guest to run its journey,
and is now in force at [root `USE-CASES.md`](../../USE-CASES.md) — the
whole route, in the order the machinery intends.

- **U1 — Unit tests that can only run on the target OS, surfaced as
  ordinary pytest items.** A developer maintains code whose unit
  tests cannot run in the work environment at all: the suite is a
  DOS build, and a DOS build only runs on DOS. They want those tests
  in their own pytest tree, behaving like every other test there —
  `pytest` runs them, `-k` and node ids narrow them, a failure
  reports the *guest* side's file, line and assertion message rather
  than a traceback into the facade, and an IDE's run-this-test
  resolves to the item wherever it was collected — a `guest_suite()`
  call in the developer's own module, or the suite executable
  itself, which the plugin now claims. What it takes to boot a
  machine, get the executable into it, run it and read the results
  back is testaferro's business; the developer names an executable.

- **U2 — Nothing to configure.** The first run costs one line. A
  developer points the facade at a freshly built suite executable
  and gets tests: testaferro classifies the binary, boots a DOS
  image it downloaded once and cached, runs the suite, and sweeps
  everything it created. No machine to declare, no image to supply,
  nothing written into the developer's own images and nothing left
  behind. Configuration exists for when the default machine is not
  enough — it is never the price of the first run.

- **U3 — A declared test machine, checked in and shared.** Several
  suites in one project need the same machine, and it is not the
  default one: a different DOS, more memory, an extra drive. The
  developer declares it once — in `conftest.py` through `config()`,
  or in a `testaferro.ini` beside the project, which is the same
  declaration written declaratively — names it from each suite, and
  checks it in. A second developer clones the repository and gets
  the same machine without being told anything. The declaration is a
  *template*, never a running machine: every session gets a fresh
  machine built from it, so suites never inherit each other's guest
  state. What the repository cannot carry — a proprietary boot
  image — stays the developer's to supply, and the declaration says
  where it goes.

- **U5 — A whole test tree in parallel.** A project with several
  guest suites should not pay for them serially. Running under
  pytest-xdist, different suites boot their guests concurrently on
  different workers while each suite's own items stay together on
  one worker, so the whole-suite batching survives. Safety comes
  from isolation rather than from locking: every run has its own
  home and its own image, so no two workers share mutable guest
  state. That is the isolation testaferro can claim, and the limit is
  worth naming — a distinct backend process and port per machine is
  reliquary's guarantee, relied on here rather than re-checked (P1).

- **U6 — A different guest test framework.** The guest unit-test
  framework is testaferro's pluggable aspect. A developer whose
  guest suite is not CppUTest supplies an adapter — argv builders
  and an output grammar, and nothing else — and everything above it
  is unchanged: the same machine selection, the same batching, the
  same pytest items. The adapter knows nothing about how the output
  was obtained, which is also why it is usable on its own, against
  output the caller captured some other way.

- **U7 — Harness support prepped in the guest.** A tester's suite
  will not pass on a bare booted OS: a TSR has to be resident first,
  and loading it twice is not idempotent, so it cannot simply run as
  a setup test — the harness needs preparing before the framework
  ever takes over. The tester declares that prep once, beside the
  suite, and gets a suite that never runs unprepared: every guest
  session it boots, a test session or an enumeration boot alike,
  arrives with the TSR already resident, no manual step and nothing
  to redo per test. A suite that declares no prep runs exactly as
  before.

  1. **Name the companion files.**
     `testaferro.guest_suite(SUITE, files=["DRIVER.COM"])` — host
     paths staged onto the work drive beside the suite, before boot,
     landing where the suite itself already resolves: a setup
     command below names one bare, no path and no letter.
  2. **Name the setup commands.** Add `setup=["DRIVER.COM /install"]`
     to the same call — commands run in the guest, in the order
     given, after the readiness wait and before anything else, once
     per **guest session** rather than once per suite, so an
     enumeration boot runs them too.
  3. **Run the suite.** `pytest` — unchanged from U1 or U2. Each
     guest session now stages the files and runs setup before the
     framework adapter takes over; a setup command that fails ends
     that session and is reported once, naming the command and the
     screen it produced, rather than once per test the missing TSR
     would otherwise have doomed.

  A device driver that must be present before the guest OS itself
  finishes booting is a different need — no post-boot step can
  supply it — met by a custom boot image (U3) or a persistent
  provisioned machine (U8), not by this journey. *(Requires F9.)*

- **U8 — A persistent machine, up for many tests, never silently
  destroyed.** A provisioned machine is expensive and its disk
  state is the point, so the tester opts a machine out of the
  sweep. The cycle is the pytest session: the machine boots when
  the first suite needs it, serves every test that names it while
  up, and shuts down when the session ends — but shutting down is
  not destroying, and the next session boots the same disks with
  the harness still in place. Destroying is explicit — a lifecycle
  verb (F2), never a side effect of a test run. This is a stated
  exception to U3's fresh-machine rule, and it is the tester's
  trade, made by name: state carries across suites and cycles
  because carrying it is what was asked for, and what persists,
  where, is enumerable and removable (P5). *(Unbuilt: F2.)*

- **U9 — A standard environment, by name.** Between nothing and a
  declaration sits a name: `machine="freedos"` selects a standard
  environment testaferro itself curates — an authored machine
  document and a once-downloaded cached image, today's
  zero-configuration machine made plural and nameable as guests
  grow. Resolution runs project declarations first, then the
  standard catalog (D10), and never the user's reliquary home
  (D6): a test run depends only on state testaferro authored or
  the project checked in. *(Resolution and the catalog are built:
  `machine="freedos"` names the standard DOS environment. Plural
  is what waits — a second entry arrives with a second guest.)*

- **U10 — A scripted guest interaction, not shaped as a suite.** A
  guest-driven test is sometimes a linear script rather than a suite
  of named cases — boot the guest, run one setup step, drive an
  interactive tool, check what it printed — with no natural
  `Group.Name` decomposition and no guest-side self-reporting grammar
  for a framework adapter to parse. The developer wants the same
  zero-configuration guest testaferro already gives U1 and U2 — a
  cached image, a disposable per-session overlay, host files staged
  in — without inventing a suite shape, or a framework adapter, for
  output that was never going to exist. They get a live guest handle
  from ordinary pytest code and drive it directly, one command at a
  time, reading each answer back on the host. *(Unbuilt: F18.)*
