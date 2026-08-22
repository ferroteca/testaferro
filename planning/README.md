<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# planning

Maintainer-facing planning. The directories are the classification;
file names carry no suffix, and a document's location tells you its
standing without reading a word of it.

Human usage documentation is [README.md](../README.md); maintenance
guidance for the code as it stands is [AGENTS.md](../AGENTS.md).

## The one vocabulary

**A use case, a principle and a task carry the same lifecycle**:
each is *proposed*, *pledged*, *completed*, or *rejected*. One
vocabulary runs through the whole planning machinery — the same four
words classify demand, rules and work alike — and the directories
below are that vocabulary made physical.

- `proposed/` — argued but not pledged. **Nothing is worked from
  here.**
- `pledged/` — owed by the project, and not yet delivered.

Neither shelf is named after an act, and the second one used to
be — `accepted/`, until the approval words gave out (D8). Admitting
a document to `proposed/` is an approval too, so a shelf named for
an act claims a word the other gate still has to borrow. Both names
state what an item *is*: **proposed**, argued and binding nothing;
**pledged**, owed with no date attached.

**There is no roadmap here, deliberately.** A roadmap promises an
order and a time this project does not commit to. `pledged/` says
the project will do it and nothing about when: it answers "is this
right?" with yes, "will it happen?" with yes, and "when?" with
nothing at all. A pledge nobody means is withdrawn to `proposed/` or
rejected outright, never left sitting. Big items wait in `proposed/`
and are bitten off one at a time, in no pre-promised order.

Anything here that can be depended on carries a handle, so that one
item points at another by something stable rather than by a heading
someone may reword. Features take numbers — `F3 — Intra-suite
sharding` — which is the old milestone identifier and none the worse
for it: what a feature number does *not* carry is an order or a
date. Designs take no number of their own; a design serves one
feature and is identified by its path.

**A feature must be small enough to implement in one sprint**, and
is broken up when it is not. The sprint measures the feature rather
than scheduling it, and it is deliberately unspecified — a rough
unit of time and size this project sets for itself, resourcing
dictating. Do not read the traditional two weeks into it: this is a
solo project worked with AI tooling, so a sprint is measured in
hours, making an acceptable feature far smaller than "milestone"
suggests. The bound bites at the pledge: large, shapeless capability
is welcome in `proposed/`, and cutting it into implementable pieces
is part of what pledging it means. A split retires the parent's
number and issues a fresh one to each piece; sub-numbering would
build a hierarchy, and hierarchy is how a feature list turns into a
work-breakdown schedule.

The handles of *vision* — use cases, principles, decisions — are
permanent, and travel into the in-force lists on delivery. The
handles of *work* evaporate: a delivered feature stops existing as
an item, leaving code and the norms that specify it, and its number
retires rather than being reused. Gaps in the sequence are history,
not a promise.

Work does refer to other work — an item names what it needs
delivered first, citing the prerequisite's handle, written in the
dependent item and pointing at the handle rather than at a heading.
**Those references are not a delivery order**: that B needs A says
nothing about when either is picked up, or what comes between them.
Most references sit within one tier, and a proposed item may freely
depend on a pledged one. The reverse is a flaw rather than a
reference — a pledged item that cannot be completed without
something still only proposed has been pledged too early, and
either the prerequisite is pledged too or the pledge is withdrawn.
A date is a promise and belongs nowhere here.

**The lifecycle directories hold the same filenames** —
`USE-CASES.md`, `ARCHITECTURE.md`, `FEATURES.md` — because they hold
the same artifacts in different states. A thing in `proposed/` moves
to `pledged/`, and **the commit that moves it is the record**. Each
mirrored file appears in `pledged/` with its first promoted entry
rather than standing empty, and leaves again when its last one
does. **`pledged/FEATURES.md` held six stays** — F7 and F8, then F11
and F12, then F13 alone, then F9 and F18, then F3 alone (that fifth a
same-day round trip, pledged and withdrawn once starting it found its
batching needs a sixth framework-adapter callable, which P4 as
written does not allow, D24), then F19 alone, paired with U9 as what
it proved (D25) — and stands empty since. `ARCHITECTURE.md` did it
once, holding P1 and P2 from D18 until F12 built what they promised,
and stands empty since too. `USE-CASES.md` did it three times over —
U4 from D13 until a guest ran the journey it describes, then U7 and
U10 together, then U9 alone, severed from its own plural growth — and
stands empty since as well. Each leaves when its last entry arms or
delivers, which is the machinery working rather than churn.

