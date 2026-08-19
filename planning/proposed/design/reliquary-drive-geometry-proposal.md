<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# Proposal: surface a stopped machine's drive geometry

> **Answered 2026-07-30.** Reliquary 0.1.0.dev6 ships
> `describe_drives()` / `refresh_drives()` under its own D83, which
> retired the F29 it had entered for this ask. The shape is the
> provider's, as this proposal asked it to be: one report rather
> than two, answered from a record read at every start, with the
> at-rest recognition claim narrowed to FAT12/FAT16/FAT16B in the
> same change. Testaferro consumes the letter-map slice and has
> moved its pin; the closing paragraph below — that it stays on
> 0.1.0.dev4 until a release carries the surface — is spent, and
> kept because it records the terms the pin was held on.

A **downstream proposal to reliquary**, from Testaferro, its
consumer. It serves F4 (test placement, designed in
[test-placement.md](test-placement.md)), and it is written the way
consumer-side input should be: the shape that costs the consumer
least, the requirements it cannot meet alone, and nothing the
provider owns asked back.

Written against the published 0.1.0.dev5 and checked at reliquary's
0.1.0.dev6 tip; the code claims below cite the tip.

## The ask

One public, machine-level query for a **created, stopped machine**:
what drives it has and what they actually hold.

- **Per drive, the provider's own facts**: key, medium and slot as
  declared; the materialization it performed (`use`, `copy`,
  `difference`) and the backing it chose (qcow2, raw, a
  directory served as a FAT volume).
- **Per drive, what was read at rest**: the volumes it holds —
  count, each volume's filesystem read for what it declares itself
  to be, its label where one exists, and its geometry where the BPB
  states one (heads, sectors per track, derived cylinders).
- **The platform's derivation over that: volume to guest
  filesystem namespace**, in each platform's own vocabulary — the
  letter map for DOS and Windows (letter to drive key and volume
  index), a filesystem map for Linux and BSD guests (volume to the
  device node and mount the guest would see) when those platforms
  arrive. DOS is the delivered case and the only one this consumer
  needs; the point of naming the general shape is that the report's
  design should leave room for it, with each platform layer owning
  its own words. Undetermined drives are *named as undetermined and
  why* — D78's honesty carried into the answer, never smoothed
  over.

Not all of this serves Testaferro — the letter map is the slice F4
consumes, for defaulting where tests land — but the rest is not
speculative surface: it is a report over readings 0.1.0.dev5
already performs. The at-rest layer walks the partition table, pins
FAT types value by value, and reads the BPB; the letter map
consumes per-disk volume counts computed and cached in machine
state; dev5's own changelog says the geometry reading "is the
answer the drive-letter map needs" and wired exactly that in. What
does not exist is a surface: the counts live in a private helper,
the five file verbs consume the map internally and answer only
about an *address*, and `platform_dos.drive_letters` now requires a
`volumes` argument no public caller can supply. The observation
exists; the ask is a window onto it.

Whether it is one verb or two, what its CLI twin is called, and
what dress the report wears are the provider's calls; the parity
rule there (every API a command, every command an API) implies the
CLI twin exists, which is itself of general use — asking what a
machine's disk actually holds, from the shell, without booting it.

## The window, verified at the tip

Create leaves a machine's phase `ready` (machines.py:433), and the
at-rest gate admits exactly that phase (machines.py:980) — so the
query is answerable in the gap between `create_machine` and
`start_machine`, which is precisely where a consumer stages files,
and again after any stop. Volume counts are cleared at every start
and re-read affordably (D77 there), so the answer is always about
*this* boot's disk, never a stale one. An integration proof of the
never-booted case belongs to whoever builds against it; the code
reading is stated here so the proposal is checkable.

## Why the consumer cannot do this alone

- The counts are observations of materialized images. A consumer at
  authoring time has no image to read, and at any time lacks the
  provider's at-rest machinery — which is one release old and
  should not grow a second implementation downstream.
- An unknown disk ahead of the consumer's own shifts every letter
  behind it by an unknown amount, so partial knowledge places
  nothing. The one count a consumer holds honestly — its own
  directory-source drive is one volume *by construction*, the
  provider's own documented rule — is exactly the count that
  cannot help while any disk before it is unread.
- Asserting a count instead would re-adopt, one layer down, the
  very assumption D78 deleted as a silent-wrong-answer defect; and
  declaring one is refused by D56, rightly, which closes the other
  door and is not asked to reopen.

## Why it belongs to reliquary

The same reasoning that moved drive-letter placement out of its
consumers: these are facts about artifacts the provider
materialized, read by machinery the provider owns, in vocabulary
(the letter) the provider's platform layer defines. A consumer that
computed any of it would be mirroring, and mirrors are what D78
just finished punishing.

## However answered, the answer is the provider's

Two things were ruled on the way here (owner, 2026-07-29), and both
shape what is *not* being asked. First, a consumer-side bridge —
Testaferro asserting volume counts of its own to feed
`drive_letters` — existed briefly in a working tree and was rejected
the same hour: a rule held by the vocabulary's owner is a shortcut
with a retirement path, while the same rule adopted by a consumer is
a mirror, and mirrors are what D78 finished punishing. Second, and
stronger: 0.1.0.dev5 already implements enough that no inference
should be needed at all — the at-rest layer reads partitions and
BPBs, the counts are computed and cached for the file verbs, and the
letter map consumes them. How the surface produces its answer —
that reading, or any shortcut of the provider's own choosing (a
directory-source disk being one volume by construction is its
documented rule already) — is an implementation detail Testaferro
does not need to know, and this proposal deliberately does not ask
to know it. What it asks for is the answer.

Testaferro therefore stays pinned to 0.1.0.dev4 — not adopting
0.1.0.dev5 at all — until a release carries the surface.

## What this proposal does not ask

- No client-side letter computation, and no exposure of internals —
  the report's shape and its home are reliquary's design to make.
- No declared volume counts: D56 stands untouched.
- No softening of refusals: an unreadable disk stays unplaced, with
  its reason and its id; a mixed-controller machine stays
  undetermined. The ask is that the *report* say so, in the same
  words the file verbs already use.
- No guest inspection: everything here is P10's read-on-the-host
  source, exactly as the letter map itself uses it.
- No sequencing and no dates: Testaferro pins exactly (D4) and
  moves the pin as its own deliberate act when the release exists.
