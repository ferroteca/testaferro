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

## Decisions

### D21 — testaferro is GPL-3.0-only, relicensing is reserved, and contributions are assigned

**Decided** owner, 2026-07-29. **Supports** (none): no use case or
principle demands a licence, and the governing vision is silent on
ownership. Recorded because it constrains what may enter the codebase
forever afterward, which nothing else in this record would otherwise
state. The record was searched first and holds no prior licensing
entry; D1, D4, D20 and P17 bear on the vetting below and are cited
where they do.

**The licence is GPL-3.0-only, replacing BSD-3-Clause.** testaferro
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

**The vetting round produced three testaferro-specific rulings**, and
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

### D20 — testaferro installs its own FreeDOS, once

**Decided** owner, 2026-07-28. **Supports** U2, U4 (pledged), P17, P8.

**Zero configuration had never worked, and nothing had ever looked.**
The image it downloaded was FreeDOS 1.4's FloppyEdition boot floppy,
which boots the *installer*: a language menu, then "Do you want to
proceed [Y,N]?", and never a DOS prompt. Every guest command therefore
waited for a prompt that was not coming and timed out. U2 and U4 both
promise that a suite executable and nothing else runs; the first
integration run ever made found that it could not have.

**The image is now testaferro's own, installed rather than
downloaded.** The recipe — reliquary's codex `freedos` blueprint and
its install script — is **vendored into `testaferro/assets/`** and
read from there, so nothing about the environment testaferro offers by
name resolves out of the provider's codex at run time (P17). The
install runs **once**, into the cache; every guest session afterwards
layers a `difference` overlay over the result, so no session can write
into the copy they all share. It took 326 seconds and produced 13MB.

**D10 is not overruled.** What it declined was reading `freedos` as
the codex install recipe *per session* — "an install per session is
not a price a test run pays" — and that stands unchanged: a run
attaches a disk that already exists. What is new is only that the
disk is one testaferro built rather than one it fetched.

**The consequence is recorded rather than left to be discovered: zero
configuration has left the cheap half of P10's line.** A layered
system drive materializes through an external image tool and the
system itself materializes through a guest install, so the
zero-configuration path is no longer something the unit tier may walk.
Cases that were about testaferro's own bookkeeping now declare a boot
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
and layout** is the sixth interface, and what testaferro puts there
changed: `boot.img` becomes `freedos.qcow2`, and
`stop(clear_downloads=True)` now discards an install rather than a
download — minutes to replace, not seconds. The **embedding API**'s
`boot_image=` is untouched and still boots a tester's own floppy
(U3); what changed is only what happens when nobody says.

**Weighed and declined:** answering the installer's prompt with `N`,
which does reach `A:\>` — I tried it. It works today and makes the
curated environment depend on an installer's wording, which a FreeDOS
release can move under us; P17 says what testaferro offers,
testaferro authors, and "boots an installer and declines it" is not
that. Also declined: publishing a prebuilt image for consumers to
download, which is faster on first use and costs a hosting decision
and an artifact to keep in step; it stays available if the install
proves slow in practice.

**Folded into:** [../testaferro/assets/](../testaferro/assets/),
[../testaferro/reliquary.py](../testaferro/reliquary.py),
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
for the first time met three frames of testaferro's internals with
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
trade testaferro already makes for ordinary guest failures — one
convention for both beats a summary line for one of them.

