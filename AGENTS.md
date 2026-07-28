# AGENTS.md — repository guidance

Canonical, agent-agnostic guidance for working on testaferro — how to
change this repository safely. Human usage documentation belongs in
[README.md](README.md); where the project is going, what it has
decided, and how work enters is
[planning/README.md](planning/README.md).

## Project state

A pytest facade over reliquary for DOS CppUTest suites, built and
working under its unit tier — though no guest has run since the
migration to the blueprint model, so end-to-end proof is owed (see
"Unit and integration" below). Reliquary is the sole guest-machine
runner (P1); testaferro's pluggable aspect is the guest unit-test
framework (U6).

Package layout (each module states its contract in its docstring):

- [testaferro/backend.py](testaferro/backend.py) — the `Backend`
  seam (`TestId`, `TestOutcome`, the five-operation ABC).
- [testaferro/cpputest.py](testaferro/cpputest.py) — the CppUTest
  **framework adapter**: argv builders + output grammars, derived
  from CppUTest v4.0's own source, not from observed samples.
- [testaferro/machines.py](testaferro/machines.py) — named test-machine
  declarations backed by immutable `MachineSpec` templates, plus
  platform-aware selection and loading of the optional per-project
  `testaferro.ini` (declarative twin of `config()`). A `MachineSpec`
  holds the *authored* reliquary blueprint JSON and mirrors none of
  reliquary's schema: fields pass through untouched and reliquary
  validates them when it parses the document. Keys hyphenated in the
  blueprint (`backend-settings`, `control-planes`) are written with
  underscores in Python and INI and normalized on construction.
- [testaferro/suite.py](testaferro/suite.py) — `SuiteBackend`, the
  internal execution × framework composition.
- [testaferro/binfmt.py](testaferro/binfmt.py) — stdlib-only
  executable-format classification. `classify()` names the guest OS
  able to run a file — "dos" for plain MZ and headerless/.com
  images, None for a provable PE, NE/LX/LE, ELF, or Mach-O
  (including universal) — with format and architecture named for
  error messages; a future guest extends this by claiming formats
  currently mapped to None. Shared by the facade's dispatch and
  each guest binding's own guard.
- [testaferro/cache.py](testaferro/cache.py) — `cache_root()`,
  testaferro's durable filespace (LOCALAPPDATA or XDG_CACHE_HOME),
  shared by the guest bindings.
- [testaferro/qemu.py](testaferro/qemu.py) — the QEMU/DOS platform
  binding: `suite_backend()` guards with `binfmt.classify()`
  (rejections name the format and architecture) and returns a
  `QemuSuiteBackend`, with `framework` defaulting to the CppUTest
  adapter. Each facade session writes the declaration as a blueprint
  into a disposable reliquary home under `cache_root()`, then
  `create_machine()` → `start_machine()`; every guest run is one
  `reliquary.exec()` against that machine, and `stop_machine()` plus
  a sweep of the home ends the session. Zero configuration uses
  `boot_image=` or a once-downloaded cached FreeDOS image.
  `start()`/`stop()` (re-exported as `testaferro.start`/`stop`) open
  an optional session: one lazily-staged image choice shared by all
  suites, whose whole area — image and run homes — is swept by
  `stop()`.

  Four invariants live here:

  - **A running machine is tracked, and stopped before anything is
    swept.** A machine outlives the call that booted it, so `_running`
    holds every backend with a live guest; `stop()` and an `atexit`
    failsafe both stop those machines *before* removing directories.
    Sweeping first would delete the disk out from under a running
    guest and leak the process. Any new exit path must go through
    `_stop_running_machines()`.

  - **The reliquary context is hermetic.** Each session pins
    `reliquary.Context(home_dir=…, cache_dir=…,
    blueprints_dir=<session dir>, autoseed=False)`, so resolution
    sees only what testaferro authored for that run — never the
    user's reliquary home or the built-in codex. Autoseeding is off
    by default in reliquary's embedding API; pinning it per session
    is what keeps a host process that turned the process-global on
    from reaching in. Reaching a blueprint by name from the user's
    home is a deliberate decision, not a default to drift into.
  - **The work drive is testaferro's, and it is staged before boot.**
    The suite executable reaches the guest on a drive whose media is
    located at a host directory, added to the blueprint at the lowest
    free disk slot. The backend snapshots that directory when the
    drive is attached, so staging must happen before
    `start_machine()`, never lazily on first run.
  - **`_work_drive()` mirrors reliquary's DOS letter rule** —
    floppies take A:/B: by slot, disks C: onward in slot order — to
    name the drive it just added. Since reliquary 0.1.0.dev3 that
    mirror runs past what reliquary itself will say:
    `platform_dos.drive_letters()` places the first hard disk at C:
    and refuses every later one, because volume count is not a
    declared fact. Zero-configuration runs land the work drive
    first, so their letter is reliquary's own; a machine that
    declares its own disk gets testaferro's assumption of one volume
    per disk instead. `test_the_letter_agrees_with_reliquarys_own_assignment`
    holds the copy to reliquary wherever reliquary answers — keep
    that guard, and prefer a public call over the local rule the day
    reliquary can determine the rest.

  Guest output is whatever `reliquary.exec()` returns: the visible
  screen, as rows. A command that scrolls past a screenful leaves
  only its tail, which is why `enumerator=` matters for real suites.
