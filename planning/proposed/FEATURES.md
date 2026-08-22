<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# Proposed features

> **Status:** drafted, not pledged. **Nothing is worked from here.**
> Large capability the project may want, each carrying whatever
> design is already settled about it — migrated from the retired
> `ROADMAP.md` when Testaferro adopted the planning model (D7). A
> feature arrives in `pledged/FEATURES.md` by being moved there, and
> the commit that moves it is the record of the pledge.

Each feature carries an **F-number**: the handle a dependency, a
commit or a decision points at. F-numbers are the handles of *work*,
so they **evaporate on delivery** — the item stops existing, its
number retires unreused, and gaps in the sequence are history rather
than a promise. **The numbers carry no order and no date**; F1 was
merely the first issued, and is already a gap.

**A feature must fit in one sprint**, and the bound bites at
**the pledge**, not here. Large, shapeless capability is welcome in
this file; cutting it into implementable pieces is part of what
pledging it means, and a split retires the parent's number for a
fresh one per piece. Entries flagged below as too large must be cut
at the pledge.

**Five numbers here are retired by split**, which is what the sprint
bound does at the pledge: the parent goes and each piece takes a
fresh one, because sub-numbering would build a hierarchy and
hierarchy is how a feature list turns into a schedule.

- **F5**, a second guest platform binding: shapeless by its own
  admission until a platform was named, and cutting it meant naming
  one. **F23** names OpenBSD — the one non-DOS guest reliquary holds
  a recipe for — and stays proposed, blocked on the provider's
  `exec` for that platform. `win9x` and `winnt` are not a remainder
  of F5; each takes a fresh number if and when it is named.
- **F1** (D9): the backend-resolution seam became F7, the
  command-line surface became the plugin, F8, and the `run` verb
  died with the wrapper it named — a lifecycle CLI survives inside
  F2, whose verbs are not test runs. Both pieces were pledged and
  both have since been delivered, so both numbers have evaporated
  in their turn.
- **F10**, the test-environment vocabulary: too large as written, so
  pledging it meant cutting it. The noun at the consumer surface
  became **F11** and the provider axis became **F12**; both have since
  been delivered and both numbers have evaporated with them, which is
  the cut working — two bounded pushes where the parent was one
  shapeless one. The binding rename it also carried had already
  landed on its own (D16).
- **F6**, the integration tier: too large as written, and it grew a
  dependency the project did not have. Its own text named its first
  slice, and that slice was **F13** — one real suite, one real
  machine, one real failure — **delivered, its number evaporated with
  it**. What F6 could not carry became **F14** (CppUTest's own
  output) and **F15** (the remaining journeys), the latter since
  split in its turn, below.

**F14 retired without ever being separate work.** It was issued to
hold an open question — whether CppUTest builds for a DOS target at
all — which turned out to be answered upstream, in CppUTest's own
`platforms/Dos`. With that settled there was nothing left in F14 that
F13 was not already doing, so it was absorbed and its number retires
unreused like any other. A number is a handle for work; where the work
turns out not to exist apart, neither does the handle.

- **F15**, the remaining journeys: cut at the pledge to the one
  journey nothing had exercised, **U5**'s parallelism, which became
  **F22** — pledged and delivered in one change, the F20 precedent —
  and is gone in its turn. The other half, U3's declared environment
  booting for real, had already been run by the tier (a
  `testaferro.ini` beside a project, claiming a suite and booting the
  environment it names, in `tests/integration/test_guest_run.py`),
  so no work remained in it to carry a number; what U3 itself still
  owes is its own clauses, and it stays drafted here, unowed.

**F3 has left this file too**, the long way round: pledged, withdrawn
the same day when its batching turned out to need a sixth
framework-adapter callable P4 did not allow (D24), and pledged again
once P4 was amended to admit an optional one (D29) — pledged and
delivered in one change, as F20 and F22 were. Its number is retired
with it.

A gap in the numbering here is where one of them went.

**F9 and F18 have left this file too**, each pledged alongside its
use case — F9 with U7, F18 with U10 — not retired, not split at the
time, just moved. Both have since delivered and retired, arming U7
and U10 with them. **F2 left last**, pledged and delivered in one
change (D30); U8 armed the same day once its one short clause was
amended to say what F2 built (D31).

