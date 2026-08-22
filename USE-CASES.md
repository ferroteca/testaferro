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

Proven by the command the README advises, run for real: a project
holding two suites under `pytest -n 2 --dist loadfile`, every worker
collecting — and so every worker booting its own enumeration guest —
each suite landing whole on one worker and booting one execution
guest there, the two suites on different workers at the same time,
and both reporting their deliberate failure normally. The worker
tags xdist puts on every item are the evidence, not a clock. One
thing the proof could not reach, because this machine had long since
built its system disk, was found by reading instead: on a machine
that never had, two workers find it missing at the same moment and
both install it — which isolation permits, at the cost of a second
install — but they used to stage into one shared partial file, and
the second's atomic move took the first's out from under it. Each
build now stages into a partial of its own. F22 delivered this,
cut from F15 to this one journey, and retired with it.

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

**U7 cites U3, still drafted, and U8, in force below**, for the
boot-level need this journey deliberately does not cover. That is a
citation rather than a dependency, exactly as U4's citations of U1–U3
were: the map's rule against leaning on a proposal tests completion,
and no clause above leans on U3 or U8 for anything this journey itself
claims — they are named only to say what a different journey answers. Declaring
`setup=` and running `pytest` are both proven against a real guest
boot: a command written to the work drive by a `setup=` entry is read
back before any test runs, and a `setup=` command that signals failure
— a real DOS program's own nonzero exit, read through
`reliquary.Session.exec(check=True)` — ends the guest session and is
reported once, in the same `GuestOutputError` shape every other guest
exchange fails in, never as a traceback into Testaferro.

- **U8 — A persistent machine, kept for many tests, never silently
  destroyed.** A provisioned machine is expensive and its disk
  state is the point, so the tester opts a machine out of the
  sweep. The cycle is the pytest session: the machine boots when
  the first suite needs it, serves every test that names it — one
  guest session at a time, rebooting the same disks between the
  suites that name it rather than staying up across them, because a
  suite reaches the guest on a work drive read once at boot — and
  shuts down when the session ends. But shutting down is not
  destroying, and the next session boots the same disks with the
  harness still in place. Destroying is explicit — a lifecycle verb,
  never a side effect of a test run. This is a stated exception to
  U3's fresh-machine rule, and it is the tester's trade, made by
  name: state carries across suites and cycles because carrying it
  is what was asked for, and what persists, where, is enumerable and
  removable (P5).

**U8 cites U3, still drafted**, only to name the rule it is an
exception to; no clause above leans on U3 being met. Its clause on
serving suites was amended at arming (D31): as drafted it read "while
up", and what F2 built reboots the kept machine between suites, for
the reason the clause now states — a second suite's staged set can
reach the guest only by a boot. The owner accepted the reboot rather
than owing pre-boot staging of every suite's set, which is a seam
change nobody has asked for. Every clause is proven against real
boots (D30): `persist=<name>` keeps the machine under
`machines/<name>`, a file written to `C:` in one guest session is
read back in the next, a suite runs on the kept machine, a machine a
run died with up is refused by name and freed by `testaferro
shutdown`, `testaferro list` enumerates what is kept and where, and
only `testaferro destroy` removes it.

- **U9 — A standard environment, by name.** Between nothing and a
  declaration sits a name: `environment="freedos"` selects a standard
  environment Testaferro itself curates — an authored machine
  document and a once-downloaded cached image, today's
  zero-configuration machine made nameable. Resolution runs project
  declarations first, then the standard catalog (D10), and never the
  user's reliquary home (D6): a test run depends only on state
  Testaferro authored or the project checked in.

  **Severed from its own plural growth** (D25): a second named
  environment waits on a second guest platform (F5), which waits
  entirely on reliquary (D2) and is neither owed nor delivered here.
  This journey covers the singular case alone — one name, resolving
  as documented — and stays true whether or not Testaferro ever grows
  a second guest.

`environment="freedos"` is proven against a real guest boot, through
the seam every entry point shares
(`resolution.resolve_backend()`/`resolve_guest_session()`): the name
resolves against the standard catalog rather than only through the
zero-configuration default's own inference reaching the same disk
unnamed, and both `guest_suite()` and `guest_session()` name it and
boot for real, the way every other proven journey here was proven.

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
  a script that actually needs it.

**U10 cites U1 and U3, still drafted, for the same reason U7's
citation of U3 stayed drafted**: the map's rule against
leaning on a proposal tests completion, and no clause above leans on
U1 or U3 for anything this journey itself claims — they are named
only to say `guest_session()` takes the same placement vocabulary
`guest_suite()` does, not to lean on those journeys being met. Its
third citation, U9, no longer carries that caveat: U9 armed above, so
`environment=` and `machine_config=` reaching the same declared or
standard environment a suite would is a claim about working code now,
not a citation of a proposal. `guest_session()` and `exec()` are both
proven against a real guest boot: `files=` stages host paths onto
the work drive before boot exactly as `guest_suite()` does, `guest.exec()`
runs a command in the guest and reads its answer back — the rows
`reliquary.Session.exec()` itself returns, never reshaped for a
framework adapter that was never going to see them — and the `with`
block's exit sweeps the guest session whether the script's own
assertions passed or one of them raised, proven by deliberately
raising inside one.
