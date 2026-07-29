# AGENTS.md — repository guidance

Canonical, agent-agnostic guidance for working on testaferro — how to
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
testaferro's pluggable aspect is the guest unit-test framework
(U6).

Package layout (each module states its contract in its docstring):

- [testaferro/backend.py](testaferro/backend.py) — the `Backend`
  seam (`TestId`, `TestOutcome`, `GuestOutputError`, the
  five-operation ABC: `start_guest`, `list_tests`, `run_test`,
  `run_all`, `stop_guest`).
  **Three spans, three words** (D15): pytest's *session* is the whole
  run; a **guest session** is one guest up, between `start_guest()`
  and `stop_guest()`; a **run** is what `testaferro.start()`/`stop()`
  open — one staged image and one sweep area, holding many guest
  sessions. Nothing but pytest's own is called a session unqualified.
- [testaferro/cpputest.py](testaferro/cpputest.py) — the CppUTest
  **framework adapter**: argv builders + output grammars, derived
  from CppUTest v4.0's own source, not from observed samples. An
  argv builder returns a **sequence of tokens, never a command
  line** — spelling one belongs to whoever executes, since only
  they know whether the program is reached by a DOS command line or
  an argv list. The two spellings live in
  [reliquary.py](testaferro/reliquary.py) (`" ".join`) and
  [plugin.py](testaferro/plugin.py) (a splat into `subprocess.run`).
  A string return would satisfy every `for` loop and every join in
  the codebase while meaning something else, which is exactly how it
  went wrong once: the binding joined a string's characters and
  every guest operation asked for `SUITE.EXE - v`. So an argv
  expectation in a test is written out as a literal, never rebuilt
  from the builder under test. A grammar that refuses **states its
  reason and does not quote the text back** (D19): the caller passed
  that text in and still holds it, and an adapter that never saw the
  guest cannot say where it came from.
- [testaferro/environments.py](testaferro/environments.py) — named
  test-environment declarations backed by immutable
  `EnvironmentSpec` templates, plus selection and loading of the
  optional per-project `testaferro.ini` (declarative twin of
  `config()`). An `EnvironmentSpec` holds the *authored* reliquary
  blueprint JSON and mirrors none of reliquary's schema: fields pass
  through untouched — `platform` among them, which is the provider's
  word rather than testaferro's (P2) — and reliquary validates them
  when it parses the document. Keys hyphenated in the blueprint
  (`backend-settings`, `control-planes`) are written with underscores
  in Python and INI and normalized on construction. **`provider`,
  `timeout` and `suites` are testaferro's own** and never reach the
  blueprint: `provider` names what runs the guest (P1, D11), and
  reliquary's document has no field for who is reading it, which is
  exactly why it is declared beside the machine spec rather than
  inside it. It is left `None` when unsaid — the default belongs to
  `resolution.py`, said in one place. `select()`
  resolves a *name* against those declarations first and the standard
  catalog second (D10); the platform *inferred* from the executable
  matches declarations only, so zero configuration stays zero (P8).
- [testaferro/catalog.py](testaferro/catalog.py) — the standard
  environments testaferro curates, reachable by name
  (`environment="freedos"`). Each entry is an authored provider document
  carried through untouched, exactly as a declaration is (P3);
  `freedos` declares only its platform, which is what makes naming it
  and naming nothing run the same guest. Siblings arrive as guests
  grow.
- [testaferro/suite.py](testaferro/suite.py) — `SuiteBackend`, the
  internal execution × framework composition. Argv crosses it
  untouched: it joins nothing and quotes nothing, because a
  composition that knows neither aspect cannot know what a command
  line looks like at the far end. It is also **the only place both
  halves of an exchange are in hand** — the argv that went out and
  the text that came back — which is why an adapter's refusal becomes
  a `backend.GuestOutputError` here, carrying both, for an entry point
  to report (D19). An adapter states its reason and nothing about
  provenance; it never saw the guest.
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
  shared by the guest bindings. Also where a finished guest home is
  handed back: `release_guest_home()` is the single place that sweeps
  or keeps one, and `keep_guest_homes()`/`kept_guest_homes()` are the
  exploration switch and its report. The layout is the vocabulary made
  physical (D15): `runs/run-*/guests/guest-*/`, and `guests/` at the
  cache root for a guest belonging to no run. That policy is testaferro's, not
  any binding's, which is what lets the plugin read the answer without
  importing a binding — or a provider.
