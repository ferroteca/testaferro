<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# Test placement: the declaration surface and its defaults

> **Delivered 2026-07-30, and F4 retired with it.** What follows is
> the design as argued, kept because the reasoning is the record;
> the code is now the truth about behaviour. Four things this
> document left "settled at the pledge" were settled there: the
> default location is the **last** letter of the map with the
> staged set in `\TESTS` under it (eight characters, because DOS
> 8.3 reads it back); the placeholder is **`{location}`**; the
> accessor is the **`location` property** on the binding's backend;
> and `--testaferro-keep-guest-home` **retrieves the location** into
> `retrieved/` under the kept home, which is how the look-in-a-folder
> story survives staging moving into the image. This file describes
> a delivered interface, which `planning/README.md` says nothing here
> should — where a delivered norm finally lives is the open question
> in [../../DECISIONS.md](../../DECISIONS.md), and this moves when
> that is answered.

Serves **F4**, and settles its design (owner, 2026-07-29). The
trigger was concrete: reliquary 0.1.0.dev5 (D78 there) stopped
assuming one volume per disk, and with the assumption went the only
public way testaferro had to *infer* a drive letter before boot —
34 unit tests fail on the pin move, all from `_work_drive()`. The
design answers with the correction reliquary itself made, applied
downstream: **the letter stops being inferred anywhere.**

## The surface

The consumer provides four things; each is independently declarable
and each has a derivable default, so a single suite executable with
nothing else said still runs (P8):

| declaration | declared | defaulted (single exe) |
|---|---|---|
| machine | `environment=` / `machine_config=` (D4, D18) | the zero-configuration guest |
| files | `files=` — the set staged into the guest | the executable alone |
| location | a guest address: `location="D:\TESTDIR"` | chosen over the enumerated drive map (below) |
| program | a guest address of what to run | location + the executable's own name |

`files`, `location` and `program` are **testaferro's own words**,
said beside the machine spec and never inside it — exactly as
`provider` and `timeout` are (D18): reliquary's document has no
field for what a test run stages. Each carries the keyword, ini and
command-line spellings every declaration has (P16). The framework
adapter still composes argv onto the program (P4, D17), so
`program=` names what to invoke, never how. Both entry points — the
collection plugin and the facade — resolve all four through the
same seam.

## The invariant: an address is stated once, staged against, spelled

Today's flow infers: compute the letter from declared facts, stage
through a host-directory snapshot, spell the command from the
inference. The new flow declares: **state the address (by the
consumer or by default), stage to that address with the provider's
at-rest file verbs, spell the command from the same address.**

- A declared address is *validated by staging*: `put_files` resolves
  it against the actual disk, at rest, at the one moment the answer
  exists — and a wrong address fails before any boot, with
  reliquary's own refusal naming the cause (P11 honored by
  inheritance). A machine whose disk holds two volumes — refused
  outright under the old assumption — becomes simply *supported*:
  the consumer's address plus the provider's reading replaces the
  guess.
- A defaulted address is *chosen over the enumerated map*: testaferro
  asks the provider what drive letters the created machine actually
  has, then applies its own policy to pick one. The facts are the
  provider's; the choice is testaferro's; nothing is inferred by
  either. The map is the one provider capability this design still
  lacks — the letter-map slice of the drive-geometry report argued
  downstream in
  [reliquary-drive-geometry-proposal.md](reliquary-drive-geometry-proposal.md).

The leading default policy, settled finally at the pledge: the last
letter of the map — the drive testaferro appended when it appended
one, the boot disk's own volume when it did not — with the staged
area a directory under it that testaferro names.

## The placement is reported, not merely performed

A consumer must be able to learn **where their harness landed** —
the location as resolved, whether they declared it or testaferro's
default policy chose it for them. Placing files somewhere a
consumer cannot name afterwards would leave their own harness logic
— setup steps that reference staged files, tooling that collects
what a run wrote beside them — guessing at the very thing this
design exists to make declarative. The contract:

