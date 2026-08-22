<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# DECISIONS

The adjudicated design-decision record. Each entry records what was
decided, by whom and when, what was weighed and declined, and where
it folded. The normative homes are elsewhere —
[INTERFACES.md](INTERFACES.md), the use-case and principle lists,
and the specifications once this project has any. This file is the
adjudication trail, and the guard against re-litigating: **anything
recorded here as killed, declined, or superseded is not revisited
without new evidence**, argued through the interface-change rule
([INTERFACES.md](INTERFACES.md)).

Decisions are numbered in the order first recorded — D1 the
earliest — and **a number is never reused**; the list reads
newest-first, so the top entry carries the highest number and a new
entry prepends with the next free one. The D-number is the
decision's citation handle everywhere: a decision names the use
cases (U-numbers) and principles (P-numbers) it supports, and it is
citable downstream — design documents, specifications, and code
commits justify choices by citing D-numbers.

**A lifecycle act alone earns no entry.** Proposing, pledging,
promoting, delivering: location already states the status and the
commit that moves the item is the record, so an entry restating the
act is the separate register this machinery refuses to keep, and
delivery evidence — the clause-by-clause case that a use case is
actually met — belongs in the moving commit's message. What earns an
entry is **adjudication**. A decision whose conclusion pledges
something records the argument and stands; a ruling made in an act's
course — a contested clause reading, a scope call, a pledge found
accidental and withdrawn — is recorded slim, as the ruling, never as
the promotion narrative around it (D14).

**The supports clause is not optional, and "none" is an answer.** A
decision genuinely demanded by nothing — a vocabulary or naming
choice — records `Supports (none)` and why. Prose in place of a
handle is the same gap wearing a sentence: a citation that resolves
to no number is not a citation, and only a numbered one can be
audited.

An overruled or no-longer-relevant decision moves, number and text
intact, to the Retired decisions section at the bottom, its note
naming what overruled it — a retired decision binds nothing but
remains the record.

**Entries keep the spellings of their time.** An entry only PARTLY
overruled stays where it is and is ANNOTATED, NEVER REWRITTEN: the
amending entry governs, and a bracketed one-line pointer at the
affected clause names it, leaving every other clause standing. This
is the retirement note's instinct applied at clause granularity, and
it is the limit of the spellings rule. That rule protects the
record's fidelity to its own moment — it is not licence to leave a
WRONG INSTRUCTION standing where a reader arriving by search will
act on it. A dated word cannot cause a bug; a wrong test can.
Correcting an entry's prose in place is never the answer either: an
error and its discovery are part of the record, and often the most
useful part of it.

> **D1–D6 are reconstructed.** This record was opened on 2026-07-27,
> after the decisions it opens with had already been made and landed.
> Their substance and dates come from the retired `ROADMAP.md` and
> from the commits that implemented them, not from a contemporaneous
> record; read them as a faithful migration rather than as entries
> written at the time. The "weighed and declined" material is only as
> complete as those sources were. D7 onward is written as it happens.

## Open questions

Questions awaiting adjudication — the front of this record rather
than a separate one, since what settles them is an entry below.
Nothing here binds anything; a question leaves this section by
becoming a D-number, and the commit that moves it is the record.

- **What norms Testaferro's interfaces.** The project holds no
  normative document today: [README.md](../README.md) describes the
  public surface but does not bind it, so there is nothing an
  implementation currently answers to and no artifact whose edit
  counts as an interface change. Two candidate answers, and the
  choice is deliberate. **Authored prose** — a specification per
  surface, kept wherever this project keeps norms — is the usual
  pick and readable by someone deciding whether to adopt the
  library. **The code is the norm** is legitimate for a library
  whose API is its own definition; it relocates the gate to code
  review rather than removing it, since an unargued change then
  *redefines* the interface instead of violating it. What is never
  tolerable is two norms for one surface. Settle this before writing
  any document that looks normative, and before pointing any
  doc-sync tooling at the tree.
- **Whether Testaferro needs a document format of its own.** A
  declaration already *is* an authored reliquary blueprint (D4), and
  `machine_config=` already accepts a whole blueprint document or a
  `.rlqb` path, so the original case for a Testaferro-owned
  superset document has mostly dissolved. What it would still buy is
  Testaferro-specific keys sitting beside the blueprint — reliquary's
  schema is closed (`additionalProperties: false`), so such keys
  would have to nest the blueprint rather than merge with it — and a
  `spec=` / `exe_type=` spelling at the call site. Against: a second
  document format to explain and version. **Decide by naming a key
  that must live beside the blueprint and cannot be a
  `guest_suite()` argument** — if none appears, the question closes
  as a refusal.
- **USB as a boot-media type.** Every test machine has exactly one
  boot image and only the media type varies — floppy, hard disk, CD,
  defaulted by the platform. Whether USB joins that set is open, and
  is largely reliquary's answer to give.

## Decisions

### D29 — P4 admits an optional sixth adapter callable, and F3 is pledged on it

**Decided** owner, 2026-08-22, by directing F3's pledge and
delivery. **Supports** U5 (in force) and P4 (in force, amended here).
Takes the route D24 named and did not take.

**The amendment.** P4 read "`SuiteBackend` calls exactly those
five." It now reads five required and one optional:
`run_some_argv(group, names)`, the argv that runs several named
tests of one group in one exchange. The count was never the
principle — the principle is that an adapter is argv builders and a
grammar and nothing else, imports no runner, and never learns how
its output was obtained — and a sixth builder of the same kind
changes none of that. What the count guarded against was a seam
growing by convenience, and the guard holds in the terms of the
amendment: the sixth is *optional*, so an adapter supplying the five
is complete and loses only the batching; it is *one group's*, because
that is the only scope CppUTest's filters keep (D24) and the facade
can compose group batches out of any selection; and nothing further
is asked of an adapter that supplies it. A future adapter whose
framework filters by any other shape still fits — the callable
states what its own framework can run in one exchange, and the
composition asks for no more.

**Why a sixth callable and not another shape.** D24 left open "a
shape that does not need it." None was found that honours P4 and
D17 together: the composition cannot build a subset argv itself
without knowing CppUTest's flags, which is the adapter's knowledge
and nobody else's; and a single `run_one_argv` repeated is what the
batching exists to replace. The adapter is the only place a
framework's selection grammar lives, so a selection of several is
the adapter's to spell.

**The `Backend` ABC gains an operation without gaining an
obligation.** `run_some(group, names)` is defaulted to one
`run_test()` per name, which is exactly what the facade did before
it existed, so a prebuilt backend written to the documented five
operations is unchanged in behaviour and in what it must implement.
`SuiteBackend` overrides it to use the adapter's sixth callable when
there is one.

**The line is the executing side's, and it is short.** A DOS program
sees at most 125 characters of arguments — the program segment
prefix's command tail — and COMMAND.COM takes 126 characters of
typed line, program and all. So a subset is cut to fit: each binding
hands `SuiteBackend` an `argv_budget` (reliquary's the typed line
less its program, computed once the location settles; DOSBox-X's the
tail alone, its `[autoexec]` being read by a wider shell), and the
composition splits a group's names across as many exchanges as fit,
measuring the argv the way the executing side will spend it and
still joining nothing (D17). The budget is a fact about the guest's
DOS, so the tail constant lives in `placement.py` with the other
things both DOS bindings do the same way.

**What the facade does with it.** `ResultBroker` batches a narrowed
selection per group: the whole suite is still one `run_all()`; a
group with several selected tests is one `run_some()`; a group down
to one selected test stays `run_test()`. Under xdist's `--dist load`
a worker holds a scattered slice of a suite, and this is what makes
that distribution efficient on a single suite rather than one
exchange per test — the U5 journey's other half, which `loadfile`
alone served.

**Folded into:** root `ARCHITECTURE.md` (P4), `src/testaferro/backend.py`,
`cpputest.py`, `suite.py`, `facade.py`, `placement.py`,
`reliquary.py`, `dosbox_x.py`, `planning/proposed/ARCHITECTURE.md`,
`planning/proposed/FEATURES.md` (F3 removed), `README.md`,
`AGENTS.md`.

### D28 — The DOSBox-X work drive is `D:`, and a document is opened by the provider that declared it

**Decided** owner, 2026-08-21, by directing F21's delivery.
**Supports** P2 (in force), P3, P17.

Three rulings made in F21's course, each with the alternative it
declined:

- **The work drive takes `D:` on both providers.** F21 left this
  between matching reliquary's letter and leaving letters each
  provider's own with `{location}` as the portable spelling. Matched:
  the owner's direction was that changing provider be as close to
  transparent as is realistic, and a `setup=` naming `D:\DRIVER.COM`
  or a suite reading its data from `D:` is exactly the declaration
  that would otherwise not move. Nothing is mounted at `C:` — DOSBox-X
  needs no system drive — and `{location}` remains the spelling
  portable to any provider serving another letter. Reopened only by
  a provider that cannot serve `D:` at all.
- **A machine document on disk is opened by the declared provider's
  binding**, each supplying its own `read_document()`, and a
  declaration naming a path asks the provider it declared — the
  default's binding when none was named, applied in
  `resolution.binding_for()` and nowhere else. Declined: keeping one
  parser in `environments.py` and sniffing the format, because a
  format is the provider's (P3) and a `.conf` read as JSON5 fails
  naming the wrong grammar.
