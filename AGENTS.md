# AGENTS.md — repository guidance

Canonical, agent-agnostic guidance for working on Testaferro — how to
change this repository safely. Human usage documentation belongs in
[README.md](README.md); where the project is going, what it has
decided, and how work enters is
[planning/README.md](planning/README.md).

## Project state

A pytest plugin over reliquary for DOS CppUTest suites (D12), with
two entry points onto one execution: the collection plugin, which
auto-loads and claims suite executables, and the embedding facade,
which is its programmatic layer. Both resolve through the same seam.
Built and working under its unit tier — though no guest has run since
the migration to the blueprint model, so end-to-end proof is owed
(see "Unit and integration" below). Reliquary is the only supported
execution provider (P1, in force), and the provider is a choice a
tester **declares**: `provider=` has all three spellings, dispatch is
keyed by it, and reliquary is the default and the one binding built.
Testaferro's pluggable aspect is the guest unit-test framework
(U6).

Package layout under `src/` (each module states its contract in its
docstring):

- [src/testaferro/backend.py](src/testaferro/backend.py) — the `Backend`
  seam (`TestId`, `TestOutcome`, `GuestOutputError`, the
  five-operation ABC: `start_guest`, `list_tests`, `run_test`,
  `run_all`, `stop_guest`).
  **Three spans, three words** (D15): pytest's *session* is the whole
  run; a **guest session** is one guest up, between `start_guest()`
  and `stop_guest()`; a **run** is what `testaferro.start()`/`stop()`
  open — one staged image and one sweep area, holding many guest
  sessions. Nothing but pytest's own is called a session unqualified.
- [src/testaferro/cpputest.py](src/testaferro/cpputest.py) — the CppUTest
  **framework adapter**: argv builders + output grammars, derived
  from CppUTest v4.0's own source, not from observed samples. An
  argv builder returns a **sequence of tokens, never a command
  line** — spelling one belongs to whoever executes, since only
  they know whether the program is reached by a DOS command line or
  an argv list. The two spellings live in
  [reliquary.py](src/testaferro/reliquary.py) (`" ".join`) and
  [plugin.py](src/testaferro/plugin.py) (a splat into `subprocess.run`).
  A string return would satisfy every `for` loop and every join in
  the codebase while meaning something else, which is exactly how it
  went wrong once: the binding joined a string's characters and
  every guest operation asked for `SUITE.EXE - v`. So an argv
  expectation in a test is written out as a literal, never rebuilt
  from the builder under test. A grammar that refuses **states its
  reason and does not quote the text back** (D19): the caller passed
  that text in and still holds it, and an adapter that never saw the
  guest cannot say where it came from.

  **A grammar tolerates the transport, and derives that from the
  source too.** CppUTest ends a failure's message with a blank line
  and indents it with a tab; a guest screen read back row by row drops
  blank rows and renders the tab as spaces. Reading the blank line as
  the terminator therefore let a message swallow the timing line, the
  next test and the summary. So a message ends at whatever CppUTest
  writes *next* — timing line, next header, another failure, or the
  summary — and the **common** indent is removed rather than each
  line stripped, which keeps a difference report's caret under the
  character it indicts. This is what P9 costs, arriving: source-derived
  fixtures could not have shown it, and the first real run did.
- [src/testaferro/environments.py](src/testaferro/environments.py) — named
  test-environment declarations backed by immutable
  `EnvironmentSpec` templates, plus selection and loading of the
  optional per-project `testaferro.ini` (declarative twin of
  `config()`). An `EnvironmentSpec` holds the *authored* reliquary
  blueprint JSON and mirrors none of reliquary's schema: fields pass
  through untouched — `platform` among them, which is the provider's
  word rather than Testaferro's (P2) — and reliquary validates them
  when it parses the document. Keys hyphenated in the blueprint
  (`backend-settings`, `control-planes`) are written with underscores
  in Python and INI and normalized on construction. **`provider`,
  `timeout` and `suites` are Testaferro's own** and never reach the
  blueprint: `provider` names what runs the guest (P1, D11), and
  reliquary's document has no field for who is reading it, which is
  exactly why it is declared beside the machine spec rather than
  inside it. It is left `None` when unsaid — the default belongs to
  `resolution.py`, said in one place. `select()`
  resolves a *name* against those declarations first and the standard
  catalog second (D10); the platform *inferred* from the executable
  matches declarations only, so zero configuration stays zero (P8).
- [src/testaferro/catalog.py](src/testaferro/catalog.py) — the standard
  environments Testaferro curates, reachable by name
  (`environment="freedos"`). Each entry is an authored provider document
  carried through untouched, exactly as a declaration is (P3);
  `freedos` declares only its platform, which is what makes naming it
  and naming nothing run the same guest. Siblings arrive as guests
  grow.
- [src/testaferro/suite.py](src/testaferro/suite.py) — `SuiteBackend`, the
  internal execution × framework composition. Argv crosses it
  untouched: it joins nothing and quotes nothing, because a
  composition that knows neither aspect cannot know what a command
  line looks like at the far end. It is also **the only place both
  halves of an exchange are in hand** — the argv that went out and
  the text that came back — which is why an adapter's refusal becomes
  a `backend.GuestOutputError` here, carrying both, for an entry point
  to report (D19). An adapter states its reason and nothing about
  provenance; it never saw the guest.
- [src/testaferro/binfmt.py](src/testaferro/binfmt.py) — stdlib-only
  executable-format classification. `classify()` names the guest OS
  able to run a file — "dos" for plain MZ and headerless/.com
  images, None for a provable PE, NE/LX/LE, ELF, or Mach-O
  (including universal) — with format and architecture named for
  error messages; a future guest extends this by claiming formats
  currently mapped to None. Shared by the facade's dispatch and
  each guest binding's own guard.
- [src/testaferro/assets/](src/testaferro/assets/) — the FreeDOS recipe
  Testaferro authors: a blueprint and the install script that drives
  it. Vendored from the provider's codex deliberately and read only
  from here (P17, D20), and read **once** — what a test run touches is
  the disk the install produced, never this. Shipped inside the
  package (`package-data` in [pyproject.toml](pyproject.toml)) because
  the package reads it at run time.
- [src/testaferro/cache.py](src/testaferro/cache.py) — `cache_root()`,
  Testaferro's durable filespace (LOCALAPPDATA or XDG_CACHE_HOME),
  shared by the guest bindings. Also where a finished guest home is
  handed back: `release_guest_home()` is the single place that sweeps
  or keeps one, and `keep_guest_homes()`/`kept_guest_homes()` are the
  exploration switch and its report. The layout is the vocabulary made
  physical (D15): `runs/run-*/guests/guest-*/`, and `guests/` at the
  cache root for a guest belonging to no run. That policy is Testaferro's, not
  any binding's, which is what lets the plugin read the answer without
  importing a binding — or a provider.
