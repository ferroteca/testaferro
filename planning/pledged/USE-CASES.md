<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: BSD-3-Clause
-->

# Pledged use cases

> **Status:** pledged — owed by the project, and not yet delivered.
> The project has undertaken these and says nothing about when. An
> entry leaves for root `USE-CASES.md` only when the code meets it
> **in full**, so this file is the gap between the pledge and the
> delivery made visible. Numbering comes from one global U-sequence,
> never reused, and an entry keeps its number every time it moves.

**Nothing here is a draft any more.** Citing a U-number in this file
names an undertaking — stronger than citing
[../proposed/USE-CASES.md](../proposed/USE-CASES.md), weaker than
citing the root list: the project owes it, and does not yet claim the
code meets it.

- **U4 — Try a suite against a guest before embedding anything.** A
  developer has just built a DOS test executable and wants to watch
  it run before writing a line into their project. The command is
  pytest's own, and it is explicit: `pytest tests/suite.exe`. The
  installed plugin claims the executable named on the command line
  and boots the standard machine, and everything else *is* pytest —
  the items, the ids, `-k`, `-x`, `--lf`, `--collect-only` — with
  no wrapper to diverge from the real thing, because the trial is a
  standard command-line pytest execution (D9). It honors the same
  declarations embedding would — a `testaferro.ini` beside the
  project selects the same machine (U3) — and zero configuration
  stays the price of the first run (U2). Trying is when things go
  wrong, so the trial does not fail blind: a suite that boots
  nothing, or whose output no framework adapter recognizes, is
  reported by what the guest actually showed, never by a traceback
  into the facade, and a plugin option preserves the run home for
  inspection. Nor does it lie by omission: enumerating inside the
  guest can lose the head of a long list, so a trial never silently
  shows fewer tests than exist — an enumeration that may have been
  truncated says so, and a host-built enumerator is the faithful
  path. What they typed to try it is what they keep: embedding is
  the same executable collected from the tree, or a `guest_suite()`
  call when programmatic control is wanted, and the trial command
  stays valid forever — the step before U1 and the same surface as
  U1, so adopting testaferro does not start with a leap of faith.
  *(Built: the plugin claims suite executables and auto-loads, and
  the trial command is pytest's own. Arming waits on end-to-end
  proof, the same proof U1, U2 and U3 wait on — F6.)*

U4 cites U1, U2 and U3, which remain drafted. That is not the
reference flaw the map names: the rule's test is **completion**, and
every clause U4 leans on names behaviour the code ships today rather
than a verdict the project has yet to reach (D13).