- **The `dosbox-x` catalog entry authors one section, `[cpu]
  cycles=max`.** D27 declined the entry as having nothing to author;
  the document channel gives it something, and a suite is run for
  its answer rather than its timing. Declined: an entry declaring
  nothing — the degenerate case P17 allows — which would buy nothing
  over `provider=`, the ground D27 refused it on. Reopened by a suite
  for which `cycles=max` changes an answer, and such a suite belongs
  on the default provider regardless (D27).

Refusals land in the binding's own voice (P1's rule, D27): a
declared `[autoexec]`, a field that is not a section, blueprint
`media`, and `boot_image=` — the last because a booted DOS runs no
`[autoexec]`, the batch shape's only way in.

**Folded into:** `src/testaferro/dosbox_x.py`,
`src/testaferro/environments.py`, `src/testaferro/resolution.py`,
`src/testaferro/reliquary.py`, `src/testaferro/catalog.py`,
`src/testaferro/plugin.py`, [../ARCHITECTURE.md](../ARCHITECTURE.md)
(P2), [proposed/ARCHITECTURE.md](proposed/ARCHITECTURE.md) (P3, the
interface enumeration), [../AGENTS.md](../AGENTS.md),
[../README.md](../README.md), [../CHANGELOG.md](../CHANGELOG.md),
`tests/test_dosbox_x.py`, `tests/test_environments.py`,
`tests/test_project_config.py`, `tests/test_resolution.py`,
`tests/integration/test_dosbox_x.py`,
[proposed/FEATURES.md](proposed/FEATURES.md) (F21 retired by
delivery), [SEQUENCES.md](SEQUENCES.md).

### D27 — DOSBox-X is the second provider, batch-shaped, and refuses guest sessions

**Decided** owner, 2026-08-21, by directing F20's delivery.
**Supports** P1 (in force, amended by this entry), P8, P10, U10.
This is the event D1, D11 and D16 each deferred to rather than
refused — "only if a second actual runner appears", "waiting on a
second concrete provider", "the day a second binding exists" — so
what those entries postponed is adjudicated here.

F20 named three questions to answer before the work, and each got
its answer from the work itself:

- **The measurement holds, dramatically.** One DOSBox-X invocation
  runs the whole integration suite — mount, run, redirect, exit — in
  about 0.3 seconds against about fifteen for a single boot on the
  default provider; the binding's five integration cases take 1.3
  seconds together against about two minutes for the boot-model six.
  The tier's cost curve changes shape exactly as argued, and P10 is
  unmoved by it: fast is not cheap in its sense — DOSBox-X starting
  a DOS is a guest starting — so the cases sit in the integration
  tier no matter what they cost.
- **U10's open question cuts the feature in one piece, not two: the
  binding refuses guest sessions, in its own voice.** The batch
  model holds no guest state between invocations, and a scripted
  interaction exists to build on exactly that state; relaunching per
  command would discard it silently, which is worse than saying no.
  So `dosbox_x.guest_session()` raises naming the reason and the
  provider that serves the entry point, and P1 gains the rule the
  architecture did not contemplate before there was an instance of
  it: **a provider serves the entry points its model can honor, and
  refuses the rest in its own voice** — the refusal is the binding's
  answer, like `PLATFORMS`, and resolution keeps no capability
  table. Giving DOSBox-X an interactive channel was weighed and
  declined: it would spend every simplification the batch shape buys
  (no readiness protocol, no screen transport, nothing at rest) to
  serve an entry point the default provider already serves well.
- **The licence is verified, and the prior-art entry is new in
  kind.** GPL-2.0-or-later (source headers carry the "or any later
  version" grant; `COPYING` is GPLv2; verified 2026-08-21 upstream
  and against the installed 2026.08.02). Tier 2 by the process
  boundary — and unlike QEMU, which is reliquary's to invoke and
  deliberately unnamed here (P2, D16), Testaferro invokes DOSBox-X
  itself, so the arm's-length analysis lives in this repository and
  the name is Testaferro's to speak: it is a provider, not something
  under one. Not a P11 dependency; never bundled into any artifact.

**The run stays reliquary's, as a decided shape.** P1's stop-short —
`start()`/`stop()` reaching the binding by name — said it was "the
first place to look the day a second binding lands". Looked: a *run*
is one staged boot-image choice and one sweep area, which only the
machine-booting model has. A DOSBox-X guest stages no image, and its
home is swept by its own `stop_guest()`; there is no run state for
it to join, so generalizing the run now would be abstraction with
nothing to hold. The entry is amended to say so rather than left
reading as a divergence.

**The seam is derived, not designed, and it is small.** What
`_GuestLifecycle` holds that is genuinely reliquary's turned out to
be nearly all of it — blueprints, sessions, the letter map,
readiness, at-rest writes. What belongs above it is the placement
vocabulary: the nearest-speaker override rule, host-side gathering
of the staged set, and `program=` resolution against a settled
location, now `testaferro.placement`, holding exactly what the two
concrete bindings do identically and nothing either does
differently. That is the interface D1 and D11 said would be derived
from concretes when there were two.

**Naming**: a binding is named for the provider it binds (D16), and
`dosbox-x` is not a Python identifier, so the declared spelling
keeps its hyphen and resolution selects the module with the same
underscore normalization hyphenated declaration keys already get —
`provider="dosbox-x"`, module `dosbox_x.py`.

**Weighed and declined**, beyond the interactive channel above: a
`providers/` package (D16 priced it at nothing "the day a second
binding exists"; two sibling modules do not need a level, and the
name-selects-module dispatch rule stays one sentence without one — a
third binding may reopen this); a `dosbox` standard catalog entry
(DOSBox-X brings its own DOS, so there is nothing to author — P17's
degenerate case — and naming an environment that declares nothing
buys nothing over declaring `provider=` until someone asks for the
name) *[the entry exists now, with a section to author: F21, D28]*;
and a machine-document channel for DOSBox-X's own conf (a
dosbox-x declaration carries Testaferro's own words only, and a
declaration carrying another provider's blueprint fields is refused
naming them rather than silently stripped — passing authored conf
sections through, P3's shape for this provider, is its own argued
feature the day a suite needs one) *[that day came: F21 delivered
the channel, D28]*. `boot_image=` is likewise not a
dosbox-x option: nothing boots, and resolution's existing
wrong-option refusal names the environment and provider *[the
binding refuses it in its own voice since F21, naming why]*.

**Folded into:** `src/testaferro/dosbox_x.py`,
`src/testaferro/placement.py`, `src/testaferro/reliquary.py`,
`src/testaferro/resolution.py`, [../ARCHITECTURE.md](../ARCHITECTURE.md)
(P1), [../AGENTS.md](../AGENTS.md), [../README.md](../README.md),
[../CHANGELOG.md](../CHANGELOG.md), `tests/test_dosbox_x.py`,
`tests/test_placement.py`, `tests/test_resolution.py`,
`tests/integration/test_dosbox_x.py`,
[proposed/FEATURES.md](proposed/FEATURES.md) (F20 retired by
delivery), [SEQUENCES.md](SEQUENCES.md).

### D26 — the test suite adopts pytest, reversing the unittest-only rule

**Decided** owner, 2026-08-20. **Supports** (none) — a tooling
choice about how the project verifies itself, not a claim owed to a
user.

AGENTS.md stated, undated and citing no D-number, that tests are
stdlib `unittest` "so the constraint is not spent on a second
runner" — reading `pytest` as a second test-running mechanism
alongside `unittest`, when the runtime dependency (P11) is already
spent on it regardless: `pytest` is what Testaferro *is a plugin
for*, required whether or not it also runs this suite. Weighed
against that reading now: the suite's own idiom — `TestCase`,
`assertEqual`, `subTest`, `setUp`/`addCleanup` — is stdlib's
vocabulary for a project whose entire subject is pytest's, so every
contributor already fluent in what this project ships arrives at its
own tests speaking a second dialect. `pytest` collects `TestCase`
classes unmodified, which was weighed and declined as the fix: it
buys a nicer invocation (`pytest` in place of `python -m unittest
discover`) without touching the actual defect, since the suite would
still be written in the borrowed idiom. The suite is rewritten
instead — plain functions, `assert`, fixtures in place of
`setUp`/`tearDown`, `parametrize` in place of `subTest` loops — so
that reading a test and reading the plugin under test cost the same
fluency.

`tests/integration/` keeps its own gate: `TESTAFERRO_INTEGRATION`
unset skips the tier, now via `pytest.mark.skipif` in place of
`unittest.skipUnless`, unchanged in substance.

**Folded into:** [../AGENTS.md](../AGENTS.md), `tests/` (full
rewrite).

### D25 — U9 is pledged severed from its own plural growth, paired with F19

**Decided** owner, 2026-08-19. **Supports** U9 (pledged by this
entry).

`machine="freedos"` resolution is already built and unit-tested
(D10, `catalog.py` and its guard test) — cited as shipped behaviour
by D10 and D18 without itself being pledged, on the same reading D13
used to decline pledging U1, U2 and U3 alongside U4: proof owed, not
work. What changes here is that the project commits to writing that
proof. **F19** — one integration case naming `"freedos"` explicitly
against a real guest boot — is pledged alongside U9 as its
prerequisite, exactly as F9 was U7's and F18 was U10's.

