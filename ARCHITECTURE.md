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
system whose consumer vocabulary is pledged and only half built (P1,
P2, D18) — a suite names an environment today, and nothing yet names
the provider — so it is not yet a claim about the code; and the
enumeration is what
the interface-change rule looks up to answer "does this change an
interface?", which keeps working best from one unmoving place. Each
follows when it can be asserted on its own terms.

The **use cases** are the other half of the decision surface and carry
equal weight. None is in force yet: root `USE-CASES.md` does not
exist, because a use case arms on *full delivery* and no guest has run
since the migration to the blueprint model. So testaferro still
promises no user a *journey* — what the entries below bind is the
shape of the thing, never a trip through it. Several of them do speak
past the maintainers: P4 tells whoever writes a framework adapter what
one is, P7 and P8 tell whoever runs a suite what will be refused and
what will keep working, P12 tells whoever depends on the library what
it will never learn about them, and P17 tells whoever names a standard
environment whose content they are getting. The rest are about how
this project is built and verified.

## The principles

- **P4 — The guest test framework is testaferro's own axis, and
  CppUTest is the only adapter built.** A **framework adapter** is
  argv builders and an output grammar for one guest unit-test
  framework, and nothing else: `list_argv()`, `run_all_argv()`,
  `run_one_argv(group, name)`, `parse_list()` and `parse_run()` are
  the whole of what one must supply, and `SuiteBackend` calls exactly
  those five. An adapter imports no runner — the shared result types
  and nothing further — and never learns how the output it parses was
  obtained, which is what makes it usable on its own against output
  the caller captured some other way (U6). **Argv crosses that seam
  as a sequence of tokens, never a command line** (D17): only the
  executing side knows whether the program is reached by a DOS
  command line or an argv list, so an adapter that has never seen one
  does not decide how it is quoted.

  **This is the one pluggable aspect that is testaferro's**;
  everything about the guest itself is the provider's (P1). The
  difference reaches verification, and in the opposite direction: a
  property of the guest machine is the provider's to guarantee, so
  doubting one produces an upstream bug report, while an adapter is
  testaferro's own code — a grammar that misreads its framework is a
  bug *here*, answerable to that framework's own source rather than
  to its maintainers (P9).

  **An adapter needs no base class, and gets none.** `Backend` is an
  ABC because its implementations hold state — a booted guest, a home
  directory, a machine handle — so they are objects already, and an
  abstract base costs nothing over them. An adapter holds none: argv
  out, text in, results out. Its natural shape in Python is a module
  of functions, which is what `framework=cpputest` passes, and a base
  class would force it into an object with nothing to construct. The
  five callables above are the contract, stated here rather than in
  an inheritance chain. A **conformance kit** is refused on D1's
  ground rather than on that one: a shared suite validating adapters
  that do not exist yet buys no leverage, and anything of the sort is
  derived from the concrete adapters there are when there are two. So
  a second adapter is a plain module supplying those five callables,
  and the guest binding defaults to CppUTest while keeping
  `framework=` a parameter. That keyword takes a Python module, which
  is why P16 names it the honest limit of "three spellings" rather
  than a keyword missing two — the vocabulary ends where objects
  begin.

  **Where the axis stops short, it says so.** A collection-plugin run
  can reach no adapter but CppUTest, `framework=` having no
  command-line or ini spelling to carry one (P16), so the host-twin
  enumerator in `plugin.py` reads its list with the CppUTest grammar
  named outright. That is not a divergence while nothing else is
  reachable, and it is the first place to look the day something is:
  a second adapter arriving with no way to select it there would make
  the hardcode a bug rather than a consequence.

  *[Amended before arming: this read "the framework adapter is
  independent of the runner", which is one clause of an axis rather
  than the axis itself. The independence is unchanged and restated
  above; what is added is what the axis claims — the surface an
  adapter supplies, which side owns verification, and why that
  surface needs no base class under it.]*

- **P6 — A running machine is stopped before anything is swept.** A
  machine outlives the call that booted it, so every backend holding
  a live guest is tracked and stopped before any directory is
  removed — by `stop()` and by the `atexit` failsafe alike. Sweeping
  first deletes the disk out from under a running guest and leaks the
  process, so any new exit path goes through the same stop.

