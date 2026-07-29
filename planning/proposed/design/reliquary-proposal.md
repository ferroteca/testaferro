<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: BSD-3-Clause
-->

# Proposal: what driver-testing guests need from reliquary

A **downstream proposal to reliquary**, from testaferro, its
consumer. It serves F9 (in-guest harness prep, designed in
[in-guest-prep.md](in-guest-prep.md)) and the machine facts the
same consumer class declares, and it is written the way
consumer-side input should be: the shape that costs the consumer
least, the requirements it cannot meet alone, and nothing the
provider owns asked back.

Written against reliquary 0.1.0.dev4 — testaferro's exact pin
(D4) — and checked against reliquary's 0.1.0.dev6 tip. Every code
claim below was verified in both and holds identically in both.

Three asks. F9 hard-depends on the first alone; the second and
third serve the sibling fact its design names — a machine that
exposes the device a driver under test drives — which reaches
reliquary as blueprint fields testaferro passes through untouched.

## 1. `exec()` reports whether the command succeeded

`exec()` returns the visible screen as rows and deliberately reads
no meaning into it. That honesty leaves a caller running a *setup*
command — one whose output is nothing and whose success is
everything — with no channel at all: success and failure both come
back as rows.

The ask: an opt-in way for `exec()` (or a sibling verb) to report
whether the command it ran signalled failure. The mechanism
reliquary owns already points the way: after the command, the
interaction layer probes with `IF ERRORLEVEL 1` and a sentinel echo
of its own composing, and reads its own sentinel back. `IF
ERRORLEVEL` is portable across every DOS shell in a way
`%ERRORLEVEL%` expansion is not. This does not read meaning into
the guest's output — the probe's answer is text reliquary itself
composed, exactly as the readiness idiom has the caller's script
set a variable and read it back. It belongs to reliquary because
the DOS interaction surface is reliquary's: the same reasoning
that moved drive-letter placement out of its consumers.

One honest limit to record: `COMMAND.COM` leaves ERRORLEVEL
unchanged on `Bad command or file name`, so a mistyped command is
not caught by the probe. Whether to additionally recognize the
shell's own error text is reliquary's call to make or decline —
its platform layer is the only defensible home such spellings
could have. testaferro will not curate them either way.

## 2. A `devices` axis, judged at assignment

What a driver-testing consumer means by "the engine must be QEMU"
is not an engine preference — it is "**this machine must contain
this device**". Reliquary's vocabulary cannot say that today:

- `Requirements` is a closed vocabulary of `control_planes`,
  `media`, `controllers`, `materialize`. There is no hardware
  axis, so a device need can never reach `assign()` and can never
  influence which backend is chosen.
- The nearest live mechanism is the `backend` pin — binding, and
  failing closed by name, which is right — combined with
  `backend-settings` for the device flags, which is the wrong fact
  recorded (see the next ask) and over-constrains besides:
  VirtualBox genuinely offers virtio-net, and a pinned `qemu`
  forecloses it forever.
- `Capabilities.vvfat` shows the failure mode to avoid: a
  capability "judged where the drive is rendered rather than at
  assignment" fails late rather than never.

The ask: a `devices` blueprint machine field — a **closed, curated
vocabulary**, grown one name at a time as demand arrives
(virtio-rng first; virtio-console and virtio-net are already
visible behind it) — with `devices` tuples on `Requirements` and
`Capabilities`, judged in `unmet()` like every other axis, at
assignment, against the whole blueprint. Each adapter reports what
it can provide and renders what it reported: QEMU renders
`-device virtio-rng-pci`; an adapter offering nothing reports an
empty tuple, which is honest and free. A machine declaring a
device nothing available can provide fails closed at preflight,
naming the device — an up-front, legible refusal, delivered by the
principle reliquary already holds: capabilities are reported,
never emulated.

This keeps blueprints portable where a pin cannot: the declaration
names the need, and assignment finds any backend that meets it.

## 3. Adapters honor `backend-settings`

Reliquary's documentation promises that `backend-settings` sections
are the escape hatch for backend-specific configuration, that "the
available keys in each backend's section are defined and documented
by that backend adapter", and that each adapter "validates its
section"; the reference's own example is `qemu.args`, and the
http-serve spec reasons about `backend-settings.qemu.args` as a
live thing. The code parses the field, validates the backend names,
carries the sections into machine state verbatim — **and no adapter
ever reads its section**. The QEMU launch renders memory, drives
and boot order, nothing else, and settings do not narrow assignment
despite the reference saying they do. The field validates,
persists, and does nothing, in the pin and at the tip alike.

The ask: implement what the documents already promise, or re-scope
the documents — with a strong preference for implementing, because
the curated `devices` vocabulary needs an escape hatch for
whatever it deliberately does not name, and this is the documented
one.

## Sequencing, from the consumer's side

testaferro pins reliquary exactly (D4), so nothing here asks for
coordination: reliquary ships when it ships, and testaferro moves
its pin as the deliberate task the pin exists to make deliberate.
The `devices` field needs no testaferro release at all — a
declaration passes through untouched the day the vocabulary
exists. No order beyond that is asked, and no date is.

## What this proposal does not ask

- Nothing reliquary's consumers could do themselves: staging,
  setup vocabulary, and everything else in F9 stay on the
  consumer's side of the seam.
- No open-ended device taxonomy — a closed vocabulary, curated by
  reliquary, grown by demand.
- No emulation of a missing device, and no softening of
  fail-closed assignment.
- No guest agent, no in-guest listener.
- No new engine-selection API: the `backend` pin already binds and
  fails closed, and this proposal asks only that what surrounds it
  become true.
