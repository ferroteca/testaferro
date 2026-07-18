# AGENTS.md — repository guidance

Canonical, agent-agnostic guidance for working on testaferro.
Human usage documentation belongs in [README.md](README.md).

## Project state

Milestone 1 built and verified end to end: a pytest facade over relict
for DOS CppUTest suites. Relict is the sole guest-machine runner;
testaferro's pluggable aspect is the guest unit-test framework.

Package layout (each module states its contract in its docstring):

- [testaferro/backend.py](testaferro/backend.py) — the `Backend`
  seam (`TestId`, `TestOutcome`, the five-operation ABC).
- [testaferro/cpputest.py](testaferro/cpputest.py) — the CppUTest
  **framework adapter**: argv builders + output grammars, derived
  from CppUTest v4.0's own source, not from observed samples.
- [testaferro/machines.py](testaferro/machines.py) — named test-machine
  declarations backed by immutable relict `MachineConfig` templates,
  plus platform-aware selection.
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
  `QemuSuiteBackend`, backed by a fresh configured `relict.Runner`
  with `framework` defaulting to the CppUTest adapter. Each facade
  session materializes the selected `MachineConfig` into a disposable
  relict home under `cache_root()`, copying mutable media so homes
  never share guest state; zero configuration uses `boot_image=` or a
  once-downloaded cached FreeDOS image.
  `start()`/`stop()` (re-exported as `testaferro.start`/`stop`) open
  an optional session: one lazily-staged image choice shared by all
  suites, whose whole area — image and run homes — is swept by
  `stop()`.
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

The framework adapter stays independent of relict: it never imports
the runner and `QemuSuiteBackend` defaults it to CppUTest while keeping
it a parameter. Consumers see none of the backend classes: the public
surface is `testaferro.config()` for named machines and
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
  facade's host surface, imported lazily) and relict (the sole
  guest-machine runner, imported by `testaferro/machines.py` and
  `testaferro/qemu.py`).
  Support Python 3.9 and newer; keep lines near 79 columns.
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