**U9 is pledged severed from its own text, not from a citation to
another item.** Its drafted form promises the standard catalog "made
plural... as guests grow"; plurality is not owed here — a second
named environment waits on a second guest platform (F5), itself
waiting entirely on reliquary (D2) — so the pledged entry drops that
promise rather than carrying it unowed. The severed pledge is the
singular case alone: one name, resolving as documented, proven by
F19, true whether or not a second guest ever arrives.

**Weighed and declined:** pledging U9 unsevered, plural growth and
all, which would rest a pledge on F5 — proposed, shapeless, and
blocked entirely on a provider release outside this project's
control. Also declined: leaving U9 unpledged and simply adding F19's
proof as housekeeping, on the reading D13 gave U1–U3 — the owner's
call here was that committing the proof in the open, alongside the
use case it closes, is worth the pledge even though the underlying
mechanism is not itself owed.

**Folded into:** [pledged/USE-CASES.md](pledged/USE-CASES.md),
[pledged/FEATURES.md](pledged/FEATURES.md), the banners under
[proposed/](proposed/), [README.md](README.md),
[../AGENTS.md](../AGENTS.md).

### D24 — F3's pledge is withdrawn: its batching needs a sixth framework callable, which P4 forbids

**Decided** owner, 2026-08-19. **Supports** (none) — a withdrawal
correcting a pledge made without checking it against P4, not an
argument for or against any use case or principle.

Starting F3 (intra-suite sharding) showed what the pledge did not
check: CppUTest's own filter model makes safe batching possible only
through a group-scoped filter argv — verified against CppUTest's
actual source (`CommandLineArguments.cpp`, `TestFilter.cpp`,
`Utest.cpp`), where a test runs only when it matches *any* group
filter *and* *any* name filter, so repeating `-sg` for two different
groups in one call over-selects the cross product rather than the
wanted pairs, and one `-sg` per call is the only safe shape. Building
that argv is CppUTest-specific knowledge, which P4 confines to the
framework adapter alone — "`SuiteBackend` calls exactly those five"
— so the sixth callable this needs contradicts it outright.

Amending P4 to make room for an optional sixth callable was an
available route and was not taken. The pledge is withdrawn instead:
F3 returns to `proposed/FEATURES.md`, annotated rather than deleted,
to be reconsidered later — pledged again once P4 is amended, or
delivered some other shape — rather than landed against a principle
in force.

**Folded into:** `planning/pledged/FEATURES.md` (emptied again),
`planning/proposed/FEATURES.md` (F3 annotated), `AGENTS.md`,
`planning/README.md`.

### D23 — Testaferro computes every drive letter itself, permanently, and stages before materialization

**Decided** owner, 2026-08-19. **Supports** P1 and P17, through the
reliquary 0.1.0a2 pin move — this entry's own reopening condition
from its prior form arrived, and the branch it named broke exactly as
flagged. Reverses two of that form's own calls, on new evidence: not
an oversight corrected, a different question asked once the ground
it was answered on gave way.

**The shape.** `_letter_map()`, in `src/testaferro/reliquary.py`,
computes a DOS drive letter for every drive a document declares — a
floppy controller's drives take `A:`/`B:` by position and a hard disk
takes `C:` onward by slot order, one volume per disk — and this is
Testaferro's own stated answer now, for every drive alike: its own
system disk, its own work drive, and a `machine_config` template's
declared drives. There is no split left between a guarantee and a
lookup; one computation serves both, and a declared machine's
`location=` resolves through it exactly as Testaferro's own does.

