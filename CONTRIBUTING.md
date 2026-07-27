# Contributing to testaferro

Thank you for helping improve testaferro. Bug reports, documentation
fixes, tests, and code changes are welcome when they preserve the
project's pluggable-aspect design and BSD licensing.

## Before you start

**Open an issue first for anything substantial.** The issue tracker
is the open door — anyone may file there, and filing commits you to
nothing. It is also, deliberately, the only way in for a change that
touches what testaferro promises: the project decides direction
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
  `testaferro.ini`, the `Backend` class, the pytest items testaferro
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

testaferro supports Python 3.9 and newer. Create and use a
project-local virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

This installs the two runtime dependencies, pytest and reliquary.
Reliquary is pinned to an exact version: its API is still changing
quickly, so the pin is what keeps a checkout reproducible. Moving it
is its own change, not a drive-by.

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
imported lazily in `testaferro/facade.py`, and reliquary in
`testaferro/qemu.py` (the guest machine) and `testaferro/machines.py`
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

testaferro is licensed under the [BSD 3-Clause License](LICENSE). By
submitting a contribution, you agree to license that contribution
under the same BSD-3-Clause terms. You retain copyright in your
contribution.

Only submit work that you have the right to contribute on those
terms. This means, as applicable, obtaining permission from an
employer or other rights holder and identifying third-party material
and its license. Contributions that would prevent testaferro from
being used or distributed under its existing BSD-3-Clause license
cannot be accepted.

Use accurate SPDX copyright information in each new file:

```text
SPDX-FileCopyrightText: YEAR COPYRIGHT HOLDER
SPDX-License-Identifier: BSD-3-Clause
```

Use the appropriate comment syntax for the file type. Files that
cannot or should not carry comments must be added to `REUSE.toml`
with their actual copyright holder.
