<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# The sequence ledger

The planning root holds what does not move ([README.md](README.md)),
and this file is the handle ledger: **the next number to issue for
every handle sequence Testaferro carries**. Issue from here and
advance the mark in the same edit, on `main`.

**These lines are not status columns.** Each records what its
sequence has spent, and says nothing about what was done, by whom,
or when. A number, once issued, is never reissued — a struck task or
a delivered feature takes its number with it, and gaps in a sequence
are history rather than a promise.

Why a ledger, when the files could be counted: **a search sees only
the branch it stands on.** A struck task's only record is its commit,
a delivered feature leaves the tree entirely, and a number issued on
an unmerged branch is visible from nowhere else. The permanent
classes count here too — a use case drafted or a decision recorded
mid-work on a branch mints a number invisible from `main`, and one
rule for every class spares each issuance the which-kind-is-this
reasoning.

Where a mark and a file's own population disagree, someone issued
past the ledger: advance the mark. The higher number governs, and
nothing is ever reissued.

## The marks

**This ledger arrived after seven sequences' worth of informal
issuance**, so each mark starts above the highest number surviving
anywhere in the record rather than at 1. A gap costs a sentence; a
reissued number would cost the guarantee that a handle in an old
commit message still resolves to one thing.

- **The next U-number to issue is U11** — use cases, drafted in
  [proposed/USE-CASES.md](proposed/USE-CASES.md) and armed into root
  [USE-CASES.md](../USE-CASES.md). U1 through U10 are spent.
- **The next P-number to issue is P19** — architectural principles,
  **one namespace** across the drafted list and the in-force one, a
  number kept when an entry moves between them. P1 through P18 are
  spent.
- **The next D-number to issue is D29** — decisions, recorded in
  [DECISIONS.md](DECISIONS.md). D1 through D28 are spent.
- **The next F-number to issue is F22** — features, drafted in
  [proposed/FEATURES.md](proposed/FEATURES.md) or cut straight to a
  pledge. F1 through F21 are spent, and most have evaporated on
  delivery; the mark counts what was *issued*, never what survives.
- **The next T-number to issue is T1** — tasks, entered pledged in
  [TASKS.md](TASKS.md). None has been issued: the queue has held no
  numbered entry, and T1 is genuinely free.

**Testaferro numbers no application surfaces.** Its interfaces are
enumerated as an ordered list in
[proposed/ARCHITECTURE.md](proposed/ARCHITECTURE.md), normative by
lookup rather than by handle, so there is no S sequence to keep a
mark for. Adding one is a governance change, not a ledger entry.

**Not every handle in this tree is Testaferro's**, which is the
other reason to issue from a ledger rather than from a count. A
downstream proposal to the provider cites the provider's numbers —
the drive-geometry proposal names an `F29` that reliquary entered
and retired, and `D107` appears in this project's own record as
reliquary's — and a reader counting populations will meet them.
They are quoted evidence, never marks here, and they belong to a
sequence this file does not keep.