**U7 and F9 were the same debt seen twice, and both are paid.**
U7 was the journey and F9 the work that completed it — neither could
arm or deliver alone, and neither did alone: F9 delivered `setup=`,
proven against a real guest boot, and U7 armed with it in the same
change. The provider capability F9 was gated on — reliquary's
`exec(check=True)` — had shipped before the pledge, ahead of
Testaferro's own pin, so nothing waited on reliquary; what was owed
was entirely Testaferro's own, and it is paid.

**U10 and F18 were the same shape of debt, with an even shorter
route to it, and both are paid too.** U10 was the journey — a
scripted guest interaction outside the suite/framework abstraction —
and F18 the work: a `guest_session()` primitive drawing on the
provisioning `ReliquarySuiteBackend` already had, refactored into a
shape both entry points share rather than duplicated. Nothing here
waited on a provider capability at all; the whole of it was
Testaferro's own refactor and one new entry point, so there was no
gate to clear before the pledge, unlike F9's — and none to clear
before delivery either.

**The planning root holds what does not move.** The map, the rule,
the record, the queue and the ledger are machinery rather than
proposals, and none of them has a lifecycle state to be in:

- [README.md](README.md) — this map.
- [INTERFACES.md](INTERFACES.md) — the vetting rule. It governs
  `proposed/` at least as much as `pledged/`; it is the test a
  proposal is judged by, not a thing that was proposed.
- [DECISIONS.md](DECISIONS.md) — the adjudication record, which cuts
  across every state by design: open questions, decisions that
  pledged something, decisions that **refused** it, and a retired
  list binding nothing at all. Adjudications only: the lifecycle acts
  themselves are recorded by the commits that perform them (D14).
- [TASKS.md](TASKS.md) — the queue. Work entered there is small and
  **pre-approved**, so there is nothing to promote and no order to
  work it in.
- [SEQUENCES.md](SEQUENCES.md) — the ledger: the next number every
  handle sequence issues. Take the mark and advance it in the same
  edit, on `main`, because a search sees only the branch it stands
  on and an evaporated handle leaves nothing behind to count.

## Where the vision stands today

The in-force artifacts belong at the **repository root**, not here,
because they are claims about the code as it exists today:
[`USE-CASES.md`](../USE-CASES.md), every entry met by the code, and
[`ARCHITECTURE.md`](../ARCHITECTURE.md), the P-numbered architectural
principles, every one honored by the code. The whole-system view
belongs there too and has not followed yet — but its reason for
waiting has gone: it described a consumer vocabulary that was pledged
and unbuilt (P1, P2, D18), and both are now armed and built, so the
view is a claim about the code and moving it is a promotion nobody
has made rather than a condition nobody has met. The interface
enumeration beside it stays regardless, being what the vetting rule
looks up. Together with the normative
specifications they are the project's **vision**: the standing
statement of what Testaferro is and is for.

**Both root lists exist now, and one of them took months.**
Testaferro adopted this model
after the code was written (D7), so its whole vision was drafted at
once into [proposed/](proposed/):
[proposed/USE-CASES.md](proposed/USE-CASES.md),
[proposed/ARCHITECTURE.md](proposed/ARCHITECTURE.md) — which carries
the interface enumeration the vetting rule looks up, and keeps it
whatever else moves — and
[proposed/FEATURES.md](proposed/FEATURES.md). The first entries were
pledged onto the `pledged/` shelf (D13), and the two
features among them were delivered — **which arms nothing**.
Features carry no vision; delivering one leaves code and retires a
number. A use case still reaches the root list only on full
delivery and a principle only on being honored as a rule. **P16 was
the first entry of any kind to arm**, and P10 and P4 followed it one
at a time; P6, P7, P8, P9, P11, P12, P13 and P17 then armed together,
on the same bar applied to each; and P1 and P2 armed once F12 built
what they promised. Root `ARCHITECTURE.md` now carries thirteen
in-force claims and the drafted list is down to four, so **no
principle is pledged at all**. Most went straight from drafted to in
force without a pledge, as P4 did — the pledged shelf holds what is
owed, and a principle the code already honors is owed nothing — while
P1 and P2 took the long route the shelf is for, pledged by D18 with
the work owing and armed when it landed.

**Then a guest ran, and U4 armed** — the first use case of any kind
to, and the reason root `USE-CASES.md` exists at all. For as long as
nothing had booted, the honest answer to "what does Testaferro promise
*a user*?" was *no journey yet stated*, however much the architecture
asserted; a use case arms on delivery, and delivery is a journey
working rather than code existing.

