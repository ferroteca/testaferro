<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# Use cases

> **Status: in force.** Every use case below is met by the code as it
> stands today, **in full** — that is the whole content of one being
> here rather than on the pledged shelf (`planning/pledged/`, owed but
> not yet delivered). A
> journey that no longer works is a bug, to be reported and fixed, and
> not unbuilt work to be scheduled. A use case reaches this file only
> on complete delivery, and partial delivery leaves it below the line.
>
> Numbering comes from one global U-sequence, never reused, and an
> entry keeps its number all the way here. A gap in the numbering is a
> use case still argued or still owed, not a missing one.

**This file exists at last.** Testaferro adopted its planning model
after the code was written (D7), so its whole vision began drafted;
for months the honest answer to "what does Testaferro promise *a
user*?" was *no journey yet stated*, because no guest had run since
the migration to the blueprint model (D4) and a use case arms on
delivery rather than on intent. A guest has now run — it boots,
takes a suite, enumerates it, runs it, and reports a failure with the
guest's own file and line — and this is what that bought.

The **architectural principles** are the other half of the decision
surface and carry equal weight; they are at
[ARCHITECTURE.md](ARCHITECTURE.md), and most of them arrived here
first. The two halves arm on different events by design: a principle
moves when the code honors it as a rule, a use case only when a
journey works end to end.

## The use cases

- **U4 — Try a suite against a guest before embedding anything.** A
  developer has just built a DOS test executable and wants to watch
  it run before writing a line into their project. The command is
  pytest's own, and it is explicit: `pytest tests/suite.exe`. The
  installed plugin claims the executable named on the command line
  and boots the standard environment, and everything else *is* pytest —
  the items, the ids, `-k`, `-x`, `--lf`, `--collect-only` — with
  no wrapper to diverge from the real thing, because the trial is a
  standard command-line pytest execution (D9). It honors the same
  declarations embedding would — a `testaferro.ini` beside the
  project selects the same test environment (U3) — and zero
  configuration stays the price of the first run (U2). Trying is when things go
  wrong, so the trial does not fail blind: a suite that boots
  nothing, or whose output no framework adapter recognizes, is
  reported by what the guest actually showed, never by a traceback
  into the facade, and a plugin option preserves the guest home for
  inspection. Nor does it lie by omission: enumerating inside the
  guest can lose the head of a long list, so a trial never silently
  shows fewer tests than exist — an enumeration that may have been
  truncated says so, and a host-built enumerator is the faithful
  path. What they typed to try it is what they keep: embedding is
  the same executable collected from the tree, or a `guest_suite()`
  call when programmatic control is wanted, and the trial command
  stays valid forever — the step before U1 and the same surface as
  U1, so adopting Testaferro does not start with a leap of faith.

**U4 cites U1, U2 and U3, which remain drafted**, and that is a
citation rather than a dependency. The map's rule against leaning on a
proposal tests **completion**, and every clause U4 leans on names
behaviour a guest has now actually performed (D13). The drafts also
still say *machine* where D18 made the noun an *environment*; nothing
below this file is a claim about the code, so the mismatch costs a
reader a moment and this entry nothing.

**It armed alone, which D13 did not expect.** That entry judged U4
would "most likely arm alongside" U1, U2 and U3, on the reasoning
that one end-to-end proof would arm all four. The proof arrived and
armed one, because arming is per journey and not per boot: U4's
journey is the *trial*, and it is the only one whose every clause has
something asserting it. U1's embedding path, U2's first run and U3's
declared environments are exercised by that proof in passing, which is
not the same as being met in full — and the difference is exactly what
this file is for.

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
  provisioned machine (U8), not by this journey.

**U7 cites U3 and U8, both still drafted**, for the boot-level need
this journey deliberately does not cover. That is a citation rather
than a dependency, exactly as U4's citations of U1–U3 were: the map's
rule against leaning on a proposal tests completion, and no clause
above leans on U3 or U8 for anything this journey itself claims — they
are named only to say what a different journey answers. Declaring
`setup=` and running `pytest` are both proven against a real guest
boot: a command written to the work drive by a `setup=` entry is read
back before any test runs, and a `setup=` command that signals failure
— a real DOS program's own nonzero exit, read through
`reliquary.Session.exec(check=True)` — ends the guest session and is
reported once, in the same `GuestOutputError` shape every other guest
exchange fails in, never as a traceback into Testaferro.
