<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: BSD-3-Clause
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

## F13 — The first end-to-end run

Serves **U4** (pledged) and **P9**, with U1, U2 and U3 behind them.
**One real suite, booting one real machine, reporting one real
failure.** No
guest has run since the migration to the blueprint model (D4), so
nothing this project says about a guest has ever been observed. The
feature adds no capability — it converts claims into evidence, which
is why its absence is what keeps root `USE-CASES.md` from existing at
all.

**One feature and not two**, because a guest suite with nothing to run
it and a tier with nothing to run are each meaningless alone. Its work
items therefore carry the one ordering that binds: the suite, the
tier, then the run.

Three things were left to decide at the pledge and are decided here —
the first of them reversed, once its open question turned out to have
been closed all along.

**The suite is a real CppUTest build, not an authored stand-in.**
CppUTest ships DOS support of its own — `platforms/Dos/` and
`src/Platforms/Dos/UtestPlatform.cpp` upstream — built with Open
Watcom for **16-bit real mode**: `wcl -bt=dos -ml -zm`, linked
`wlink system dos`, with memory-leak detection and the standard C++
library disabled. Real mode is what makes it cheap here, because
there is no DPMI host to stage beside the suite: it runs on the same
FreeDOS boot floppy zero configuration already downloads. The same
sources build a host twin (`-bt=nt`), so a host-built enumerator
arrives for free rather than as separate work.

*This reverses the call made when F6 was cut.* The split issued
**F14** to hold what looked like an open feasibility question —
whether CppUTest builds for a DOS target at all — and planned an
authored stand-in here meanwhile. The question was already answered
upstream, so F14 is absorbed into this feature and **its number
retires unreused**, having never named separable work. The gain is
not merely one fewer entry: a stand-in testaferro authored would
leave the grammars answering to themselves, where a real build
discharges the cost **P9** states against itself in the same run that
proves the machinery.

**The tier is stdlib `unittest`, under `tests/integration/`, skipped
unless asked for.** Tests here are stdlib `unittest` and that
constraint is not spent on this; `skipUnless` on an environment
variable is how the existing suite already gates on reliquary and
pytest being installed, so the tier is that mechanism one step
further. The unit run therefore stays exactly as cheap as P10 requires
it to be, and stays cheap by default rather than by discipline. Root
[AGENTS.md](../../AGENTS.md) mentions `pytest -m integration`; that
describes a *consuming* project's run and is not this tier, and the
wording is corrected with this work.

**A checked-in binary is covered in `REUSE.toml`.** It cannot carry an
SPDX header, and the licensing rule admits exactly that case. The
suite's source and its build recipe are checked in beside it, so the
binary is reproducible rather than magical, and Open Watcom is a
*maintainer's* prerequisite rather than a dependency in **P11**'s
sense — nothing a consumer installs, and that distinction wants
saying wherever the recipe lands, because it reads the other way too
easily. **P12 holds throughout**: this fixture is testaferro's own,
and neither it nor the recipe names a consuming project. Where the
CppUTest flags need a source, that source is CppUTest's own
`platforms/Dos`, which is a public fact about the framework.

**What CppUTest itself costs** is the one thing left open, and
deliberately: whether its sources are vendored here, or the fixture is
built elsewhere and only the binary lands, is a question about this
repository's weight rather than about the run, and it is answered when
the work is picked up. Neither answer changes anything above.

## What is built, and what this is waiting on

Most of it exists. `tests/integration/guest/` holds the suite — a real
CppUTest build for 16-bit DOS, its source and its Open Watcom makefile
beside it — and `tests/integration/` holds the tier, stdlib `unittest`
and skipped unless `TESTAFERRO_INTEGRATION` says otherwise. **A guest
has run it**: it boots, the executable arrives on the work drive at
`D:`, enumeration comes back and parses, a batched run and a single
run both come back, and the failure carries the guest's own file and
line to the host.

Two defects fell out of that, which is the feature doing its job:

- **Ours, and fixed.** A failure's message ran on past its end,
  because the grammar ended one at a blank line and the transport
  drops blank rows. Exactly the cost P9 states against itself.
- **The provider's, and not ours to work around.** The first command
  after boot returns the boot banner rather than its own output —
  `exec()` matches a prompt that was already on screen. Reported as
  `ferroteca/reliquary#6`. A `sleep` before the first command would
  close this today and is precisely the defensive workaround **P1**
  forbids, so the tier waits instead.

**That race is the whole of what stands between this and delivery.**
Until it lands upstream the tier's cases need a throwaway first
command to pass, which is not something to check in — so the feature
stays pledged, and the evidence for its delivery goes in the commit
that finally moves it.

**What the run must show** is the whole point, so it is enumerated:
the guest boots from the cached image, the work drive carries the
executable in at the letter testaferro named, `-ln` comes back and
parses, a run comes back and parses, one test passes and one fails,
and the failure surfaces as the guest's own file, line and assertion.
Anything it shows that testaferro did not expect is the feature
earning its keep — the screen-capture questions raised while D19 was
being built (whether `parse_list`'s strictness survives real capture,
and whether an 80-column wrap corrupts an id before it fails) can be
answered no other way.
