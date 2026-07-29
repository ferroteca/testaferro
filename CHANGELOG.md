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
  guest can run it; a tree scan claims only what a `testaferro-suites` mask in pytest's ini, or a `suites` mask on an
  environment in `testaferro.ini`, opted in; a host-runnable binary (a plain PE) is claimed only by declaration; and a file
  whose content proves nothing is never claimed from a scan. Installing into an existing venv therefore changes no
  existing run.
- **Plugin options and ini keys** as kebab-case spellings of the declaration vocabulary —
  `--testaferro-environment`, `--testaferro-boot-image`, `--testaferro-machine-config`, each also a pytest ini key.
  Command line wins over ini, and both win over a declaration. Exploration-only:
  `--testaferro-keep-guest-home` preserves each guest session's home (and names what it kept) instead of sweeping it.
- **`--testaferro-suites` and `--testaferro-timeout`**, completing the command-line half of the declaration
  vocabulary (P16). Masks can now be tried before they are written down, and command-line masks *add* to what the ini
  declares rather than replacing it. A timeout given on the command line overrides what a declaration says — the call
  speaks about this run, the declaration about the environment — and the binding takes one directly.
- **`suites` in an environment declaration** — the masks saying which executables are that environment's guest suites, in
  `config()` and in `testaferro.ini` alike. Written as a list or as one comma- or space-separated string, and matched
  case-insensitively on every host so a checked-in project collects the same suites wherever it is cloned.
- **Host-built twin enumeration**: `--testaferro-enumerator=build/host/{stem}.exe` names where each suite's host build
  lives, and collection reads the test list from it instead of booting a guest — which matters most under xdist, where
  every worker collects. A missing twin falls back to the guest, and a list read inside the guest now warns
  (`GuestEnumerationWarning`) that it may be short rather than passing itself off as complete.

- **`provider` — the execution provider is now something you declare.** `reliquary` is the default and the only one
  built, and until now nothing spelled it at all. It joins the declaration vocabulary in all three spellings —
  `guest_suite(..., provider=...)`, `provider =` in a `testaferro.ini` section, and `--testaferro-provider` /
  `testaferro-provider` — and it is testaferro's own word rather than reliquary's, so it sits beside the blueprint
  fields and never reaches the document: reliquary's schema has no field for who is reading it. A named environment
  carries its own provider, so the two are not combined. An unknown name is refused before anything is imported,
  listing what testaferro binds.

- **Standard environments, by name**: `guest_suite(..., environment="freedos")` selects an environment testaferro
  itself curates — the zero-configuration DOS guest, made nameable — so a suite can say which one it means without the
  project declaring one. A name resolves against the project's own declarations first and the standard catalog second,
  so a project declaring `freedos` still gets its own; the catalog is reached by name and never by inference, leaving
  the no-declaration path exactly as it was. Nothing resolves from the user's reliquary home.

### Changed

- **The reliquary pin moves to 0.1.0.dev4**, and testaferro stops mirroring a rule it never owned. `drive_letters()`
  now places *every* drive rather than only the first disk, so `_work_drive()` chooses the slot and asks reliquary for
  the letter — the one-volume-per-disk assumption goes back to the party that owns and states it. A drive reliquary
  will not place is now refused rather than guessed at, because a suite run off the wrong drive fails as a missing
  program and explains nothing. dev4 also stops `exec()` returning screen text it cannot attribute to the command that
  was run, which is the failure mode that made an unreadable guest answer look like a parse error.
- **Zero configuration installs its own FreeDOS system instead of downloading a boot floppy** (D20), because the floppy
  it downloaded never worked: it was FreeDOS 1.4's FloppyEdition boot image, which boots the **installer** — a language
  menu, then "Do you want to proceed [Y,N]?" — and never reaches a DOS prompt, so every guest command waited for a
  prompt that was not coming. Nothing had ever looked; the first end-to-end run found it. testaferro now carries the
  install recipe itself and runs it **once**, into the cache (a few minutes); every run afterwards attaches the result
  in seconds and layers its own copy-on-write overlay, so no run disturbs the system the others share. `boot_image=` is
  unchanged and still boots a floppy of your own. Two consequences worth knowing: the cached artifact is now
  `freedos.qcow2` rather than `boot.img`, so `stop(clear_downloads=True)` discards an install rather than a download;
  and the work drive is now the guest's **second** disk, `D:`, when the installed system is booted.
- **A failure message no longer runs on past its own end.** CppUTest ends one with a blank line, and a guest screen read
  back row by row has its blank rows dropped — so a failure arrived carrying the timing line, the next test and the run
  summary glued to it. A message now ends at whatever CppUTest writes next, and its leading indent is removed in common
  rather than per line, which keeps a difference report's caret under the character it points at. Found by the first
  real guest run, which is exactly the cost P9 states against itself.
