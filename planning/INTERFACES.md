<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# The interface-change rule

> **Status:** the governing rule for changes to Testaferro's
> world-facing interfaces. The interfaces themselves are enumerated
> in [proposed/ARCHITECTURE.md](proposed/ARCHITECTURE.md) "The
> interfaces" — that enumeration is this rule's scope, answered by
> lookup — and moves to root `ARCHITECTURE.md` when in force. This
> document says how an interface-changing decision is weighed:
> against the use cases and the architectural principles, which
> carry equal weight. When a design document and those lists
> disagree, the principles and use cases govern: the design is
> realigned to them, never the other way around.

## The decision surface

The numbered use cases and the cross-cutting P-numbered principles
are the surface every significant change is weighed against. They
are numbered so a decision, review, or specification section can
cite the use case or principle it serves — and so a proposed change
can be rejected by naming what it costs.

**Both root lists now exist.** They hold only what the code delivers
and honors today: root [`USE-CASES.md`](../USE-CASES.md) holds **U4**,
the trial journey, armed once a guest actually ran it, and root
[`ARCHITECTURE.md`](../ARCHITECTURE.md) holds thirteen principles:
P1, P2, P4, P6 through P13, P16 and P17. **No principle is pledged
any more** — what stays drafted is P3, P5, P14 and P15, so a
P-citation now points either at a rule in force or at an argument,
and never at something merely owed. **Two use cases are pledged**:
U7, alongside its prerequisite F9, and U10, alongside its
prerequisite F18, in
[pledged/USE-CASES.md](pledged/USE-CASES.md) and
[pledged/FEATURES.md](pledged/FEATURES.md). Every other use case is
drafted in [proposed/USE-CASES.md](proposed/USE-CASES.md), so read a
citation by where it points: an in-force entry binds, a pledged one
is owed, and a drafted one names an argument.

**Costs can now be named as in-force costs on both halves**, which is
the point of arming: a change that would erode zero configuration, add
a fourth dependency, ask a consumer for an emulator, or make a grammar
answerable to a captured sample is refused against a rule rather than
argued against a draft — and a change that would break the trial
journey is refused against U4 the same way. Both files number from the
same global
sequences and keep their numbers when they move. A number is never
reused.

That state has one practical consequence worth naming: the
housekeeping test below is a lookup against an enumeration that is
itself only proposed. Use it anyway — an enumeration that has been
written down is what makes the test a checklist rather than a
judgement, and its being unpledged affects what Testaferro
*promises* about those surfaces, not which surfaces exist.

## The housekeeping boundary

One class of work is exempt, and its boundary is drawn here because
here is where it would be walked around. **Housekeeping** approves
small cleanups and small reported defects as a standing class — tiny
in scope *and* clearly a problem — so they need no citation and no
adjudication.

**It stops at the interfaces, absolutely: a change that touches any
surface the enumeration names is automatically not housekeeping**,
whatever its diff looks like, and takes the rule below instead. That
test is asked first and answered by lookup, so it is a checklist,
not a judgement. **The norm is part of the interface**: an edit to a
normative document that changes what the norm requires *is* an
interface change, proposed and gated before it lands; work that
arrives already made is rejected on that ground, whatever its merit
— unless it comes from someone holding the authority to approve it,
who may land the whole change at once (below). Only an edit that
changes no rule is documentation work. This matters because
housekeeping's other two tests ("tiny", "clearly a problem") are
judged by whoever wants to do the work, and the smallest-looking
change is the one most likely to be a contract change wearing a
small diff.

**The boundary is housekeeping's alone** (D8). It exists *because*
housekeeping is ungoverned — approved as a class in advance, its
remaining two tests judged by whoever wants the work — so the
interface exclusion is the whole of what stands between that class
and an unreviewed contract change. It does **not** reach the
pledged task queue ([TASKS.md](TASKS.md)), where the gate sits at
entry and only authority may enter anything: **a small interface
change may be a task**, admitted on size and kind and never refused
for the surface it touches. Read across, the boundary counts the
same protection twice and turns away work authority has already
approved. What this rule governs is how a change *lands* — the
steps below — not which queue it waited in.

