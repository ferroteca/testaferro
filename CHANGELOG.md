# Changelog

All notable changes to testaferro are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- pytest facade for DOS-based CppUTest unit testing: `testaferro.guest_suite(path)` in an ordinary test module surfaces
  every test in a DOS-built CppUTest suite as its own pytest item, run inside a QEMU guest via the relict runner.
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
  `stop(clear_downloads=True)` also scrubs the cached download.
- Disposable per-run state: each run happens in a fresh work directory under testaferro's cache
  (`%LOCALAPPDATA%\testaferro` on Windows, `$XDG_CACHE_HOME/testaferro` elsewhere), seeded with a bootable FreeDOS
  image downloaded once and cached; pass `boot_image=` to boot a caller-supplied DOS floppy image instead.
- Named test machines: `testaferro.config()` declares reusable relict `MachineConfig` templates, and
  `guest_suite(..., machine=...)` or `platform=...` selects one. Each backend session materializes its own copy of
  mutable drive media, so template-backed runs remain isolated.
- Parallel-safe runs: every run gets a private home and private image copy, so suites in separate pytest processes
  never share mutable guest state; with pytest-xdist, `pytest -n auto --dist loadfile` keeps each suite on one worker
  (preserving one-boot batching) while different suites boot concurrently.
- Relict is the sole guest-machine runner. `testaferro.suite.SuiteBackend` composes its internal execution callable
  with a framework adapter; `guest_suite()` still accepts a prebuilt backend as the custom escape hatch, the adapter
  defaults to `testaferro.cpputest` with `framework=` to substitute, and enumeration can be delegated with
  `enumerator=` (e.g. to a host-built twin of the guest suite).
- Contributor guidelines covering development, verification, pull requests, and BSD-3-Clause contribution licensing.