- [testaferro/reliquary.py](testaferro/reliquary.py) — the reliquary
  provider binding, for DOS guests (D16). Named for the provider it
  binds, because that is the layer testaferro talks to: every call in
  it is a reliquary call, and what reliquary drives underneath is its
  own business and appears nowhere in this package. What it drives is
  still a reliquary *machine*, which is why `machine_config=` keeps
  that word while the noun a suite writes is an environment: it names
  the provider's own document, passing through as `platform` does.
  `PLATFORMS` is the one thing it tells resolution about itself — the
  guests this provider serves, its own answer to give.
  `suite_backend()` guards with `binfmt.classify()`
  (rejections name the format and architecture) and returns a
  `ReliquarySuiteBackend`, with `framework` defaulting to the CppUTest
  adapter. Each guest session writes the declaration as a blueprint
  into a disposable reliquary home under `cache_root()`, then
  `create_machine()` → `start_machine()`; every guest run is one
  `reliquary.exec()` against that machine, and `stop_machine()` plus
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

  - **The reliquary context is hermetic.** Each guest session pins
    `reliquary.Context(home_dir=…, cache_dir=…,
    blueprints_dir=<guest home>, autoseed=False)`, so resolution
    sees only what testaferro authored for that run — never the
    user's reliquary home or the built-in codex. Autoseeding is off
    by default in reliquary's embedding API; pinning it per guest
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
- [testaferro/resolution.py](testaferro/resolution.py) — the
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
- [testaferro/items.py](testaferro/items.py) — the pytest items
  testaferro produces, which is the fifth interface: `item_id()` (the
  dash rule), `failure_text()` (the guest's own file, line and
  assertion) and `guest_output_text()` (the guest's own screen, when
  its answer could not be read at all — D19). Both entry points
  surface the same guest tests, so the spellings they share live here
  rather than in either of them. `guest_output_text()` leads with the
  reason because pytest's short summary quotes a report's first line
  and drops the rest, so that line has to stand alone.
- [testaferro/plugin.py](testaferro/plugin.py) — the `pytest11`
  collection plugin, which **auto-loads on installation** (D13):
  `pytest_collect_file` claims suite executables, and each guest test
  becomes an item under the executable's node
  (`tests/SUITE.EXE::Group-Name`). Options and ini keys are declared
  from one list (`_SETTINGS`) so the two spellings cannot drift (P16);
  `--testaferro-keep-guest-home` and the enumerator are the
  exploration-only exceptions. Execution guests are stopped in
  `pytest_sessionfinish`, deliberately **not** through
  `config.add_cleanup`: config cleanups run after the terminal
  summary, so a kept guest home would be reported before the guest
  that made it was closed. The claiming policy is the load-bearing
  part — see the invariant below. Its module imports stay stdlib-only:
  a pytest run that claims no guest suite must not pay for reliquary,
  which is why `environments.py` imports the JSONC reader lazily.