## The rule

Requests triage by their use-case and principle impact. A change is
significant precisely when approving it requires a use case or a
principle to be adjusted; a significant change is not argued as a
feature on its own merits — **the amendment is the argument**, and
the interface change follows from the amended list. A significant
proposal that cannot be phrased as "the use cases should say ..." or
"the principles should say ..." is not ready to decide. The two
carry equal weight: a principle amendment is argued exactly as
vigorously as a use-case one, and neither is edited to fit a feature
someone has already decided to build.

- **No use-case or principle impact, or strong alignment with the
  existing lists.** Nothing any use case demands and nothing any
  principle requires is altered, or the change serves them as
  written. An easy decision to approve; cite what is served, or
  state that nothing is disturbed.
- **Adds a new use, or a new principle.** The change serves a use
  the project does not yet name, or is demanded by a rule it honors
  but has never stated. More work — the new entry must be drafted
  and numbered in [proposed/USE-CASES.md](proposed/USE-CASES.md) or
  [proposed/ARCHITECTURE.md](proposed/ARCHITECTURE.md) and weighed
  for coherence with the existing lists — but, being additive, still
  an easy decision.
- **Misaligned with the use cases or a principle.** The hard case,
  and the one that must be argued very vigorously: approving it in
  good faith would require a use case or a principle to change, so
  the amendment — not the feature — is what gets argued. The
  workflow is strict: draft the amendment under `proposed/` and make
  the argument; if the argument wins, the amendment moves to
  `pledged/` — the move is the pledge and the commit is its
  record ([README.md](README.md)); only then does work start.
  Pledged use cases move into root `USE-CASES.md` when their
  delivery lands in full, pledged principles into root
  `ARCHITECTURE.md` when the project honors them as a rule — every
  known residue filed as a defect in the same change — anything
  superseded retiring stubless — its number never reused,
  [DECISIONS.md](DECISIONS.md) the record. A misaligned change that
  can propose no amendment has nothing to argue and is rejected,
  regardless of its elegance.

**Authority may compress the steps.** The staged workflow above is
the route for someone who cannot approve their own change. A person
holding governance authority may land an interface or norm change
outright, in a single PR, being entitled to perform every step it
needs, and is never refused on the ground above. That is an
*execution* of the governance steps all at once rather than a bypass
of them: compressed in time, not reduced in content, so the
amendment, the decision entry and the specification update all still
land with it. A change arriving with none of them has not been
compressed but skipped, and what is lost is the adjudication trail.
Anyone without that authority takes the staged route, and finished
work from them is refused on one of two grounds, **never
identity**: not having argued the merit, or having argued it and not
won. Word it that way — the ground names the door back in, so every
refusal states what would change the answer. Note the limit
honestly: where the author of the standard is also its arbitrator,
this is not impartial adjudication. What it offers is a stated
standard and a recorded reasoning to disagree with later.

Every approved change then lands the same way:

1. **Name every interface it touches.** A change rarely touches one:
   the embedding API and `testaferro.ini` are two spellings of one
   declaration, and the item ids a suite produces are consumed by
   node-id selections written down elsewhere. An intentionally
   single-surface change states why the others are unaffected.
2. **Land it coherently and completely** — every affected surface,
   document, example, and test moved to the new shape, the old one
   deleted. Testaferro is pre-1.0 and gives no backward-compatibility
   guarantee, so the old shape is deleted rather than bridged. Cheap
   execution does not make the decision cheap; nothing downstream
   cushions a wrong one.
3. **Record it.** Amendments are drafted under `proposed/`, pledged
   by being moved out of it, and reach the root lists when
   delivered, keeping their numbers; settled decisions go to
   [DECISIONS.md](DECISIONS.md) and to their normative homes;
   user-facing contracts to [README.md](../README.md); examples stay
   synchronized.