**U7 armed next, the same way.** It was pledged alongside its
prerequisite F9 — each pledged together with what it cites rather
than the citation left resting on something merely proposed — and a
real guest boot proved the journey: `setup=` commands run before any
test, once per guest session, and a real failure ends the session
cleanly rather than dooming every test after it. F9 delivered and
retired with it, leaving code behind — U7's own number is permanent
now, at the root list it reached.

**U10 armed next in turn, the same way again.** It was pledged
alongside its prerequisite F18, and a real guest boot proved this
journey too: `guest_session()` opens the same zero-configuration
guest `guest_suite()` gives every suite, `files=` stages host paths
onto the work drive before boot exactly as `guest_suite()` does, and
`exec()` runs a guest command and reads its answer back, in the order
the script asks rather than a suite's enumeration — the same guest
session sweeping away on exit whether the script's own assertions
passed or one of them raised. F18 delivered and retired with it,
leaving `_GuestLifecycle` — the provisioning `ReliquarySuiteBackend`
and `GuestSession` now share rather than each carrying its own copy
— behind as the code. **U9 armed next in turn, the same bar again.**
It was pledged alongside its prerequisite F19 (D25), the standard
catalog's resolution already existing and unit-tested, so what F19
owed was proof rather than mechanism — one integration case naming
`"freedos"` explicitly, through the same seam every entry point
shares, against a real guest boot. That case now exists and passes:
`environment="freedos"` resolves against the standard catalog rather
than only through the zero-configuration default's own inference
reaching the same disk unnamed, and boots for real through both
`resolve_backend()` and `resolve_guest_session()`. F19 delivered and
retired with it, leaving no code behind — the mechanism was already
built, and this pledge's whole content was the proof. **U5 armed the
same way, by the shortest route yet.** F15 was cut at the pledge to
the one journey no proof had touched — parallelism — and the piece
took a fresh number, F22, the rest of F15 having already been run by
the tier without anyone calling it work; the owner compressed pledge
and delivery into one change, as F20's had been, so neither shelf
file reappeared for it. The proof is the README's own advice run for
real: two suites under `pytest -n 2 --dist loadfile`, each whole on
its own worker, both booting at once. Delivery found one thing the
proof itself could not, on a machine whose system disk was long
built: two workers installing it for the first time at the same
moment staged into one shared partial file, and each build now
stages into its own. **F3 then took the route D24 had named and not
taken**: P4 amended to admit an optional sixth adapter callable
(D29), F3 pledged on it and delivered in the same change — a
`run_some()` operation on the seam, defaulted so the escape hatch
owes nothing new, and a per-group batch in the broker, proven
against a real guest both directly and under `--dist load`. **F2
took the same compressed route and is the first delivery that armed
nothing** (D30): `persist=` keeps a machine by name, the `testaferro`
console script enumerates and removes what is kept, and every clause
of U8 but one is proven against real boots — the one short, a
machine staying up across the suites that name it in one run, is
recorded at U8's entry with its reason, and the use case stays
drafted until that is built or the owner amends the clause. Several
drafted entries describe code that already exists; that makes their
route short, not automatic — the pledge is still an act, and
delivery still has to be true.

**What did not arm is worth naming, because the bar is what makes
the root list mean anything.** P3 and P5 each describe the code, and
each is contradicted by a small piece of it — recorded at the entry,
where whoever reads the principle meets it. P14 and P15 are about how
this project argues rather than about what it built, and the in-force
list asserts of every entry that the code honors it, which a rule of
conduct gives nothing to check.

Each mirrored artifact appears in **both** directories, because use
cases and principles have **three** states, not two: drafted →
pledged → in force. Pledging and delivery are different events, and
the gap between them is real — the root lists are implementation
claims, so pledging a use case can never put it there. **Promotion
to the root runs on two bars, not one** (D8), because the two
artifacts are armed by different events. A use case moves on *full*
delivery — partial delivery leaves it below the line. A principle
moves on being honored *as a rule*, and that bar carries a hard
condition: every known residue is filed as a defect in the same
change. Filing the residue is what converts a shortfall from unbuilt
work into a bug, which is exactly what arming means — below the root
list a principle is pledged vision and a shortfall is unbuilt work;
at the root list the project asserts the code honors it, and a
divergence becomes a bug.

