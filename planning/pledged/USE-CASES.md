<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# Pledged use cases

> **Status:** pledged — owed by the project, and not yet delivered.
> The project has undertaken these and says nothing about when. An
> entry leaves for root `USE-CASES.md` only when the code meets it
> **in full**, so this file is the gap between the pledge and the
> delivery made visible. Numbering comes from one global U-sequence,
> never reused, and an entry keeps its number every time it moves.

**Nothing here is a draft any more.** Citing a U-number in this file
names an undertaking — stronger than citing
[../proposed/USE-CASES.md](../proposed/USE-CASES.md), weaker than
citing the root list: the project owes it, and does not yet claim the
code meets it.

- **U9 — A standard environment, by name.** Between nothing and a
  declaration sits a name: `machine="freedos"` selects a standard
  environment Testaferro itself curates — an authored machine
  document and a once-downloaded cached image, today's
  zero-configuration machine made nameable. Resolution runs project
  declarations first, then the standard catalog (D10), and never the
  user's reliquary home (D6): a test run depends only on state
  Testaferro authored or the project checked in.

  Resolution and the catalog are built and unit-tested — `catalog.py`
  and its guard test, `machine="freedos"` resolving since F7 (D10,
  D18) — so what this pledge owes is not the mechanism but the proof:
  a real guest boot naming `"freedos"` explicitly, the way every other
  proven journey here was proven, rather than only through the
  zero-configuration default's own inference doing the same job
  unnamed. *(Requires F19.)*

  **Pledged severed from its own plural growth** (D25): a second
  named environment waits on a second guest platform (F5), which
  waits entirely on reliquary (D2) and is neither owed nor pledged
  here. This pledge covers the singular case alone — one name,
  resolving as documented, proven by F19 — and stays true whether or
  not Testaferro ever grows a second guest.

U9 cites F19, and both are pledged in this same commit — the map's
rule against a pledged item resting on a proposed one
([../README.md](../README.md)) is met by pledging the prerequisite
rather than by severing the reference. Neither arms alone: F19's
delivery is what U9 waits on.