- [testaferro/facade.py](testaferro/facade.py) — the pytest facade
  and public entry point: `guest_suite(path_or_backend, ...)` items
  (re-exported as `testaferro.guest_suite`), path→binding dispatch
  (an explicit `platform=`, named `machine=`, or `binfmt.classify()`
  inference selects the binding module from `_PLATFORM_BINDINGS`;
  machine-specific options pass through to the selected binding),
  selection-aware batching (`ResultBroker`), guest-failure replay.
  The returned test function is re-homed
  (`code.replace(co_filename=...)`) to the guest_suite() call site so
  IDE per-item actions — run one item, jump to source — resolve to
  the consumer's module, not the facade; item ids join group and name
  with a dash (`Vring-Wraps`), never a dot, because IDE tree→target
  mapping treats dots as hierarchy separators.

The framework adapter stays independent of reliquary: it never imports
the runner and `QemuSuiteBackend` defaults it to CppUTest while keeping
it a parameter. Consumers see none of the backend classes: the public
surface is `testaferro.config()` / `testaferro.load_config()` for
named machines (including `testaferro.ini`) and
`testaferro.guest_suite()` for platform/machine selection. A prebuilt
`Backend` remains the custom escape hatch. End-to-end proof belongs in
a consuming project that runs real guest tests through the facade,
both batched and `-k`-narrowed.

## Planning and governance

- [planning/README.md](planning/README.md) is the map of the
  maintainer-facing planning machinery, and the place to start. The
  directories are the classification, and the lifecycle ones hold the
  **same filenames** — `USE-CASES.md`, `ARCHITECTURE.md`,
  `FEATURES.md` — because they hold the same artifacts in different
  states: `planning/proposed/` is argued but not accepted, and
  nothing is worked from there; `planning/accepted/` is approved but
  not yet delivered. Promotion is by *moving* a document or an entry,
  and the commit is the acceptance record. The **planning root**
  holds what never moves and so has no state — the map, the vetting
  rule (`INTERFACES.md`), the adjudication record (`DECISIONS.md`,
  which spans open, accepted, refused and retired alike), and the
  task queue. Design sits with what it serves. Once an interface
  ships, its normative specification leaves `planning/` for good —
  current truth does not live there.
- **The vision governs, and it is not in force yet.** The numbered
  use cases and P-numbered architectural principles carry equal
  weight and are the surface every significant change is weighed
  against; when a plan of any kind disagrees with them, they govern
  and the plan is realigned. testaferro adopted this model after the
  code was written (D7), so its whole vision is drafted in
  [planning/proposed/](planning/proposed/) and nothing has reached
  the root lists — root `USE-CASES.md` and `ARCHITECTURE.md` do not
  exist. Cite a U- or P-number knowing it names a draft.
- **Interface changes are vetted** by
  [planning/INTERFACES.md](planning/INTERFACES.md), and the
  enumeration it scopes over is
  [planning/proposed/ARCHITECTURE.md](planning/proposed/ARCHITECTURE.md)
  "The interfaces" — the embedding API, the machine declaration,
  `testaferro.ini`, the `Backend` ABC, the pytest items testaferro
  produces, and the cache layout. Ask "does this change an
  interface?" **first**, and answer it by lookup against that list
  rather than from intuition about the diff. A yes is never
  housekeeping, however small the diff.
- **There is no roadmap** (D7): `accepted/` says the direction is
  agreed and nothing about when, so the absence of order in
  `TASKS.md` holds equally for accepted features, the only binding
  order running inside a feature. **Features carry F-numbers** — the
  handle a dependency, commit or decision points at — which unlike
  U-, P- and D-numbers **evaporate on delivery**, retiring unreused,
  gaps being history rather than a promise. Designs take no number.
  **A feature must fit in one sprint**, here hours, so an accepted
  feature is far smaller than "milestone" suggests; the bound bites
  at acceptance. References between items run **down the lifecycle or
  sideways, never up**. Do not produce a roadmap, a schedule, or a
  delivery estimate, and do not sort the backlog into one when asked
  where to start: what is coming is what has been accepted, and the
  project does not say when.
