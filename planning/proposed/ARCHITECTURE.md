<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: BSD-3-Clause
-->

# Proposed architecture

> **Status:** drafted, not pledged. **Nothing is worked from here.**
> The whole-system view and the itemized architectural principles,
> P-numbered so use cases, decisions, designs and commits can cite
> them — reconstructed from the project's own prose when testaferro
> adopted the planning model (D7). An entry leaves for
> [pledged/](../pledged/) when the project undertakes it and for
> [root `ARCHITECTURE.md`](../../ARCHITECTURE.md) when the code
> honors it — that root file now holds all but four of them (P1, P2,
> P4, P6 through P13, P16 and P17), and a
> divergence from anything in it is a bug rather than unbuilt work.
> Nothing in *this* file carries that weight. Numbering comes from one
> global P-sequence, never reused, and an entry keeps its number all
> the way to the root list.

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
(U6), and **everything about the guest itself** is the provider's,
testaferro adding a thin binding when a provider is ready to
surface (D2).

## The seams

The unit of design is the **backend operation** performed for one
suite: enumerate its tests, run them all, run one, and open and
close a session around that. Beneath the facade three things
compose:

1. **The `Backend` seam** — the five-operation ABC every execution
   path implements, and the public escape hatch: a caller with a
   wholly different execution mechanism passes a prebuilt `Backend`
   and keeps everything above it (D1).
2. **The provider binding** — one module per provider, holding
   everything about how that provider is asked to build, boot and
   drive what runs a suite. Reliquary lives here, and QEMU does not
   live here at all: it is reliquary's own business, a layer further
   down than testaferro can see (P1, P2). *[Amended: this said one
   module per guest OS family, which named the layer beneath the
   provider rather than the provider.]*
3. **The framework adapter** — argv builders and output grammars for
   one guest unit-test framework, independent of how the output was
   obtained and of who obtained it. This seam is the one specified in
   force: P4, at [root `ARCHITECTURE.md`](../../ARCHITECTURE.md),
   names the five callables an adapter supplies.

`SuiteBackend` is the internal composition of an execution path with
a framework adapter. It is internal on purpose: composing them is
not a public contract, and its runner-callable shape must not become
one (D1).

A **test environment** is what a suite runs in, and it is the whole
consumer-facing vocabulary for guest matters: **standard**
environments testaferro authors and names (U9, D10), and **custom**
ones a tester declares — a choice of provider plus everything that
provider needs, as deep as that provider goes (P2). *[Amended. This
said **platform** and **test machine**, the pair D3 made the
consumer's vocabulary; `platform` is reliquary's own word, reaching
testaferro as configuration passing through (P3) rather than as
something a suite says. D3 was retired by D18, which pledged the
amendment; F11 delivered the noun and F12 the provider axis, so both
halves of it are built.]*

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
2. **The test-environment declaration** — the vocabulary of a
   declaration, whichever spelling carries it: blueprint machine
   fields passed through untouched (P3), `platform` among them, plus
   testaferro's own spellings around them — `environment=`,
   `provider=`, `boot_image=`, `machine_config=`, and the
   underscore-for-hyphen normalization of blueprint keys.
3. **`testaferro.ini`** — the authored per-project file: its
   section-per-environment shape, its scalar and JSON value
   spellings, its relative-path resolution, and the upward search
   that finds it. The declarative twin of `config()`, so a change to
   either is a change to both.
4. **The `Backend` ABC** — public because a prebuilt backend is a
   documented escape hatch; its five operations are a contract with
   callers who implement it.
5. **The pytest items testaferro produces** — the id spelling
   (`Group-Name`, a dash and never a dot, because IDE tree-to-target
   mapping reads dots as hierarchy), the re-homed source location,
   and the shape of a guest failure's report — the guest's own file,
   line and assertion when it ran, and its own screen when its answer
   could not be read at all (D19). Consumers write node
   ids into CI invocations and IDE run configurations, so these are
   world-facing whether or not they look like an API.
6. **The cache location and layout** — `%LOCALAPPDATA%\testaferro`
   or `$XDG_CACHE_HOME/testaferro`, what testaferro puts there, and
   what `stop()` and `stop(clear_downloads=True)` sweep. A durable
   on-disk footprint on the user's machine is a contract with them.

