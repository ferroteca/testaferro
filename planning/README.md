<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: BSD-3-Clause
-->

# planning

Maintainer-facing planning. The directories are the classification;
file names carry no suffix, and a document's location tells you its
standing without reading a word of it.

Human usage documentation is [README.md](../README.md); maintenance
guidance for the code as it stands is [AGENTS.md](../AGENTS.md).

## The one vocabulary

**A use case, a principle and a task carry the same lifecycle**:
each is *proposed*, *accepted*, *completed*, or *rejected*. One
vocabulary runs through the whole planning machinery — the same four
words classify demand, rules and work alike — and the directories
below are that vocabulary made physical.

- `proposed/` — argued but not accepted. **Nothing is worked from
  here.**
- `accepted/` — approved, and not yet delivered.

**There is no roadmap here, deliberately.** A roadmap promises an
order and a time this project does not commit to. `accepted/` says
the direction is agreed and nothing more: it answers "is this
right?" with yes and "when?" with nothing at all. Big items wait in
`proposed/` and are bitten off one at a time, in no pre-promised
order.

Anything here that can be depended on carries a handle, so that one
item points at another by something stable rather than by a heading
someone may reword. Features take numbers — `F1 — The command-line
entry` — which is the old milestone identifier and none the worse
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
suggests. The bound bites at acceptance: large, shapeless capability
is welcome in `proposed/`, and cutting it into implementable pieces
is part of what accepting it means. A split retires the parent's
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
delivered first, citing the prerequisite's handle. **Those
references are not a delivery order**: that B needs A says nothing
about when either is picked up, or what comes between them. Most
references sit within one tier, and a proposed item may freely
depend on an accepted one. The reverse is a flaw rather than a
reference — an accepted item that cannot be completed without
something still only proposed has been accepted too early, and
either the prerequisite is accepted too or the acceptance is
withdrawn. A date is a promise and belongs nowhere here.

**The lifecycle directories hold the same filenames** —
`USE-CASES.md`, `ARCHITECTURE.md`, `FEATURES.md` — because they hold
the same artifacts in different states. A thing in `proposed/` moves
to `accepted/`, and **the commit that moves it is the record**.
`accepted/` does not exist yet: nothing has been promoted into it,
and it appears with its first accepted document rather than standing
empty.

**The planning root holds what does not move.** The map, the rule,
the record and the queue are machinery rather than proposals, and
none of them has a lifecycle state to be in:

- [README.md](README.md) — this map.
- [INTERFACES.md](INTERFACES.md) — the vetting rule. It governs
  `proposed/` at least as much as `accepted/`; it is the test a
  proposal is judged by, not a thing that was proposed.
- [DECISIONS.md](DECISIONS.md) — the adjudication record, which cuts
  across every state by design: open questions, decisions that
  accepted something, decisions that **refused** it, and a retired
  list binding nothing at all.
- [TASKS.md](TASKS.md) — the queue. Work entered there is small and
  **pre-approved**, so there is nothing to promote and no order to
  work it in.

## Where the vision stands today

The in-force artifacts belong at the **repository root**, not here,
because they are claims about the code as it exists today:
`USE-CASES.md`, every entry met by the code, and `ARCHITECTURE.md`,
the whole-system view plus the P-numbered architectural principles,
every principle honored by the code. Together with the normative
specifications they are the project's **vision**: the standing
statement of what testaferro is and is for.

**Neither root document exists yet.** testaferro adopted this model
after the code was written (D7), so its whole vision was drafted at
once and sits in [proposed/](proposed/) awaiting acceptance:
[proposed/USE-CASES.md](proposed/USE-CASES.md),
[proposed/ARCHITECTURE.md](proposed/ARCHITECTURE.md) — which carries
the interface enumeration the vetting rule looks up — and
[proposed/FEATURES.md](proposed/FEATURES.md). Until a use case or
principle is accepted and then delivered, this project has no
in-force list, and the honest answer to "what does testaferro
promise?" is *nothing yet stated*. Several drafted entries describe
code that already exists; that makes their route short, not
automatic — acceptance is still an act, and delivery still has to be
true.