- **P7 — Fail before the guest boots.** A provably foreign binary —
  the host build of the suite passed by mistake — an ambiguous
  environment selection, or an unusable option is rejected up front,
  naming what was found and what the choices were. Nothing that can
  be known cheaply is discovered by booting a machine and watching it
  fail. Where nothing can be proven — a headerless `.com`-style
  image carries no header to judge — it passes through for the guest
  itself to judge, which is honesty about the limit rather than an
  exception to the rule.

  *[Amended before arming: this said "an ambiguous **machine**
  selection", D3-era vocabulary P2 has since retired. The rule is
  unchanged — what can be ambiguous is which declared *environment*
  runs the executable, which is what `environments.select()` refuses
  and what its message lists.]*

- **P8 — Zero configuration is an entry point, not a demo.** Every
  configuration surface added leaves the no-declaration path working:
  a suite executable and nothing else still runs. (U2.)

  **What arms here is the rule, not a proof of the journey.** That
  each surface leaves the path intact is checked on this side of the
  line — an inferred platform matches declarations only, so the
  catalog is reached by asking for it and never by falling into it —
  while the boot that path ends in waits on the integration tier,
  with U2 (F6, P10). Arming this asserts that the entry point is kept
  open, which is the part a new option can close by accident.

- **P9 — Grammars derive from source, never from samples.** A
  framework adapter's argv builders and output grammars are derived
  from that framework's own source, and its unit fixtures are
  source-derived rather than captured. The cost is stated plainly:
  source-derived fixtures cannot prove a real run, so a grammar
  change warrants a real end-to-end run before it is trusted.

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

- **P11 — The standard library, plus two dependencies at named
  seams.** pytest and reliquary are the whole dependency list; pytest
  is imported lazily in the facade, and reliquary only in the guest
  binding and in `environments.py` for its JSONC reader. Python 3.9 and
  newer. A third dependency is argued, never added.

- **P12 — The library never names its consumers.** No consuming
  project appears in source, tests, human documentation, or
  repository guidance; consumers and runners are referred to in
  general instructional terms. A library that knows who uses it has
  acquired a dependency in the wrong direction.

- **P13 — No backward compatibility before 1.0.** Changes land
  coherently and completely — every affected surface, document,
  example and test moved to the new shape, the old one deleted rather
  than bridged. Cheap execution does not make the decision cheap.

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
  passes through it.** `memory`, `drives` and `platform` are the
  provider's words in an authored document (P2, P3) — carried
  untouched, never interpreted — so their having no
  `--testaferro-memory` is the boundary working rather than a
  shortfall. The keywords this binds are the ones testaferro itself
  defines: `environment`, `machine_config`, `boot_image`, `suites`,
  `timeout`. `template` is an alias of `machine_config` rather than a
  keyword of its own.

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

- **P17 — What testaferro offers, testaferro authors.** Every
  environment testaferro puts a name on — the standard catalog's
  own (U9, D10), and any blueprint, script or medium shipped
  with one — is authored here and complete in itself: the document,
  the drives it declares, and the media those locate. **Nothing
  testaferro offers is a name resolved out of the provider's own
  shipped content**: reliquary's codex is not an input to a test
  run, at resolution or at materialization, and neither is the
  user's reliquary home (D6). This is P5's hermeticity read forward
  from the guest session to the catalog — P5 governs what a run may
  *reach*, this governs what testaferro may *offer* — and the reason
  is the same twice: a test run depends only on state testaferro
  authored or the project checked in, and a curated environment
  leaning on a provider's catalog inherits that catalog's
  versioning, availability and install cost while owning none of
  them (D10: an install per session is not a price a test run pays).
  Provider content stays reachable the way everything else does —
  the tester declares it (P1, P3), which is their choice to make and
  never testaferro's default to drift into.

  **An entry declaring nothing is still complete.** `freedos` names
  only its platform and takes the binding's zero-configuration boot
  image, which is testaferro's own authored media definition —
  a URL and its hashes, written in `testaferro/reliquary.py` — and
  not a name looked up anywhere. What this principle forbids is
  reaching into the provider's shipped content for a name, not
  declaring little. *[Amended before arming: "from the session to
  the catalog" is written "from the guest session" above, D15 having
  since taken the unqualified word for pytest's own span. The second
  paragraph is added — `catalog.py` has always read this way, and
  the first paragraph alone could be read as requiring every entry
  to spell out a boot medium.]*
