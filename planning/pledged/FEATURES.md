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

> **Pledged 2026-08-16** (owner), in the shape **D23** settles: the
> bytes move to remanence, and an address is guaranteed where
> testaferro authored the disk or asked of the guest where it did
> not. The design is
> [design/remanence-at-rest.md](design/remanence-at-rest.md).

Staging and retrieval stop being provider calls. `_place()` and
`_retrieve_if_kept()` reach the guest's filesystems through
**remanence**, leaving reliquary the *execution* provider and
nothing else. Serves **P1** — a provider is whatever runs a guest
suite, and reading a stopped disk is not running anything, so
binding at-rest access to the execution provider makes every future
binding (F5) carry a staging implementation it has no reason to
own — and **P17**, the staged set being testaferro's own product to
place.

**This is forced work, not an improvement.** Reliquary is deleting
its file family and drive report — `put_files`, `get_files`,
`describe_drives` and their siblings, deleted rather than
deprecated — so `_place()`, `_retrieve_if_kept()`,
`_default_location()` and `_placed_letter()` all break on the
release that lands it. The reliquary releases testaferro supports
(D22) therefore stop at the last one carrying those verbs until
this is delivered.

**No drive map, and none needed.** Neither upstream will report a
drive letter: what testaferro needs at rest is an image and a
volume, which wants no letter at all, and what it needs at run time
is the letter *DOS assigned*, which is a fact about the running
guest. So the default location becomes a constant testaferro
**guarantees** on the system disk it authors (P17, D10), and any
other machine's letter is **asked of the guest** over the readiness
channel `_wait_ready()` already uses. F4 retired derivation and this
honors that: nothing is inferred, and a declared address is still
the consumer's own word.

**Delivery lands a P11 amendment.** P11 is in force at two
dependencies and the interface-change rule names adding a third as
an in-force cost; this feature is that argument, and its delivery
moves P11 to three, entering D22's enumerated set. There is no pin
to coordinate: reliquary is dropping remanence from its own
dependencies, so testaferro's pin answers to nothing but testaferro.

### Work items

1. Pin remanence; amend **P11** and D22's enumerated set.
2. The at-rest module over remanence: open the image, validate the
   guest address, walk, write, commit — and its mirror for
   retrieval.
3. The address, both halves: the authored constant on the system
   disk, and the guest-reported letter for a machine testaferro did
   not author, carried on the readiness script's variable.
4. `_place()` and `_retrieve_if_kept()` moved onto the module;
   `_default_location()` and `_placed_letter()` retired with the
   drive report they read.
5. The unit tier over the new module, and one integration run
   proving a suite still stages and boots (P10).
