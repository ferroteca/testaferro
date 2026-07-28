# Changelog

All notable changes to testaferro are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **The pytest collection plugin**: `pytest tests/SUITE.EXE` is now the whole command. The plugin auto-loads through a
  `pytest11` entry point, claims suite executables, and collects each guest test as an item under the executable's own
  node (`tests/SUITE.EXE::Vring-Wraps`), so `-k`, `-x`, `--lf`, `--collect-only` and node ids all work with no wrapper
  in between. A failure carries the guest's own file, line and assertion rather than a traceback into testaferro.
- **A claiming policy that makes installation-is-activation safe**: a file named on the command line is claimed when a
  guest can run it; a tree scan claims only what a `testaferro-suites` mask in pytest's ini, or a `suites` mask on a
  machine in `testaferro.ini`, opted in; a host-runnable binary (a plain PE) is claimed only by declaration; and a file
  whose content proves nothing is never claimed from a scan. Installing into an existing venv therefore changes no
  existing run.
- **Plugin options and ini keys** as kebab-case spellings of the declaration vocabulary — `--testaferro-machine`,
  `--testaferro-platform`, `--testaferro-boot-image`, `--testaferro-machine-config`, each also a pytest ini key.
  Command line wins over ini, and both win over a declaration. Exploration-only:
  `--testaferro-keep-guest-home` preserves each guest session's home (and names what it kept) instead of sweeping it.
- **`suites` in a machine declaration** — the masks saying which executables are that machine's guest suites, in
  `config()` and in `testaferro.ini` alike. Written as a list or as one comma- or space-separated string, and matched
  case-insensitively on every host so a checked-in project collects the same suites wherever it is cloned.
- **Host-built twin enumeration**: `--testaferro-enumerator=build/host/{stem}.exe` names where each suite's host build
  lives, and collection reads the test list from it instead of booting a guest — which matters most under xdist, where
  every worker collects. A missing twin falls back to the guest, and a list read inside the guest now warns
  (`GuestEnumerationWarning`) that it may be short rather than passing itself off as complete.

- **Standard environments, by name**: `guest_suite(..., machine="freedos")` selects a machine testaferro itself
  curates — the zero-configuration DOS machine, made nameable — so a suite can say which machine it means without the
  project declaring one. A name resolves against the project's own declarations first and the standard catalog second,
  so a project declaring `freedos` still gets its own; the catalog is reached by name and never by inference, leaving
  the no-declaration path exactly as it was. Nothing resolves from the user's reliquary home.

### Changed

- **One word stopped meaning three things.** pytest owns "session" for the whole run, and testaferro was using it for
  two more: one guest being up, and the shared area `start()` opens. The `Backend` ABC's `start_session()` /
  `stop_session()` are now **`start_guest()` / `stop_guest()`** — a *guest session* is one guest up and able to answer
  — and what `testaferro.start()`/`stop()` open is a **run**, which holds many guest sessions. `start()` and `stop()`
  keep their names. The cache layout follows: `runs/run-*/guests/guest-*/`, with `guests/` at the cache root for a
  guest belonging to no run, replacing `sessions/session-*/runs/run-*`. Those directories were never runs' homes —
  each is one guest's — so `--testaferro-keep-run-home` is now `--testaferro-keep-guest-home`. Anyone implementing a
  custom `Backend` renames two methods; an existing cache keeps a stale `sessions/` tree, which is disposable state and
  can be deleted.
- Resolving an executable and its options to a backend moved out of the pytest facade into the core
  (`testaferro.resolution.resolve_backend`): config search, platform validation, format classification, machine
  selection, binding import and option validation now answer the same way for every entry point rather than only for
  `guest_suite()`. The seam takes the `testaferro.ini` search directory as a parameter instead of deriving it from the
  caller's stack frame, which the facade still does for its own call site. No public surface changes.

## [0.1.0.dev5] - 2026-07-28

### Changed

- The distribution is renamed **pytest-testaferro**, following the pytest plugin naming convention; the import name,
  and every other spelling of the project's identity, remains `testaferro`. The bare `testaferro` name on PyPI is
  retired with a final tombstone release (0.1.0.dev4, from `tombstone/`) that points at — and depends on —
  `pytest-testaferro`. Version numbering continues past the tombstone, so the first release under the new name is
  0.1.0.dev5.
