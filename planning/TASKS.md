<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: BSD-3-Clause
-->

# TASKS

The accepted work backlog. A **proposed** task lives in the issue
tracker, which is the only queue a proposed task has: the tracker is
a task's proposed state and this file is its accepted one. Nothing
parks here awaiting a verdict; arriving *is* the verdict.

**Everything in this file is accepted.** That is the whole of what
it means, and it is the one vocabulary ([README.md](README.md))
applying here exactly as it does in the directories: an entry is in
the *accepted* state, so entering it is approving it. Nothing waits
on a verdict, nothing needs a citation, a use case, or a decision of
its own, and there is nothing to promote — it arrived accepted.

**The state is `accepted`; the directory is not the home.**
`proposed/` and `accepted/` hold *demand and capability* — the use
cases, the principles, and the features that deliver them — each
argued at length before it is accepted. A task is none of those: it
is free-standing work too small to be a feature, and too small to
need the argument. **That is the distinguisher**, not size alone. So
it stays at the planning root, in the accepted state, among the
machinery.

**This file is the third work input queue**, and it differs from the
other two by being the one that skips the argument.

Adding to it is governed, by the gate that covers writing anywhere
under `planning/` — see [README.md](README.md). The gate weighs most
here, this being the one governed act that grants approval with no
argument behind it, and it sits at entry only: once something is
here, anyone may pick it up. **Agents do not add tasks on their own
initiative, and ask before editing this file at all.**

**A queue holds what waits.** Work that arrives already done never
appears here: there is nothing to schedule, only a decision to make,
and an entry filed and closed in one act is ceremony.

**There is no order here.** Nothing in this file is scheduled, and
nothing claims priority over anything else; whoever picks work up
picks whatever they like. The one ordering that does bind is a
feature's: **work that only makes sense as part of one accepted
feature lives with that feature**, in `accepted/FEATURES.md`, and
has to be done to complete it. A task here that merely *relates* to
a feature is still free to be picked whenever.

Housekeeping is the same instinct one size smaller: work tiny enough
and obvious enough that it needs no entry here **at all**, approved
as a class in advance, with the commit as its record. This file is
where the pre-approved work that is still worth writing down goes.
The full intake machinery — the raw queues, the housekeeping test,
and how acceptance is recorded — is in [README.md](README.md).

**The one thing that never belongs here:** work that changes an
interface. A yes to that test is never small work, however small the
diff, and takes the argued route through
[INTERFACES.md](INTERFACES.md) instead.

## Tasks

<!-- - <what to do, and enough context to pick it up cold> -->

## Rejected

A thin index into [DECISIONS.md](DECISIONS.md) — what was refused,
and the D-number that refused it.

<!-- - <task> — refused, D<n> -->
