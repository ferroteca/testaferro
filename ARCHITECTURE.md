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

- **P10 — testaferro's own unit tier never starts a guest.** This
  one is about *this repository's* tests of itself, and not about a
  consumer's tests of their suite — whose whole business is starting
  a guest, and which this project exists to make possible. The tier
  split is by **cost**, not by coverage. testaferro's unit tests may
  use the provider freely and should — `create_machine()` is cheap
  and self-contained, and running it for real is the best coverage
  available on this side of the line — but `start_machine()`, `stop_machine()` and `exec()`
  belong to integration, because they start something real and leave
  a process behind. The cheap half is conditional on the
  **blueprint** rather than on the call: a drive materializing a
  blank sends the provider out to an external image tool, so a
  machine declaring one belongs to integration too. **Naming that
  tool is not this principle's business** — what a provider reaches
  for underneath is the provider's own (P2), and what testaferro can
  see is only that the call stopped being cheap.

  **The tier those calls belong to does not exist yet** (F6), and
  this entry does not pretend otherwise: it forbids them on this side
  of the line and promises no home on the other. That is why its
  absence is not residue against this principle — nothing here claims
  an integration suite, only that certain calls are not the unit
  tier's to make. *[Amended before arming: this read
  "never launch a hypervisor", and named the tool. Both spoke a layer
  below the provider, which P1 and P2 put out of testaferro's
  vocabulary. The boundary is unchanged and one step wider on
  purpose: a provider that runs a program without booting a machine
  starts a guest all the same, and testaferro's unit tests may
  not.]*

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