- The reliquary pin moves to **0.1.0.dev3**, and the QEMU binding follows its working-directory rework. A session's
  context is now `Context(home_dir=…, cache_dir=…, blueprints_dir=…, autoseed=False)`: the retired `assets=` named a
  project asset root, and the blueprints directory names the one kind of document testaferro actually writes.
  Hermeticity is unchanged and now says both halves out loud — where blueprints come from, and that the built-in codex
  is never reached — where the single `assets=` knob used to declare them together. The per-run blueprint lands in
  `<run home>/blueprints` rather than `<run home>/assets`; that directory is testaferro's own disposable state, so
  nothing a consumer holds moves.
- Where the work drive's DOS letter comes from is now stated rather than assumed. reliquary 0.1.0.dev3 determines a
  letter for the first hard disk alone — a later disk's letter depends on how many volumes the disks before it carry,
  which a blueprint does not declare — so a zero-configuration run's `C:` is reliquary's own answer, while a machine
  that declares its own disk gets testaferro's assumption of one volume per disk. Behavior is unchanged; the guard test
  now holds the local rule to reliquary wherever reliquary answers, and to non-collision where it declines.

## [0.1.0.dev0] - 2026-07-27

### Added

- pytest facade for DOS-based CppUTest unit testing: `testaferro.guest_suite(path)` in an ordinary test module surfaces
  every test in a DOS-built CppUTest suite as its own pytest item, run inside a QEMU guest via reliquary.
- Selection-driven execution: running everything batches the whole suite into a single guest run (one execution boot
  per session), while a narrowed selection (`pytest -k ...`, explicit node ids) runs only the selected tests in the
  guest, individually.
- Guest-side failure reporting: a failing guest test fails its pytest item with the guest's original file, line, and
  assertion message rather than a traceback into the facade, and the generated test function reports the
  `guest_suite()` call site as its source so IDE run-this-test and jump-to-source resolve to the consuming module.
- Executable format screening before any guest boots: a provably non-DOS binary (Windows PE, Linux/BSD ELF, macOS
  Mach-O, 16-bit NE/LX/LE; x86 through ARM64) is rejected with a clear error naming the format and architecture found;
  headerless `.com`-style raw images pass through for the guest itself to judge.
- Session lifecycle: `testaferro.start()` / `testaferro.stop()` make the image choice once and sweep every run's state
  together; `start()` costs nothing until a guest runs and registers an `atexit` failsafe, and
  `stop(clear_downloads=True)` also scrubs the cached download. Guest machines still running are stopped before
  anything is swept — including at interpreter exit — so an interrupted run leaves no orphaned virtual machine.
- Disposable per-run state: each run happens in a fresh reliquary home under testaferro's cache
  (`%LOCALAPPDATA%\testaferro` on Windows, `$XDG_CACHE_HOME/testaferro` elsewhere), seeded with a bootable FreeDOS
  image downloaded once and cached; pass `boot_image=` to boot a caller-supplied DOS floppy image instead.
- The suite executable reaches the guest on a host-directory (hostdir) work drive testaferro adds to the machine and
  stages before boot — normally the guest's `C:`. The boot image is never written into.
- Named test machines: `testaferro.config()` declares reusable reliquary **blueprint** templates, and
  `guest_suite(..., machine=...)` or `platform=...` selects one. A declaration is a template, not a running machine:
  each backend session creates a fresh machine from it, so runs remain isolated.
- Optional per-project `testaferro.ini`: one section per named machine (the declarative twin of `config()`).
  `guest_suite()` searches upward from the calling module and loads it automatically; `testaferro.load_config()`
  loads an explicit path or searches from the current directory. Relative media/template paths resolve from the
  file's directory; structured blueprint fields accept JSON values.
- Parallel-safe runs: every run gets a private home and private image copy, so suites in separate pytest processes
  never share mutable guest state; with pytest-xdist, `pytest -n auto --dist loadfile` keeps each suite on one worker
  (preserving one-boot batching) while different suites boot concurrently.
- Reliquary is the sole guest-machine provider, pinned to an exact version while its API stabilizes.
  `testaferro.suite.SuiteBackend` composes its internal execution callable
  with a framework adapter; `guest_suite()` still accepts a prebuilt backend as the custom escape hatch, the adapter
  defaults to `testaferro.cpputest` with `framework=` to substitute, and enumeration can be delegated with
  `enumerator=` (e.g. to a host-built twin of the guest suite).
- Contributor guidelines covering development, verification, pull requests, and BSD-3-Clause contribution licensing.