**Design sits with what it serves.** A design for one feature lives
beside that feature — `proposed/design/` or `pledged/design/` — so
the design and the demand it answers move together, and a design for
a proposal that dies is swept with it. A `design/` directory at this
level would hold only open design problems belonging to no single
feature; the whole-system view itself is root `ARCHITECTURE.md`.
Neither directory exists yet.

**Nothing under `planning/` describes a delivered interface.** Once
an interface ships, its normative specification is current truth and
moves out of here. That is a one-way move: a norm never comes back.
Testaferro holds no normative specifications today — what norms its
interfaces is an open question in [DECISIONS.md](DECISIONS.md).

## How an idea enters

**An idea enters this project through three work queues:**

1. **[Issues](https://github.com/ferroteca/testaferro/issues)** —
   the raw, unfiltered intake, often from outside: a bug hit, a
   question asked, a wish stated.
2. **The [proposed/](proposed/) directory** — the same idea argued in
   the project's own vocabulary, as a drafted use case, principle or
   feature. Nothing is worked from here until it is pledged.
3. **[TASKS.md](TASKS.md)** — small, **pre-approved** work. Entering
   it is approving it, so it needs no citation and no decision, and
   there is no order to work it in.

Nothing flows without starting in one of them; the only exception is
a small raw commit approved under housekeeping.

**Writing into `planning/` is a governed act.** The issue tracker is
the one open door: anyone may file there, and entry grants nothing.
Everything here is the project speaking in its own voice, so the
same gate governs all three acts — entering a document in
`proposed/`, promoting it to `pledged/`, and entering work in
[TASKS.md](TASKS.md). Only what each grants differs: a live
argument, a pledge, an approval. The gate weighs most on the
last, which *is* the whole vetting with nothing behind it. It sits
at entry only; anyone may pick up what is already there. Authority
is the owner alone today.

The queues are not peers; issues are upstream of both others. Raw
intake is triaged into a drafted proposal, entered as a task, fixed
directly as housekeeping, or rejected with its reason recorded in
[DECISIONS.md](DECISIONS.md). What keeps the third queue from being
a hole in the vetting is **the gate at its door**: only authority
writes to it, and entering an item *is* approving it (D8). It is
not housekeeping's interface test — that boundary is housekeeping's
alone, compensating for a class nobody with authority ever reviews,
and a queue only the owner can write to needs no such compensation.
So **a small interface change may be a task**, admitted on size and
kind and never refused for the surface it touches; what it may not
do is skip the landing rules in [INTERFACES.md](INTERFACES.md),
which bind it exactly as they bind a feature. Composed that way the
guarantee still holds — **no interface change without having passed
through a queue** — because passing through this one means an
approval was given, not that the subject was safe.

**Housekeeping** is the same instinct one size below the third
queue: small cleanups and small reported defects — tiny in scope
*and* crystal clear they are a problem — are approved as a class, in
advance, and are too small to be worth writing down at all. A
qualifying item is approved on sight and needs no entry anywhere;
whoever lands the work invokes the bucket by naming it in the
commit, and the commit is the record.

Refusing is half of both rules. Housekeeping's interface test is its
first gate and it is a lookup, not a judgement —
[proposed/ARCHITECTURE.md](proposed/ARCHITECTURE.md) enumerates the
interfaces (at the root, once in force), and the rule that weighs a
hit is [INTERFACES.md](INTERFACES.md). It governs that bucket only;
the third queue's gate is authority at entry (above). A use-case or
principle amendment and a design decision are never admissible to
either bucket. Past that, doubt escalates: if it has to be argued
in, it does not belong in. (A defect against an in-force principle
is neither — the principle is already its own demand, so it needs no
approval, only fixing.)

## How an idea is pledged

**The move is the act.** Promoting a document — or an entry within
one — from `proposed/` to `pledged/`, or from `pledged/` to the
root standing list, *is* the pledge, and the commit that does it is
the record. There is no separate register to keep in step, and
nothing is pledged by being cited somewhere.

**So the act earns no entry in [DECISIONS.md](DECISIONS.md)** (D14).
Proposing, pledging, promoting and delivering are already stated by
location and recorded by the moving commit, and delivery evidence —
the clause-by-clause case that a use case is met in full — belongs
in that commit's message. What earns an entry is adjudication: a
decision that concluded in a pledge records the argument, and a
ruling made in an act's course is recorded slim, as the ruling
alone.

Every pledged item cites what demands it: a use case (its U-number,
in force at the root or still drafted under `proposed/`) or an
architectural principle (its P-number), which drives work just as
well. When a proposal dies, the sweep finds every item that falls
out with it.