**The plugin's options have joined this list**, and they are not a
seventh surface but a second presentation of the first two:
pytest's own command line and ini carry testaferro's options, each
the kebab-case spelling of a declaration keyword (P16, D9), and the
items the plugin collects extend the fifth surface's id contract to
`suite.exe::Group-Name` spellings. Two additions came with them and
belong to the surfaces they extend: `suites` masks are declaration
vocabulary (the second and third surfaces), and **which files the
plugin claims** is world-facing in its own right — a project's tree
is scanned by it, so what a scan may claim is a contract with every
project that installs the distribution. A **lifecycle CLI** (F2)
joins as its own small surface when it lands: verbs over machines
and caches, never over test runs.

**The second and third surfaces were renamed by the work**, not by
the pledge that owed it. P1 and P2 — pledged by D18, since armed —
make a
declaration a *test environment* rather than a machine, and this
enumeration went on naming a machine until the code did otherwise,
because it is looked up to answer "does this change an interface?"
and so must name the surfaces as they exist. `provider=` joined the
second surface the same way, when F12 landed it in all three
spellings.

**testaferro currently has no norms.** Each surface above should name
the artifact that says exactly what it *is* and that the
implementation answers to; none does, because no such artifact
exists. [README.md](../../README.md) describes the public surface
without binding it. What norms these interfaces — authored prose, or
the code itself — is an open question in
[../DECISIONS.md](../DECISIONS.md), and it is worth settling before
anything that looks normative is written.

## The principles

- **P3 — testaferro mirrors no provider's schema.** An authored
  machine document belongs to the declared provider's own
  vocabulary — a reliquary blueprint today — and passes through
  untouched for that provider to validate, so a new field is
  expressible the day the provider ships it, without a testaferro
  change. The single deliberate exception is key spelling:
  hyphenated blueprint keys are written with underscores in Python
  and INI and normalized on construction, neither host spelling
  admitting a hyphen. (D4, D11.)

  **What stops this arming is the word "single".** The code does
  three further things to an authored document, each small and each
  deliberate: `EnvironmentSpec` case-folds `platform` and supplies
  `"dos"` where the author wrote none; the binding supplies a memory
  default, the boot floppy and its own work drive (D5); and
  `_work_drive()` reads the `hdd<n>` slot keys and mirrors a
  letter-assignment rule reliquary owns and does not expose. None of
  them mirrors reliquary's *schema* — no field is validated, no shape
  restated, and a new blueprint field still needs no testaferro
  change — so the spirit holds while the sentence does not. Arming it
  means either widening the exception clause to name what testaferro
  authors on the tester's behalf, or dropping the case-fold and the
  `platform` default and letting the provider see what was written.
  Which of those is right is a decision, not a residue to file.
- **P5 — The guest side is testaferro's, and hermetic.** Every
  session pins its own reliquary home, cache and asset root under
  testaferro's cache, so resolution sees only what testaferro
  authored: never the user's reliquary home, never the built-in
  codex, and never their boot image, which is read and never written.
  (D6.)

  **The last clause is the one that is not true yet.** A `boot_image=`
  given to one suite is attached to the guest **in place** —
  `materialize: "use"`, with no `read-only` on the drive — so a guest
  that writes to A: writes the tester's own file. The run-level
  `start(boot_image=…)` path is safe, because it copies the image
  into the run's area first; the per-suite path never acquired the
  same protection. That is a defect to fix rather than a sentence to
  soften, and fixing it is what arms this principle. Two smaller
  things go with it: "asset root" names the `assets=` knob reliquary
  retired in 0.1.0.dev3 — the pin is home, cache, blueprints
  directory and `autoseed=False` now (D6, restated) — and "every
  session" wants D15's qualifier, since what pins a context is a
  guest session.
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

**Four are left, and for two different reasons.** P3 and P5 describe
the code and do not yet describe it accurately — each has a residue
naming itself, recorded at the entry. P14 and P15 describe the
project's *conduct* rather than its code, and the in-force list says
of every entry that "the code honors it": a rule about how a decision
is argued has no code to be honored by, so whether that list carries
governance posture at all is a question about what the file is for,
and it has not been asked. Nothing is wrong with either pair sitting
here; drafted is where a principle waits, not where it fails.

**Principles that moved on have left this file** for
[root `ARCHITECTURE.md`](../../ARCHITECTURE.md). Most went straight
there without stopping at `pledged/` — P4 first, then P6, P7, P8, P9,
P11, P12, P13 and P17 together — while P1 and P2 took the long route,
pledged by D18 and armed once F12 built what they promised. That
shelf now holds no principle at all, which is why
`pledged/ARCHITECTURE.md` is gone. A gap in the
numbering here is where one went. The whole-system view above and
the interface enumeration stay here whatever moves, because the
vetting rule looks the interfaces up in this file.