Each mirrored artifact appears in **both** directories, because use
cases and principles have **three** states, not two: drafted →
accepted → in force. Acceptance and delivery are different events,
and the gap between them is real — the root lists are implementation
claims, so accepting a use case can never put it there. This is also
what arms a principle: below the root list it is accepted vision and
a shortfall is unbuilt work; at the root list the project asserts the
code honors it, and a divergence becomes a bug.

**Design sits with what it serves.** A design for one feature lives
beside that feature — `proposed/design/` or `accepted/design/` — so
the design and the demand it answers move together, and a design for
a proposal that dies is swept with it. A `design/` directory at this
level would hold only open design problems belonging to no single
feature; the whole-system view itself is root `ARCHITECTURE.md`.
Neither directory exists yet.

**Nothing under `planning/` describes a delivered interface.** Once
an interface ships, its normative specification is current truth and
moves out of here. That is a one-way move: a norm never comes back.
testaferro holds no normative specifications today — what norms its
interfaces is an open question in [DECISIONS.md](DECISIONS.md).

## How an idea enters

**An idea enters this project through three work queues:**

1. **Issues** — the raw, unfiltered intake, often from outside: a
   bug hit, a question asked, a wish stated.
2. **The [proposed/](proposed/) directory** — the same idea argued in
   the project's own vocabulary, as a drafted use case, principle or
   feature. Nothing is worked from here until it is accepted.
3. **[TASKS.md](TASKS.md)** — small, **pre-approved** work. Entering
   it is approving it, so it needs no citation and no decision, and
   there is no order to work it in.

Nothing flows without starting in one of them; the only exception is
a small raw commit approved under housekeeping.

**Writing into `planning/` is a governed act.** The issue tracker is
the one open door: anyone may file there, and entry grants nothing.
Everything here is the project speaking in its own voice, so the
same gate governs all three acts — entering a document in
`proposed/`, promoting it to `accepted/`, and entering work in
[TASKS.md](TASKS.md). Only what each grants differs: a live
argument, an acceptance, an approval. The gate weighs most on the
last, which *is* the whole vetting with nothing behind it. It sits
at entry only; anyone may pick up what is already there. Authority
is the owner alone today.

The queues are not peers; issues are upstream of both others. Raw
intake is triaged into a drafted proposal, entered as a task, fixed
directly as housekeeping, or rejected with its reason recorded in
[DECISIONS.md](DECISIONS.md). What keeps the third queue from being
a hole in the vetting is the same test housekeeping uses: **does it
change an interface?** A yes is never small work, however small the
diff, and takes the argued route. Composed that way, the guarantee
holds — **no interface changes without having passed through a
queue.**

**Housekeeping** is the same instinct one size below the third
queue: small cleanups and small reported defects — tiny in scope
*and* crystal clear they are a problem — are approved as a class, in
advance, and are too small to be worth writing down at all. A
qualifying item is accepted on sight and needs no entry anywhere;
whoever lands the work invokes the bucket by naming it in the
commit, and the commit is the record.

Refusing is half of both rules. The interface test above is the
first gate and it is a lookup, not a judgement —
[proposed/ARCHITECTURE.md](proposed/ARCHITECTURE.md) enumerates the
interfaces (at the root, once accepted and delivered), and the rule
that weighs a hit is [INTERFACES.md](INTERFACES.md). A use-case or
principle amendment and a design decision are likewise never
admissible to either bucket. Past that, doubt escalates: if it has
to be argued in, it does not belong in. (A defect against an
in-force principle is neither — the principle is already its own
demand, so it needs no approval, only fixing.)

## How an idea is accepted

**The move is the act.** Promoting a document — or an entry within
one — from `proposed/` to `accepted/`, or from `accepted/` to the
root standing list, *is* the acceptance, and the commit that does it
is the record. There is no separate register to keep in step, and
nothing is accepted by being cited somewhere.

Every accepted item cites what demands it: a use case (its U-number,
in force at the root or still drafted under `proposed/`) or an
architectural principle (its P-number), which drives work just as
well. When a proposal dies, the sweep finds every item that falls
out with it.
