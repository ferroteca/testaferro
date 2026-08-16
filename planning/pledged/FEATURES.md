<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# Pledged features

Large capability that is **pledged but not yet built**, each
carrying the work breakdown that delivers it. A feature arrives here
by whichever door it comes to the pledge — moved out of
[proposed/FEATURES.md](../proposed/FEATURES.md), or cut straight to
this file where the argument and the pledge land together. Either
way the arrival is the pledge and the commit is its record
([README.md](../README.md)). A feature leaves by being delivered, or
by being **withdrawn** to that file when the pledge turns out to be
one nobody meant.

**Pledged is not scheduled.** Nothing here is queued or dated, and
nothing claims priority over anything else; the pledge says the
project will do it and says nothing whatever about when. The one
ordering that binds runs inside a feature: its work items have to be
done to complete it.

Each feature carries an **F-number** and must fit in **one sprint**;
a feature too large is cut on pledge, the split retiring the
parent's number for a fresh one per piece. The rules are in
[README.md](../README.md).

## F16 — At-rest file access through remanence

> **Pledged 2026-08-16** (owner), in the shape D23 settled: the
> address stays the provider's answer and only the bytes move. The
> design is
> [design/remanence-at-rest.md](design/remanence-at-rest.md).
> **Gated on a downstream ask to reliquary** — see below.

Staging and retrieval stop being provider calls. `_place()` and
`_retrieve_if_kept()` reach the guest's filesystems through
**remanence**, the disk-image library reliquary itself already
writes through (P27 there), leaving reliquary the *execution*
provider and nothing else. Serves **P1** — a provider is whatever
runs a guest suite, and reading a stopped disk is not running
anything, so binding at-rest access to the execution provider makes
every future binding (F5) carry a staging implementation it has no
reason to own — and **P17**, the staged set being testaferro's own
product to place.

**testaferro does not resolve drive letters.** F4 retired letter
inference and this does not take it back: testaferro asks the
provider where a location resolves to, takes its refusal when a
declared address is wrong, and writes the bytes itself.

**The gate.** Reliquary offers neither of the two things this needs —
the resolved image path for a guest address, and a hold on the
machine for the length of a stopped write. Reconstructing the path
from the provider's private machine-home layout is refused (D16,
P2). So the first work item is a downstream ask argued in
reliquary's own planning, and until it lands nothing here is worked.

**Delivery lands a P11 amendment.** P11 is in force at two
dependencies and the interface-change rule names adding a third as
an in-force cost; this feature is that argument, and its delivery
moves P11 to three. The remanence pin must agree with reliquary's
release for release — two pins for one compiled extension is an
unsatisfiable install — so it enters D22's enumerated set on the
same terms.

### Work items

1. The upstream ask, argued and landed in reliquary first.
2. Pin remanence in agreement with reliquary's pin; amend **P11**
   and D22's enumerated set.
3. The at-rest module: open, validate the guest address, walk,
   write, commit; and its mirror for retrieval.
4. `_place()` and `_retrieve_if_kept()` moved onto it, the
   declared-address refusal still the provider's and the defaulted
   address still falling back to the work drive.
5. The unit tier over the new module, and one integration run
   proving a suite still stages and boots (P10).
