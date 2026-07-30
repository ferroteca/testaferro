# Changelog

All notable changes to testaferro are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0.dev7] - 2026-07-30

**The licence changes, and the suite goes where you say.** testaferro is GPL-3.0-only from this release — what went out
under BSD stays under BSD, and nothing is taken back retroactively — so a distributed work incorporating it must now be
copyleft too. Functionally this is the release where placement stops being testaferro's secret: `files=`, `location=`
and `program=` say what is staged into the guest, where it lands and what runs there, each defaulted so a lone suite
executable still needs none of them. The drive testaferro used to add to every machine is gone from the surface with
them — staging happens at rest, into a drive the machine already has, so a zero-configuration guest is now a one-disk
machine with its suite at `C:\TESTS`. The provider pin moves to reliquary 0.1.0.dev6, which is what made that possible:
the drive letter is read off the created machine rather than inferred, and inference retires everywhere. The supported
Python floor rises to 3.12 with it.

### Changed

- **The test suite is no longer packaged.** Through `0.1.0.dev6` the
  sdist carried the nine top-level `tests/*.py` files and nothing
  under `tests/integration/` — half a suite, missing both the tier
  that holds most of the real coverage and the guest fixture, so it
  looked runnable and proved nothing. `MANIFEST.in` now prunes it from
  both artifacts. Nothing a consumer imports changes; what goes is
  dead weight in the sdist. It also keeps the distribution
  single-licensed, since the guest fixture is deliberately
  BSD-3-Clause and no longer travels inside a GPL-3.0-only artifact.
  Running the suite means cloning the repository, which was already
  true of any guest run — the integration tier needs QEMU and an
  installed FreeDOS system.

- **BREAKING: the supported Python floor is now 3.12**, raised from
  `3.9`. This follows reliquary's own floor (D95 there), and testaferro
  cannot claim a floor below the provider it requires. The floor is now
  **tested rather than asserted** — `uv run --python 3.12` joins the
  required checks, which is the correction reliquary's own experience
  argues for: it published `>=3.9` unexercised, and 3.9, 3.10 and 3.11
  all failed the day someone ran them.

- **uv provisions the development environment and publishes releases.**
  `uv sync` replaces the `venv` + `pip install -e .` setup and
  `uv.lock` is now committed rather than ignored, so the environment
  the suite passes in is reproducible — which matters because with no
  CI the local suite *is* the gate. `uv build` and `uv publish` replace
  `python -m build` and `twine`; `twine check` goes with them, its
  rendering job being an RST problem this markdown readme does not
  have. AGENTS.md gains the build and publish section it never had,
  including the rule that no FreeDOS media may enter either artifact —
  the recipe ships, never what it builds.

- **Reliquary is pinned to `0.1.0.dev6`, and the drive letter is no
  longer inferred anywhere** (D4). The pin had been held at
  `0.1.0.dev4` deliberately, across two releases: `0.1.0.dev5` stopped
  assuming one volume per disk (D78 there) — a disk takes one letter
  per volume it *actually holds*, read off the image at rest — which
  ended the only way testaferro had to derive its work drive's letter
  while authoring a blueprint, before any machine or image exists.
  Nothing downstream could answer that honestly, and a consumer-side
  bridge asserting volume counts of its own was implemented, rejected
  and reverted rather than shipped. `0.1.0.dev6` answers it:
  `describe_drives()` reports a created machine's drives and the
  letter map over them (D83 there).

  So the question moved to the one moment it can be answered.
  `_work_drive()` is now `_work_slot()`, which chooses the disk slot
  and stops there — all that authoring decides — and `_placed_letter()`
  asks the created machine, between `create_machine()` and
  `start_machine()`, where images exist to read and reliquary will
  still read them at rest. What the guest is told is what the provider
  placed. A drive the report leaves unplaced is refused **carrying
  reliquary's own reason and id**, because an unreadable disk ahead of
  the work drive shifts every letter behind it and only the specific
  refusal says which disk and why.

  **A machine whose disk holds two volumes is now simply supported.**
  The old inference could not survive one and refused it outright; the
  report places it, and testaferro reads the answer.

