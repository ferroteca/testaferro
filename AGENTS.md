# AGENTS.md — repository guidance

Canonical, agent-agnostic guidance for working on testaferro.
Human usage documentation belongs in [README.md](README.md).

## Project state

Milestone 1 built and verified end to end: a pytest facade over a
core that is agnostic to both pluggable aspects — guest OS and guest
unit-test framework.

Package layout (each module states its contract in its docstring):

- [testaferro/backend.py](testaferro/backend.py) — the `Backend`
  seam (`TestId`, `TestOutcome`, the five-operation ABC).
- [testaferro/cpputest.py](testaferro/cpputest.py) — the CppUTest
  **framework adapter**: argv builders + output grammars, derived
  from CppUTest v4.0's own source, not from observed samples.
- [testaferro/suite.py](testaferro/suite.py) — `SuiteBackend`, the
  generic runner × framework composition.
- [testaferro/qemu.py](testaferro/qemu.py) — the QEMU/DOS backend:
  `suite_backend()` interrogates the referenced executable (plain MZ
  and headerless/.com images accepted; provable PE, NE/LX/LE, ELF,
  and Mach-O rejected with format and architecture named) and
  returns a
  `QemuSuiteBackend` — `SuiteBackend` with
  `quemados.run_guest_program` prebound and `framework` defaulting
  to the CppUTest adapter. Each facade session runs in a fresh,
  disposable quemados home under testaferro's cache dir, seeded from
  `boot_image=` or a once-downloaded cached FreeDOS image; the
  process-global quemados home is bracketed per guest run.
  `start()`/`stop()` (re-exported as `testaferro.start`/`stop`) open
  an optional session: one lazily-staged image choice shared by all
  suites, whose whole area — image and run homes — is swept by
  `stop()`.
- [testaferro/facade.py](testaferro/facade.py) — the pytest facade
  and public entry point: `guest_suite(path_or_backend, ...)` items
  (re-exported as `testaferro.guest_suite`),
  path→backend dispatch (lazily via `testaferro.qemu`),
  selection-aware batching (`ResultBroker`), guest-failure replay.
  The returned test function is re-homed
  (`code.replace(co_filename=...)`) to the guest_suite() call site so
  IDE per-item actions — run one item, jump to source — resolve to
  the consumer's module, not the facade; item ids join group and name
  with a dash (`Vring-Wraps`), never a dot, because IDE tree→target
  mapping treats dots as hierarchy separators.

The two aspects stay orthogonal: a framework adapter never imports a
runner, a runner never learns a framework, and no module may
hard-bind a specific guest OS to a specific framework. They meet only
inside `SuiteBackend`, which takes both as parameters;
`QemuSuiteBackend` prebinds the runner aspect and *defaults* the
framework to the CppUTest adapter — the flagship pair — but the
framework stays a parameter, and any other pairing composes through
`SuiteBackend`. Consumers see neither backend class: the public
surface is `testaferro.guest_suite()`, which selects the backend from the
executable itself (a prebuilt `Backend` is accepted as the custom
escape hatch).
Guest-OS runners live in their own packages; end-to-end proof belongs
in a consuming project that runs real guest tests through the facade,
both batched and `-k`-narrowed.

## Parked work: parallelism

Multi-process parallelism (pytest-xdist) already works across suites
(`-n auto --dist loadfile`; private homes/images make it safe). The
backlog, in value order:

1. **Intra-suite sharding** — the one with real payoff. A middle
   backend operation between `run_all()` and `run_test()` ("run this
   subset in one boot"): CppUTest filter argv can select several
   tests per invocation, so a worker holding part of a suite boots
   once, not per test. Makes `--dist load` efficient on a single
   suite (~Nx wall clock for N workers) and softens `-k` narrowed
   selections in serial runs too. Touches `ResultBroker`, the
   `Backend` seam, and the CppUTest argv builders.
2. **QMP port collision check** — before leaning on parallel runs,
   verify (read-only) that the runner's free-port selection is
   collision-safe when several VMs start concurrently.
3. **Download lock** — two cold-cache workers can both download the
   default boot image; `.part` + `os.replace` keeps it correct but
   duplicates the fetch. A lock file in the cache would serialize it.
4. **Enumeration per worker** — each xdist worker imports the test
   modules, so guest-side enumeration (no `enumerator=`) costs a
   boot per worker. Document the `enumerator=` recommendation or
   cache enumeration keyed on the executable's hash.
5. **xdist_group auto-marking** — would let `--dist loadgroup` keep
   multi-suite files whole; deferred (unregistered marks warn when
   xdist is absent) and likely moot once sharding lands.

## Constraints

- Python code: stdlib plus two declared dependencies — pytest (the
  facade's host surface, imported lazily) and quemados (the QEMU
  runner, imported only in `testaferro/qemu.py`) — so every other
  module stays stdlib-only. Any other guest-OS runner remains a
  *consumer's* dependency, passed into `SuiteBackend` at the
  consumer's call site, never imported here.
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
