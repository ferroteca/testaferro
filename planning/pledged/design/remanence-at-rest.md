<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# At-rest file access: remanence rather than the provider

Serves **F16**, and settles its design. **The shape is settled**
(owner, 2026-08-16): the address stays the provider's answer and
only the bytes move. The alternative weighed and declined —
staging into an image testaferro owns before any machine exists —
is recorded in [../../DECISIONS.md](../../DECISIONS.md) D23, with
what would reopen it.

## What changes

testaferro reaches the guest's filesystems through two provider
calls. `_place()` stages the suite with
`reliquary.put_files(work, location, machine=...)` between
`create_machine()` and `start_machine()`, and `_retrieve_if_kept()`
pulls the location back out with `reliquary.get_files()` after the
stop. Both become **remanence** calls. Reliquary stays the
*execution* provider and nothing else.

## The change removes a layer; it does not add a capability

The chain today is already three deep:

```
testaferro.reliquary._place()
  → reliquary.drives.put_files()      machine resolution, machine
                                       lock, guest-address parse,
                                       letter → drive → volume
    → reliquary.at_rest.py            reliquary's recognition claim,
                                       whole-disk rule, error
                                       vocabulary (P27 there)
      → remanence                     opens the image, walks the
                                       partition table, writes FAT,
                                       commits under an undo journal
```

Remanence already writes every byte testaferro stages. What is at
issue is not who can write a FAT volume but **who owns the policy
between a guest address and a sector**.

## The split: the address is asked, the bytes are written

**testaferro does not resolve drive letters.** F4 retired letter
inference deliberately, and taking address resolution back would be
that inference returning under another name. The invariant F4
settled stands unchanged — *an address is stated once, staged
against, and spelled* — and a wrong declared address must still
fail with the provider's own refusal naming the cause, because the
consumer named that address and is the only one who can correct it.

So testaferro asks reliquary **where the location resolves to**,
takes its refusal when the address is wrong, and then does its own
open, walk, write and commit through remanence.

That splits the eight things reliquary's layer holds today into
what is asked for and what is taken on:

**Asked of the provider** — one surface addition, argued upstream:

1. **Address resolution** — a guest address to the host image file
   and the volume within it, off the same letter map
   `describe_drives()` already derives, refusing exactly as
   `put_files` refuses today.
2. **The hold** — a way to take the machine for the length of the
   write, so nothing else opens the image behind testaferro.
   Reliquary's own P27 refuses a hybrid because it leaves two
   authorities for the same disk facts; the objection does not
   weaken for being raised from outside the provider.

**Taken on by testaferro:**

3. **Guest-address validation** — a name a DOS guest could not type
   is refused, never mangled. Cheap, and testaferro already knows
   DOS 8.3 (`_STAGED_DIR` is eight characters for that reason).
4. **The tree walk.** `put_files` walks a host directory and
   creates guest directories as it goes; remanence's surface is
   `make_directory` / `write_file(path, contents)` / `commit`, one
   file at a time. A loop, and the retrieval direction is its
   mirror over `entries()` / `read_file()`.
5. **The error vocabulary.** `_place()`'s fallback is keyed on
   `reliquary.ReliquaryError` and `_retrieve_if_kept()` swallows
   the same class; both become `remanence.Error`, except where the
   failure is the *address*, which stays the provider's refusal.

**Already remanence's, and inherited rather than rebuilt:** the
recognition claim over FAT and MBR, the whole-disk rule, and the
undo journal beneath `commit()`.

## What delivery lands beyond the code

- **A P11 amendment.** P11 is in force and says pytest and
  reliquary "are the whole dependency list… A third dependency is
  argued, never added"; the interface-change rule names *adding a
  third dependency* as an in-force cost a change is refused
  against. This is that argument, and delivery moves P11 to three
  dependencies at named seams.
- **A P2 / D16 reading.** `reliquary.py`'s docstring says whatever
  the provider drives underneath "has no name anywhere in this
  package". Remanence is not the provider's underneath in the sense
  that clause forbids — it is a first-party library reliquary and
  testaferro consume as peers — but the clause is written broadly
  enough that delivery has to say so, or move the at-rest work out
  of that module.
- **The pin agreement.** Reliquary pins remanence to one exact
  release (`remanence==0.0.1a5` today) and its P27 makes a pin move
  a verification event rather than a substitution. testaferro's pin
  must agree release for release: two different pins in one
  environment is an unsatisfiable install, not a version skew, and
  remanence is a compiled extension so there is no vendoring around
  it. D22 already governs how the supported set is claimed —
  enumerated, never bracketed — and this is a second dependency
  claimed the same way.

## The gate

**This feature cannot be completed until the provider offers items
1 and 2**, and reliquary offers neither today: `describe_drives()`
reports `key`, `medium`, `slot`, `media`, `materialize` and the
geometry, none of which is a host path, and the write lock
`put_files` takes is internal. Reconstructing the path from the
machine home's layout is refused — that is the coupling D16 and P2
exist to prevent.

So the pledge is gated on a downstream ask to reliquary, argued
there and landed there first, the way F9's provider changes already
are. Until it lands, nothing in this feature is worked.

## Work breakdown

1. The upstream ask: reliquary exposes the resolved image path and
   volume for a guest address, and a hold for the length of a
   stopped-machine write. Argued in reliquary's own planning.
2. Pin remanence, in agreement with reliquary's pin; amend **P11**
   and D22's enumerated set with it.
3. The at-rest module: open, validate the guest address, walk,
   write, commit; and its mirror for retrieval.
4. `_place()` and `_retrieve_if_kept()` moved onto it, with the
   declared-address refusal still the provider's and the defaulted
   address still falling back to the work drive.
5. The unit tier over the new module, and one integration run
   proving a suite still stages and boots (P10 says why the second
   is not optional).
