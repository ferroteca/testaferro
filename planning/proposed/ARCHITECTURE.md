<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: BSD-3-Clause
-->

# Proposed architecture

> **Status:** drafted, not pledged. **Nothing is worked from here.**
> The whole-system view and the itemized architectural principles,
> P-numbered so use cases, decisions, designs and commits can cite
> them — reconstructed from the project's own prose when testaferro
> adopted the planning model (D7). When pledged and honored, this
> becomes root `ARCHITECTURE.md`, the in-force claim: *the model is
> the shipped system's and every principle is honored as the code
> stands today*. It is not that yet. Numbering comes from one global
> P-sequence, never reused, and an entry keeps its number all the way
> to the root list.

Principles carry **equal weight with the use cases**
([USE-CASES.md](USE-CASES.md)) as a decision surface: a principle
amendment is argued exactly as vigorously as a use-case one, and a
principle drives work directly — a feature or task may be demanded by
a P-number just as by a U-number. Most entries below shape the
system; the last few are the process posture that keeps the
architecture governable, and live here because one list with one
lifecycle beats a second list for three entries.

## What testaferro is

testaferro is a **pytest plugin for tests that can only run inside
a guest machine** — distribution `pytest-testaferro`, import and
identity `testaferro` (D12). A unit-test suite built for a guest
OS — today a DOS build of a CppUTest suite — runs inside that
guest, and its individual tests surface on the host as ordinary
pytest items: collected, selected, batched, and reported like
local tests, with `pytest tests/suite.exe` the whole first command
(D9). The embedding API is the same plugin's programmatic layer;
the framework adapters remain usable on their own, against output
obtained some other way (U6); and a small lifecycle CLI (F2) is
the one deliberately non-pytest surface.

It is deliberately not a VM tool. The declared provider owns the
guest machine entirely — reliquary today, the only supported one
(P1, D11) — while testaferro owns the pytest side of the seam and
the knowledge of what a guest test suite's output means. Two
pluggable aspects follow from that division, and only one of them
is testaferro's: the **guest unit-test framework** is testaferro's
(U6), and the **guest platform** is the provider's, testaferro
adding a thin binding when a platform is ready to surface (D2).

## The seams

The unit of design is the **backend operation** performed for one
suite: enumerate its tests, run them all, run one, and open and
close a session around that. Beneath the facade three things
compose:

1. **The `Backend` seam** — the five-operation ABC every execution
   path implements, and the public escape hatch: a caller with a
   wholly different execution mechanism passes a prebuilt `Backend`
   and keeps everything above it (D1).
2. **The platform binding** — one module per guest OS family,
   holding everything about how that platform's machines are built,
   booted, and driven through reliquary. QEMU lives here and nowhere
   the consumer can see it (P2).
3. **The framework adapter** — argv builders and output grammars for
   one guest unit-test framework, independent of how the output was
   obtained and of who obtained it (P4).

`SuiteBackend` is the internal composition of an execution path with
a framework adapter. It is internal on purpose: composing them is
not a public contract, and its runner-callable shape must not become
one (D1).

A **platform** is a type — the OS family a suite is built for; a
**test machine** is one named declaration carrying a platform. That
pair is the whole consumer-facing vocabulary for guest matters (D3).

## The interfaces

The seams are the inside; this is the outside boundary — the surfaces
through which the world drives testaferro. **This enumeration is
normative**: housekeeping's first test and the interface-change rule
([../INTERFACES.md](../INTERFACES.md)) both answer "does it change an
interface?" by lookup against this list, and changing any surface
named here follows that rule.

1. **The embedding API** — the public module surface:
   `guest_suite()`, `config()`, `load_config()`, `start()`/`stop()`,
   and the framework adapter modules (`testaferro.cpputest`) usable
   on their own. This is the primary interface, and the one U1 is
   written against.
2. **The machine declaration** — the vocabulary of a declaration,
   whichever spelling carries it: blueprint machine fields passed
   through untouched (P3), plus testaferro's own spellings around
   them — `boot_image=`, `machine_config=`, `platform=`, `machine=`,
   and the underscore-for-hyphen normalization of blueprint keys.
3. **`testaferro.ini`** — the authored per-project file: its
   section-per-machine shape, its scalar and JSON value spellings,
   its relative-path resolution, and the upward search that finds it.
   The declarative twin of `config()`, so a change to either is a
   change to both.
4. **The `Backend` ABC** — public because a prebuilt backend is a
   documented escape hatch; its five operations are a contract with
   callers who implement it.
5. **The pytest items testaferro produces** — the id spelling
   (`Group-Name`, a dash and never a dot, because IDE tree-to-target
   mapping reads dots as hierarchy), the re-homed source location,
   and the shape of a guest failure's report. Consumers write node
   ids into CI invocations and IDE run configurations, so these are
   world-facing whether or not they look like an API.
6. **The cache location and layout** — `%LOCALAPPDATA%\testaferro`
   or `$XDG_CACHE_HOME/testaferro`, what testaferro puts there, and
   what `stop()` and `stop(clear_downloads=True)` sweep. A durable
   on-disk footprint on the user's machine is a contract with them.

**Plugin options join this list when F8 lands**, and they are not a
seventh surface but a second presentation of the first two:
pytest's own command line grows testaferro's options, each the
kebab-case spelling of a declaration keyword (P16, D9), and the
items the plugin collects extend the fifth surface's id contract to
`suite.exe::Group-Name` spellings. A **lifecycle CLI** (F2) joins
as its own small surface when it lands: verbs over machines and
caches, never over test runs.