- **Autoseeding is no longer pinned off, because it no longer exists.**
  The guest context passed `autoseed=False` so that a host process
  which turned reliquary's process-global on could not reach into a
  test run's resolution. `0.1.0.dev6` deleted autoseeding outright
  (D88 there) rather than defaulting it — the blueprints and scripts
  directories are the sole sources, and a name they do not hold is
  refused. The guarantee testaferro was pinning per guest session is
  now structural, so the argument is gone rather than weakened.

- **BREAKING: testaferro is now GPL-3.0-only.** The project was
  BSD-3-Clause through `0.1.0.dev7`; every release from here is copyleft.
  Anyone may still run, study, modify, and redistribute it, but a
  distributed work incorporating testaferro must now also be GPL-3.0-only,
  and it can no longer be taken into a proprietary product.
  Already-published releases are unaffected: what went out under BSD stays
  under BSD, and this changes nothing retroactively.

  `LICENSE` now carries the GPL v3 text, `LICENSES/` gains
  `GPL-3.0-only.txt`, and the SPDX header on every file in the repository
  reads `GPL-3.0-only`, as do `REUSE.toml` and the `license` field in
  `pyproject.toml` — with one deliberate exception. The integration guest
  fixture (`SUITE.CPP` and its makefile) stays BSD-3-Clause, because the
  built `SUITE.EXE` statically embeds Open Watcom's DOS runtime, whose
  Watcom-1.0 licence has no runtime exception and is GPL-incompatible: any
  GPL code in that binary would make it arguably undistributable. The
  binary's REUSE annotation now names what is actually inside it (Paul's
  fixture, CppUTest's BSD-3-Clause library code, the Sybase runtime), the
  makefile carries the notices that must travel with it, and
  `LICENSES/BSD-3-Clause.txt` and the new `LICENSES/Watcom-1.0.txt` hold
  the texts.

- **The relicensing reservation is now stated, and it is the reason
  contributions require a copyright assignment.** Paul Galbraith holds
  copyright in the whole work and reserves the right to relicense it on
  any terms. Nothing is planned or in preparation; the reservation exists
  so the option is not lost by default. It takes nothing back — every
  version published under the GPL stays under the GPL permanently, which
  `CLA.md` section 4 makes a binding term rather than a promise.

  **New: `CLA.md`**, a copyright assignment with an automatic fallback to
  an exclusive sublicensable licence for jurisdictions that bar assignment
  between living persons, plus a licence-back so a contributor keeps full
  use of their own work. It carries an explicit notice that it awaits
  legal review before the first external contribution is accepted under
  it.

