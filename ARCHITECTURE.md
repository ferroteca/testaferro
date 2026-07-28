<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: BSD-3-Clause
-->

# Architecture

> **Status: in force.** Every principle below is honored by the code
> as it stands today — that is the whole content of a principle being
> here rather than in [planning/pledged/](planning/pledged/).
> **A divergence from any of them is a bug**, to be reported and
> fixed, and not unbuilt work to be scheduled. That is the difference
> arming makes, and it is why a principle reaches this file only when
> every known residue has been closed or filed as a defect in the same
> change.
>
> Numbering comes from one global P-sequence, never reused, and an
> entry keeps its number all the way here. A gap in the numbering is a
> principle still argued or still owed, not a missing one.

**This file holds principles.** The whole-system view and the
interface enumeration stay in
[planning/proposed/ARCHITECTURE.md](planning/proposed/ARCHITECTURE.md),
deliberately and for two different reasons. The view describes a
system whose consumer vocabulary is pledged but unbuilt (P1, P2, D18),
so it is not yet a claim about the code; and the enumeration is what
the interface-change rule looks up to answer "does this change an
interface?", which keeps working best from one unmoving place. Each
follows when it can be asserted on its own terms.

The **use cases** are the other half of the decision surface and carry
equal weight. None is in force yet: root `USE-CASES.md` does not
exist, because a use case arms on *full delivery* and no guest has run
since the migration to the blueprint model. What testaferro promises a
user is therefore still nothing yet stated; what it promises a
*maintainer* starts here.

## The principles

- **P16 — One vocabulary, three spellings.** Every consumer-facing
  option is one vocabulary spelled three ways: a `guest_suite()`
  keyword, a `testaferro.ini` key, and the plugin's option on
  pytest's own command line — kebab-case there, underscores in
  Python and INI. What you typed to try a suite is what you keep
  when you embed it, because the trial and the embedded run are the
  same execution (D9). A keyword inexpressible in the other
  spellings is a keyword worth questioning. Exploration-only
  options — preserving a guest home, enumeration overrides — are the
  named exception, concerning trying a suite out rather than
  defining tests.

  **A consumer-facing option is testaferro's own vocabulary, not what
  passes through it.** `memory` and `drives` are the provider's words
  in an authored document (P2, P3) — carried untouched, never
  interpreted — so their having no `--testaferro-memory` is the
  boundary working rather than a shortfall. The keywords this binds
  are the ones testaferro itself defines: `machine`, `platform`,
  `machine_config`, `boot_image`, `suites`, `timeout`. `template` is
  an alias of `machine_config` rather than a keyword of its own.

  **`framework` is the honest limit, not a gap.** It takes a Python
  module — argv builders and an output grammar — and no command line
  or ini file can carry one, so the vocabulary ends where objects
  begin. `enumerator` sits under the exploration exception, which is
  why its command-line form names a host-built twin by path while its
  embedding form takes a callable.

  P16 is three surfaces over two interfaces: the embedding API and
  `testaferro.ini` are two spellings of one declaration
  ([planning/INTERFACES.md](planning/INTERFACES.md)), and the
  plugin's options are a second presentation of them rather than a
  surface of their own. In the code, the two spellings are declared
  from one list in `testaferro/plugin.py` so they cannot drift; a
  keyword added to one and not the others is the bug this principle
  names.