- **Search the record before a governed act.** Before drafting a
  proposal, accepting one, or changing a norm, search
  [planning/DECISIONS.md](planning/DECISIONS.md) for what bears on it
  and report what you found — including finding nothing. Anything
  recorded as killed, declined or superseded is not revisited without
  new evidence, so re-raising one unknowingly wastes the argument; an
  entry that *supports* the change is worth citing.
- **Writing anywhere under `planning/` is a governed act**, and
  authority is the owner alone. One gate covers entering a document
  in `proposed/`, promoting one to `accepted/`, and entering work in
  `TASKS.md`; the issue tracker is the one open door. **Agents do not
  add tasks on their own initiative and ask before editing
  `TASKS.md` at all.** The gate sits at entry only, so anyone may
  pick up what is already there.

## Constraints

These are the standing engineering constraints, and most of them are
also drafted principles — the P-numbers point at
[planning/proposed/ARCHITECTURE.md](planning/proposed/ARCHITECTURE.md),
which becomes their canonical home once accepted. Until then this
section is the operative statement.

- Python code: stdlib plus two declared dependencies (P11) — pytest (the
  facade's host surface, imported lazily) and reliquary (the sole
  guest-machine runner, imported by `testaferro/qemu.py` for the
  machine lifecycle and by `testaferro/machines.py` for its JSONC
  reader alone). Support Python 3.9 and newer; keep lines near 79
  columns.
- Reliquary is pinned to an exact version in
  [pyproject.toml](pyproject.toml) (D4). Its API is still moving fast and
  has already removed the layer testaferro was built on once; a
  floating requirement would break consumers without warning. Moving
  the pin is a deliberate task — expect the binding to need work,
  and re-run the checks below against the new version.
- As a reusable library, testaferro never names specific consuming
  projects in source, tests, README.md, or repository guidance (P12). Refer
  to consumers and runners only in general instructional terms.
- Tests are stdlib `unittest` under `tests/`.
- Licensing is BSD-3-Clause, REUSE-style.
  New files authored by Paul need
  `SPDX-FileCopyrightText: 2026 Paul Galbraith` and
  `SPDX-License-Identifier: BSD-3-Clause` headers; files that cannot
  carry headers are covered in `REUSE.toml`. Contributor-facing
  submission terms live in [CONTRIBUTING.md](CONTRIBUTING.md)
  (contributors retain copyright — never attribute a contributor's
  work to Paul in SPDX notices).

## Checks

```powershell
python -m compileall -q testaferro tests
python -m unittest discover -s tests -v
```

Output-grammar changes additionally warrant a real end-to-end run
from a consuming project (`pytest -m integration`), since the unit
fixtures are source-derived, not captured.

## Unit and integration

The split is by **cost**, not by coverage (P10): a unit test is cheap and
draws in nothing external or uncontrolled. Nearly all of this
project's behaviour can only be proved by booting a guest, so the
integration tier will always carry most of the real coverage — which
is a reason to push the unit tier as far as it will go, not a reason
to relax it.

Unit tests may use reliquary freely; what they must never do is
launch a virtualization platform. The boundary is exact:

- `create_machine()` is **cheap and hypervisor-free** — blueprint
  parsing, namespace and media resolution, hash verification, drive
  materialization, machine state. Unit tests run it for real, and
  should: it is the best coverage available on this side of the line.
- `start_machine()` launches QEMU. It, `stop_machine()`, and `exec()`
  are stubbed in the unit suite and belong to integration.

**The cheap half of that is conditional on the blueprint, not on the
call.** `create_machine()` stays cheap only while every drive's media
is `use` (attached in place), which is what testaferro authors. A
blueprint declaring a blank (`{"size": ...}`) materializes it through
**qemu-img** — the same external toolchain, so such a machine belongs
in an integration test. Reliquary's own codex `freedos` blueprint
declares exactly such a blank, so this is easy to walk into.

Six tests once launched real VMs while appearing mocked, costing ~10s
of a 12s suite; the unit suite now runs in about one second. If it
starts creeping, something has crossed the line — `--durations` finds
it quickly.

`_work_drive()` duplicates a rule reliquary owns and does not expose
(DOS drive letters). `WorkDrivePlacementTests` cross-checks the copy
against `reliquary.platform_dos.drive_letters`, so the duplication
fails loudly rather than silently running a suite off the wrong
drive. Keep that guard until reliquary offers a public query.

There is **no integration suite yet**, so no guest has run since the
migration to the blueprint model. End-to-end proof is still owed, and
it is what would arm the use cases: building that tier is F6 in
[planning/proposed/FEATURES.md](planning/proposed/FEATURES.md).
