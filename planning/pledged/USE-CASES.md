<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
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

U7 cites F9, and both are pledged in this same commit — the map's
rule against a pledged item resting on a proposed one
([../README.md](../README.md)) is met by pledging the prerequisite
rather than by severing the reference. Neither arms alone: F9's
delivery is what U7 waits on.

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
  a script that actually needs it. *(Requires F18.)*

U10 cites F18 the same way U7 cites F9, so both are pledged together
here too: an internal refactor with no provider gate to clear, but
still work neither use case arms without.
