<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: BSD-3-Clause
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

- **What norms testaferro's interfaces.** The project holds no
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
- **What a machine name resolves to.** `machine="freedos"` (and a
  future `--machine freedos`) can mean the zero-configuration
  FreeDOS boot floppy that works today, or a named reliquary
  blueprint. The second reads better and is newly possible, but
  reliquary's codex `freedos` blueprint is an *install recipe* — a
  blank disk plus install and verify scripts — not a ready image, so
  it implies provisioning and machine reuse (F2), reinstalling
  FreeDOS per pytest run not being viable while the binding sweeps
  its whole run home at `stop_session()`. It also means opting into
  reliquary's home-mode asset resolution, which D6 deliberately
  avoids. Settled before F1 is built.
- **Whether testaferro needs a document format of its own.** A
  declaration already *is* an authored reliquary blueprint (D4), and
  `machine_config=` already accepts a whole blueprint document or a
  `.rlqb` path, so the original case for a testaferro-owned
  superset document has mostly dissolved. What it would still buy is
  testaferro-specific keys sitting beside the blueprint — reliquary's
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
- **Whether the QEMU binding module is renamed for the platform it
  binds.** The platform concept already keeps QEMU out of the
  consumer's vocabulary (P2); what remains is whether the internal
  module `testaferro/qemu.py` should be named for the platform (e.g.
  `dos.py`), leaving QEMU and reliquary entirely to the binding's
  implementation. Internal naming, so this touches no enumerated
  surface — but it is a rename with citations across
  [AGENTS.md](../AGENTS.md) and the tests, so it is worth deciding
  rather than drifting.

## Decisions

### D8 — The planning machinery realigns to the cross-project standard

**Decided** owner, 2026-07-28. **Supports** P14, P15 (drafted).

The governance model this project adopted (D7) is the one in force
across the owner's projects, and that standard moved after
testaferro instantiated it. Three changes, taken together:

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

### D7 — testaferro adopts the planning governance model, and keeps no roadmap

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
testaferro's own cache, so resolution sees only what testaferro
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
testaferro did not author and cannot sweep. It remains available as a
deliberate future decision — it is what the `machine="freedos"` open
question above turns on — not a default to drift into.

**Folded into:** `testaferro/qemu.py` (stated as an invariant in its
module contract), [AGENTS.md](../AGENTS.md).

### D5 — testaferro supplies the work drive itself

**Decided** owner, 2026-07-27. **Supports** U1, U3 (drafted).

The suite executable reaches the guest on a host-directory drive
that **testaferro adds to the blueprint**, at the lowest free disk
slot, staging the executable into it before the machine boots.

**Weighed and declined:** requiring the blueprint to declare a
hostdir drive for testaferro to copy into, which is how the original
design assumed insertion would work. Supplying the drive is strictly
better for the consumer: a declaration then says nothing about
testing, and a plain machine blueprint works unmodified. Two
constraints came with the choice — the backend snapshots a host
directory when the drive is attached, so staging cannot be lazy; and
testaferro must name the drive letter the guest will give it, which
means locally mirroring reliquary's DOS letter-assignment rule until
reliquary exposes that mapping. A specified insertion point remains
the eventual shape (F4).

**Folded into:** `testaferro/qemu.py` (`_work_drive()` and its
cross-check test), [AGENTS.md](../AGENTS.md).

### D4 — A machine declaration is an authored reliquary blueprint

**Decided** owner, 2026-07-27. **Supports** U3, P3 (drafted).

Reliquary's `Runner`/`MachineConfig` layer — the layer testaferro was
first built on — was removed in reliquary 0.1.0.dev2 and replaced by
blueprints and the machine lifecycle. `config()`, `testaferro.ini`
and `machine_config=` were moved onto blueprints directly: a
declaration *is* an authored blueprint document, and testaferro
carries the JSON through untouched for reliquary to validate.

**Weighed and declined:** mirroring reliquary's schema in
testaferro — validating fields, normalizing values, or restating the
document's shape. Passing it through means a new blueprint field is
expressible the day reliquary ships it, without a testaferro change.
Only one normalization is kept, and deliberately: keys hyphenated in
the blueprint (`backend-settings`, `control-planes`) are written with
underscores in Python and INI and normalized on construction,
because neither host spelling admits a hyphen.

The same decision fixed reliquary's pin at an exact version. Its API
has already removed the layer testaferro was built on once; a
floating requirement would break consumers without warning, so
moving the pin is a deliberate task rather than a chore.

**Folded into:** `testaferro/machines.py`, `testaferro/qemu.py`,
`pyproject.toml`, [AGENTS.md](../AGENTS.md), [README.md](../README.md).

### D3 — Platforms and test machines are the consumer's vocabulary

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

**Folded into:** `testaferro/machines.py`, `testaferro/facade.py`,
`testaferro/binfmt.py` (`Format.platform`), [README.md](../README.md).

### D2 — Guest-side mechanics belong to reliquary, never to testaferro

**Decided** owner, 2026-07-18. **Supports** P1 (drafted).

Any guest-side agent or listener that handles execute requests
inside a VM belongs to reliquary. So do guest-OS platform workflows
beyond DOS — install media, unattended setup, platform-specific
completion detection, and the former win9x install/cache plans.
testaferro binds a platform reliquary already supports, and the
binding is thin.

**Weighed and declined:** building any in-guest component in
testaferro to make a workflow work sooner. It would duplicate the
runner's whole reason to exist and leave two projects owning guest
mechanics.

**Folded into:** [AGENTS.md](../AGENTS.md); the division of
ownership between the two projects.

### D1 — Reliquary is the sole guest-machine provider; no runner seam

**Decided** owner, 2026-07-18. **Supports** P1 (drafted).

testaferro integrates directly with reliquary's blueprint and
machine-lifecycle interface. There is no `runner=` override, no
structural runner contract, no conformance kit, and no mirrored
configuration hierarchy. Reliquary owns QEMU lifecycle, machine
configuration and validation, provisioning, guest control,
completion detection, and all in-guest mechanics; testaferro owns
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

**Folded into:** `testaferro/qemu.py`, `testaferro/suite.py`,
[AGENTS.md](../AGENTS.md).

## Retired decisions

Overruled or no longer relevant, kept intact for the record. A
retired decision binds nothing.

<!-- ### D<n> — <title>  *(retired: overruled by D<m>)* -->
