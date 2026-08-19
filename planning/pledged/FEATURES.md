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

> **The gate cleared before the pledge.** Reliquary's `exec --check`
> shipped in 0.1.0.dev6 (D89 there, retiring the F26 reliquary had
> entered for this ask), and Testaferro's pin has since moved past it
> to 0.1.0a2 (D4) — for reasons unrelated to this feature, but the
> effect is the same: the provider capability F9 was gated on is
> already in Testaferro's dependency closure. Nothing here is built
> yet; what remains is entirely Testaferro's own side.

Serves **U7** (pledged). Two levels, both declared, both optional.
The per-boot level's design is settled in
[design/in-guest-prep.md](design/in-guest-prep.md); the provider
change it rested on is argued in a downstream proposal to reliquary —
[design/reliquary-proposal.md](design/reliquary-proposal.md) — whose
first ask has since shipped and is already in hand.

- **Per-boot prep**: one declaration now, carrying the keyword and
  INI spellings every declaration has (P16), and not a blueprint
  field — like `provider` and `timeout` it is Testaferro's own
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

  Failure is the provider's to detect, never Testaferro's to
  parse: `reliquary.Session.exec(check=True)` reports each command's
  success (guest-side mechanics belong to reliquary, D2), and a
  consumer's setup programs owe an honest exit code in return.
  **Weighed and declined:** pre-boot validation of
  `setup` commands against the staged files and a shell-builtin
  list. The builtin list is a vocabulary Testaferro would have to
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
downstream proposal argues, with no Testaferro change at all.

The prep vocabulary is new declaration surface and lands through
the interface-change rule; one declaration, three spellings, so it
touches the embedding API, the declaration, and `testaferro.ini`
together (the first, second and third interfaces).

## F18 — `guest_session()`, a lower-level guest primitive

Serves **U10** (pledged). `guest_suite()` is deliberately shaped
around one thing: a suite executable that self-enumerates and
self-reports named sub-tests — the CppUTest model,
`list_tests()`/`run_test()`/`run_all()` under the hood, via a
framework adapter's `list_argv()`/`run_all_argv()`/`parse_run()`
grammar (U1, U6). That shape does not fit a guest-driven test that is
a linear script instead: no natural `Group.Name` decomposition,
nothing to enumerate, nothing for an adapter to parse.

`ReliquarySuiteBackend` (`testaferro/reliquary.py`) already has
everything a scripted test needs, entirely internally: the
zero-config FreeDOS guest built once and cached, a fresh disposable
copy-on-write overlay per guest session, host files staged onto a
live vvfat work drive (`files=`), and `reliquary.Session.exec()` to
run one guest command and read its output back (U2). None of it is
reachable except by going through the suite/framework abstraction —
there is no way today to get a live guest handle and call `.exec()`
a few times in a row from a plain pytest test.

`guest_session()` is a context manager exposing that provisioning
directly, taking the same `files=`/`environment=`/`machine_config=`
this feature's sibling already does, and handing back a guest handle
whose `exec(command, timeout=None)` mirrors
`reliquary.Session.exec()`'s contract. The provisioning internals —
image cache, overlay, vvfat staging, readiness wait — are shared with
`guest_suite()` rather than duplicated; this is a refactor of
`ReliquarySuiteBackend`'s existing internals into a shape both
entry points draw on, not a second implementation living beside the
first. Whether the handle also carries `send_text()`/`wait_text()`/
`screen_text()`, for interactive-style driving that reacts to guest
state rather than just running one command and reading its result —
mirroring what `reliquary.Session` already exposes at that level — is
open; the minimal shape is `exec()` alone.

Purely additive: `guest_suite()` stays the right tool for anything
shaped as a suite of named tests. Joins the embedding API, the first
interface, and lands through the interface-change rule on that
ground alone — no principle or use case needs to change to admit it,
only U10, pledged alongside this feature.

Nothing here waits on a provider capability the way F9 did: the
whole of it is Testaferro's own refactor and one new entry point, so
the debt is entirely Testaferro's own to pay, not gated on anything
outside it.
