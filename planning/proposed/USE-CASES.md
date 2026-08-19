<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# Proposed use cases

> **Status:** drafted, not pledged. **Nothing is worked from here.**
> These are the use cases as reconstructed from the project's own
> prose — [README.md](../../README.md), [AGENTS.md](../../AGENTS.md)
> and the retired `ROADMAP.md` — when Testaferro adopted the planning
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
numbering here is where one went. U4 was pledged by D13, waited on
the pledged shelf for a guest to run its journey, and is now in force
at [root `USE-CASES.md`](../../USE-CASES.md) — the whole route, in
the order the machinery intends. U7 is pledged now too, alongside its
prerequisite F9, and waits in
[pledged/USE-CASES.md](../pledged/USE-CASES.md).

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
  back is Testaferro's business; the developer names an executable.

- **U2 — Nothing to configure.** The first run costs one line. A
  developer points the facade at a freshly built suite executable
  and gets tests: Testaferro classifies the binary, boots a DOS
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
  state. That is the isolation Testaferro can claim, and the limit is
  worth naming — a distinct backend process and port per machine is
  reliquary's guarantee, relied on here rather than re-checked (P1).

- **U6 — A different guest test framework.** The guest unit-test
  framework is Testaferro's pluggable aspect. A developer whose
  guest suite is not CppUTest supplies an adapter — argv builders
  and an output grammar, and nothing else — and everything above it
  is unchanged: the same machine selection, the same batching, the
  same pytest items. The adapter knows nothing about how the output
  was obtained, which is also why it is usable on its own, against
  output the caller captured some other way.

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
  environment Testaferro itself curates — an authored machine
  document and a once-downloaded cached image, today's
  zero-configuration machine made plural and nameable as guests
  grow. Resolution runs project declarations first, then the
  standard catalog (D10), and never the user's reliquary home
  (D6): a test run depends only on state Testaferro authored or
  the project checked in. *(Resolution and the catalog are built:
  `machine="freedos"` names the standard DOS environment. Plural
  is what waits — a second entry arrives with a second guest.)*

- **U10 — A scripted guest interaction, not shaped as a suite.** A
  guest-driven test is sometimes a linear script rather than a suite
  of named cases — boot the guest, run one setup step, drive an
  interactive tool, check what it printed — with no natural
  `Group.Name` decomposition and no guest-side self-reporting grammar
  for a framework adapter to parse. The developer wants the same
  zero-configuration guest `guest_suite()` already gives U1 and U2 — a
  cached image, a disposable per-session overlay, host files staged
  in — without inventing a suite shape, or a framework adapter, for
  output that was never going to exist.

  1. **Open a guest session.** `with testaferro.guest_session() as
     guest:` — no configuration needed for the default machine, same
     as U2: the cached FreeDOS image, downloaded once and reused,
     boots inside a fresh disposable overlay that this session alone
     writes to.
  2. **Stage what the script needs.** `files=["DRIVER.COM"]` on the
     same call — host paths staged onto the work drive before boot,
     the identical placement vocabulary `guest_suite()` takes (U1).
     `environment=` and `machine_config=` reach the same declared or
     standard machine a suite would (U3, U9), for a script that needs
     more than the default.
  3. **Drive the guest, one command at a time.**
     `guest.exec(command, timeout=None)` — ordinary Python, called as
     many times as the script needs, each answer read back on the
     host as it returns, in the order the test itself decides rather
     than a suite's enumeration. Nothing to enumerate, nothing for a
     framework adapter to parse.
  4. **Leave the guest behind.** The `with` block's exit sweeps the
     session's overlay — the same per-session teardown a suite gets,
     whether the script's own assertions passed or one of them
     raised.

  `guest_suite()` remains the right tool for anything shaped as a
  suite of named tests; this journey is purely additive beside it,
  reaching for the same provisioning through a lower-level door
  rather than a second implementation of it. Driving the guest
  interactively — reacting to what is on screen rather than just
  running one command and reading its result, the way
  `reliquary.Session` itself can — is not what this journey commits
  to: the minimal shape is `exec()` alone, and widening it waits for
  a script that actually needs it. *(Unbuilt: F18.)*
