<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: BSD-3-Clause
-->

# Pledged architecture

> **Status:** pledged — owed by the project, and not yet honored as a
> rule. A principle leaves for root `ARCHITECTURE.md` when the code
> honors it as a rule, every known residue filed as a defect in the
> same change; until then it waits here, undertaken and unarmed.
> Numbering comes from one global P-sequence, never reused, and an
> entry keeps its number every time it moves.

**The whole-system view and the interface enumeration are not here.**
They stay in
[../proposed/ARCHITECTURE.md](../proposed/ARCHITECTURE.md), which is
where the vetting rule ([../INTERFACES.md](../INTERFACES.md)) looks
the interfaces up. This file holds pledged principles alone, and a
principle here is an undertaking rather than a claim about the code.

**P1 and P2 are pledged severed** (D18), on the reading D13 used for
U4: the rule against leaning on a proposal tests **completion**, not
citation, and every drafted entry they cite — P3, P8, P17, U9 —
names behaviour the code ships today. U7 is cited only to illustrate
how deep a provider document may go, which blueprint pass-through
already allows.

- **P1 — The execution provider is a declared choice, and
  reliquary is the only supported one.** A **provider** is whatever
  actually runs a guest suite — reliquary today, with vagrant,
  dosbox and wine the shape of the others. They occupy one layer —
  a test environment uses one *or* another, and the environment
  names which (D11); testaferro passes that provider's own
  configuration through untouched (P3). *[Amended from
  "guest-machine provider" and pledged by D18: not every provider
  boots a machine — wine and dosbox run a program without one — so
  the layer is named for what it does, which is also why a suite
  names an environment rather than a machine (P2).]* The axis is
  testaferro's own: a future provider is a new binding here, never
  capability pushed upstream. What D1 refused stays refused — no
  structural runner contract, no conformance kit, no mirrored
  configuration hierarchy, and no abstraction built ahead of a
  second concrete provider; a prebuilt `Backend` remains the escape
  hatch, and the seam a provider implements. **The split governs
  verification as much as implementation**: a property of the guest
  machine is the provider's to guarantee and to test, so doubting
  one produces an upstream bug report — never a local audit of its
  internals, and never a defensive workaround here. (D1, D11, D18.)

- **P2 — Suites name test environments.** A **test environment** is
  what a suite runs in, and naming one is the whole of what a
  suite-facing consumer writes: a **standard** environment
  testaferro authors and names (U9, D10, P17), or a **custom** one
  the tester declares. The environment is the one place a provider
  is named (P1, D11).

  **How deep a custom environment goes is the tester's to choose,
  and it goes as deep as the provider does.** A name and nothing
  else, or a complete provider document — a reliquary blueprint
  with its drives, its provisioning scripts, its
  `backend-settings` — carried through untouched for the provider
  to validate (P3, D4, U7). Precision is never rationed here, and a
  tester who needs the provider's most specific knob reaches it by
  writing the provider's own document.

  What testaferro declines is not depth but **vocabulary**: it
  names providers and never what a provider drives underneath. It
  asks no consumer for an emulator, keys no table by one, and
  interprets no field below the provider's own — `platform`
  included, which is a blueprint field passing through (P3) rather
  than a word testaferro speaks. A `backend-settings` block naming
  QEMU is the tester configuring *reliquary*, and testaferro
  carries it without opinion or comprehension.

  Inference must still pick something when a tester declares
  nothing, so the executable's own format selects a standard
  environment (P8) — testaferro reading a binary, not a vocabulary
  the consumer writes in. *[Amended twice before being pledged by
  D18. First: this made **platform** and **machine** the consumer's
  pair, per D3, which D18 retires. Then "and nothing underneath
  one" was struck, having read as a limit on what a tester may
  configure when it was only ever about what testaferro says.]*

- **P16 — One vocabulary, three spellings.** Every consumer-facing
  option is one vocabulary spelled three ways: a `guest_suite()`
  keyword, a `testaferro.ini` key, and the plugin's option on
  pytest's own command line — kebab-case there, underscores in
  Python and INI. What you typed to try a suite is what you keep
  when you embed it, because the trial and the embedded run are the
  same execution (D9). A keyword inexpressible in the other
  spellings is a keyword worth questioning. Exploration-only
  options — preserving a run home, enumeration overrides — are the
  named exception, concerning trying a suite out rather than
  defining tests. **The subject now exists**: the plugin ships, its
  options and ini keys are declared from one list so the two
  spellings cannot drift, and `--testaferro-keep-guest-home` and the
  enumerator are the named exception in the flesh. What stands
  between that and the root list is stated below.

P16 is three surfaces over two interfaces: the embedding API and
`testaferro.ini` are two spellings of one declaration
([../INTERFACES.md](../INTERFACES.md)), and the plugin's options are
a second presentation of them rather than a surface of their own.
That is also why it was pledged rather than severed the way U4 was:
when it was written nothing in the code stood behind it, and the
plugin's option design cited it (D13).

**What counts as a consumer-facing option**, since the principle is
unassertable without saying: testaferro's own vocabulary, and not
what passes through it. `memory` and `drives` are the provider's
words in an authored document (P2, P3) — carried untouched, never
interpreted — so their having no `--testaferro-memory` is not a
shortfall but the boundary working. The keywords P16 binds are the
ones testaferro itself defines: `machine`, `platform`,
`machine_config`, `boot_image`, `suites`, `timeout`. `template` is
an alias of `machine_config` rather than a keyword of its own.

**`framework` is the honest limit, not a gap.** It takes a Python
module — argv builders and an output grammar — and no command line
or ini file can carry one. A keyword inexpressible in the other
spellings is worth questioning, and this one has been: what it names
is an object, so the answer is that the vocabulary ends where
objects begin rather than that a spelling is missing. `enumerator`
sits under the exploration exception already named above, which is
why its command-line form may name a host-built twin by path while
the embedding form takes a callable.

**The residue is closed.** `timeout` and `suites` had no
command-line spelling when this was pledged; both have one now, and
the binding accepts a timeout so the option has somewhere to land.
Every keyword the paragraph above binds is spelled all three ways,
so what stands between this and root `ARCHITECTURE.md` is the act
rather than the work.