**testaferro currently has no norms.** Each surface above should name
the artifact that says exactly what it *is* and that the
implementation answers to; none does, because no such artifact
exists. [README.md](../../README.md) describes the public surface
without binding it. What norms these interfaces — authored prose, or
the code itself — is an open question in
[../DECISIONS.md](../DECISIONS.md), and it is worth settling before
anything that looks normative is written.

## The principles

- **P1 — The guest-machine provider is a declared choice, and
  reliquary is the only supported one.** Providers occupy one
  layer — reliquary and vagrant sit in the same space — so a
  machine uses one *or* another, and the declaration names which
  (D11); testaferro passes that provider's machine configuration
  through untouched (P3). The axis is testaferro's own: a future
  provider is a new binding here, never capability pushed upstream.
  What D1 refused stays refused — no structural runner contract, no
  conformance kit, no mirrored configuration hierarchy, and no
  abstraction built ahead of a second concrete provider; a prebuilt
  `Backend` remains the escape hatch, and the seam a provider
  implements. **The split governs verification as much as
  implementation**: a property of the guest machine is the
  provider's to guarantee and to test, so doubting one produces an
  upstream bug report — never a local audit of its internals, and
  never a defensive workaround here. (D1, D11.)
- **P2 — Suites name platforms and machines, never emulators.**
  QEMU is an implementation detail of a binding and appears nowhere
  in what a suite-facing consumer writes; the facade's binding
  table keys by platform name. The machine *declaration* is the one
  place a provider is named (P1): the tester who declares a machine
  may say what provides it, and everything beneath the provider
  stays invisible. (D3, D11.)
- **P3 — testaferro mirrors no provider's schema.** An authored
  machine document belongs to the declared provider's own
  vocabulary — a reliquary blueprint today — and passes through
  untouched for that provider to validate, so a new field is
  expressible the day the provider ships it, without a testaferro
  change. The single deliberate exception is key spelling:
  hyphenated blueprint keys are written with underscores in Python
  and INI and normalized on construction, neither host spelling
  admitting a hyphen. (D4, D11.)
- **P4 — The framework adapter is independent of the runner.** It is
  argv and grammar only; it never imports reliquary, and the guest
  binding defaults it to CppUTest while keeping it a parameter. That
  independence is what makes the adapter usable against output
  obtained some other way. (U6.)
- **P5 — The guest side is testaferro's, and hermetic.** Every
  session pins its own reliquary home, cache and asset root under
  testaferro's cache, so resolution sees only what testaferro
  authored: never the user's reliquary home, never the built-in
  codex, and never their boot image, which is read and never written.
  (D6.)
- **P6 — A running machine is stopped before anything is swept.** A
  machine outlives the call that booted it, so every backend holding
  a live guest is tracked and stopped before any directory is
  removed — by `stop()` and by the `atexit` failsafe alike. Sweeping
  first deletes the disk out from under a running guest and leaks the
  process, so any new exit path goes through the same stop.
- **P7 — Fail before the guest boots.** A provably foreign binary —
  the host build of the suite passed by mistake — an ambiguous
  machine selection, or an unusable option is rejected up front,
  naming what was found and what the choices were. Nothing that can
  be known cheaply is discovered by booting a machine and watching it
  fail. Where nothing can be proven — a headerless `.com`-style
  image carries no header to judge — it passes through for the guest
  itself to judge, which is honesty about the limit rather than an
  exception to the rule.
- **P8 — Zero configuration is an entry point, not a demo.** Every
  configuration surface added leaves the no-declaration path working:
  a suite executable and nothing else still runs. (U2.)
- **P9 — Grammars derive from source, never from samples.** A
  framework adapter's argv builders and output grammars are derived
  from that framework's own source, and its unit fixtures are
  source-derived rather than captured. The cost is stated plainly:
  source-derived fixtures cannot prove a real run, so a grammar
  change warrants a real end-to-end run before it is trusted.
- **P10 — Unit tests never launch a hypervisor.** The tier split is
  by **cost**, not by coverage. Unit tests may use reliquary freely
  and should — `create_machine()` is cheap and hypervisor-free, and
  running it for real is the best coverage available on this side of
  the line — but `start_machine()`, `stop_machine()` and `exec()`
  belong to integration. The cheap half is conditional on the
  blueprint rather than on the call: a drive materializing a blank
  goes through qemu-img, and a machine declaring one belongs to
  integration.
- **P11 — The standard library, plus two dependencies at named
  seams.** pytest and reliquary are the whole dependency list; pytest
  is imported lazily in the facade, and reliquary only in the guest
  binding and in `machines.py` for its JSONC reader. Python 3.9 and
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
- **P14 — Interface and principle changes are vetted.** Every
  interface-changing decision triages by its impact on the use cases
  *and* the principles, under the interface-change rule
  ([../INTERFACES.md](../INTERFACES.md)); a change misaligned with
  either is argued as the amendment it requires — a principle
  amendment as vigorously as a use-case one — never as a feature on
  its own merits.
- **P15 — The self-description changes by proposal, never by
  arrival.** What the project says it is and is for — the standing
  lists, the normative artifacts once they exist, and everything
  under `planning/` — changes only through a proposal that wins its
  gate first, entered through one of the three queues. The door is
  open: anyone may argue for any change. What is refused is
  *arrival*, and the ground is the missing argument rather than the
  work's quality or its author. Governance authority may compress the
  steps into one PR — compressed in time, never reduced in content.
  (D7.)

**Pledged principles have left this file** for
[../pledged/ARCHITECTURE.md](../pledged/ARCHITECTURE.md); a gap in
the numbering here is where one went. The whole-system view above and
the interface enumeration stay here whatever moves, because the
vetting rule looks the interfaces up in this file.
