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

**Arming it is an open call, and there is known residue.** A
principle reaches root `ARCHITECTURE.md` on being honored *as a
rule*, with every known residue filed as a defect in the same
change. Two declaration keywords have no plugin spelling today:
`timeout`, which would need the binding to accept one, and
`framework`, which is a Python object and may be the honest limit of
"three spellings" rather than a gap — deciding which is part of
arming. Until that call is made this stays pledged vision, and a
shortfall stays unbuilt work rather than a bug.
