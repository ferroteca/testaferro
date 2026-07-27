<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: BSD-3-Clause
-->

# Proposed use cases

> **Status:** drafted, not accepted. **Nothing is worked from here.**
> These are the use cases as reconstructed from the project's own
> prose — [README.md](../../README.md), [AGENTS.md](../../AGENTS.md)
> and the retired `ROADMAP.md` — when testaferro adopted the planning
> model (D7). They are the decision surface *once accepted*; until
> then a citation of a U-number here names a draft, and should be
> read as weaker than citing an in-force entry. Numbering comes from
> one global U-sequence, never reused, and an entry keeps its number
> when it moves to `accepted/` and again when it reaches root
> `USE-CASES.md`.

**Acceptance and delivery are different events.** An entry moves to
`accepted/` when the direction is agreed, and to root `USE-CASES.md`
only when the code meets it in full. Several entries below already
describe working code, which makes their route short but not
automatic: root is an implementation claim, and this project cannot
currently make it. There is no integration suite, so no guest has run
since the migration to the blueprint model (D4) — U1, U2, U3 and U5
are implemented but **unproven**, and end-to-end proof is owed before
any of them is armed.

Reconstructed drafts, so read them for accuracy first: these are the
owner's use cases put into words by an agent, not dictated by him.
Reshape freely — a proposed use case may be changed in nature at
will; only an in-force one may not.

- **U1 — Unit tests that can only run on the target OS, surfaced as
  ordinary pytest items.** A developer maintains code whose unit
  tests cannot run in the work environment at all: the suite is a
  DOS build, and a DOS build only runs on DOS. They want those tests
  in their own pytest tree, behaving like every other test there —
  `pytest` runs them, `-k` and node ids narrow them, a failure
  reports the *guest* side's file, line and assertion message rather
  than a traceback into the facade, and an IDE's run-this-test and
  jump-to-source resolve to the developer's own module. What it
  takes to boot a machine, get the executable into it, run it and
  read the results back is testaferro's business; the developer
  names an executable.

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

- **U4 — Try a suite against a guest before embedding anything.** A
  developer has just built a DOS test executable and wants to watch
  it run before writing a line into their project: one command
  naming the executable, and pytest's own output. What they typed to
  try it is what they write when they embed it — the command line and
  the call site are one surface, and the tool can print the test
  module to paste in. This is the step before U1, and it exists so
  that adopting testaferro does not start with a leap of faith.
  *(Unbuilt: F1.)*

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
