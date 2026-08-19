<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# Pledged features

> **Status:** pledged — owed by the project, and not yet delivered.
> The project will do these and says nothing about when: **the
> absence of order is uniform**, and whoever picks work up picks
> whatever they like. The one ordering that binds runs *inside* a
> feature — the work items delivering it have to be done to complete
> it.

**F-numbers are the handles of work, so they evaporate on delivery**:
the item stops existing, its number retires unreused, and gaps in the
sequence are history rather than a promise. **A feature here fits in
one sprint** — the bound bites at the pledge, which is why the large
and shapeless entries stay in
[../proposed/FEATURES.md](../proposed/FEATURES.md). Every entry cites
what demands it.

## F9 — In-guest harness prep

Serves **U7** (pledged). Two levels, both declared, both optional.
The per-boot level's design is settled in
[design/in-guest-prep.md](design/in-guest-prep.md); the provider
changes it rests on are argued separately, as a downstream proposal
to reliquary —
[design/reliquary-proposal.md](design/reliquary-proposal.md) — so
this feature waits on the first of those changes and on the
deliberate pin move it implies (D4).

- **Per-boot prep**: one declaration now, carrying the keyword and
  INI spellings every declaration has (P16), and not a blueprint
  field — like `provider` and `timeout` it is testaferro's own
  word, said beside the machine spec, never inside it.

  **`files=` shipped with F4** and is not owed here. It was always
  one declaration rather than two spellings, and F4's delivery is
  where it landed: host paths staged beside the suite, at the
  location, before boot. What it buys this feature is unchanged —
  everything arrives in one guest directory, so a setup command
  names a staged file with no path and no letter, and
  `{location}` spells that directory for the commands that need it
  written out.

  `setup=` — commands run in the guest in the order given, once
  per **guest session** (D15) — every guest session, an
  enumeration boot included, since a suite that needs its TSR to
  run needs it to enumerate too — after the readiness wait,
  before anything else. Ordering within the list is the caller's.
  A setup command that fails ends the session and reports once,
  in the existing `GuestOutputError` shape: the command sent and
  the screen that came back.

  Failure is the provider's to detect, never testaferro's to
  parse: the downstream proposal asks reliquary's `exec()` to
  report each command's success (guest-side mechanics belong to
  reliquary, D2), and a consumer's setup programs owe an honest
  exit code in return. **Weighed and declined:** pre-boot validation of
  `setup` commands against the staged files and a shell-builtin
  list. The builtin list is a vocabulary testaferro would have to
  keep on the shell's behalf — the kind of mirror the drive-letter
  inference paid to delete — and the staged-file check refuses
  legitimate commands naming programs on the system disk, a
  tester's floppy, or `PATH`. Keeping `files` and `setup`
  agreeing is the caller's own obligation, and a typo surfaces as
  a loud setup failure rather than a pre-boot refusal.

- **Boot-level support**: a device driver or installed component
  that must exist before the guest OS finishes booting. No
  post-boot step can add it: it rides a tester-authored boot image
  (U3) or a provisioned platform — a full machine document whose
  scripts bake a disk, the provider owning the in-guest install
  work (D2), viable per-run only where the machine persists (U8,
  F2).

The sibling fact — the *machine* exposing the device a driver
under test drives — is deliberately not this feature. It is a
machine fact, declared in the environment and passed through
untouched exactly as every blueprint field is (D4), so it becomes
expressible the day reliquary ships the `devices` vocabulary the
downstream proposal argues, with no testaferro change at all.

The prep vocabulary is new declaration surface and lands through
the interface-change rule; one declaration, three spellings, so it
touches the embedding API, the declaration, and `testaferro.ini`
together (the first, second and third interfaces).
