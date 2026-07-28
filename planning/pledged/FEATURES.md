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

## F7 — The backend-resolution seam

Serves **U4** (pledged), **U9** (drafted) — and every entry point
equally. Extracted from retired F1, whose first work item it was:
`facade._dispatched_backend()` — config search, platform validation,
format classification, machine selection (project declarations first,
then the standard catalog, D10), binding import, option validation —
moves into the core as the single place where "an executable plus
options" becomes a `Backend`. The facade and the plugin (F8) both
call it. Extracting it is real work because today it is fused to the
pytest entry point: it takes `search_from`, which `guest_suite()`
computes from the caller's stack frame.

## F8 — The pytest collection plugin

Serves **U4** (pledged), **U1** (drafted). The command-line surface
(D9): a `pytest11` plugin whose `pytest_collect_file` claims suite
executables, so `pytest tests/suite.exe` is a standard pytest
execution and a tree scan collects guest suites beside host tests.
The reference standard is **pytest-cpp** (MIT) for the pytest-facing
half — mask-gated scans, always-claim for files named on the command
line, framework facades, per-test filter argv; where it probes
binaries by running them, testaferro declares or defaults, because
probing here means booting a guest.

Settled design:

- **Claiming policy.** A file named on the command line is always
  claimed when classification or a declaration says a guest runs
  it; tree scans claim only what masks or `testaferro.ini` opt in;
  a host-runnable format (a plain PE) is claimed only by explicit
  declaration — inference cannot know the nature of the situation
  demands a VM — and headerless `.com` images are never claimed
  from a scan.
- **Items live under the executable's node** —
  `tests/suite.exe::Group-Name` — extending the fifth interface's
  id contract; the dash rule holds. The failure representation
  carries the guest's file, line and assertion; item location may
  point at guest source when it can be resolved, and never
  pretends to when it cannot.
- **Enumeration prefers the host-built twin** (`enumerator=`, in
  its three spellings); in-guest enumeration is the fallback, and
  a possibly-truncated result is named as such, never passed off
  as complete (U4). Collection must be deterministic across xdist
  workers (U5) — collection-time guest boots multiply by worker
  count, which is the twin's whole case.
- **Options and keys follow P16**: the plugin adds pytest options
  and ini keys as kebab-case spellings of the declaration
  vocabulary, exploration-only options included (preserve the run
  home; enumerate-and-stop is pytest's own `--collect-only`).
- **The plugin auto-loads**, through a `pytest11` entry point, so
  `pytest tests/suite.exe` works the moment the distribution is
  installed — pytest's own command with no wrapper and no flag in
  front of it, which is what U4 promises and what the `pytest-`
  distribution category means (D12). What makes
  installation-is-activation safe is the claiming policy above
  rather than the plugin being off: landing in a venv changes no
  existing run, because a tree scan claims nothing that a mask or
  `testaferro.ini` has opted in. Settled at the pledge, D13.