- [testaferro/facade.py](testaferro/facade.py) — the pytest facade
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
named test environments (including `testaferro.ini`) and
`testaferro.guest_suite()` for `environment=` selection or a
`provider=` said inline. A prebuilt
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
  and the plan is realigned. testaferro adopted this model after the
  code was written (D7), so its vision began wholly drafted in
  [planning/proposed/](planning/proposed/); U4 and P16 were pledged
  first (D13), then P1 and P2 (D18), and nothing had reached the
  root lists until P16 armed, followed by P10 and P4 one at a time,
  then by P6, P7, P8, P9, P11, P12, P13 and P17 together, and then by
  P1 and P2 once F12 built what they promised. Root
  [ARCHITECTURE.md](ARCHITECTURE.md) carries thirteen principles —
  P1, P2, P4, P6 through P13, P16 and P17 — and root
  `USE-CASES.md` still does not exist, so **the architecture binds
  and no use case does**. Four principles stay drafted: P3 and P5,
  each contradicted by a small piece of the code and each saying so
  at its own entry, and P14 and P15, which govern conduct rather
  than code. **No principle is pledged**, so a P-number now names
  either a rule in force or an argument. A principle may arm without
  ever being pledged, as most of these did — the pledged shelf holds
  what is owed, not a stop every entry makes. Cite a U- or
  P-number knowing it names a draft, unless it sits in
  [planning/pledged/](planning/pledged/), where it names something
  the project owes and has not yet delivered, or at the root, where
  a divergence is a bug rather than unbuilt work.
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

- Python code: stdlib plus two declared dependencies (P11) — pytest (the
  facade's host surface, imported lazily) and reliquary (the only
  supported guest-machine provider, imported by `testaferro/reliquary.py` for the
  machine lifecycle and by `testaferro/environments.py` for its JSONC
  reader alone). Support Python 3.9 and newer; keep lines near 79
  columns.
- Reliquary is pinned to an exact version in
  [pyproject.toml](pyproject.toml) (D4). Its API is still moving fast and
  has already removed the layer testaferro was built on once; a
  floating requirement would break consumers without warning. Moving
  the pin is a deliberate task — expect the binding to need work,
  and re-run the checks below against the new version.
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
- Every environment testaferro offers by name is testaferro's own
  (P17): a standard-catalog entry — and any blueprint, script or
  medium shipped with one — is authored here and complete in itself,
  never a name resolved out of reliquary's codex or the user's
  reliquary home (D6, D10). `StandardCatalogTests` guards it: a
  catalog document declares its media beside the machine that uses
  them. Provider content reaches a run only because a tester
  declared it.
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
start a guest (P10). The boundary is exact:

- `create_machine()` is **cheap and self-contained** — blueprint
  parsing, namespace and media resolution, hash verification, drive
  materialization, machine state. Unit tests run it for real, and
  should: it is the best coverage available on this side of the line.
- `start_machine()` starts a guest for real, and leaves a process
  behind. It, `stop_machine()` and `exec()` are stubbed in the unit
  suite and belong to integration.

**The cheap half of that is conditional on the blueprint, not on the
call.** `create_machine()` stays cheap only while every drive's media
is `use` (attached in place), which is what testaferro authors. A
blueprint declaring a blank (`{"size": ...}`) materializes it through
an **external image tool** — the same uncontrolled toolchain, so such
a machine belongs in an integration test. Reliquary's own codex `freedos` blueprint
declares exactly such a blank, so this is easy to walk into.

Six tests once launched real VMs while appearing mocked, costing ~10s
of a 12s suite. The suite runs in about eight seconds today, and
roughly six of those are `tests/test_plugin.py`: a collection plugin's
whole subject is what pytest does with a file, so each case runs
pytest for real in a subprocess. Those runs stay on this side of the
line because the tree's own `conftest.py` puts a fake binding in
`sys.modules` before resolution imports it — no guest started, and
no reliquary either. Everything else is still about one second, so a
jump outside `test_plugin.py` means something crossed the line;
`--durations` finds it quickly.

`_work_drive()` duplicates a rule reliquary owns and does not expose
(DOS drive letters). `WorkDrivePlacementTests` cross-checks the copy
against `reliquary.platform_dos.drive_letters`, so the duplication
fails loudly rather than silently running a suite off the wrong
drive. Keep that guard until reliquary offers a public query.

There is **no integration suite yet**, so no guest has run since the
migration to the blueprint model. End-to-end proof is still owed, and
it is what would arm the use cases: building that tier is F6 in
[planning/proposed/FEATURES.md](planning/proposed/FEATURES.md).
