# Contributing to Testaferro

Thank you for helping improve Testaferro. Bug reports, documentation
fixes, tests, and code changes are welcome when they preserve the
project's pluggable-aspect design and GPL licensing.

Code contributions carry a licensing requirement that is stricter than
most projects': every accepted contribution is assigned to the project
owner. Read [Contribution licensing](#contribution-licensing) before you
write code — it is a real condition, not a formality, and it is better
learned before the work than after.

## Before you start

**Open an issue first for anything substantial.** The issue tracker
is the open door — anyone may file there, and filing commits you to
nothing. It is also, deliberately, the only way in for a change that
touches what Testaferro promises: the project decides direction
before work is picked up, so finished work arriving with no agreed
proposal behind it is refused for *not having argued the merit* —
never for its quality and never for who wrote it. That is a door, not
a wall: make the argument in the issue, and if it wins, the work is
welcome.

Small, focused fixes may go directly to a pull request. Two things
decide whether yours is one, and the first is a lookup rather than a
judgement:

- **Does it change an interface?** The surfaces are enumerated in
  [planning/proposed/ARCHITECTURE.md](planning/proposed/ARCHITECTURE.md)
  "The interfaces" — the public Python API, the machine declaration,
  `testaferro.ini`, the `Backend` class, the pytest items Testaferro
  produces, and the cache layout. A yes is never a small change,
  however small the diff, and takes the argued route.
- **Is it tiny *and* clearly a problem?** A small cleanup or a small
  reported defect is approved as a class, in advance; it needs no
  issue and no ceremony, and the commit is the record.

How direction is agreed, recorded, and refused is
[planning/README.md](planning/README.md); the rule that weighs an
interface change is
[planning/INTERFACES.md](planning/INTERFACES.md); what has already
been settled — and what was declined, which is worth checking before
you argue for it — is
[planning/DECISIONS.md](planning/DECISIONS.md).

Keep changes narrowly scoped and avoid unrelated cleanup. New behavior
should include focused tests, especially for the output grammars and
the facade's batching behavior.

## Development setup

Testaferro supports Python 3.12 and newer.
[uv](https://docs.astral.sh/uv/) provisions the environment — one
command creates `.venv`, installs the project editable, and installs
its dependencies:

```powershell
uv sync
```

Run things with `uv run` (for example `uv run python -m unittest
discover -s tests`), which uses that environment without activating
it. Do not hand-manage `.venv` — it is uv's.

That installs the three runtime dependencies: pytest, reliquary and
remanence. Reliquary and remanence are both pinned to exact versions:
their APIs are still changing quickly, so the pins are what keep a
checkout reproducible. Moving either is its own change, not a
drive-by.

`uv.lock` is **not** tracked, and is git-ignored so uv can rewrite it
freely. A library's lockfile reaches no consumer — it ships in neither
artifact — so a committed one would only develop this checkout against
a resolution no user gets. `pytest` is declared unbounded, so letting
`uv sync` resolve it fresh is what keeps the local suite an honest
gate: it runs against what an install would actually pull. Expect the
version of an unpinned dependency to differ between two contributors,
and say which one you saw when reporting a failure.

The unit suite also runs under a plain stdlib Python: tests that need
pytest or reliquary skip when those are absent. Run the full suite from
an environment that has both installed before submitting.

Unit tests here are **cheap** — the whole suite runs in a couple of
seconds and never launches a virtual machine. They do use reliquary
for real, up to but not including the boot. If a change makes the
suite noticeably slower, something has started drawing in an external
resource; see [AGENTS.md](AGENTS.md) for where that line sits and
why.

Runtime code is standard-library-only outside two seams — pytest is
imported lazily in `src/testaferro/facade.py`, and reliquary in
`src/testaferro/reliquary.py` (the guest machine) and
`src/testaferro/environments.py`
(its JSONC reader, for the `.rlqb` dialect). Please discuss a new
dependency before adding one.

## Make and verify a change

- Match the existing style and keep lines near 79 columns.
- Add or update stdlib `unittest` coverage under `tests/` for changed
  behavior.
- Update README.md when public behavior changes — and note that
  changing public behavior is an interface change, so it should have
  been agreed before the work started (above).
- Add SPDX headers to new files as described below.

Run the required checks:

```powershell
python -m compileall -q testaferro tests
python -m unittest discover -s tests -v
```

Changes to an output grammar (e.g. `testaferro.cpputest`)
additionally warrant a real end-to-end run from a consuming project —
a suite executing in an actual guest through the facade — since the
unit fixtures are source-derived, not captured.

## Submit a pull request

Describe the problem, the chosen solution, and how you verified it.
Keep each pull request reviewable as one coherent change, and respond
to review by updating the same branch.

Maintainer guidance and internal engineering constraints live in
[AGENTS.md](AGENTS.md). Contributors should read it before changing
the backend seam, an output grammar, packaging, or licensing behavior.

## Contribution licensing

Testaferro is licensed under the [GNU General Public License v3.0
only](LICENSE). It is copyleft: anyone may run, study, modify, and
redistribute it, and any distributed work incorporating it must also
be GPL-3.0-only. It cannot be taken into a proprietary product.

### The reserved right, stated plainly

Paul Galbraith holds copyright in Testaferro and **reserves the right
to relicense it**, on any terms, at any time. No relicensing is
planned or in preparation. The reservation exists so that the option
is not lost by default — not because there is a plan behind it.

Two things follow, and both are worth being explicit about:

- **Nothing is taken back.** Every version published under the GPL
  stays under the GPL, permanently and irrevocably. A relicensed
  edition could only ever sit *alongside* what has already been
  released, never replace it, and could not reach backwards into
  published history. Your right to use and fork what exists does not
  depend on the owner's goodwill.
- **The owner would be the only party able to do it.** Relicensing
  requires the licensor to hold rights in the whole work. That is the
  reason for the assignment below, and it is the honest reason — not
  administrative tidiness.

If you are not comfortable with that reservation, that is a
legitimate position and we would rather you know it now than discover
it at merge time. Bug reports, discussion, and review need no
assignment at all.

### Copyright assignment

**Copyrightable contributions require a signed copyright assignment**
before they can be merged. This covers code, documentation,
environment assets, and test fixtures of any substance. It does not
cover bug reports, feature requests, review comments, or discussion.

The instrument is [CLA.md](CLA.md), signed separately and once. A
statement in a pull request or a commit trailer is **not** a
substitute: an assignment must be executed as its own agreement, and
the project keeps a durable record linking each accepted contribution
to it.

Where the law of your jurisdiction does not permit copyright to be
assigned between living persons — Germany is the usual example — the
agreement falls back automatically to the fullest exclusive licence
that jurisdiction does allow. You do not need to work out which case
you are in; the document handles both.

If you contributed the work in the course of employment, or anyone
else has a claim on it, **their consent is required too**, on the
entity form in the same document. In most jurisdictions an employer
owns what its employees write, and an individual signature alone
would grant nothing.

Contributions whose ownership cannot be established completely and on
the record are declined. This is not a judgement about the
contributor — it is that unclear title cannot be repaired later, and
the project prefers a clean reimplementation by the owner over code
it cannot account for.

### Third-party material cannot be accepted

This is the rule most likely to surprise you, and it is stricter than
it was under the project's former BSD licence.

**Do not submit code you did not write**, even when its licence is
permissive and even when it would be GPL-compatible. You cannot
assign copyright in work you do not own, so third-party material —
however freely licensed — cannot pass through this process. That
includes snippets from Stack Overflow, blog posts, other projects,
and vendored files.

This applies with particular force to code from **GPL-licensed
projects**. GPL compatibility is not the test here; assignability is,
and copyleft code from another author fails it.

If a third-party component genuinely belongs in Testaferro, it comes
in as a **declared dependency** with its own licence intact, never as
copied source, and only after discussion. See [AGENTS.md](AGENTS.md)
for the rules governing which licences may be depended on and on what
terms.

### Reference projects and clean-room work

Testaferro studies prior art openly. The default boundary is absolute
and it is **not** a licensing conclusion:

> Designs may be studied and reimplemented. Code is never read for
> reimplementation, ported, or translated.

A close translation is a port no matter what the source licence
permits. If you have read another project's implementation of
something, say so before submitting work in that area — that is a
normal and welcome thing to disclose, not an accusation to avoid.

The project keeps one deliberate, recorded exception: the CppUTest
adapter's argv builders and output grammars are derived from
CppUTest's own source, a choice the project made with the licence
vetted and the reasons recorded in [AGENTS.md](AGENTS.md). An
exception like that is the owner's to make and record — never a
contributor's to assume. AGENTS.md carries the full doctrine and the
standing of every project Testaferro references.

### The project name

The name **Testaferro** is owned by Paul Galbraith and is not part of the
GPL grant — a reservation the GPL expressly permits at section 7(e).
Forks and redistributions must use a different name; see
[TRADEMARKS.md](TRADEMARKS.md).

### SPDX headers

Use accurate SPDX copyright information in each new file:

```text
SPDX-FileCopyrightText: YEAR COPYRIGHT HOLDER
SPDX-License-Identifier: GPL-3.0-only
```

Use the appropriate comment syntax for the file type. Files that
cannot or should not carry comments must be added to `REUSE.toml`
with their actual copyright holder. Once a contribution is accepted
under the assignment, the owner holds its copyright, and the REUSE
record states ownership — authorship credit lives in the git
history.