- [src/testaferro/at_rest.py](src/testaferro/at_rest.py) — at-rest
  access to a guest's own drives, over `remanence`, and **the only
  module that imports it** (P11): everything it can refuse is
  refused in its own `AtRestError`, so no caller needs the
  dependency to catch a failure. Staging a suite into a stopped
  disk is not execution, so it is not the provider's work to
  supply (P1, F16, D23).
  **A volume is addressed here, never a drive letter.** At rest
  there are no letters — DOS assigns one at boot from the system
  installed on the disk, so a letter read off a stopped image
  predicts that boot rather than reporting it (D23, and reliquary's
  own D107 independently). `put_tree`/`get_tree` take an image, a
  volume within it, and a path within that volume; `split_address`
  separates a guest address's letter from its path and **returns
  the letter rather than resolving it**, because whoever knows
  which volume that letter names is the one who can say. The device
  type is **declared** (`mbr-sector-hd`) because a qcow2 records
  nothing about the drive that wrote it and remanence refuses to
  guess between candidates. 8.3 is remanence's rule and it enforces
  it, naming the character or the length that broke — nothing here
  re-checks it, and nothing anywhere mangles a name into something
  typeable.
- [src/testaferro/reliquary.py](src/testaferro/reliquary.py) — the reliquary
  provider binding, for DOS guests (D16). Named for the provider it
  binds, because that is the layer Testaferro talks to: every call in
  it is a reliquary call, and what reliquary drives underneath is its
  own business and appears nowhere in this package.

  **Reliquary and remanence answer no drive-letter question at all,
  by design rather than by gap** (0.1.0a2, D108 there; remanence's
  own D57): `describe_drives` and the rest of the file-verb layer are
  deleted outright, and neither will say which letter a volume gets —
  a fact about a booted guest, never a stopped image. **Testaferro
  now answers it instead, deterministically, for every drive it ever
  declares** — `_letter_map()` — because Testaferro authors the whole
  document: a floppy controller's drives take `A:`/`B:` by position
  and a hard disk takes `C:` onward by slot order, one volume per
  disk, which holds by construction for Testaferro's own media and is
  taken as given for a `machine_config` template too. This reinstates,
  as **deliberate, permanent policy** rather than a stopgap, the
  inference D78 killed upstream for the general case — the difference
  is that Testaferro now *states* the one-volume-per-disk assumption
  as its own rather than presenting it as something read back.
  Checked against a real boot: the zero-configuration guest's system
  disk answers `C:` and its work-drive sibling `D:`, exactly as
  computed. What reliquary drives underneath is still its own
  business, which is why `machine_config=` keeps that word while the
  noun a suite writes is an environment: it names the provider's own
  document, passing through as `platform` does. `PLATFORMS` is the
  one thing it tells resolution about itself — the guests this
  provider serves, its own answer to give.

  **Zero configuration boots a FreeDOS system Testaferro installed**
  (D20), not a downloaded floppy. `assets/` holds the recipe — the
  blueprint and its install script, vendored so nothing resolves out
  of the provider's codex at run time (P17) — and
  `_build_default_image()` runs it **once**, into the cache. A guest
  session layers a `difference` overlay over that disk and so cannot
  write into the copy every other session shares. The image it
  replaced booted FreeDOS's *installer* and never reached a prompt, so
  zero configuration could not have worked; nothing had looked until
  an integration run did. `boot_image=` is unchanged and still boots a
  tester's own floppy (U3) — what changed is only what happens when
  nobody says. The suite is staged onto Testaferro's own **work
  drive**, a vvfat sibling of the system disk, and the guest reads it
  at **`D:\`**.

  `suite_backend()` guards with `binfmt.classify()`
  (rejections name the format and architecture) and returns a
  `ReliquarySuiteBackend`, with `framework` defaulting to the CppUTest
  adapter. Each guest session writes the declaration as a blueprint
  into a disposable reliquary home under `cache_root()`, then
  `create_machine()` → `start_machine()`; every guest run is one
  `session.exec()` against that machine, and `stop_machine()` plus
  a sweep of the home ends the guest session. Zero configuration uses
  `boot_image=` or a once-downloaded cached FreeDOS image.
  `start()`/`stop()` (re-exported as `testaferro.start`/`stop`) open
  an optional *run*: one lazily-staged image choice shared by all
  suites, whose whole area — image and guest homes — is swept by
  `stop()`.

  Four invariants live here:

  - **A running machine is tracked, and stopped before anything is
    swept.** A machine outlives the call that booted it, so `_running`
    holds every backend with a live guest; `stop()` and an `atexit`
    failsafe both stop those machines *before* removing directories.
    Sweeping first would delete the disk out from under a running
    guest and leak the process. Any new exit path must go through
    `_stop_running_machines()`.

  - **The reliquary session is hermetic.** Each guest session opens
    `reliquary.Session(reliquary.Context(home_dir=…, cache_dir=…,
    blueprints_dir=<guest home>, scripts_dir=…))` (`_open_session()`,
    formerly `_context()`; 0.1.0a2 made the session the only door,
    P26 there, so every provider verb this binding calls is now a
    method on the object it returns), so resolution sees only what
    Testaferro authored for that run — never the user's reliquary
    home or the built-in codex. Reaching a blueprint by name from
    the user's home is a deliberate decision, not a default to
    drift into. `Session` itself now refuses construction without a
    home (`dir.unassigned`), which is what 0.1.0.dev6's autoseeding
    deletion (D88 there) was already heading toward: there is no
    process-global left to fence off.
  - **Testaferro's own work drive is a standing fixture, not a
    reaction** (F4, superseding D5, and D108's own consequence). A
    vvfat medium — a host directory QEMU serves live as a FAT volume,
    never materialized into an image — is a sibling of whatever else
    the machine declares in **every** session, gathered host-side
    into `<guest home>/work` *before* `create_machine()` even runs.
    There is nothing to write into it at rest: its content already
    exists the moment the drive does, so `_place()` only needs to
    settle *where* — the address is **stated once, and spelled**:
    `_default_location()` picks the work drive's own letter
    (`_letter_map()`) when nobody said, `_run_in_guest` spells the
    command off the same settled value, and only a `location=` naming
    some *other* drive still asks `at_rest.put_tree()` (over
    remanence, F16, D23) to write it there, since that drive is not
    live-served.

    Three declarations drive placement, each Testaferro's own word
    and none of them a blueprint field: `files=` (host paths staged
    beside the suite), `location=` (the guest address they land at)
    and `program=` (what to run, `{location}` substituted). Each
    defaults, which is what keeps `pytest tests/SUITE.EXE` a one-liner
    (P8) — the executable alone, at the work drive's own letter,
    `D:\` for the zero-configuration guest.

    **There is no more reactive fallback.** Through 0.1.0.dev7 an
    unwritable primary drive made Testaferro append its own drive,
    recreate the machine and stage there instead; since the work
    drive is now a standing fixture rather than something appended on
    failure, there is nothing left to react to — a placement that
    fails now simply fails, naming the address that would not
    resolve, before any boot.
  - **A started machine is not a ready guest, and Testaferro waits.**
    `start_machine()` launches a machine and never claimed to wait for
    the guest inside it. Reliquary ships **no readiness script on
    purpose** — what "ready" means belongs to whatever is being built
    — and the channel it provides is a machine variable: a script of
    the caller's own sets one as its last step and the host reads it
    back, cleared at every start so the answer is about *this* boot.
    So `assets/freedos-ready.rlqs` waits for a prompt and sets
    `ready`, `_wait_ready()` runs it by label through `run_script()`
    (0.1.0a2 retired `load_script()`/`execute_script()` with the rest
    of the module-level API) and checks the variable, and a guest
    that never reports itself ready
    fails there rather than being typed at. Skipping this is what made
    the first command of every run come back as the boot's own output.
    The prompt is matched as a **pattern**, because Testaferro's
    installed system boots to `C:` and a tester's floppy to `A:`.
  - **Setup commands run once per guest session, right after
    readiness — harness prep (F9), not placement.** `setup=` is a
    fourth Testaferro-only word beside `files=`/`location=`/
    `program=`, never a blueprint field: `_run_setup()` runs each
    guest command in the order given, after `_wait_ready()` and
    before anything else, every guest session an enumeration boot
    included — a suite whose TSR must be resident needs it resident
    to enumerate too (D15). Failure is the provider's to detect, not
    Testaferro's to parse: each command goes through
    `session.exec(check=True)`, and a command reliquary reports as
    failed becomes the same `GuestOutputError` every guest exchange
    fails in, naming the command — ending the session in one report
    rather than letting every later test fail mysteriously. A suite
    declaring none runs exactly as it did before this existed.
  - **A declared boot image is staged too, and for a different
    reason.** What boots is Testaferro's copy inside the guest home,
    because the tester's own file is read and never written (P5). A
    drive attached in place is one the guest may write to, and
    reliquary parses a media's `read-only` without passing it to
    QEMU, so the flag would look like protection and be none.
    `_blueprint()` therefore authors over locations that are
    **already staged** — it copies nothing, which is what keeps the
    snapshot rule above from being quietly broken by a document
    builder.

  Guest output is whatever `session.exec()` returns: the visible
  screen, as rows. A command that scrolls past a screenful leaves
  only its tail, which is why `enumerator=` matters for real suites.

  **The provisioning above is shared, not `ReliquarySuiteBackend`'s
  alone** (U10, F18). `_GuestLifecycle` carries every guest-session
  method above — `start_guest`/`stop_guest`, `_gather`, `_create`,
  `_place`, `_wait_ready`, `_run_setup`, `_blueprint`, boot-image
  staging, the `location` property — with `exe_path` optional: a
  suite executable when there is one, `None` when there is not.
  `ReliquarySuiteBackend(_GuestLifecycle, SuiteBackend)` adds only
  `_run_in_guest()` and `_exe_name()`, the two methods that actually
  need a suite executable. `GuestSession(_GuestLifecycle)` adds none
  — it is a context manager over the same lifecycle, `__enter__`
  calling `start_guest()` and `__exit__` calling `stop_guest()`
  unconditionally, with `exec(command, timeout=None, check=False)`
  calling `session.exec()` directly and returning its rows unjoined,
  mirroring that method's own contract rather than reshaping the
  answer for a framework adapter that was never going to see it.
  `guest_session()` is `suite_backend()`'s sibling factory, the same
  validation (a non-DOS `machine_config=`, `boot_image=` and
  `machine_config=` together) and no executable to classify.
- [src/testaferro/resolution.py](src/testaferro/resolution.py) — the
  backend-resolution seam: `resolve_backend()` is the single place
  where an executable plus options becomes a `Backend`, and every
  entry point calls it. Config search, format classification,
  environment selection, binding import and option validation live
  here, so they answer the same way whoever asked. **Dispatch keys by
  provider** (P1, D11): the environment names one or takes
  `_DEFAULT_PROVIDER`, and the name selects the sibling module of the
  same name, a binding being named for the provider it binds (D16).
  `_PROVIDERS` is the gate on that — a name outside it is refused
  rather than turned into an import. `platform` reaches resolution
  only as a field on the selected environment or as what the format
  inferred, and no longer picks anything: it is checked against the
  binding's own `PLATFORMS`, because which guests a provider serves is
  the provider's answer and not a table kept upstream of it. Neither
  word is one a consumer types about an emulator (P2). It is
  deliberately
  entry-point-neutral: `search_from` — where the `testaferro.ini`
  search begins — is a parameter, because nothing here can know how
  the caller was reached. Its imports stay stdlib-only;
  `environments` (and so reliquary) is imported inside the call.
  `resolve_guest_session()` is the same seam for a scripted guest
  interaction (U10, F18): the same environment/provider resolution,
  minus the format-classification step it exists to feed — there
  being no executable to interrogate when none is named — and it
  calls `binding.guest_session()` rather than `binding.suite_backend()`.
- [src/testaferro/items.py](src/testaferro/items.py) — the pytest items
  Testaferro produces, which is the fifth interface: `item_id()` (the
  dash rule), `failure_text()` (the guest's own file, line and
  assertion) and `guest_output_text()` (the guest's own screen, when
  its answer could not be read at all — D19). Both entry points
  surface the same guest tests, so the spellings they share live here
  rather than in either of them. `guest_output_text()` leads with the
  reason because pytest's short summary quotes a report's first line
  and drops the rest, so that line has to stand alone.
- [src/testaferro/plugin.py](src/testaferro/plugin.py) — the `pytest11`
  collection plugin, which **auto-loads on installation** (D13):
  `pytest_collect_file` claims suite executables, and each guest test
  becomes an item under the executable's node
  (`tests/SUITE.EXE::Group-Name`). Options and ini keys are declared
  from one list (`_SETTINGS`) so the two spellings cannot drift (P16);
  `--testaferro-keep-guest-home` and the enumerator are the
  exploration-only exceptions. **What keep-guest-home keeps changed
  with F4**: staging lands inside a drive image now, so the binding
  retrieves the location back to `retrieved/` under the kept home
  after the stop — best-effort, because a failed retrieval must not
  turn inspection into a failed run, and the images are the fallback
  evidence. It shows what the run *wrote*, not only what was staged.
  Execution guests are stopped in
  `pytest_sessionfinish`, deliberately **not** through
  `config.add_cleanup`: config cleanups run after the terminal
  summary, so a kept guest home would be reported before the guest
  that made it was closed. The claiming policy is the load-bearing
  part — see the invariant below. Its module imports stay stdlib-only:
  a pytest run that claims no guest suite must not pay for reliquary,
  which is why `environments.py` imports the JSONC reader lazily.
- [src/testaferro/facade.py](src/testaferro/facade.py) — the pytest facade
  and public entry point: `guest_suite(path_or_backend, ...)` items
  (re-exported as `testaferro.guest_suite`), selection-aware batching
  (`ResultBroker`), guest-failure replay. A path target is resolved
  through the seam above; what the facade adds is the caller's stack
  frame — the call site is both where the `testaferro.ini` search
  starts and where the items report their source.
  The returned test function is re-homed
  (`code.replace(co_filename=...)`) to the guest_suite() call site so
  IDE per-item actions — run one item, jump to source — resolve to
  the consumer's module, not the facade; item ids join group and name
  with a dash (`Vring-Wraps`), never a dot, because IDE tree→target
  mapping treats dots as hierarchy separators.

The framework adapter stays independent of reliquary: it never imports
the runner and `ReliquarySuiteBackend` defaults it to CppUTest while keeping
it a parameter. **P4 is in force over that seam** — the five callables
an adapter supplies (`list_argv`, `run_all_argv`, `run_one_argv`,
`parse_list`, `parse_run`), argv crossing as tokens, and no ABC
built ahead of a second concrete adapter — so a divergence there is
a bug rather than unbuilt work. Consumers see none of the backend classes: the public
surface is `testaferro.config()` / `testaferro.load_config()` for
named test environments (including `testaferro.ini`),
`testaferro.guest_suite()` for `environment=` selection or a
`provider=` said inline, and `testaferro.guest_session()` (U10, F18)
for a guest-driven test shaped as a linear script rather than a suite
— the same `environment=`/`provider=`/`files=`/`machine_config=`
vocabulary, a context manager rather than pytest items, and
`GuestSession.exec()` in place of a `Backend`. A prebuilt
`Backend` remains the custom escape hatch. End-to-end proof belongs in
a consuming project that runs real guest tests through the facade,
both batched and `-k`-narrowed.

## Planning and governance

- [planning/README.md](planning/README.md) is the map of the
  maintainer-facing planning machinery, and the place to start. The
  directories are the classification, and the lifecycle ones hold the
  **same filenames** — `USE-CASES.md`, `ARCHITECTURE.md`,
  `FEATURES.md` — because they hold the same artifacts in different
  states: `planning/proposed/` is argued but not pledged, and
  nothing is worked from there; `planning/pledged/` is owed but
  not yet delivered. Promotion is by *moving* a document or an entry,
  and the commit is the record of the pledge — a lifecycle act earns
  no entry in `DECISIONS.md`, and delivery evidence goes in the
  moving commit's message (D14). The **planning root**
  holds what never moves and so has no state — the map, the vetting
  rule (`INTERFACES.md`), the adjudication record (`DECISIONS.md`,
  which spans open, pledged, refused and retired alike), and the
  task queue. Design sits with what it serves. Once an interface
  ships, its normative specification leaves `planning/` for good —
  current truth does not live there.
- **The vision governs, and it is not in force yet.** The numbered
  use cases and P-numbered architectural principles carry equal
  weight and are the surface every significant change is weighed
  against; when a plan of any kind disagrees with them, they govern
  and the plan is realigned. Testaferro adopted this model after the
  code was written (D7), so its vision began wholly drafted in
  [planning/proposed/](planning/proposed/); U4 and P16 were pledged
  first (D13), then P1 and P2 (D18), and nothing had reached the
  root lists until P16 armed, followed by P10 and P4 one at a time,
  then by P6, P7, P8, P9, P11, P12, P13 and P17 together, and then by
  P1 and P2 once F12 built what they promised. Root
  [ARCHITECTURE.md](ARCHITECTURE.md) carries thirteen principles —
  P1, P2, P4, P6 through P13, P16 and P17 — and root
  [USE-CASES.md](USE-CASES.md) now exists, carrying **U4**, armed once
  a guest ran the journey it describes; **U7**, armed once a real
  guest boot proved `setup=`, its prerequisite F9 delivered and
  retired with it; **U9**, armed once a real guest boot proved
  `environment="freedos"` resolves against the standard catalog rather
  than only through the zero-configuration default's own inference,
  its prerequisite F19 delivered and retired with it, severed from
  U9's own plural growth (D25) — a second named environment still
  waits on a second guest platform, unbuilt and blocked entirely on
  reliquary; and **U10**, armed once a real guest boot proved
  `guest_session()`, its prerequisite F18 delivered and retired with
  it in turn. `planning/pledged/` now holds nothing. Every other U- or
  P-number still open names either a rule in force or an argument,
  never something merely owed.
  Four principles stay drafted: P3 and P5, each contradicted by a
  small piece of the code and each saying so at its own entry, and
  P14 and P15, which govern conduct rather than code. An entry may
  arm without ever being pledged, as most of the principles did — the
  pledged shelf holds what is *owed*, not a stop every entry makes.
  Cite a U- or P-number knowing it names a draft unless it sits in
  [planning/pledged/](planning/pledged/), where it names something
  the project owes and has not yet delivered, or at the root, where a
  divergence is a bug rather than unbuilt work.
- **Interface changes are vetted** by
  [planning/INTERFACES.md](planning/INTERFACES.md), and the
  enumeration it scopes over is
  [planning/proposed/ARCHITECTURE.md](planning/proposed/ARCHITECTURE.md)
  "The interfaces" — the embedding API, the machine declaration,
  `testaferro.ini`, the `Backend` ABC, the pytest items Testaferro
  produces, and the cache layout. Ask "does this change an
  interface?" **first**, and answer it by lookup against that list
  rather than from intuition about the diff. A yes is never
  housekeeping, however small the diff.
- **There is no roadmap** (D7): `pledged/` says the work is owed
  and nothing about when, so the absence of order in
  `TASKS.md` holds equally for pledged features, the only binding
  order running inside a feature. **Features carry F-numbers** — the
  handle a dependency, commit or decision points at — which unlike
  U-, P- and D-numbers **evaporate on delivery**, retiring unreused,
  gaps being history rather than a promise. Designs take no number.
  **A feature must fit in one sprint**, here hours, so a pledged
  feature is far smaller than "milestone" suggests; the bound bites
  at the pledge. References between items run **down the lifecycle or
  sideways, never up**. Do not produce a roadmap, a schedule, or a
  delivery estimate, and do not sort the backlog into one when asked
  where to start: what is coming is what has been pledged, and the
  project does not say when.
- **Search the record before a governed act.** Before drafting a
  proposal, pledging one, or changing a norm, search
  [planning/DECISIONS.md](planning/DECISIONS.md) for what bears on it
  and report what you found — including finding nothing. Anything
  recorded as killed, declined or superseded is not revisited without
  new evidence, so re-raising one unknowingly wastes the argument; an
  entry that *supports* the change is worth citing.
- **Writing anywhere under `planning/` is a governed act**, and
  authority is the owner alone. One gate covers entering a document
  in `proposed/`, promoting one to `pledged/`, and entering work in
  `TASKS.md`; the issue tracker is the one open door. **Agents do not
  add tasks on their own initiative and ask before editing
  `TASKS.md` at all.** The gate sits at entry only, so anyone may
  pick up what is already there.

## Constraints

These are the standing engineering constraints, and most of them are
now **in-force principles** — the P-numbers point at root
[ARCHITECTURE.md](ARCHITECTURE.md), which is their canonical home, so
breaking one here is a bug rather than a preference ignored. This
section restates them in working terms; where the two differ, the
principle governs.

- Python code: stdlib plus three declared dependencies (P11) — pytest (the
  facade's host surface, imported lazily), reliquary (the only
  supported guest-machine provider, imported by `src/testaferro/reliquary.py` for the
  machine lifecycle and by `src/testaferro/environments.py` for its JSON5
  reader alone), and remanence (at-rest access to the guest's own drive
  images, imported by the at-rest module alone — staging a suite into a
  stopped disk is not execution and is not the provider's to supply).
  Support Python 3.12 and newer; keep lines near 79
  columns.
- Reliquary and remanence are both pinned to exact versions in
  [pyproject.toml](pyproject.toml) (D4; P18's enumerated set, of one
  each). Both APIs are still moving fast — reliquary has already removed
  the layer Testaferro was built on twice, the drive letter map and then
  the file verbs themselves, together in 0.1.0a2 (D108 there) — and
  neither will ever answer a drive-letter question again (remanence's
  own D57), by design rather than by gap. `_letter_map()` is
  Testaferro's own answer instead, computed deterministically from
  every drive it declares — see `reliquary.py` above. Moving either
  pin is a deliberate task — expect the binding or the at-rest module
  to need work, and re-run the checks below against the new version.
- **The plugin auto-loads, so what it claims is a promise to every
  project that installs it.** One rule carries that weight, and it is
  easy to break by accident: `binfmt`'s `"dos"` verdict has two
  strengths, and only one of them claims a file. A plain MZ header
  *proves* a DOS program; `binfmt.HEADERLESS` says only that nothing
  proves otherwise — which is equally true of a test module, a
  README, and every other file pytest walks past. Reading the second
  as the first makes the plugin claim pytest's own files and boot a
  guest to run them. So: proof claims a file; absence of proof claims
  nothing on its own (a named file needs a `.com`/`.exe` name or a
  declaration), a scan claims only what a mask or `testaferro.ini`
  opted in, and a host-runnable format needs a declaration.
  `PluginTests` guards each of those four, and
  `test_a_named_file_that_is_not_a_program_is_left_alone` guards the
  one that already went wrong once.
- Every environment Testaferro offers by name is Testaferro's own
  (P17): a standard-catalog entry — and any blueprint, script or
  medium shipped with one — is authored here and complete in itself,
  never a name resolved out of reliquary's codex or the user's
  reliquary home (D6, D10). `StandardCatalogTests` guards it: a
  catalog document declares its media beside the machine that uses
  them. Provider content reaches a run only because a tester
  declared it.
- As a reusable library, Testaferro never names specific consuming
  projects in source, tests, README.md, or repository guidance (P12). Refer
  to consumers and runners only in general instructional terms.
- Tests are stdlib `unittest` under `tests/`, integration included:
  `tests/integration/` is skipped unless `TESTAFERRO_INTEGRATION` is
  set, so the constraint is not spent on a second runner.
- Licensing is GPL-3.0-only, REUSE-style. The full policy — the
  relicensing reservation, the dependency licence tiers, and the
  standing of every project Testaferro references — is the
  "Licensing" and "Prior art and external references" sections
  below, and breaking it is the one mistake in this file that cannot
  be repaired later. Contributor-facing submission terms live in
  [CONTRIBUTING.md](CONTRIBUTING.md); the assignment instrument is
  [CLA.md](CLA.md).

## Licensing

The project is **GPL-3.0-only** and follows REUSE conventions. The name
**Testaferro** is reserved to Paul Galbraith under
[TRADEMARKS.md](TRADEMARKS.md) — a reservation GPL section 7(e)
expressly permits; do not weaken or contradict that policy in docs or
packaging metadata.

Every new file authored for the project needs:

```text
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
```

Use the appropriate comment syntax for the file type. Files that
cannot or should not carry headers must be covered by `REUSE.toml`.

### The relicensing reservation, and what it constrains

Paul holds copyright in the whole work and **reserves the right to
relicense the project on any terms**. Nothing is planned; the
reservation exists so the option is not lost by default. Two
consequences bind everything below, and neither is negotiable at the
level of an individual change:

- **The project must own every line it ships.** Relicensing is only
  available to a party holding rights in the whole work, and
  enforcing copyleft requires standing that only an owner has. One
  file the project cannot account for forecloses both, permanently
  and silently.
- **Assignability, not licence compatibility, is the test for
  incoming code.** GPL-compatible is not good enough. Code the
  project cannot acquire *title* to cannot enter, whatever its
  licence.

**Vet against a commercial dual licence, and say only "relicensing"
out loud.** These are two different jobs and the difference between
them is deliberate. What the project *states* — in README.md,
CONTRIBUTING.md, and CLA.md — is that relicensing is reserved and
nothing is planned, which is true and is all the disclosure the
reservation needs. What the project *vets against* is the strictest
realistic outcome, which is a commercial dual licence, because
vetting to a weaker bar would forfeit the reserved option invisibly.

So the question to ask of any external source is **"could this ship
inside a proprietary product?"** — never "is this GPL-compatible?"
The second question has a comfortable answer far more often than the
first, which is exactly why it is the wrong one. Testaferro's own GPL
arm could absorb a great deal that a commercial arm never could, and
the difference between those two sets is precisely what the
reservation is holding open.

The asymmetry is what makes this worth the discipline: judging
correctly costs nothing at the moment a dependency or a reference is
first considered, and cannot be revisited afterwards at any price. By
the time it matters the code is load-bearing, and the upstream author
is under no obligation to sell anything.

Contributions are therefore accepted only under the copyright
assignment in `CLA.md`, with an automatic fallback to an exclusive
sublicensable licence where a jurisdiction bars assignment. Once
assigned, a contributor's files carry Paul's copyright notice,
because he is then the actual owner — the REUSE record states
ownership, not authorship, and authorship credit lives in the git
history. Keep the human submission terms in `CONTRIBUTING.md`
synchronized with this policy.

**Never merge third-party source.** Not permissively licensed source,
not public-domain-looking snippets, not vendored files. The
contributor cannot assign what they do not own, and neither can the
project. Third-party code enters as a declared dependency or not at
all. (`src/testaferro/assets/` is vendored from reliquary's codex and is
not an exception: reliquary is the same owner's work, so there is no
third party — see the prior-art section.)

### Dependency licence tiers

Every runtime dependency sorts into exactly one tier, and the tiers
are drawn against the commercial-dual-licence bar above rather than
against GPL compatibility. Adding a dependency in a lower tier than
it belongs is the single change most likely to cost the project
something it cannot get back.

| Tier | What qualifies | Standing |
|---|---|---|
| **1 — Sublicensable** | MIT, BSD-2/3-Clause, Apache-2.0, ISC, PSF, MIT-CMU/HPND, Zlib | Freely dependable. Attribution obligations carry into any redistribution. |
| **2 — Arm's length only** | LGPL as an unmodified, separately installed dependency; GPL invoked as a **separate process** or booted as a **guest OS** | Permitted, never combined. Vendoring, forking, patching, or bundling it into a frozen executable demotes it to tier 3. |
| **3 — Refused** | Any GPL/AGPL code that would be linked, imported, or copied into the project | Never — with the one standing exception below. Compatible with the GPL arm and fatal to the reservation, which is the whole point of the tier. |

**Reliquary and remanence are the standing exceptions to tier 3, and
ownership is why.** Both are GPL-3.0-only — reliquary from
`0.1.0.dev5` — and Testaferro imports both, which for any other
author's code would be refused outright. They are dependable here
because all three projects belong to the same owner, and each one's
contribution policy (assignment, the same reserved relicensing right)
keeps it relicensable by the same hand — so a commercial arm of
Testaferro can only exist as a decision that licenses all three
together, which is the owner's to make. Record each dependency's
standing as **owner-relicensable**, not tier 1: the moment either
contained code its owner could not relicense, this analysis would
fail with it. P11 caps the runtime closure at pytest, reliquary and
remanence; this section is why the cap is also a licensing boundary,
and it is why the cap is not merely a taste for small dependency
lists — **every addition to it is a licensing decision**, and only
the owner's own work can be added without demoting the reservation.

Build-time and development dependencies are normally out of scope —
they are not distributed, so their licences impose nothing. This
repository has **one exception to that carve-out**: the checked-in
integration binary `tests/integration/guest/SUITE.EXE` embeds
material from its build inputs and ships with the repository. What it
embeds and on what terms is recorded in the prior-art section below.

## Prior art and external references

**Every project named in this section is vetted against the
commercial-dual-licence bar above, never against GPL compatibility.**
The default rule is doctrine, and it is independent of any licence:
designs are studied and reimplemented; code is never read for
reimplementation, ported, or translated. A close translation is a
port whatever a licence permits. This project keeps **one recorded
exception** to that doctrine — the CppUTest entry below — and an
exception is the owner's to make and record, never assumed.

Where doctrine and licence agree, **record both reasons anyway**,
because they fail differently: a licence argument can be falsified by
a licence change, and doctrine cannot. Every licence stated below was
verified against the upstream repository or release tag on
2026-07-29; a licence that matters again later (a promotion from
name-drop to design reference, a re-derivation against newer source)
is re-verified then, at the version in question.

### Reliquary — the provider, and the standing tier-3 exception

The only guest-machine provider (P1, D1) and a declared, imported
runtime dependency. GPL-3.0-only from its `0.1.0.dev5`; the release
Testaferro currently pins (`0.1.0a2`, D4) is well past that
conversion, so today's installed closure is the copyleft one this
standing was written for, not merely anticipating it. Imported GPL
is tier 3 for any other author's work; reliquary is
dependable because it is the same owner's, under the same assignment
policy and the same reserved relicensing right, so both projects can
only ever be relicensed by the same hand and in one decision. That
standing is **owner-relicensable** — it is not tier 1, and it fails
the day reliquary contains code its owner cannot relicense, which
reliquary's own CLA exists to prevent.

`src/testaferro/assets/` is *copied* from reliquary's codex (P17, D20) —
the one place this repository carries another repository's files —
and is not third-party material for the same reason: same owner, so
title is already consolidated. What reliquary drives underneath is
its own business: **QEMU appears nowhere in this package** (P2), is
deliberately never named in Testaferro's source or docs, and there is
nothing to vet here because nothing is referenced. Keep it that way —
the arm's-length analysis for QEMU lives in reliquary, the project
that actually invokes it.

### CppUTest — the recorded doctrine exception

BSD-3-Clause, verified at the `v4.0` tag — `COPYING` and each
individual file named below carry the same three-holder notice
(Copyright (c) 2007 Michael Feathers, James Grenning and Bas Vodde).
Two distinct uses, both deliberate:

- **The adapter derives from its source.** `src/testaferro/cpputest.py`'s
  argv builders and output grammars follow CppUTest v4.0's own
  `TestOutput.cpp` and `CommandLineTestRunner.cpp` rather than
  observed samples (P9), and the integration makefile's flags follow
  CppUTest's `platforms/Dos/Makefile`. This is reading an upstream
  implementation — the doctrine's exception, made on the licence
  ground the doctrine usually refuses to rest on. It holds because
  what is taken is the program's observable interface (what it
  prints, what argv it accepts) re-expressed as Testaferro's own
  parsing code, and because BSD-3-Clause is sublicensable, so even
  the most conservative reading — a derivation of BSD-licensed
  source — survives the commercial bar with attribution carried.
  **The exception is version-pinned by nature**: what was derived
  from v4.0 is settled under v4.0's licence and no future CppUTest
  relicensing can reach it, but re-deriving against newer source
  re-opens the question at that version's licence. Verify before
  re-deriving.
- **`SUITE.EXE` compiles it in.** The integration fixture links
  `src/CppUTest` and `src/Platforms/Dos` — only BSD-3-Clause code
  sits under `src/` at the v4.0 tag — so the checked-in binary
  contains CppUTest object code, and BSD's binary-distribution
  notice obligation applies: the holders are named in `REUSE.toml`'s
  annotation for the binary, the licence text stays in
  `LICENSES/BSD-3-Clause.txt`, and both travel with the repository.

One cosmetic caveat for the record: CppUTest's per-file headers carry
unfilled template placeholders ("the name of `<organization>`"); the
`COPYING` file and its named holders govern.

### Open Watcom — the toolchain, and why the fixture is not GPL

The maintainer's compiler for `SUITE.EXE` (never a consumer's
concern, and not a P11 dependency). Licence: Sybase Open Watcom
Public License 1.0 (`Watcom-1.0`), and its DOS C/C++ runtime is
**statically linked into every executable it builds** — including the
checked-in `SUITE.EXE`. Three facts, verified 2026-07-29, govern how
this repository handles that:

- **The licence has no runtime exception.** Its "Original Code"
  expressly includes compiled object code, so the runtime portions
  inside a built binary remain Covered Code. The project's
  maintainers confirm the omission is historical accident, not
  intent (open-watcom-v2 discussion #382), but only SAP could change
  the text, and a relicensing effort (to Apache-2.0 with LLVM
  exception, discussion #271) has not completed. If it ever does,
  this entry is re-evaluated at that version.
- **Distributing the binary carries obligations**, and the makefile
  header discharges them: retain Sybase's notices, ship the licence
  text (`LICENSES/Watcom-1.0.txt`), and state prominently where the
  runtime's source is available (§2.2(d)). Modifying the runtime
  itself would add a source-publication obligation — do not patch it.
- **Watcom-1.0 is GPL-incompatible**, and no settled reading brings
  the statically linked runtime under GPL's system-library
  exception. A GPL-licensed program linked against it is arguably
  undistributable — so **nothing GPL may enter `SUITE.EXE`**, which
  is why `SUITE.CPP` and the guest makefile are deliberately
  BSD-3-Clause in a GPL repository and must stay that way. The
  binary is mere aggregation beside the GPL work, not a combination
  with it.

For the commercial bar: the fixture is not product code, Watcom-1.0
permits object-code distribution under one's own licence with the
notices intact, and the whole question stays fixture-sized so long as
Open Watcom never touches `src/testaferro/`.

### pytest — host surface

MIT, tier 1. The facade's host surface (P11), imported lazily.
Nothing further to hold.

### FreeDOS — the zero-configuration guest

GPL programs, and **tier 2 by the machine boundary**: a guest
operating system Testaferro installs and boots inside a VM, never
linked, never imported, never shipped. The LiveCD is downloaded by
the tester's machine at run time and the installed image lives in the
tester's cache (D20). That separation is load-bearing: **never bundle
FreeDOS media, or the installed image, into the distribution** — a
wheel or sdist carrying either would be distributing GPL material and
would demote the tier.

### pytest-embedded — concept reference

Espressif's host-pytest-around-a-native-guest-framework plugin is the
closest prior art to Testaferro's shape, and the one README
comparison that is a genuine concept reference rather than
positioning. MIT (each package in its repo licenses separately; the
repo root is a compound MIT/CC0 notice — cite the package licence,
not the root). Both reasons on record: doctrine (its designs may be
studied from docs and published behaviour; its code is never read),
and licence (tier 1, so even the licence poses no bar). It is not
directly reusable regardless — it assumes Espressif targets, serial
transport, and Unity's grammar.

### Positioning references — named, nothing taken

README.md's "Where it fits" names four more projects purely to
orient a reader: pytest-vagrant (BSD-3-Clause), pytest-testinfra
(Apache-2.0), pytest-cpp (MIT), and vmtest (BSD-3-Clause, u-root
Authors). A name-drop takes nothing from a project, so no licence
could make one unsafe; the licences are recorded anyway so that a
future promotion — to concept reference or dependency — starts from
a known standing instead of an assumption. pytest-xdist appears in
README usage advice as a consumer-side tool (MIT); it is not a
dependency and nothing of it enters this codebase.

## The environment

**uv provisions and owns the environment.** One command creates
`.venv`, installs the project editable, and installs its dependencies:

```powershell
uv sync
```

`uv.lock` is committed, and it is what makes "the environment the
suite passed in" reproducible — which matters here because with no CI
the local suite *is* the gate. `uv sync` reproduces the lock exactly;
`uv lock` is what deliberately moves it. Do not hand-manage `.venv`,
and do not install tooling globally.

## Checks

Run checks through uv, which uses the locked environment.

```powershell
uv run python -m compileall -q src/testaferro tests
uv run python -m unittest discover -s tests -v
uv run --python 3.12 python -m unittest discover -s tests
uv build
```

**The third line is the floor check, and it is not optional.** The
supported floor is a published claim (`requires-python`), so it is
tested rather than asserted — the same reading applied everywhere
else here, where an untested claim is an unclaimed capability rather
than a quiet promise (P11). uv installs the interpreter itself, so it
costs one line. Reliquary learned this the expensive way: it
published `>=3.9` unexercised, and 3.9, 3.10 and 3.11 all failed the
day someone ran them (D95 there).

Output-grammar changes additionally warrant a real end-to-end run,
since the unit fixtures are source-derived and not captured (P9) —
which is not a formality: the first real run found a failure message
running on past its own end, because the transport drops the blank
line the grammar ended on. That run is the integration tier, and it
boots a guest, so it is asked for rather than discovered:

```powershell
$env:TESTAFERRO_INTEGRATION = "1"
uv run python -m unittest discover -s tests/integration -v
```

**A pin move is one of the changes that warrants it**, whatever it
touches: the provider owns the guest lifecycle, so a release can move
behaviour no unit fixture observes. Adopting `0.1.0.dev6` was exactly
that — the unit tier proved the letter read against a
directory-source drive, and only the guest run proved it against the
layered qcow2 the zero-configuration journey actually boots.

## Building and publishing

**`uv build` builds an sdist and then a wheel from that sdist**,
which is what checks the source archive is complete rather than
merely present. After packaging metadata changes, inspect `PKG-INFO`
in both artifacts for at least the name, version, Python requirement
and runtime dependencies.

**Nothing FreeDOS may enter either artifact.** The media and the
installed image are GPL-incompatible to redistribute here (see the
licensing section), and they live in the cache rather than the tree
precisely so a build cannot sweep them up. `[tool.setuptools.package-data]`
ships `assets/*.rlqb` and `assets/*.rlqs` — the recipe, not what it
builds — and that distinction is the thing to re-check whenever the
asset list grows.

**The suite is not packaged either**, in either artifact, which is
what [MANIFEST.in](MANIFEST.in)'s `prune tests` is for. The same call
was made in reliquary the same day (D96 there, which forbids its
suite *and* its `planning/` tree in both artifacts), so this is a
standing rule across these projects rather than a Testaferro
preference. Setuptools'
default sdist picks up the top-level `tests/*.py` and nothing under
`tests/integration/`, so before that line the sdist shipped *half* a
suite — the unit files without the tier carrying most of the real
coverage, and without the guest fixture. Half a suite is worse than
none: it looks runnable and proves nothing. Not packaging it also
keeps the distribution single-licensed, since
`tests/integration/guest/` is deliberately BSD-3-Clause and would
otherwise travel inside a GPL-3.0-only artifact. Whoever wants to run
the suite clones the repository, which is the only way to get a guest
run anyway — the integration tier needs QEMU and an installed FreeDOS
system, and no sdist can carry either. **Re-check this whenever a test
directory is added**, because the default is to include, not exclude.

**Publishing is `uv publish`**, which uploads `dist/*` to PyPI. With
no CI there is no trusted-publishing path, so it takes a token
(`UV_PUBLISH_TOKEN` or `--token`), and `uv publish --dry-run` walks
the whole path without uploading. `twine check` is deliberately not
in this list: its rendering job is an RST problem and this readme is
markdown, the index validates and rejects bad metadata itself, and a
rejected upload does not consume the version.

## Unit and integration

The split is by **cost**, not by coverage (P10): a unit test is cheap and
draws in nothing external or uncontrolled. Nearly all of this
project's behaviour can only be proved by booting a guest, so the
integration tier will always carry most of the real coverage — which
is a reason to push the unit tier as far as it will go, not a reason
to relax it.

Unit tests may use reliquary freely; what they must never do is
start a guest (P10). The boundary is exact:

- `create_machine()` is **cheap and self-contained** — blueprint
  parsing, namespace and media resolution, hash verification, drive
  materialization, machine state. Unit tests run it for real, and
  should: it is the best coverage available on this side of the line.
- `start_machine()` starts a guest for real, and leaves a process
  behind. It, `stop_machine()`, `exec()`, `run_script()` and
  `get_machine_var()` are stubbed in the unit suite and belong to
  integration.

**`run_script()` is on that list and not obviously.** A script's
`machine` header is a precondition reliquary *establishes*, so running
the readiness script — which says `machine running` — against a
machine the unit fixture never really started **starts it for real**.
Stubbing `start_machine` alone does not hold the line, and the way
that announces itself is a unit run booting QEMU.

**The cheap half of that is conditional on the blueprint, not on the
call.** `create_machine()` stays cheap only while every drive's media
is `use` (attached in place). A blueprint declaring a blank
(`{"size": ...}`) — or a `difference` overlay — materializes it
through an **external image tool**, the same uncontrolled toolchain,
so such a machine belongs in an integration test.

**Zero configuration is now on the far side of that line** (D20), and
this is the boundary moving rather than a rule relaxing. The default
system materializes through a guest *install*, and a guest session
layers a `difference` overlay over it; neither is the unit tier's to
do. Unit cases that are about Testaferro's own bookkeeping declare a
`boot_image` instead and stay cheap, and `tests/test_reliquary.py`
refuses `_build_default_image` at module scope so that reaching it
fails on the spot.

**Integration does not mean "boots a guest"** — it means the fixture
is expensive, which is a different claim (P10). `tests/integration/
test_at_rest.py` is the case that makes the distinction earn its
keep: it needs the installed FreeDOS system, so it belongs on that
side of the line, but every case runs between `create_machine()` and
a first start that never happens. Eleven of them cost about fifteen
seconds together, against roughly fifteen for a *single* boot.

**That file exists because mocks at this seam go stale silently.**
`PlacementTests` in the unit suite holds Testaferro's own policy over
a resolution it stubs; it is only as good as the stub's shape being
right, and a stub cannot notice that the real answer moved — which is
exactly what happened when 0.1.0a2 deleted the drive-letter report
these tests used to stub (D108). So the at-rest file pins remanence's
actual answers against a real qcow2 instead — FAT16 recognition,
`at_rest.put_tree` creating its own directory, a copy that does not
mirror, and the refusal's **rule id** rather than its prose. **The
letter-map cross-check this file used to carry is gone with the
report it checked**, not merely stale: there is no provider answer
left to confirm the zero-configuration guarantee against, so that
half of the guarantee now rests on the guarantee alone (still true —
Testaferro's own one-disk machine still has one FAT16 volume — but
unconfirmed by a second source). Keep both remaining halves: the unit
tier is the always-on guard, and this is what keeps its fixtures
honest. Remanence's at-rest answers are machine input that Testaferro
*acts* on, and a wrong reading places a suite on the wrong drive —
which is the variability-times-blast-radius that earns pinned
coverage.

**A dry create reaches past that line without crossing it**, and it
is the unit tier's newest reach. `create_machine(dry_run=True)`
(0.1.0.dev5) runs the whole preflight — media resolution, drive and
controller assignment, boot validation, the schema — and builds
none of it, returning a `DryRun` whose `plan` is the document
reliquary would have acted on. So the **zero-configuration document
is now unit-testable**: a placeholder file stands in for the built
system, because nothing reads it. `BlueprintAcceptanceTests` is that
suite, and it exists because `BlueprintAuthoringTests` structurally
cannot fail the way that matters — reading back Testaferro's own
dict proves Testaferro consistent with itself, and a document
reliquary has since stopped accepting passes it unmoved. Prefer a
dry create whenever the question is *would reliquary take this*; it
costs under a second. What a dry run cannot answer is anything read
off a materialized image — the drive report is created-only by the
provider's ruling (D83 there), so letters are never asked of it.

**That guard exists because the same mistake happened twice.** Six
tests once launched real VMs while appearing mocked, costing ~10s
of a 12s suite. Then the default became an install, and the case
exercising it went on mocking `reliquary.fetch_media` — which had
stopped being the seam. Nothing failed; a unit run simply installed
an operating system for five minutes. The lesson both times is the
same: a mock that no longer intercepts does not announce itself.

The suite runs in about nineteen seconds today, and
roughly six of those are `tests/test_plugin.py`: a collection plugin's
whole subject is what pytest does with a file, so each case runs
pytest for real in a subprocess. Those runs stay on this side of the
line because the tree's own `conftest.py` puts a fake binding in
`sys.modules` before resolution imports it — no guest started, and
no reliquary either. Everything else is a few seconds, so a
jump outside `test_plugin.py` means something crossed the line;
`--durations` finds it quickly, and a jump into the *minutes* means
an install did.

`_work_slot()` chooses the slot; `_letter_map()` **computes every
drive's letter from the declaration, deterministically** (0.1.0a2,
D108). Through 0.1.0.dev4 the letter was derived while authoring the
blueprint, which 0.1.0.dev5 ended by reading volumes off the image at
rest (D78 there) and 0.1.0.dev6 answered with `describe_drives()`
instead (D83 there) — and 0.1.0a2 deletes that report outright, with
no provider answer left to ask for and remanence refusing the same
question by design (its own D57). What comes back reinstates D78's
assumption deliberately, as Testaferro's own stated policy rather
than something read back: one volume per hard disk, true by
construction for Testaferro's own media and taken as given for a
`machine_config` template. `WorkDrivePlacementTests` states every
slot case; `PlacedLetterTests` holds the letter computation, pure
declaration arithmetic with no machine or session in sight.

**Placement is where the letter is actually used**, and it is tested
in three places for three different reasons. `PlacementTests` holds
the *policy* — the work drive's own letter is the default, always,
computed rather than read. `DeclaredPlacementTests` runs the real
session flow with `_resolve_volume`/`at_rest.put_tree` stubbed, and
holds the rules a policy cannot state: a declared address is never
defaulted over and is the address the command spells. The integration
tier holds the thing neither can reach — a real guest, its work drive
live-served with no write at rest at all, reading its suite back from
`D:\` with DOS's own `DIR`.

**The integration tier exists and passes** — `tests/integration/`,
holding Testaferro's own CppUTest DOS suite (`guest/`, with its
source, its Open Watcom makefile and the built `SUITE.EXE`) and the
cases that boot it. Six of them: the guest enumerates, runs batched
and singly, replays a failure with the guest's own file and line,
`pytest SUITE.EXE` collects and runs for real, and a `testaferro.ini`
beside a project claims the suite and boots the environment it
declares with nothing named on the command line. Under two minutes.

Three defects fell out of building it, which is what it was for. A
grammar that ended a failure message on a blank line the transport
drops (fixed above). An `exec()` that returned screen text it could
not attribute to the command (`ferroteca/reliquary#6`, fixed in
0.1.0.dev4). And Testaferro typing at a guest that was not listening —
**ours**, and the readiness contract above is the fix.