**Folded into:** [../testaferro/backend.py](../testaferro/backend.py)
(`GuestOutputError`), [../testaferro/suite.py](../testaferro/suite.py),
[../testaferro/items.py](../testaferro/items.py)
(`guest_output_text()`),
[../testaferro/cpputest.py](../testaferro/cpputest.py),
[../testaferro/plugin.py](../testaferro/plugin.py),
[../testaferro/facade.py](../testaferro/facade.py),
[../AGENTS.md](../AGENTS.md), [../CHANGELOG.md](../CHANGELOG.md),
[pledged/USE-CASES.md](pledged/USE-CASES.md) (U4's built-so-far note).

### D18 — A suite names a test environment; D3's pair is retired

**Decided** owner, 2026-07-28. **Supports** P1, P2 (pledged by this
entry). Overrules D3.

**The amendment is the argument** ([INTERFACES.md](INTERFACES.md)),
and this is the hard case that rule exists for: the vocabulary
testaferro speaks was settled by D3, so nothing about it could be
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
testaferro authors and names, or a custom one the tester declares as a
choice of provider plus that provider's configuration. `platform` goes
back to being what it always was — a field in an authored blueprint,
the provider's word, passing through untouched (P3, D4) — rather than
a concept a consumer writes in.

**What this does not do is ration precision.** A custom environment
goes as deep as the provider does: a complete blueprint, its drives,
its provisioning scripts, its `backend-settings`, carried through for
the provider to validate. The boundary is vocabulary, not reach —
testaferro names providers and never what one drives, interpreting no
field below the provider's own. An earlier draft of P2 said "and
nothing underneath one", which read as a limit on the tester rather
than on testaferro, and was struck before this pledge.

**D3 retires** to the retired section, its text intact. Note what
survives it: its *weighed and declined* clause refused emulator names
in the consumer-facing surface, and that refusal is not loosened here
— it is strengthened, since D16 has since taken the emulator out of
testaferro's own naming too.

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

**Folded into:** [../testaferro/cpputest.py](../testaferro/cpputest.py),
[../testaferro/suite.py](../testaferro/suite.py),
[../testaferro/reliquary.py](../testaferro/reliquary.py),
[../testaferro/plugin.py](../testaferro/plugin.py),
[../AGENTS.md](../AGENTS.md), [../CHANGELOG.md](../CHANGELOG.md).

### D16 — A binding is named for the provider it binds

**Decided** owner, 2026-07-28. **Supports** P1, P2 (drafted, as
amended). Closes the open question "Whether the QEMU binding module is
renamed for the platform it binds."

**It is renamed, and for neither of the things that question
offered.** `testaferro/qemu.py` becomes `testaferro/reliquary.py` and
`QemuSuiteBackend` becomes `ReliquarySuiteBackend`, because the module
was named for something it never touches: every call in it is a
reliquary call, and QEMU is what reliquary drives — a layer below the
one testaferro talks to. The question had asked whether to name it for
the *platform* instead (`dos.py`); that is the other thing it is not.
A platform is what a suite is built for, while a binding is the seam
to whoever runs it, and those are different axes — one provider will
bind several platforms, and one platform will be served by several
providers (D11). So `_PLATFORM_BINDINGS` becomes
`_PLATFORM_PROVIDERS`: which provider runs a platform today, keyed
that way until the vocabulary work makes the provider the thing a
tester names.

**testaferro names providers and never what is under them.** The
distinction the owner drew is the operative one: reliquary, vagrant,
dosbox and wine are things this project may know about; QEMU is
reliquary's implementation detail and belongs in no name, docstring or
error message here. So the rename came with a sweep — the package
docstring, the facade's, the error a non-DOS declaration raises, the
distribution's own description and keywords, and the guidance.

**Two mentions are kept deliberately**, and neither makes QEMU
testaferro's vocabulary: [../README.md](../README.md)'s "Where it
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
`testaferro/reliquary.py` the name `reliquary` refers to the provider
distribution, absolute imports making that unambiguous to Python
though not instantly to a reader — so the binding's own tests import
it as `binding` and say which is which.

**Folded into:** `testaferro/reliquary.py`,
`testaferro/resolution.py`, `testaferro/__init__.py`,
`testaferro/facade.py`, `tests/test_reliquary.py`,
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

**"Session" had three claimants**, two of them testaferro's own and
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
`start_guest()` / `stop_guest()`. "Guest" is testaferro's established
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
`runs/run-*/` is one testaferro run, `guests/guest-*/` inside it is
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

**Folded into:** `testaferro/backend.py` (the ABC),
`testaferro/qemu.py`, `testaferro/cache.py`, `testaferro/facade.py`,
`testaferro/plugin.py`, [../README.md](../README.md),
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

### D12 — testaferro is a pytest plugin, distributed as pytest-testaferro

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
testaferro is"), [../README.md](../README.md),
[../pyproject.toml](../pyproject.toml), `tombstone/`,
[../CHANGELOG.md](../CHANGELOG.md).

### D11 — Providers are testaferro's axis, named in the declaration

**Decided** owner, 2026-07-28. **Supports** P1, P2, P3 (drafted, as
amended).

The vision names more guest-machine providers than reliquary —
vagrant and kin as possibilities — and the axis is **testaferro's
own**: reliquary and vagrant occupy the same space, so a machine
uses one *or* the other, and a future provider is a testaferro
binding rather than capability pushed upstream — reliquary is
already large, and growing it into a portmanteau of runners serves
neither project. The provider is nothing testaferro hides: the
tester declares it (`reliquary` today, the default and the only
supported one), and a tester who wants specific machines from a
provider passes that provider's own configuration through —
testaferro carries it untouched, exactly as it carries reliquary
blueprints (P3, generalized). Suites still name platforms and
machines only; the declaration is the one place a provider appears
(P2).

**D1 holds, read in its own vocabulary.** In D1, "runner" named
the direct-virtualization piece itself — QEMU lifecycle, machine
configuration, provisioning, guest control — and its refusals are
about not building or abstracting that piece here: no structural
runner contract, no conformance kit, no mirrored configuration
hierarchy, no abstraction ahead of concrete need. All of that
holds unchanged; testaferro still builds none of it (D2). What D1
did not contemplate is more than one external provider of the
piece it refused to build, and this entry adds that recognition:
the "no `runner=` override" clause refused a caller-supplied
virtualization contract, not a choice among testaferro's own
provider bindings. The annotation at that clause points here so
the narrower reading is the recorded one. The seam a provider
implements is the `Backend` ABC D1 already blessed, any richer
interface is derived from concrete implementations when one
actually arrives, and construction still waits on a second
concrete provider.

**Weighed and declined:** placing machine-shaped providers in
reliquary as its backends, keeping testaferro provider-blind. It
reads clean from testaferro's side and bloats reliquary from its
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
curated catalog of **standard environments** testaferro itself
authors — "freedos" naming today's zero-configuration machine,
siblings arriving as guests grow. Never the user's reliquary home:
D6's hermeticity holds, and a test run depends only on state
testaferro authored or the project checked in.

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
degenerate form of the problem testaferro exists for, and mark
exactly where the reference stops transferring: a command prefix
cannot carry a machine lifecycle. Where pytest-cpp probes binaries
by executing them, testaferro declares or defaults — probing here
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
machine-lifecycle interface. There is no `runner=` override
["runner" here is the virtualization piece itself, which testaferro
still does not build; choosing among external providers of it is
D11's axis], no structural runner contract, no conformance kit, and
no mirrored configuration hierarchy. Reliquary owns QEMU lifecycle, machine
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

**Folded into:** `testaferro/machines.py`, `testaferro/facade.py`,
`testaferro/binfmt.py` (`Format.platform`), [README.md](../README.md).