- **One question, one vocabulary, one answer.** The answer is a
  guest address (`D:\TESTDIR`), the same terms a declaration uses —
  the symmetry that makes the surface learnable: what you could
  have declared is what you are told. And it is the *same* answer
  whether the consumer stated it or testaferro chose it; who chose
  is deliberately not part of the answer, the courtesy this design
  asks of the provider one seam down applied at its own surface —
  the asker learns the fact, never the mechanism.
- **The staged set keeps its shape beneath it.** Files keep their
  names and relative paths under the location, so the resolved root
  plus the declared set is the whole answer — no per-file map is
  needed or offered.
- **In-guest references resolve by placeholder.** Declared text
  that must name the location before it is known — a setup command
  naming a staged file, a `program=` under a defaulted location —
  uses substitution testaferro already speaks: `{stem}` and
  `{name}` in the enumerator option are the precedent, and the
  location joins that vocabulary, substituted when testaferro
  knows. Spelling settled at the pledge.
- **Host-side code asks after resolution.** The embedding surface
  answers from the moment the location is settled — immediately for
  a declared address, once the provider's map is read for a
  defaulted one — and refuses before that rather than guessing,
  which is the same shape `_work_drive` holds today for a letter it
  cannot determine. The exact accessor is the pledge's to settle;
  the contract that there is one, in guest terms, is settled here.

## Staging moves to rest

The work drive D5 supplied was a mechanism for getting bytes into
the guest before there was a writer for images; reliquary
0.1.0.dev5 ships the writer (its file verbs mount a FAT volume in a
stopped machine's drive image, with a commit point behind every
write). Staging therefore becomes:

    create_machine → put_files(location, …) → start_machine

**The window is verified at the tip, not assumed**: a created,
never-booted machine's phase is `ready` (machines.py:433), and the
at-rest gate admits exactly that phase (machines.py:980). An
integration case must still prove it end to end when this is built.

D5's constraints dissolve rather than transfer: "the backend
snapshots a host directory at attach, so staging cannot be lazy"
becomes "staging happens at rest, between create and start" — a
narrower rule that no blueprint-authoring code can quietly break. A
testaferro-supplied directory-source drive may survive as an
implementation detail where a machine offers no writable room (a
tester's write-protected floppy), but the *surface* stops promising
one: what is promised is the location.

## What it costs

- **`--testaferro-keep-guest-home` changes meaning.** With no host
  work directory, inspecting what a run left behind means reading
  the guest's drives at rest (`get_files`) after stop, not opening a
  folder. The option survives; what it keeps is the guest home and
  the machine's images, and the design owes its exploration story a
  spelled-out answer at the pledge.
- **The pin waits on the provider, deliberately.** Staging needs
  0.1.0.dev5; the default-location map needs the release carrying
  the downstream ask — however the provider chooses to answer it,
  that being an implementation detail this side never learns (the
  proposal records why a consumer-side bridge was rejected).
  testaferro stays on 0.1.0.dev4 until then, and the pin move (D4)
  lands with what it waited for.
- **Interface changes, enumerated for the vetting rule**: the
  embedding API and `testaferro.ini` gain three declarations; the
  machine declaration is untouched; the cache layout loses the
  staged work area; the pytest items and `Backend` ABC are
  untouched. INTERFACES.md's process applies at the pledge.

## Relation to the record

- **Supersedes D5 when it lands** — the hostdir work drive was the
  declined alternative's cost paid in mechanism, and the eventual
  shape D5 itself named (F4) is this design.
- **F9's `files=` is this `files=`** — one declaration, not two
  spellings. The in-guest-prep design reads unchanged with "the work
  drive" generalized to "the location"; its provider asks are
  separate and stay in
  [reliquary-proposal.md](../../pledged/design/reliquary-proposal.md),
  pledged now alongside F9.
- **P8 stays armed by construction**: every default above is
  derivable without guessing, which the letter inference never was.
- **U2, U3 unchanged in promise**; U3's tester-owned floppy keeps
  its read-never-written guarantee (P5) because staging writes only
  testaferro's copy.
