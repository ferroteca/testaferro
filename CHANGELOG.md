# Changelog

All notable changes to testaferro are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