- **A guest answer no adapter can read now reports as the guest's own screen** (D19), at both entry points and at both
  moments — enumeration, where it aborts collection, and a run, where each item fails. Previously a grammar's
  `ValueError` escaped, so trying a suite for the first time produced three frames of testaferro's internals with the
  guest's one useful line buried underneath, and pytest's short summary — which quotes only a report's first line —
  dropped that line entirely. The report now leads with why testaferro could not read the answer, names the argv the
  guest was given, says outright that what follows is what the guest showed in response, and ends with the screen
  itself. No traceback, in either place. A host-built twin that prints something unreadable is reported the same way,
  naming the twin, since a host program has no guest screen to show.
- **A framework adapter's refusals state a reason and no longer quote the text back.**
  `cpputest.parse_list()` names the token it choked on; `parse_run()` names the summary line it did not find. Standalone
  callers (U6) passed that text in and still hold it, and an adapter that never saw the guest is not the party to
  present it — the same boundary D17 drew for quoting, read for provenance.
- **Backend dispatch keys by provider rather than by guest OS.** Resolution used to hold a table saying which binding
  ran which platform; it now selects the binding the declaration named and asks *it* which platforms it serves, because
  that is the provider's own answer and not a fact to keep upstream of it. What a run sees is a better refusal: an
  environment the provider cannot run is now turned away naming the provider and what it does run — *test environment
  'warp' declares platform 'os2', which the 'reliquary' provider does not run; it runs: dos* — where before it said
  only that no binding here ran it.
- **A suite names a test environment, and that is the whole guest-facing vocabulary.** `machine=` is now
  `environment=` at `guest_suite()`, and `--testaferro-machine` / `testaferro-machine` are now
  `--testaferro-environment` / `testaferro-environment`. `machines.py` is `environments.py` and `MachineSpec` is
  `EnvironmentSpec`, because *machine* stopped being testaferro's word: what runs a suite is a **test environment** —
  one testaferro authors and names, such as `freedos`, or one the tester declares. `config()` keeps its name, and
  `machine_config=` keeps its own, naming the provider's machine document rather than testaferro's noun.
- **`platform=` left the consumer surface, without leaving `testaferro.ini`.** It is gone from `guest_suite()`, from
  `config()`'s signature, and from the plugin (`--testaferro-platform` and `testaferro-platform` are removed).
  Naming an environment does both jobs it did — choosing among declarations, and overriding what the executable's
  format inferred — so nothing is lost. In a declaration it stays exactly as writable as before, now as one more
  blueprint field passing through untouched for reliquary to validate, which is whose word it always was. Format
  inference is unchanged and internal: an executable with nothing declared still selects an environment on its own.
  What does go is testaferro cross-checking a supplied template's `platform` against a separate argument — write it
  in the template, where the rest of the blueprint lives.
- **testaferro names providers, not what is under them.** The guest binding was called `testaferro/qemu.py` and
  `QemuSuiteBackend`, named for something it never touches: every call in it is a reliquary call, and QEMU is what
  reliquary drives. It is now `testaferro/reliquary.py` and `ReliquarySuiteBackend`, and the sweep took QEMU out of the
  package's docstrings, its error messages, the distribution description and keywords — reliquary, vagrant, dosbox and
  wine are the layer this project may name; what any of them drives underneath is theirs. Nothing about behaviour
  changed. The mentions that remain describe *other* projects, in the README's comparison section.
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
  (`testaferro.resolution.resolve_backend`): config search, format classification, environment
  selection, binding import and option validation now answer the same way for every entry point rather than only for
  `guest_suite()`. The seam takes the `testaferro.ini` search directory as a parameter instead of deriving it from the
  caller's stack frame, which the facade still does for its own call site. No public surface changes.
- A framework adapter's argv builders now return a **sequence of tokens** rather than a command-line string:
  `cpputest.run_one_argv("Vring", "Wraps")` is `("-v", "-sg", "Vring", "-sn", "Wraps")`, and `VERBOSE_ARGS` / `LIST_ARGS`
  are tuples. Spelling a command line is the executing side's business — the reliquary binding joins the tokens for its
  DOS guest, a host
  subprocess splats them — so the adapter no longer decides for a runner it deliberately knows nothing about. Anyone
  calling a builder directly reads the return value as tokens; `" ".join(...)` around one is now correct where it was
  the defect below.

### Fixed

- **Every guest operation ran with mangled argv.** The reliquary binding joined the framework's argv with `" ".join(args)`
  while the adapter returned a string, so joining iterated its characters: the guest was asked to run `SUITE.EXE - v`,
  and a single-test run `SUITE.EXE - v   - s g   V r i n g   - s n   W r a p s`. Enumeration, run-all and run-one were
  all affected. The unit tier missed it because the expectation was built by the same expression it was testing; the
  command line is now written out as a literal, and the integration tier that would have caught it in a boot is still
  owed.

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