## F23 — An OpenBSD guest, through the reliquary binding

Serves **U9**'s plural growth (the clause D25 severed from the
pledge: a second standard environment, "as guests grow") and **U6**
(the framework adapter is unchanged by what OS runs it). Cut from
F5 by naming the platform: **OpenBSD**, because it is the one
non-DOS guest reliquary already holds an authored recipe for — its
codex carries `openbsd.rlqb` and `openbsd-install` (OpenBSD 7.9
amd64, autoinstall over reliquary's run-scoped HTTP server) — so
the provisioning half D2 puts on reliquary's side is the half that
already exists there.

**Blocked on reliquary, and exactly where.** Reliquary's `exec`
refuses every platform but DOS by rule id
(`platform.verb-not-implemented`, "DOS is the delivered workflow"),
and its README says the same: other platform names reserve the QEMU
lifecycle and raise until an adapter is implemented. Every
Testaferro guest operation is one `Session.exec()`, so until an
OpenBSD adapter gives that verb — plus readiness and output capture
— the same contract DOS has, there is nothing here to bind (D2). This
entry is therefore **not pledgeable** until that release ships; it
names what to build the day it does. The prerequisite is the
provider's own work and carries the provider's own handle, quoted
here when it exists rather than minted (SEQUENCES.md).

**What Testaferro builds, once unblocked — and it is thin:**

- **`binfmt`: ELF is claimed by declaration, never inferred.** An
  ELF header proves Linux-or-BSD and nothing finer; `classify()`
  already reports it as `an ELF x86-64 (Linux/BSD)` with platform
  `None`. That stays: a scan never claims an ELF, and a named file
  is claimed only when a declaration's `platform = openbsd` says a
  guest runs it (P7, the same rule a host-runnable PE already gets).
  Nothing new is sniffed.
- **The reliquary binding serves a second platform.** `PLATFORMS`
  becomes `("dos", "openbsd")`; what differs is confined to the
  guest-OS aspect the binding already owns (D16): the command line
  spelled from argv tokens is a shell's, the work drive is whatever
  reliquary's OpenBSD adapter attaches and the *location* is its
  mount point rather than a letter — `_letter_map()` is DOS's and is
  not asked — and `_logical_lines()`'s 80-column rejoin applies only
  if the adapter's capture is a text screen. The argv budget is the
  shell's, not COMMAND.COM's 126. Readiness is the adapter's script,
  authored in `assets/` as `freedos-ready` is (P17).
- **A second standard environment, `"openbsd"`** (U9's plural
  clause): a catalog entry naming the platform, the system disk
  built once by the codex recipe exactly as FreeDOS is (D20) and
  kept in the cache — an install measured in tens of minutes, paid
  once, never by a test run (D10). `persist=` works unchanged, which
  is where an install of that size most wants to live (U8).
- **The framework adapter changes nothing** (P4, U6): CppUTest's
  argv and grammar are the same on OpenBSD, and the binding is what
  decides how tokens become a command line.

**The proof is the cost, and it is an open question.** The integration
suite is `tests/integration/guest/SUITE.EXE`, built with Open Watcom
for DOS; an OpenBSD build of the same `SUITE.CPP` needs clang
*inside* an OpenBSD guest, or a cross toolchain the host does not
have. Two routes, neither decided: build it in the guest as part of
the standard environment's recipe and check the binary in as the
DOS one is (licence-clean — no Watcom runtime — so the BSD carve-out
in that directory would not apply to it), or build it in the
integration fixture on every run and pay the minutes. One real-boot
case is owed either way: the suite enumerates, runs, and reports its
deliberate failure with the guest's own file and line.

**Out of scope, by the cut:** DOSBox-X (it is DOS by definition);
`win9x` and `winnt`, which reliquary names in its schema and holds
no recipe for — a fresh number when one is named, not a residue of
this one; any in-guest agent or listener (D2, D1); and a
`guest_session()` over OpenBSD beyond what `exec()` gives — ssh is
reliquary's to offer if it ever is.

**Sprint bound:** fits once unblocked, on condition the proof route
is settled at the pledge — building a toolchain story is the part
that could not.
