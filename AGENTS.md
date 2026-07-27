# AGENTS.md — repository guidance

Canonical, agent-agnostic guidance for working on testaferro.
Human usage documentation belongs in [README.md](README.md).

## Project state

Milestone 1 built and verified end to end: a pytest facade over reliquary
for DOS CppUTest suites. Reliquary is the sole guest-machine runner;
testaferro's pluggable aspect is the guest unit-test framework.

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
    `reliquary.Context(home=…, cache=…, assets=<session dir>)`, so
    resolution sees only what testaferro authored for that run —
    never the user's reliquary home or the built-in codex. Reaching
    a blueprint by name would mean opting into home mode; that is a
    deliberate decision, not a default to drift into.
  - **The work drive is testaferro's, and it is staged before boot.**
    The suite executable reaches the guest on a host-directory
    (hostdir) drive added to the blueprint at the lowest free disk
    slot. The backend snapshots a host directory when the drive is
    attached, so staging must happen before `start_machine()`, never
    lazily on first run.
  - **`_work_drive()` mirrors reliquary's DOS letter rule** —
    floppies take A:/B: by slot, disks C: onward in slot order — to
    name the drive it just added. Reliquary exposes no "what letter
    is this drive" call; if it grows one, prefer it over the local
    copy of the rule.

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

## Roadmap

Parked and planned work — the parallelism backlog, future guest
OSes, configuration, lifecycle, and runner-seam questions — lives in
[ROADMAP.md](ROADMAP.md). Consult it before starting feature work,
and record newly agreed-but-deferred direction there, not here.

## Constraints

- Python code: stdlib plus two declared dependencies — pytest (the
  facade's host surface, imported lazily) and reliquary (the sole
  guest-machine runner, imported by `testaferro/qemu.py` for the
  machine lifecycle and by `testaferro/machines.py` for its JSONC
  reader alone). Support Python 3.9 and newer; keep lines near 79
  columns.
- Reliquary is pinned to an exact version in
  [pyproject.toml](pyproject.toml). Its API is still moving fast and
  has already removed the layer testaferro was built on once; a
  floating requirement would break consumers without warning. Moving
  the pin is a deliberate task — expect the binding to need work,
  and re-run the checks below against the new version.
- As a reusable library, testaferro never names specific consuming
  projects in source, tests, README.md, or repository guidance. Refer
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

The split is by **cost**, not by coverage: a unit test is cheap and
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
migration to the blueprint model. End-to-end proof is still owed.