**Testaferro's own work drive is a permanent fixture, staged before
the machine exists.** A vvfat medium — a host directory QEMU serves
live as a FAT volume, never materialized into an image — is a
sibling of whatever else a session's machine declares, in every
session, gathered before `create_machine()` runs. Its content exists
the moment the drive does, so nothing is written into it at rest; the
zero-configuration guest's default location moves from `C:\TESTS`
(the system disk, written into over remanence) to `D:\` (the work
drive, live). Retrieval, and a declared `location=` naming some
*other* drive, still go through `at_rest` (F16) — that drive is not
live-served.

**Reversed: asking the guest.** The prior form of this entry deferred
the declared-machine lookup to the guest reporting its own letters
once booted, drafted as **F17** and never pledged. Retired outright,
by owner direction, as part of a standing policy across reliquary,
remanence and Testaferro: neither sibling project will ever answer a
drive-letter question again (remanence's own D57), so the answer is
Testaferro's to own rather than to keep asking for. A boot-time
report would have been the more *conservative* fact — confirmed
per-run rather than assumed — but the cost of confirming it (a
staged marker, a second machine variable, a guest round trip before
any placement could be known) bought back only the one case D78
already named as the risk: a disk holding more volumes than declared.
Testaferro accepts that risk knowingly now, as policy, rather than
paying to confirm its absence every run.

**Reversed: staging before materialization.** Declined in this
entry's prior form on the guest story — supplying media for every run
was "the work-drive fallback promoted back into the promise, after F4
spent the effort demoting it." Adopted now because the fallback it
was demoting *to* an implementation detail no longer has anything to
be a fallback *for*: with no drive-letter answer to fail toward, a
defaulted address had nothing left to retry onto, so making the work
drive a standing fixture removes a failure mode rather than reopening
one. P8's zero-configuration promise is unaffected — `pytest
tests/SUITE.EXE` still needs nothing declared — and the media
Testaferro now supplies for every run is a live-served directory, not
an image it must build or own.

**The cost, restated rather than deferred.** A wrong declared
`location=` is still refused before any boot: `_letter_map()` refuses
a letter no drive answers to, by name, before `create_machine()` — a
computation, not a report, but a refusal all the same. F4's
invariant — an address is stated once, staged against, and spelled —
still holds. What changed is P7's absorption of the limit: the
"nothing can be proven, so the judgement passes to the guest" framing
this entry's prior form reserved for the deferred half no longer
applies to anything real, since nothing here still asks the guest to
prove it — the limit is now a stated assumption, and P7's carve-out
stands unused until a case actually needs it.

**What would reopen it:** an authority that reports a *stopped*
machine's letters without predicting them — letters read off an
installed system at rest, which is the thing both upstreams have
just removed.

### D22 — Supported versions are enumerated, not bracketed

**Decided** owner, 2026-07-30. **Adopts** P18 (drafted), which
carries the rule and its residue; this entry records only what
adopting it settled.

**Weighed and declined: a range as the source of the claim** —
`requires-python = ">=3.12"`, `reliquary>=0.1.0.dev6` — on the
ground that **capability is not monotonic in version number**, so no
bound expresses support in either direction. The evidence arrived
with F4: reliquary 0.1.0.dev5 read FAT32 at rest and 0.1.0.dev6
refuses it by name, which makes `>=0.1.0.dev5` a false claim about
the capability F4's staging runs on, while a ceiling would exclude a
later release that works. A range remains what *ships*, PEP 440
having no OR — the decision is that it is derived from the tested
set rather than standing as the claim itself.

**What would reopen it:** a packaging ecosystem that can express a
disjoint set directly, or a provider whose releases are additive by
policy, which would make a floor true rather than merely convenient.

### D21 — Testaferro is GPL-3.0-only, relicensing is reserved, and contributions are assigned

**Decided** owner, 2026-07-29. **Supports** (none): no use case or
principle demands a licence, and the governing vision is silent on
ownership. Recorded because it constrains what may enter the codebase
forever afterward, which nothing else in this record would otherwise
state. The record was searched first and holds no prior licensing
entry; D1, D4, D20 and P17 bear on the vetting below and are cited
where they do.

**The licence is GPL-3.0-only, replacing BSD-3-Clause.** Testaferro
is copyleft from here: it may be run, studied, modified, and
redistributed freely, and may not be taken into a proprietary
product. Releases through `0.1.0.dev7` went out under BSD and stay
there — a licence change binds forward only, and nothing published is
withdrawn. This follows the standing `manage-contribution-licensing`
policy for the owner's GPL-3.0 projects, with reliquary's D82 as the
worked precedent; where this entry is thinner than D82, that record
carries the fuller argument and this one adopts it.

**Weighed and declined:** **GPL-3.0-or-later**, because "or later"
delegates the definition of future terms to a third party — the one
thing an owner reserving relicensing rights should not do — and the
assignment policy already closes the door that flexibility would have
held open. **AGPL-3.0-only**, which closes a narrow hosted-service
gap at the price of the many corporate policies that refuse AGPL
outright; a testing library wants to be usable.

**Relicensing is reserved, and nothing is planned.** The owner holds
copyright in the whole work and reserves the right to relicense on
any terms. There is no second licence and nothing in preparation; the
reservation exists so the option is not lost by default, and it is
framed as relicensing rather than dual licensing deliberately —
naming one particular use of the right would advertise an intention
the project does not have. The reservation is stated openly in
README.md, CONTRIBUTING.md, and CLA.md, together with its binding
counterweight: CLA.md section 4 makes it a term, not a promise, that
no relicensing withdraws a release already made under the GPL.

**Contributions are assigned, not merely licensed**, via `CLA.md` —
assignment with an automatic fallback to an exclusive sublicensable
licence where a jurisdiction bars assignment (§29 UrhG being the
standing example), a licence-back so assigning costs a contributor no
use of their own work, and the reservation disclosed beside the
requirement it explains. Enforcement standing is the stronger reason:
only a copyright owner may sue, so consolidated ownership is what
keeps the GPL on this project enforceable rather than decorative.
**Assignability replaces licence compatibility as the incoming test**;
the dependency licence tiers and the vetting bar — every external
source judged as though the likely relicensing is a commercial dual
licence, because that is the strictest realistic outcome and vetting
weaker forfeits the option invisibly — live in AGENTS.md, their
normative home.

**The vetting round produced three Testaferro-specific rulings**, and
they are the reason this entry is not a bare adoption of D82:

- **The CppUTest derivation is a recorded doctrine exception.** The
  adapter's grammars and the guest makefile's flags follow CppUTest
  v4.0's own source (P9) — reading an upstream implementation, which
  the clean-room doctrine otherwise forbids. It stands on the licence
  instead: BSD-3-Clause (verified at the v4.0 tag, file by file) is
  sublicensable, so even read as a derivation it survives the
  commercial bar with attribution carried. The exception is
  version-pinned: re-deriving against newer CppUTest source re-opens
  the licence question at that version.
- **Nothing GPL may enter SUITE.EXE, so the guest fixture stays
  BSD.** The checked-in binary statically embeds Open Watcom's DOS
  runtime, and the Sybase Open Watcom Public License 1.0 has **no
  runtime exception** — compiled object code is expressly Covered
  Code, the licence is GPL-incompatible, and no settled reading
  brings a compiler runtime under GPL's system-library exception. A
  GPL SUITE.CPP would therefore have made the binary arguably
  undistributable. Ruled: `SUITE.CPP` and the guest makefile are
  deliberately BSD-3-Clause in a GPL repository; the binary is
  annotated as the aggregate it is (Paul + CppUTest + Sybase); the
  makefile carries the licence's §2.2(d) source-availability notice;
  `LICENSES/Watcom-1.0.txt` ships. **Weighed and declined:**
  converting the fixture to GPL anyway (rests a distribution right
  on an unsettled system-library argument); dropping the checked-in
  binary (the reproducible-fixture arrangement predates this entry
  and licensing is no reason to lose it); waiting on Open Watcom's
  in-progress relicensing to Apache-2.0-with-LLVM-exception (not
  completed, and the project does not vet against futures).
- **Reliquary's standing is owner-relicensable, not a tier.**
  Imported GPL code is refused from any other author; reliquary (GPL
  from its 0.1.0.dev5; the pinned dev4 predates that, D4) is
  dependable solely because both projects are the same owner's under
  the same assignment policy, so any relicensing is one decision
  licensing both. The vendored assets (P17, D20) are the same fact in
  file form: copied from the same owner's codex, so no third party
  exists. Both reasons are recorded in AGENTS.md because they fail
  differently — the standing dissolves if reliquary ever holds code
  its owner cannot relicense.

**Folded into:** [../LICENSE](../LICENSE), `../LICENSES/`,
[../REUSE.toml](../REUSE.toml), [../pyproject.toml](../pyproject.toml),
[../CLA.md](../CLA.md), [../CONTRIBUTING.md](../CONTRIBUTING.md),
[../README.md](../README.md), [../AGENTS.md](../AGENTS.md) (the
"Licensing" and "Prior art and external references" sections, the
normative home of the tiers and the reference standings),
[../CHANGELOG.md](../CHANGELOG.md),
[../tests/integration/guest/](../tests/integration/guest/), and the
SPDX header of every file in the repository.

### D20 — Testaferro installs its own FreeDOS, once

**Decided** owner, 2026-07-28. **Supports** U2, U4 (pledged), P17, P8.

**Zero configuration had never worked, and nothing had ever looked.**
The image it downloaded was FreeDOS 1.4's FloppyEdition boot floppy,
which boots the *installer*: a language menu, then "Do you want to
proceed [Y,N]?", and never a DOS prompt. Every guest command therefore
waited for a prompt that was not coming and timed out. U2 and U4 both
promise that a suite executable and nothing else runs; the first
integration run ever made found that it could not have.

**The image is now Testaferro's own, installed rather than
downloaded.** The recipe — reliquary's codex `freedos` blueprint and
its install script — is **vendored into `src/testaferro/assets/`** and
read from there, so nothing about the environment Testaferro offers by
name resolves out of the provider's codex at run time (P17). The
install runs **once**, into the cache; every guest session afterwards
layers a `difference` overlay over the result, so no session can write
into the copy they all share. It took 326 seconds and produced 13MB.

**D10 is not overruled.** What it declined was reading `freedos` as
the codex install recipe *per session* — "an install per session is
not a price a test run pays" — and that stands unchanged: a run
attaches a disk that already exists. What is new is only that the
disk is one Testaferro built rather than one it fetched.

**The consequence is recorded rather than left to be discovered: zero
configuration has left the cheap half of P10's line.** A layered
system drive materializes through an external image tool and the
system itself materializes through a guest install, so the
zero-configuration path is no longer something the unit tier may walk.
Cases that were about Testaferro's own bookkeeping now declare a boot
image and stay cheap. This is not a shortfall against P10 — that
entry forbids the unit tier starting a guest and this is the boundary
moving, not the rule.

**The blast radius grew, so it is guarded.** The old default was a
download and the case exercising it mocked `reliquary.fetch_media`;
the day the default became an install, that stopped being the seam and
nothing failed — a unit run simply installed an operating system.
`tests/test_reliquary.py` now refuses `_build_default_image` at module
scope, so the next such slip fails on the spot instead of taking five
minutes quietly. AGENTS.md already recorded one incident of this exact
shape; this is the second.

**The work drive is D:.** With the system on `hdd0`, the work drive
takes the next slot, and `_work_drive()`'s one-volume-per-disk
assumption — flagged in AGENTS.md as unverified past the first disk —
is now exercised by a real guest and correct.

**Recorded because the surface is enumerated.** The **cache location
and layout** is the sixth interface, and what Testaferro puts there
changed: `boot.img` becomes `freedos.qcow2`, and
`stop(clear_downloads=True)` now discards an install rather than a
download — minutes to replace, not seconds. The **embedding API**'s
`boot_image=` is untouched and still boots a tester's own floppy
(U3); what changed is only what happens when nobody says.

**Weighed and declined:** answering the installer's prompt with `N`,
which does reach `A:\>` — I tried it. It works today and makes the
curated environment depend on an installer's wording, which a FreeDOS
release can move under us; P17 says what Testaferro offers,
Testaferro authors, and "boots an installer and declines it" is not
that. Also declined: publishing a prebuilt image for consumers to
download, which is faster on first use and costs a hosting decision
and an artifact to keep in step; it stays available if the install
proves slow in practice.

**Folded into:** [../src/testaferro/assets/](../src/testaferro/assets/),
[../src/testaferro/reliquary.py](../src/testaferro/reliquary.py),
[../tests/test_reliquary.py](../tests/test_reliquary.py),
[../pyproject.toml](../pyproject.toml), [../README.md](../README.md),
[../AGENTS.md](../AGENTS.md), [../CHANGELOG.md](../CHANGELOG.md),
[proposed/ARCHITECTURE.md](proposed/ARCHITECTURE.md) (the sixth
surface).

### D19 — A guest's own words, never a traceback through the courier

**Decided** owner, 2026-07-28. **Supports** U4 (pledged), P4.

U4 promises that a trial "does not fail blind": a suite that boots
nothing, or whose output no framework adapter recognizes, is reported
by what the guest actually showed. It was not built. A grammar's
`ValueError` escaped both entry points, so a developer trying a suite
for the first time met three frames of Testaferro's internals with
the guest's one useful line buried under them — and pytest's short
summary, which quotes only a report's first line, dropped that line
entirely. The fix states the contract the defect revealed had never
been stated.

**Three parties, and each says only what it knows.** The **adapter**
states its reason and does not quote the caller's text back: it never
saw the guest and cannot say where the text came from, which is D17's
reasoning about quoting applied to provenance, and the caller passed
that text in and still holds it. The **composition** (`SuiteBackend`)
is the only place both halves of the exchange are in hand — argv out,
text back — so it is where a refusal becomes a `GuestOutputError`
carrying both. The **entry point** renders it, through the one
spelling both share in `items.py`, beside `failure_text()`.

**The report leads with the reason and ends with the screen**, with a
line between them saying outright that what follows is what the guest
showed in response. Leading with the reason is forced by pytest:
the short summary quotes the first line only, so that line has to be
the one worth reading alone. A collector reports through
`Collector.CollectError` and an item through the existing
`GuestTestFailure`, which are different pytest mechanisms for the
same rule — and neither prints a frame.

**Recorded because the surface is enumerated.**
[proposed/ARCHITECTURE.md](proposed/ARCHITECTURE.md) names "the shape
of a guest failure's report" inside the fifth interface, so this is
not housekeeping whatever its diff, and it takes the landing steps in
[INTERFACES.md](INTERFACES.md). Two surfaces move: the fifth, and the
first — a framework adapter is usable on its own (U6), so what its
refusals say is part of the embedding API. No amendment was needed:
U4 already demanded this, which is what made the shortfall unbuilt
work rather than an argument to have.

**Weighed and declined:** keeping the text inside the adapter's own
message and having the entry point print only that. It fixes the
traceback and leaves the adapter presenting a guest it has never seen,
which is exactly the boundary D17 drew. Also declined: reporting
through an exception subclass so the short summary keeps its
`reprcrash`. `CollectError` gives no summary text at all, which is the
trade Testaferro already makes for ordinary guest failures — one
convention for both beats a summary line for one of them.

**Folded into:** [../src/testaferro/backend.py](../src/testaferro/backend.py)
(`GuestOutputError`), [../src/testaferro/suite.py](../src/testaferro/suite.py),
[../src/testaferro/items.py](../src/testaferro/items.py)
(`guest_output_text()`),
[../src/testaferro/cpputest.py](../src/testaferro/cpputest.py),
[../src/testaferro/plugin.py](../src/testaferro/plugin.py),
[../src/testaferro/facade.py](../src/testaferro/facade.py),
[../AGENTS.md](../AGENTS.md), [../CHANGELOG.md](../CHANGELOG.md),
[pledged/USE-CASES.md](pledged/USE-CASES.md) (U4's built-so-far note).

### D18 — A suite names a test environment; D3's pair is retired

**Decided** owner, 2026-07-28. **Supports** P1, P2 (pledged by this
entry). Overrules D3.

**The amendment is the argument** ([INTERFACES.md](INTERFACES.md)),
and this is the hard case that rule exists for: the vocabulary
Testaferro speaks was settled by D3, so nothing about it could be
argued as a feature on its own merits. P1 and P2, amended and argued
in [proposed/](proposed/), have won and move to
[pledged/ARCHITECTURE.md](pledged/ARCHITECTURE.md).

**P1 — the provider is an *execution* provider.** D3-era wording said
"guest-machine provider", which excludes half of what the axis is for:
wine and dosbox run a program without booting a machine at all. The
layer is named for what it does. Everything D1 refused it still
refuses, verbatim.

**P2 — a suite names a test environment.** One noun replaces D3's
pair. A **test environment** is what a suite runs in: a standard one
Testaferro authors and names, or a custom one the tester declares as a
choice of provider plus that provider's configuration. `platform` goes
back to being what it always was — a field in an authored blueprint,
the provider's word, passing through untouched (P3, D4) — rather than
a concept a consumer writes in.

**What this does not do is ration precision.** A custom environment
goes as deep as the provider does: a complete blueprint, its drives,
its provisioning scripts, its `backend-settings`, carried through for
the provider to validate. The boundary is vocabulary, not reach —
Testaferro names providers and never what one drives, interpreting no
field below the provider's own. An earlier draft of P2 said "and
nothing underneath one", which read as a limit on the tester rather
than on Testaferro, and was struck before this pledge.

**D3 retires** to the retired section, its text intact. Note what
survives it: its *weighed and declined* clause refused emulator names
in the consumer-facing surface, and that refusal is not loosened here
— it is strengthened, since D16 has since taken the emulator out of
Testaferro's own naming too.

**Pledged severed**, on the reading D13 used for U4. Both entries cite
drafted material — P3, P8, P17, U9 — and the map's rule against a
pledged item resting on a proposed one tests **completion**, not
citation. Each of those names behaviour the code ships today:
pass-through is honored by `machines.py`, zero configuration by the
inference path, the authored catalog by `catalog.py` and its guard
test, and `machine="freedos"` resolves since F7. U7 is cited only to
illustrate how deep a provider document may go, which blueprint
pass-through already allows — `scripts` is expressible in
`testaferro.ini` today.

**Two consequences, recorded rather than left to be discovered.**
Neither principle is *honored* yet: the code still says `platform=`
and `machine=`, so both sit pledged and unarmed, and arming waits on
F10 with every residue filed in the same change. And this reaches a
**pledged use case**: U4 leans on U3's "selects the same machine", so
that clause moves when the vocabulary does — the cost D13 recorded for
reshaping what U4 rests on, now incurred deliberately.

**Weighed and declined:** keeping D3 and adding *environment* beside
*platform* and *machine*, so nothing already written would need
changing. It buys compatibility with a vocabulary the project has
decided is wrong, and leaves two names for one thing — which is the
condition D15 was just spent removing elsewhere. Also declined:
pledging F10 in the same act. The bound bites at the pledge and F10 is
flagged too large; cutting it is its own decision, and this one is
about the vocabulary rather than the work.

**Folded into:** [pledged/ARCHITECTURE.md](pledged/ARCHITECTURE.md)
(P1, P2), [proposed/ARCHITECTURE.md](proposed/ARCHITECTURE.md) (the
seams, the interface enumeration's note),
[proposed/FEATURES.md](proposed/FEATURES.md) (F10),
[../AGENTS.md](../AGENTS.md), D3 (retired).

### D17 — Argv crosses the framework seam as tokens

**Decided** owner, 2026-07-28. **Supports** P4, U6 (drafted).

A framework adapter's argv builders return a **sequence of tokens**,
and whoever executes spells the command line: the reliquary binding
joins them for its DOS guest, the host-twin enumerator splats them
into `subprocess.run`.
Ruled in the course of fixing the defect underneath — the binding
joined the adapter's *string* with `" ".join(args)`, which iterates
characters, so every guest operation asked for `SUITE.EXE - v` and a
single-test run for `SUITE.EXE - v   - s g   V r i n g`. The contract
had never been stated in either direction, so the fix had to state it
before it could pick a side.

The side is P4's. An adapter that is "argv and grammar only", and
never learns how the output was obtained, cannot also know how a
command line is quoted — a string makes it decide anyway, on behalf
of a runner it deliberately knows nothing about, while a sequence
leaves the spelling to the one party that knows it is DOS. The
string had already been paying for that: `plugin.py` split one back
apart with `shlex.split()` to run a host-built twin, a round trip
that exists only because the wrong side had spoken first.

**Recorded because the surface is enumerated.**
[proposed/ARCHITECTURE.md](proposed/ARCHITECTURE.md) names the
framework adapter modules "usable on their own" inside the first
interface, the embedding API, so a change to a public return type
there is not housekeeping whatever its diff, and takes the landing
steps in [INTERFACES.md](INTERFACES.md). That first interface is the
only one touched: the `Backend` ABC's five operations are unchanged,
the run callable stays an internal composition seam rather than a
public runner contract (D1), and no machine declaration, item id or
cache path is involved.

**Weighed and declined:** keeping the string and having the binding
append it whole. It fixes the same defect in one line, but leaves
`argv` naming something that is not argv, leaves each caller to guess
whether to split it, and leaves the quoting question with the module
least equipped to answer it.

**Folded into:** [../src/testaferro/cpputest.py](../src/testaferro/cpputest.py),
[../src/testaferro/suite.py](../src/testaferro/suite.py),
[../src/testaferro/reliquary.py](../src/testaferro/reliquary.py),
[../src/testaferro/plugin.py](../src/testaferro/plugin.py),
[../AGENTS.md](../AGENTS.md), [../CHANGELOG.md](../CHANGELOG.md).

### D16 — A binding is named for the provider it binds

**Decided** owner, 2026-07-28. **Supports** P1, P2 (drafted, as
amended). Closes the open question "Whether the QEMU binding module is
renamed for the platform it binds."

**It is renamed, and for neither of the things that question
offered.** `testaferro/qemu.py` becomes `src/testaferro/reliquary.py` and
`QemuSuiteBackend` becomes `ReliquarySuiteBackend`, because the module
was named for something it never touches: every call in it is a
reliquary call, and QEMU is what reliquary drives — a layer below the
one Testaferro talks to. The question had asked whether to name it for
the *platform* instead (`dos.py`); that is the other thing it is not.
A platform is what a suite is built for, while a binding is the seam
to whoever runs it, and those are different axes — one provider will
bind several platforms, and one platform will be served by several
providers (D11). So `_PLATFORM_BINDINGS` becomes
`_PLATFORM_PROVIDERS`: which provider runs a platform today, keyed
that way until the vocabulary work makes the provider the thing a
tester names.

**Testaferro names providers and never what is under them.** The
distinction the owner drew is the operative one: reliquary, vagrant,
dosbox and wine are things this project may know about; QEMU is
reliquary's implementation detail and belongs in no name, docstring or
error message here. So the rename came with a sweep — the package
docstring, the facade's, the error a non-DOS declaration raises, the
distribution's own description and keywords, and the guidance.

**Two mentions are kept deliberately**, and neither makes QEMU
Testaferro's vocabulary: [../README.md](../README.md)'s "Where it
fits" section, which describes what *other* projects do (pytest-cpp's
qemu harness, pytest-embedded's QEMU service, Go's vmtest), and the
`backend-settings` fixture in the project-config tests, which is a
reliquary blueprint field carrying a tester's own authored value
through untouched (P3) — a passenger, not a word this project speaks.

**This did not wait for F10.** The vocabulary feature is about what a
*tester* names, and needs its principle amendments pledged first; this
is an internal module naming what it actually calls, which is true
today under P1 and D11 whatever the consumer-facing vocabulary
becomes. F10 keeps the rest — `provider=` in the declaration, the
table keyed by provider — and no longer carries this rename.

**Weighed and declined:** `testaferro/providers/reliquary.py`, a
package anticipating siblings. With one provider it is structure built
ahead of a second concrete implementation, which is the shape D1
refused; the directory costs nothing to introduce the day a second
binding exists. Also noted rather than declined: inside
`src/testaferro/reliquary.py` the name `reliquary` refers to the provider
distribution, absolute imports making that unambiguous to Python
though not instantly to a reader — so the binding's own tests import
it as `binding` and say which is which.

**Folded into:** `src/testaferro/reliquary.py`,
`src/testaferro/resolution.py`, `src/testaferro/__init__.py`,
`src/testaferro/facade.py`, `tests/test_reliquary.py`,
[../AGENTS.md](../AGENTS.md), [../README.md](../README.md),
[../CONTRIBUTING.md](../CONTRIBUTING.md),
[../pyproject.toml](../pyproject.toml),
[proposed/FEATURES.md](proposed/FEATURES.md) (F10).

### D15 — A guest session, a run, and pytest's session are three things

**Decided** owner, 2026-07-28. **Supports (none)** — a naming choice,
demanded by no use case and no principle. Recording it anyway,
because it renames two of the five operations on an enumerated
interface and relabels the cache layout, and because the confusion it
removes is the kind that returns silently if nobody wrote down why.

**"Session" had three claimants**, two of them Testaferro's own and
nesting inside each other:

- **pytest's session** — the whole run. Not ours, unrenameable, and
  already in our code as the hook `pytest_sessionfinish`.
- **The backend's per-suite lifecycle** — `start_session()` /
  `stop_session()` on the `Backend` ABC: one guest up and able to
  answer.
- **The shared area opened by `testaferro.start()`** — one staged
  image and one sweep area serving many suites, i.e. one per pytest
  run, spelled `_session` in the binding and `sessions/` in the
  user's cache.

So a reader met the same word for the run, for the area the run
shares, and for one guest inside it — and the vision had already
absorbed the confusion: U8 reads "The cycle is the pytest session",
using a third word for the middle thing in the same sentence as the
word for the outer one.

**The middle thing is a guest session**, and the ABC operations are
`start_guest()` / `stop_guest()`. "Guest" is Testaferro's established
consumer-facing prefix — `guest_suite()` is the public entry point,
the items are guest tests, a failure is a guest failure — so this is
no new vocabulary, and it survives the amendments to P1 and P2, which
retire *machine* but leave *guest* untouched. "Session" is kept
rather than replaced because it is the right English for a span
during which something is available for use, which is exactly what
lies between the two calls; the ambiguity was never the word but the
missing qualifier. It also survives U8: for a persistent machine the
guest session simply *becomes* the whole run rather than one suite —
same concept, wider extent.

**The outer thing is a run**, and stops being called a session at
all, because it is not one — it is shared setup for a run.
`testaferro.start()` / `stop()` keep their names, having never
carried the word.

**The cache layout follows the vocabulary** (the sixth interface):
`runs/run-*/` is one Testaferro run, `guests/guest-*/` inside it is
one guest session's home, and a guest belonging to no run sits in
`guests/` at the cache root. What were called "run homes" were never
runs' — each is one guest's — so `--testaferro-keep-run-home` becomes
`--testaferro-keep-guest-home`, and `cache.release_run_home()` and
friends follow. Existing caches keep an orphaned `sessions/` tree;
that directory is disposable state by its own contract, so it is
noted in the changelog rather than migrated.

**Weighed and declined:** `machine_session` / `machine_cycle`, which
name what the P1 and P2 amendments are retiring — wine and dosbox run
a program without booting a machine — and would have to be re-picked
at F10. Also declined: `guest_cycle`, "cycle" suggesting a repeating
round rather than a span something is available for. Also declined:
leaving the outer span a "session" and disambiguating only the inner
one, which fixes the collision a reader hits and leaves the one a
maintainer hits.

**Folded into:** `src/testaferro/backend.py` (the ABC),
`testaferro/qemu.py`, `src/testaferro/cache.py`, `src/testaferro/facade.py`,
`src/testaferro/plugin.py`, [../README.md](../README.md),
[../AGENTS.md](../AGENTS.md), [../CHANGELOG.md](../CHANGELOG.md).

### D14 — A lifecycle act earns no decision entry

**Decided** owner, 2026-07-28. **Supports** P14, P15 (drafted).

The cross-project standard this machinery instantiates (D7, D8) has
amended what earns a place in this record, and the amendment is
adopted here. **Proposing, pledging, promoting and delivering earn
no entry**: location already states the status and the commit that
moves the item is the record, so an entry restating the act is the
separate register the machinery refuses to keep. Delivery evidence —
the clause-by-clause case that a use case is actually met — belongs
in the moving commit's message, where the act it evidences is.

What still earns an entry is **adjudication**. A decision whose
conclusion pledges something records the argument and stands. A
ruling made in an act's course — a contested clause reading, a scope
call, a pledge found accidental and withdrawn — is recorded slim, as
the ruling, never as the promotion narrative around it.

**D13 stands as written**, under the form in force when it was
written earlier the same day, and is annotated rather than
rewritten: entries keep the spellings of their time. Its rulings are
exactly what this entry keeps — U4 severed from the drafted use
cases it cites, P16 pledged rather than severed, the plugin's
auto-load, F7 and F8 unsplit — while its opening paragraph, which
narrates the promotion itself, is what this rule now leaves to
[pledged/](pledged/) and to the commit that moved them.

**Weighed and declined:** rewriting D13 slim. It would tidy away the
one form the amended rule exists to prevent, at the cost of the
record's fidelity to its own moment; the annotation names the form
without erasing that it was used. Also declined: reading the rule
back over D1–D12, none of which records a lifecycle act.

**Folded into:** the record's discipline above,
[README.md](README.md), [../AGENTS.md](../AGENTS.md), D13
(annotation).

### D13 — U4 is pledged severed, with P16, F7 and F8; the plugin auto-loads

**Decided** owner, 2026-07-28. **Supports** U4, P16 (pledged by this
entry).

The first promotion under the model D7 adopted: U4, P16, F7 and F8
move out of [proposed/](proposed/) into [pledged/](pledged/), and
the commit that moves them is the record of the pledge. [Since D14 a
promotion earns no entry of its own; what an entry records is the
rulings below.] They move unmodified but for the one thing F8 left
open, settled below.

**U4 is pledged severed.** It cites U1, U2 and U3, which stay
drafted, and the map ([README.md](README.md)) makes a pledged item
resting on a proposed one a flaw rather than a reference. The test
that rule states is **completion**, not citation, and every clause
U4 leans on names behaviour the code ships today: zero configuration
boots a cached image, a `testaferro.ini` beside the project selects
a declared machine, and the embedding API is the first enumerated
interface. U1, U2 and U3 sit in `proposed/` because D7 drafted the
whole vision at once *after* the code existed — not because the
project is undecided about them — so U4's citations locate shipped
behaviour rather than awaiting a second verdict. Nothing pledged
here waits on anything proposed.

Two consequences, recorded rather than left to be discovered.
**Reshaping U2 or U3 now costs something**: both remain reshapable —
only an in-force entry may not be — but the clauses U4 leans on
carry a pledge now, so changing them re-opens one. And **severance
changes the pledge, not the arming**: U4 reaches root
`USE-CASES.md` only on full delivery, behind the same end-to-end
proof (F6) that U1, U2 and U3 wait on, so it will most likely arm
alongside them.

**P16 is pledged, not severed**, because the argument that carried
U4 does not transfer: P16's subject is the plugin's option surface,
which does not exist, so no shipped behaviour stands behind it. F8's
settled design is written against it — options and ini keys as
kebab-case spellings of the declaration vocabulary — and a pledged
feature's design wants a pledged rule behind it. P16 spans three
surfaces over two interfaces, the embedding API and `testaferro.ini`
being two spellings of one declaration, so the plugin's options join
no new surface ([proposed/ARCHITECTURE.md](proposed/ARCHITECTURE.md)
"The interfaces").

**The plugin auto-loads**, through a `pytest11` entry point, so
`pytest tests/suite.exe` works the moment the distribution is
installed. That is F8's one decide-at-the-pledge item. U4 promises
pytest's own command with no wrapper, and the `pytest-` distribution
category (D12) means exactly this; what makes
installation-is-activation safe is F8's claiming policy — a tree
scan claims only what a mask or `testaferro.ini` opts in — rather
than the plugin being off.

F7 and F8 are pledged **unsplit**: each is one bounded push, the
execution machinery they re-present already exists, and neither
carries the "too large" flag F6 does.

**Weighed and declined:** pledging U1, U2 and U3 alongside U4, which
would have dissolved the up-reference by making it moot. They are
built and awaiting proof rather than work, so the shelf that means
*owed and not yet delivered* is the wrong place to park them, and
the severance argument holds without them. Also declined: leaving
P16 in `proposed/` to arm straight into root `ARCHITECTURE.md` when
F8 lands honoring it — legitimate under the compression rule, but it
leaves a pledged feature's design citing a drafted principle for the
whole of the work. Also declined: an explicit `-p testaferro`
opt-in, which changes no venv on installation but puts a flag in
front of the first command U4 is about.

**Folded into:** [pledged/USE-CASES.md](pledged/USE-CASES.md),
[pledged/ARCHITECTURE.md](pledged/ARCHITECTURE.md),
[pledged/FEATURES.md](pledged/FEATURES.md), the banners under
[proposed/](proposed/), [README.md](README.md),
[../AGENTS.md](../AGENTS.md).

### D12 — Testaferro is a pytest plugin, distributed as pytest-testaferro

**Decided** owner, 2026-07-28. **Supports** U1, U4 (drafted).

The self-description moves from "a pytest facade" to **a pytest
plugin**: after D9 the plugin is how nearly every consumer meets
the project, and the category is real — the plugin list, the
`Framework :: Pytest` classifier, the `pytest-` distribution
prefix. Naming is two-level, the convention pytest plugins use
(pytest-testinfra over import `testinfra` is the exact precedent):
the **distribution is `pytest-testaferro`**, while the import, the
plugin name, the cache directory, the repository, and the identity
all stay `testaferro`. The reframe sharpens the name rather than
retiring it: a testaferro is a front man, and the plugin is
precisely pytest presenting, under its own name, tests another
machine ran. What exceeds a plugin is stated rather than lost: the
embedding API is the same plugin's programmatic layer, the
framework adapters stay usable standalone (U6), and the lifecycle
CLI (F2) is deliberately not pytest.

The bare `testaferro` name on PyPI (a few dev builds) is retired
testinfra-style, not vacated: one final tombstone release,
**0.1.0.dev4** (authored in `tombstone/`), whose description says
renamed — install `pytest-testaferro` — carrying `Development
Status :: 7 - Inactive` and a dependency on the new distribution
so stale pins resolve to the real thing; earlier releases are
yanked and the project archived on the web side. Deleting the name
was declined: a freed name with install history is a supply-chain
hazard, and what PEP 541 frowns on is speculative reservation, not
an explicit signpost.

**Weighed and declined:** keeping distribution `testaferro` with
only the trove classifier for discoverability (the plugin list and
the eye both key on the prefix); renaming the project outright
(the identity is apt — sharpened by the plugin reframe — and the
org naming coheres); deleting the PyPI name (above).

**Folded into:**
[proposed/ARCHITECTURE.md](proposed/ARCHITECTURE.md) ("What
Testaferro is"), [../README.md](../README.md),
[../pyproject.toml](../pyproject.toml), `tombstone/`,
[../CHANGELOG.md](../CHANGELOG.md).

### D11 — Providers are Testaferro's axis, named in the declaration

**Decided** owner, 2026-07-28. **Supports** P1, P2, P3 (drafted, as
amended).

The vision names more guest-machine providers than reliquary —
vagrant and kin as possibilities — and the axis is **Testaferro's
own**: reliquary and vagrant occupy the same space, so a machine
uses one *or* the other, and a future provider is a Testaferro
binding rather than capability pushed upstream — reliquary is
already large, and growing it into a portmanteau of runners serves
neither project. The provider is nothing Testaferro hides: the
tester declares it (`reliquary` today, the default and the only
supported one), and a tester who wants specific machines from a
provider passes that provider's own configuration through —
Testaferro carries it untouched, exactly as it carries reliquary
blueprints (P3, generalized). Suites still name platforms and
machines only; the declaration is the one place a provider appears
(P2).

**D1 holds, read in its own vocabulary.** In D1, "runner" named
the direct-virtualization piece itself — QEMU lifecycle, machine
configuration, provisioning, guest control — and its refusals are
about not building or abstracting that piece here: no structural
runner contract, no conformance kit, no mirrored configuration
hierarchy, no abstraction ahead of concrete need. All of that
holds unchanged; Testaferro still builds none of it (D2). What D1
did not contemplate is more than one external provider of the
piece it refused to build, and this entry adds that recognition:
the "no `runner=` override" clause refused a caller-supplied
virtualization contract, not a choice among Testaferro's own
provider bindings. The annotation at that clause points here so
the narrower reading is the recorded one. The seam a provider
implements is the `Backend` ABC D1 already blessed, any richer
interface is derived from concrete implementations when one
actually arrives, and construction still waits on a second
concrete provider.

**Weighed and declined:** placing machine-shaped providers in
reliquary as its backends, keeping Testaferro provider-blind. It
reads clean from Testaferro's side and bloats reliquary from its
own, and the two projects' owner prefers the seam here. Also
declined: building the provider dimension now — a seam with one
implementation, the exact shape D1 killed.

**Folded into:** [proposed/ARCHITECTURE.md](proposed/ARCHITECTURE.md)
(P1, P2, P3), D1 (annotation).

### D10 — A machine name resolves to declarations, then the standard catalog

**Decided** owner, 2026-07-28. **Supports** U2, U3, U9 (drafted).
Closes the open question "What a machine name resolves to."

`machine="freedos"` resolves against the project's declared
machines first (`config()` / `testaferro.ini`), then against a
curated catalog of **standard environments** Testaferro itself
authors — "freedos" naming today's zero-configuration machine,
siblings arriving as guests grow. Never the user's reliquary home:
D6's hermeticity holds, and a test run depends only on state
Testaferro authored or the project checked in.

**Weighed and declined:** resolving names from the user's reliquary
home — re-declined on D6's unchanged ground. Also declined: reading
"freedos" as reliquary's codex install recipe — an install per
session is not a price a test run pays, and install recipes become
reachable only where a machine persists (U8, F2).

**Folded into:** [proposed/USE-CASES.md](proposed/USE-CASES.md)
(U9), [proposed/FEATURES.md](proposed/FEATURES.md) (F7); the open
question retires into this entry.

### D9 — The command-line surface is a pytest plugin

**Decided** owner, 2026-07-28. **Supports** U1, U4 (drafted).

The way to run a guest suite from a command line is pytest itself:
a collection plugin claims suite executables via
`pytest_collect_file`, so `pytest tests/suite.exe` is a standard
pytest execution — no wrapper, no second reporter, no second
executable for running tests. **pytest-cpp** (MIT) is the reference
standard for the pytest-facing half: mask-gated tree scans,
always-claim for explicitly named files, framework facades,
per-test filter argv. Its `cpp_harness` options — wrapping
execution in qemu or wine for cross-compiled binaries — are the
degenerate form of the problem Testaferro exists for, and mark
exactly where the reference stops transferring: a command prefix
cannot carry a machine lifecycle. Where pytest-cpp probes binaries
by executing them, Testaferro declares or defaults — probing here
means booting a guest.

**Weighed and declined:** the wrapper CLI — retired F1's `run`
verb, which resolved a backend, generated a one-line module and
handed it to `pytest.main()`. Its own first principle — run pytest
so no second reporter can diverge — argues past itself: the plugin
removes the wrapper entirely, and `--snippet` and `--` forwarding
with it. A small lifecycle CLI survives for machine and cache
verbs (F2), which are not test runs.

**Folded into:** [proposed/USE-CASES.md](proposed/USE-CASES.md)
(U4), [proposed/FEATURES.md](proposed/FEATURES.md) (F7, F8),
[proposed/ARCHITECTURE.md](proposed/ARCHITECTURE.md) (P16 and the
interface note).

### D8 — The planning machinery realigns to the cross-project standard

**Decided** owner, 2026-07-28. **Supports** P14, P15 (drafted).

The governance model this project adopted (D7) is the one in force
across the owner's projects, and that standard moved after
Testaferro instantiated it. Three changes, taken together:

- **The second shelf is `pledged/`, and the lifecycle word with
  it**: *proposed, pledged, completed, rejected*. `accepted/` named
  an act, and both gates perform approvals — admitting a document to
  `proposed/` is one too — so a shelf named for an act claims a word
  the other gate still has to borrow. Both names now state what an
  item *is*: argued and binding nothing, or owed with no date
  attached. A pledge can therefore be wrong where bare agreement
  could not: an item nobody intends to deliver is withdrawn to
  `proposed/` or rejected outright, never left sitting. No directory
  moved on disk — `accepted/` had not been created yet — so the
  rename lands in prose alone.
- **The task queue is guarded by authority, not by the interface
  test.** [TASKS.md](TASKS.md) had read "work that changes an
  interface never belongs here", importing housekeeping's boundary.
  That boundary compensates for a class nobody with authority ever
  reviews; the task queue has its own guard — only authority writes
  to it, and entering an item *is* approving it — so reading the
  test across counts the same protection twice and turns away work
  authority has already approved. A small interface change may be a
  task, admitted on size and kind; the landing rules
  ([INTERFACES.md](INTERFACES.md)) bind it exactly as they bind a
  feature.
- **Promotion to the root runs on two bars.** A use case moves on
  *full* delivery. A principle moves on being honored *as a rule*,
  with every known residue filed as a defect in the same change —
  filing the residue is what converts a shortfall from unbuilt work
  into a bug, which is what arming means.

**Weighed and declined:** keeping the stricter task rule as a
deliberate local divergence. It would preserve a protection the
queue already has at its door, at the price of diverging from a
standard whose whole value is that an agent or contributor arriving
here already knows the rules (D7).

**Folded into:** [README.md](README.md), [TASKS.md](TASKS.md),
[INTERFACES.md](INTERFACES.md), the banners under
[proposed/](proposed/), [AGENTS.md](../AGENTS.md).

### D7 — Testaferro adopts the planning governance model, and keeps no roadmap

**Decided** owner, 2026-07-27. **Supports** P14, P15 (drafted).

The project's direction had accumulated in a single `ROADMAP.md`
mixing four different things: agreed-but-unbuilt capability, settled
design decisions, open questions, and small work items — with a
"milestone (low priority)" heading asserting an order the project
never actually committed to. It is replaced by this `planning/`
machinery, in which **location is the classification**: `proposed/`
is argued but not accepted, `accepted/` is approved and undelivered
[the second shelf is now `pledged/`, and the vocabulary with it —
D8], and the repository root carries what the code delivers today. The
same model is in force across the projects this owner controls, so
an agent or contributor arriving here already knows where to look.

**ROADMAP.md is retired**, and no successor is kept. A roadmap
promises an order and a time nothing else in this machinery commits
to, and it classifies by *when* where every other artifact here
classifies by *state*. Its content was distributed rather than
deleted: landed direction to [AGENTS.md](../AGENTS.md) and
[README.md](../README.md), unbuilt capability to
[proposed/FEATURES.md](proposed/FEATURES.md), settled decisions to
D1–D6 below, unsettled ones to Open questions above. The retired
file survives in git history.

**Weighed and declined:** keeping the roadmap alongside the new
machinery, as a reading convenience. It would have re-imported the
ordering claim through the back door, and left two places recording
the same direction with nothing deciding which wins.

**Folded into:** [README.md](README.md), [INTERFACES.md](INTERFACES.md),
[TASKS.md](TASKS.md), and the drafted vision under
[proposed/](proposed/).

### D6 — The reliquary context is hermetic, one per session

**Decided** owner, 2026-07-27. **Supports** U1, U2, P5 (drafted).

Each backend session pins `reliquary.Context(home_dir=…,
cache_dir=…, blueprints_dir=<session dir>, autoseed=False)` under
Testaferro's own cache, so resolution sees only what Testaferro
authored for that run — never the user's reliquary home and never the
built-in codex. The declaration is written into that private home as a
blueprint and the machine is created and booted from it there.

**Restated 2026-07-27** for reliquary 0.1.0.dev3, which retired
`assets=` — the single knob this decision was originally written
against. It had declared two things at once: where documents are read
from, and that the codex is out of reach. Those are now two axes, so
the pin names both. What the decision holds is unchanged; saying it
now takes two arguments rather than one.

**Weighed and declined:** resolving a blueprint by name from the
user's reliquary home. That would make a test run depend on state
Testaferro did not author and cannot sweep. It remains available as a
deliberate future decision — it is what the `machine="freedos"` open
question above turns on — not a default to drift into.

**Folded into:** `testaferro/qemu.py` (stated as an invariant in its
module contract), [AGENTS.md](../AGENTS.md).

### D5 — Testaferro supplies the work drive itself

**Decided** owner, 2026-07-27. **Supports** U1, U3 (drafted).
**Superseded** 2026-07-30 by the delivery of F4, whose design is
[proposed/design/test-placement.md](proposed/design/test-placement.md).
The surface no longer promises a drive; it promises a **location**,
and the suite is staged there at rest with reliquary's file verbs
between `create_machine` and `start_machine`. Both constraints named
below dissolved rather than transferring: staging happens after
materialization, so the attach-time snapshot rule is gone with the
drive that needed it, and the letter is **read off the created
machine** rather than mirrored — reliquary 0.1.0.dev6's
`describe_drives()` answers it, so the mirror this entry accepted as
a cost is deleted. What survives is the fallback: a machine offering
no writable room of its own still gets a Testaferro-supplied
directory-source drive, now an implementation detail rather than the
promise. The "eventual shape (F4)" this entry named is the shape
that landed.

The suite executable reaches the guest on a host-directory drive
that **Testaferro adds to the blueprint**, at the lowest free disk
slot, staging the executable into it before the machine boots.

**Weighed and declined:** requiring the blueprint to declare a
hostdir drive for Testaferro to copy into, which is how the original
design assumed insertion would work. Supplying the drive is strictly
better for the consumer: a declaration then says nothing about
testing, and a plain machine blueprint works unmodified. Two
constraints came with the choice — the backend snapshots a host
directory when the drive is attached, so staging cannot be lazy; and
Testaferro must name the drive letter the guest will give it, which
means locally mirroring reliquary's DOS letter-assignment rule until
reliquary exposes that mapping. A specified insertion point remains
the eventual shape (F4).

**Folded into:** `testaferro/qemu.py` (`_work_drive()` and its
cross-check test), [AGENTS.md](../AGENTS.md).

### D4 — A machine declaration is an authored reliquary blueprint

**Decided** owner, 2026-07-27. **Supports** U3, P3 (drafted).

Reliquary's `Runner`/`MachineConfig` layer — the layer Testaferro was
first built on — was removed in reliquary 0.1.0.dev2 and replaced by
blueprints and the machine lifecycle. `config()`, `testaferro.ini`
and `machine_config=` were moved onto blueprints directly: a
declaration *is* an authored blueprint document, and Testaferro
carries the JSON through untouched for reliquary to validate.

**Weighed and declined:** mirroring reliquary's schema in
Testaferro — validating fields, normalizing values, or restating the
document's shape. Passing it through means a new blueprint field is
expressible the day reliquary ships it, without a Testaferro change.
Only one normalization is kept, and deliberately: keys hyphenated in
the blueprint (`backend-settings`, `control-planes`) are written with
underscores in Python and INI and normalized on construction,
because neither host spelling admits a hyphen.

The same decision fixed reliquary's pin at an exact version. Its API
has already removed the layer Testaferro was built on once; a
floating requirement would break consumers without warning, so
moving the pin is a deliberate task rather than a chore.

**Folded into:** `testaferro/machines.py`, `testaferro/qemu.py`,
`pyproject.toml`, [AGENTS.md](../AGENTS.md), [README.md](../README.md).

### D2 — Guest-side mechanics belong to reliquary, never to Testaferro

**Decided** owner, 2026-07-18. **Supports** P1 (drafted).

Any guest-side agent or listener that handles execute requests
inside a VM belongs to reliquary. So do guest-OS platform workflows
beyond DOS — install media, unattended setup, platform-specific
completion detection, and the former win9x install/cache plans.
Testaferro binds a platform reliquary already supports, and the
binding is thin.

**Weighed and declined:** building any in-guest component in
Testaferro to make a workflow work sooner. It would duplicate the
runner's whole reason to exist and leave two projects owning guest
mechanics.

**Folded into:** [AGENTS.md](../AGENTS.md); the division of
ownership between the two projects.

### D1 — Reliquary is the sole guest-machine provider; no runner seam

**Decided** owner, 2026-07-18. **Supports** P1 (drafted).

Testaferro integrates directly with reliquary's blueprint and
machine-lifecycle interface. There is no `runner=` override
["runner" here is the virtualization piece itself, which Testaferro
still does not build; choosing among external providers of it is
D11's axis], no structural runner contract, no conformance kit, and
no mirrored configuration hierarchy. Reliquary owns QEMU lifecycle, machine
configuration and validation, provisioning, guest control,
completion detection, and all in-guest mechanics; Testaferro owns
executable-to-platform and machine selection, durable caches,
isolated per-session reliquary homes, getting the suite executable
into the guest, pytest sessions and parallelism, test-framework
composition, batching, and result replay. A prebuilt `Backend`
remains the custom escape hatch for a caller with a wholly different
execution mechanism, and is already the appropriate seam for one.

**Weighed and declined:** the `testaferro-runner-api` draft — a
protocol module, a configuration chain, a conformance kit and its
tests. With one implementation such a seam adds translation work
without providing variation or leverage. The dev2 migration tested
that position rather than overturning it: the removal of
`Runner`/`MachineConfig` was absorbed in two modules. The draft is
archived in [drafts/runner-api/](../drafts/runner-api/) as
historical reference, not planned work; reconsider extracting a
runner seam only if a second actual runner appears, and derive any
future interface from the concrete implementations then.

`SuiteBackend` may retain its internal runner-callable composition
for locality and testing without turning that callable into a public
runner contract.

**Folded into:** `testaferro/qemu.py`, `src/testaferro/suite.py`,
[AGENTS.md](../AGENTS.md).

## Retired decisions

Overruled or no longer relevant, kept intact for the record. A
retired decision binds nothing.

<!-- ### D<n> — <title>  *(retired: overruled by D<m>)* -->

### D3 — Platforms and test machines are the consumer's vocabulary  *(retired: overruled by D18)*

**Decided** owner, 2026-07-18. **Supports** U1, U2, U3, P2 (drafted).

Two separated concepts carry everything guest-related to the
consumer. A **platform** is a type — the OS family a suite is built
for ("dos", and later names as reliquary grows them) — knowing which
binary formats it can run and its default boot-media type. A **test
machine** is one named declaration carrying a platform. Several
machines may share a platform; an MZ executable maps to its *native*
candidate platforms and a unique configured machine wins, an
ambiguous or empty result raising and listing the choices. Zero
configuration keeps working: a platform offers an implicit machine
only when it can self-provision without options.

**Weighed and declined:** naming emulators in the consumer-facing
surface. QEMU is an implementation detail of a binding and never
appears in what a consumer writes; the facade's binding table keys
by platform name for that reason.

**Folded into:** `testaferro/machines.py`, `src/testaferro/facade.py`,
`src/testaferro/binfmt.py` (`Format.platform`), [README.md](../README.md).
