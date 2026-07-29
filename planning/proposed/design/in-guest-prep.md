<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: BSD-3-Clause
-->

# In-guest prep: the design

Design for **F9**'s per-boot prep level — the testaferro half. The
provider changes the level rests on are argued separately, as a
downstream proposal to reliquary:
[reliquary-proposal.md](reliquary-proposal.md). The split follows
the division of labor, not the size of the parts. This design was
itself shaped by consumer-side input, from the class of consumer
that tests DOS device drivers; consumers are referred to only
generally (P12).

## What the level needs, and from whom

A driver-testing suite needs three things a bare booted guest does
not have:

1. **Companion files** beside the suite — the driver TSRs the suite
   exercises.
2. **Setup commands** run before any test — the TSRs must be
   resident first, and loading one twice is not idempotent.
3. **A machine that exposes the device** the driver drives — a
   hardware fact of the machine, without which the test is not a
   weaker test but a different one.

The first is testaferro's alone. The second is testaferro's
surface over a provider capability that does not exist yet. The
third is not testaferro's at all: it is a machine fact, declared in
the environment and passed through untouched (D4), waiting only on
reliquary having a word for it — the second ask of the
[downstream proposal](reliquary-proposal.md). That division is this
document's spine.

## `files=` and `setup=`

Two declarations, keyword and INI twins (P16), both testaferro's
own words beside the machine spec — like `provider`, `timeout` and
`suites`, they never reach the blueprint.

- **`files=`** — host paths staged onto the work drive beside the
  suite executable, before boot. This extends the one-file staging
  the backend already does, under the same invariant: the backend
  snapshots the host directory when the drive is attached, so
  staging happens before `start_machine()`, never lazily (D5).
  Landing on the work drive is what makes the letter problem not
  exist: setup commands name a staged file bare, no path, no
  letter, and the existing letter resolution covers them for free.
  In the INI spelling the value is a JSON list, relative paths
  resolved from the file's directory as `boot_image` already is.

- **`setup=`** — commands run in the guest in the order given,
  once per **guest session** (D15). That means *every* guest
  session, an enumeration boot included: a suite that needs its
  TSR to run needs it to enumerate, and a consumer whose
  enumeration is answered host-side by `enumerator=` simply never
  boots that session. Setup runs after the readiness wait and
  before anything else. Ordering within the list is the caller's;
  a wrong order is a consumer bug testaferro does not try to
  detect.

- **Setup failure is loud, and reported once.** A setup command
  that fails ends the guest session and raises the existing
  `GuestOutputError` shape — the command sent and the screen that
  came back — once, against the session, not once per item. Every
  test failing because a TSR never went resident is a report
  about nothing; one failure naming the setup command is the
  answer.

- **A suite that declares neither runs exactly as today.** No new
  concept reaches a self-contained suite.

## What testaferro declines to own

Declining these is what keeps the feature small, and each decline
lands as a named obligation on the caller — acceptable, because
each is a thing the caller can straightforwardly do right and
testaferro can only do wrong.

- **No pre-boot validation of `setup` against `files`.** The
  tempting check — refuse a setup command whose first token names
  no staged file and no known shell builtin — requires a builtin
  vocabulary testaferro would keep on the shell's behalf, varying
  by DOS flavor and shell version: the kind of mirrored rule
  `_work_drive()` just paid to delete. And the staged-file half
  refuses legitimate commands naming programs on the system disk,
  a tester's boot floppy, or `PATH`. The two lists agreeing is the
  caller's obligation; a typo surfaces as a loud setup failure.

- **No parsing of setup output.** Whether a command succeeded is
  detected by the provider — the [downstream
  proposal](reliquary-proposal.md)'s first ask — never by
  testaferro reading a screen. The obligation this pushes back:
  **a setup program owes an honest exit code.** A TSR can —
  INT 21h AH=31h carries a return code even when staying
  resident — and a driver's install failing silently is a defect
  in the driver on its own terms.

- **No device vocabulary, no engine words.** Which hardware a
  machine exposes is declared in the environment as blueprint
  fields, passing through untouched for the provider to validate
  (D4) — testaferro interprets no field below the provider's own.
  The INI needs no change either: a `devices` list is a
  structured literal, which `testaferro.ini` values already parse.

- **No mid-session file push, no file retrieval, no script
  grammar.** Real scripting belongs to the provider's own
  documents, reached by `machine_config=`.

## What this rests on, and in what order

F9 hard-depends on one provider change alone: `exec()` reporting
whether a command succeeded, the downstream proposal's first ask.
The proposal's other two asks serve the sibling machine fact — the
declared device — which needs no testaferro change at all.

The pin (D4) orders everything: reliquary ships first, testaferro
moves its pin as the deliberate task the pin exists to make
deliberate, and F9's per-boot prep lands against the moved pin.
The `devices` declaration, by contrast, needs no testaferro
release: the day reliquary ships the vocabulary, an environment
declares it and the document passes through (D4). No order beyond
that is promised, here or anywhere.
