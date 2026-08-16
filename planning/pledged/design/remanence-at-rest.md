<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# At-rest file access: remanence rather than the provider

Serves **F16**, and settles its design. The shape is **D23**: the
bytes move to remanence, and an address is guaranteed where
testaferro authored the disk or asked of the guest where it did not.
The alternatives weighed and declined are recorded there.

## What changes

testaferro reaches the guest's filesystems through two provider
calls. `_place()` stages the suite with
`reliquary.put_files(work, location, machine=...)` between
`create_machine()` and `start_machine()`, and `_retrieve_if_kept()`
pulls the location back out with `reliquary.get_files()` after the
stop. Both become **remanence** calls against the image itself.
Reliquary stays the *execution* provider and nothing else.

## Why now: the provider is leaving this ground

The chain today is three deep, and its middle is being removed:

```
testaferro.reliquary._place()
  → reliquary.drives.put_files()      being deleted
    → reliquary.at_rest.py            being deleted
      → remanence                     the dependency reliquary
                                       is also dropping
```

Reliquary is deleting the whole file family and the drive report —
`put_file`, `get_file`, `put_files`, `get_files`, `list_files`,
`describe_drives`, `refresh_drives` — **deleted rather than
deprecated**, with the out-of-band door (`get_machine_dir()`) named
as the sanctioned route in their place. It is dropping the remanence
dependency with them.

So this is not a layer testaferro chooses to shed. It is one being
withdrawn, and four call sites break on the release that lands it:
`_place()`, `_retrieve_if_kept()`, `_default_location()` and
`_placed_letter()`. Until F16 is delivered, D22's enumerated set of
supported reliquary releases stops at the last one carrying those
verbs.

## The address: guaranteed, or asked

**The need splits, and only one half ever wanted a letter.**

*At rest*, writing the staged set wants an **image and a volume**.
Remanence answers that with no letter in sight —
`Session.load_media(path)` → `Medium.partitions()` →
`Partition.filesystem()` → `StorageSpace.write_file()`. This is all
of the actual staging work.

*At run time*, the command typed at the guest wants a **letter** —
and specifically the letter DOS assigned at boot, which is a fact
about the running guest rather than about an image at rest.

The drive map was a host-side prediction of the second thing, and
after both upstreams land there is no such map to read: reliquary
deletes its report, remanence deletes its DOS letter layer
(`MachineReport`, `DriveMapping`, `dos_assignment_rules` and the
rest). testaferro answers the run-time question from the two
authorities that remain, and neither is a derivation:

**Guaranteed, where testaferro authored the disk.** The
zero-configuration guest's system disk is testaferro's own: its
FreeDOS recipe, blueprint and install script are authored in
`assets/` and the install is testaferro's (P17, D10). Staging onto a
disk testaferro authored makes the address a constant it
*guarantees* rather than a fact it reads.

This retires F4's *last letter of the map* policy, and takes its
reasoning with it honestly: that policy existed because
"landing on top of somebody's `C:\` root is the one place a default
must not put a stranger's files". On a disk testaferro authored end
to end there is no stranger, so the objection does not transfer.

**Asked, where it did not.** For a consumer-declared machine, the
running DOS is the only authority there ever was. `_wait_ready()`
already runs a script and reads a machine variable back; the same
channel carries the letter the guest itself found. **Asking is not
deriving** — F4 retired a rule testaferro kept a copy of, and this
is the system answering about itself, which is better evidence than
anything readable at rest.

The same channel answers `_placed_letter()`'s question, which has no
other source: the work-drive fallback's letter shifts with whatever
drives the consumer declared, so there is no constant to guarantee
and no consumer word to take.

## What the change costs, and where P7 lands

A wrong declared `location="D:\TESTDIR"` used to be refused by the
staging call, before the guest booted — F4's invariant that an
address is *stated once, staged against, and spelled*. With nothing
host-side to resolve a letter against, a wrong letter is now found
by the guest instead.

**That reads as a P7 breach and is not one.** P7 already carries the
case: where nothing can be proven, judgement passes to the guest
itself, "honesty about the limit rather than an exception to the
rule". The limit is real — the letter does not exist until DOS
assigns it — and the alternative is refusing against a prediction,
which is worse than refusing late.

What must not be lost is the *quality* of the refusal. A suite run
off a wrong drive fails as a missing program and says nothing
useful, so the guest-side check has to name the address that was
declared and what the guest actually has, exactly as the staging
refusal did.

## What delivery lands beyond the code

- **A P11 amendment.** P11 is in force at two dependencies and says
  "a third dependency is argued, never added"; the interface-change
  rule names adding a third as an in-force cost. This is that
  argument, and delivery moves P11 to three dependencies at named
  seams, with remanence entering D22's enumerated set.
- **No pin to coordinate.** Reliquary is dropping remanence from its
  own dependencies, so the two projects no longer share a compiled
  extension and testaferro's pin answers to nothing but testaferro.
- **A P2 / D16 reading.** `reliquary.py`'s docstring says whatever
  the provider drives underneath "has no name anywhere in this
  package". With reliquary no longer using remanence at all, the
  clause is simply not engaged — remanence is testaferro's own
  dependency, not the provider's underneath — but the at-rest work
  should move out of that module rather than sit in one named for
  the provider.

## Work breakdown

1. Pin remanence; amend **P11** and D22's enumerated set.
2. The at-rest module over remanence: open the image, validate the
   guest address, walk the host tree, write, commit — and its mirror
   over `entries()` / `read_file()` for retrieval. Its own module,
   not `reliquary.py`.
3. The address, both halves: the authored constant on the system
   disk, and the guest-reported letter carried on the readiness
   script's variable, with a refusal that names the declared address
   against what the guest has.
4. `_place()` and `_retrieve_if_kept()` moved onto the module;
   `_default_location()` and `_placed_letter()` retired with the
   drive report they read.
5. The unit tier over the new module, and one integration run
   proving a suite still stages and boots (P10 says why the second
   is not optional).