- **Every external reference is vetted against the reservation.**
  AGENTS.md now records the standing of each project testaferro depends
  on, derives from, or names — the dependency licence tiers, the
  clean-room doctrine and its one recorded exception (the CppUTest
  adapter's source-derived grammars), and what the checked-in integration
  binary embeds.

### Added

- **Test placement: `files=`, `location=` and `program=`** (F4,
  superseding D5). Where a suite lands in the guest is now something
  you can **say**, in the guest's own terms, with all three spellings
  every declaration has (P16) — keyword, `testaferro.ini`, and
  `--testaferro-…`:

  - `files=` — host paths staged into the guest beside the suite. A
    named directory contributes its contents, so `files=["fixtures"]`
    lands the fixtures where a guest program looks for them.
  - `location=` — the guest address the set lands at (`D:\TESTDIR`);
    a letter, not a slot.
  - `program=` — the guest address of what to run there, in which
    `{location}` stands for the location however it was settled. The
    framework adapter still composes argv onto it (P4), so this names
    what to invoke and never how.

  **Each defaults, so nothing above is required**: `pytest
  tests/SUITE.EXE` is the fully-defaulted corner of this surface
  rather than a case beside it (P8). The default is the executable
  alone, at the **last** letter of the machine's drive map in a
  `\TESTS` directory, run by its own name — last rather than first
  because a default must not scatter files across the root of a disk
  somebody else owns.

  **Where a run landed can be asked**, in the same terms a
  declaration uses: `backend.location` answers a guest address, and
  answers the same whether you declared it or testaferro chose it —
  who chose is deliberately not part of the answer. It refuses before
  the placement is settled rather than guessing.

- **Staging happens at rest, and the work drive is gone from the
  surface.** The suite used to reach the guest on a host-directory
  drive testaferro added to every blueprint, because that was the
  only way bytes got in. Reliquary's at-rest file verbs write a
  stopped machine's drives, so the set is now written with
  `put_files()` **between `create_machine()` and `start_machine()`**,
  into a drive the machine already has. A zero-configuration guest is
  now a **one-disk machine**, and its suite lives at `C:\TESTS`.

  The address is **stated once, staged against, and spelled**: the
  staging validates it by resolving it against a real disk, and the
  command spells the same value, so a run cannot be launched from
  somewhere the files did not go. A declared address that will not
  work fails **before any boot**, carrying reliquary's own refusal.
  A machine whose disk holds two volumes — refused outright under the
  old one-volume assumption — is simply supported.

  **The old drive survives as a fallback only**, for a machine
  offering no writable room of its own (an unreadable disk, a FAT
  reliquary does not claim). Only a *defaulted* location falls back
  that way; a declared one surfaces the refusal, because the consumer
  named that address and is the only one who can correct it.

- **`--testaferro-keep-guest-home` now retrieves what the run left
  behind.** With staging inside a drive image, keeping the home alone
  would keep everything except the part worth looking at, so the
  location comes back to `retrieved/` under the kept home after the
  guest stops — which means it holds what the run *wrote*, not only
  what was staged. Best-effort: a retrieval that fails leaves the
  home and its images rather than failing the run.

- **The at-rest surface staging depends on is now covered against a
  real disk** (`tests/integration/test_at_rest.py`). It layers over
  the FreeDOS system testaferro already installs, so no image is
  checked in and the disk under test is the one users actually get —
  and because at-rest work needs no boot, eleven cases cost about
  what one boot does. They pin what the provider *answers*: the
  letter map, FAT16 recognition, `put_files` creating its own
  directory, a copy that does not mirror what a run left, and a bad
  address refusing by **rule id** rather than by prose. The unit
  suite's stubbed reports could not have caught any of those moving.

- **Unit tests now prove the blueprints testaferro authors are ones
  reliquary accepts**, using `create_machine(dry_run=True)`
  (`0.1.0.dev5`). The existing authoring tests read back testaferro's
  own dict, which proves it consistent with itself and cannot fail the
  way that matters: a document reliquary has stopped accepting passes
  them unmoved. A dry create runs the whole preflight — media
  resolution, drive and controller assignment, boot validation, the
  schema — and builds none of it.

  This puts the **zero-configuration document in the unit tier for the
  first time.** Its system disk is materialized `difference`, so a real
  create reaches for qcow2 tooling and the case had to live in
  integration (P10); a dry create never touches an image, so a
  placeholder file stands in for the built system.

## [0.1.0.dev6] - 2026-07-29

**A guest actually runs.** Until this release nothing testaferro said about a guest had ever been observed: no VM had
booted since the move to reliquary blueprints, and the image zero configuration downloaded turned out to be FreeDOS's
*installer*, which never reaches a prompt. testaferro now installs its own FreeDOS system once and boots it, and an
integration tier proves the whole journey end to end — a DOS CppUTest suite enumerated, run, and a failure reported
with the guest's own file and line.

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

### Fixed

- **testaferro waits for the guest before typing at it.** Starting a machine is not the same as the guest inside it
  being able to take a command, and testaferro was not waiting — so the first command of every run was typed while
  FreeDOS was still running its startup files, and came back as the boot's own output instead. testaferro now runs a
  readiness script of its own (`assets/freedos-ready.rlqs`) that waits for a prompt and sets a machine variable, and
  checks that variable before it asks the guest anything; a guest that never reports itself ready fails there, plainly,
  rather than answering with something else's text. The prompt is matched as a pattern, so a floppy-booted guest at
  `A:` is as ready as an installed system at `C:`.
- **A boot image you supply is no longer writable by the guest.** `boot_image=` attached your file to the machine in
  place, so a guest writing to `A:` — which DOS does for reasons of its own — edited the image you handed over. What
  boots is now testaferro's own copy inside that guest's disposable home, staged before boot exactly as the suite
  executable is. Two suites in one run no longer share a floppy either of them can change, either. Setting the
  blueprint's `read-only` flag would not have fixed it: reliquary parses the field without passing it to QEMU.

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
