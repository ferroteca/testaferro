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
  defining tests. **Arms with F8**; until the plugin exists this
  principle has no subject.

P16 is three surfaces over two interfaces: the embedding API and
`testaferro.ini` are two spellings of one declaration
([../INTERFACES.md](../INTERFACES.md)), and the plugin's options are
a second presentation of them rather than a surface of their own.
That is also why it is pledged rather than severed the way U4 was —
nothing in the code stands behind it yet, and F8's option design
cites it (D13).
