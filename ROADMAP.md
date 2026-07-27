# Roadmap

Parked and planned direction for testaferro, agreed in design
discussion and deliberately not built yet. Maintenance guidance for
the current code lives in [AGENTS.md](AGENTS.md); this file records
where the project wants to go and the design decisions already made
for getting there.

Platform and test-machine configuration — `config()`, selection, and
the local `testaferro.ini` — is landed on reliquary's **blueprint**
model: a declaration is an authored blueprint, and each backend
session has reliquary create and boot a machine from it. Reliquary
remains the only guest-machine provider. Guest-OS workflows beyond
DOS (install media, unattended setup, platform-specific completion
detection) belong in reliquary; testaferro adds a thin binding when a
platform is ready to surface through the facade. Parallelism work is
grouped below as a low-priority milestone.

Reliquary is moving fast and testaferro follows it. The
`Runner`/`MachineConfig` layer this project was first built on was
removed in reliquary 0.1.0.dev2 and replaced by blueprints and the
machine lifecycle; the dependency is pinned to an exact version for
that reason. Expect further adaptation work to arrive as reliquary
releases, and treat a version bump as a task rather than a chore.

## Platforms and test machines

Two separated concepts, and the consumer-facing vocabulary for
everything guest-related; reliquary and QEMU stay implementation details.

- A **platform** is a *type* — the OS family a suite is built for:
  "dos", and later names as reliquary grows them. A platform knows
  which binary formats it can run and its default boot-image media
  type.
- A **test machine** is a reliquary blueprint: the machine's own
  description, boot media included, carrying its platform type.
  Several machines may share a platform — FreeDOS and MS-DOS machines
  are both "dos".

Agreed shape:

- **`testaferro.config(machine, platform=None, **options)`**
  declares one test machine: it builds a blueprint machine spec from
  the options or accepts a machine template (below). `platform=`
  remains available but is not mandatory: a template that declares
  its platform supplies it; otherwise the explicit argument, then
  testaferro's "dos" default, supplies it. An explicit platform that
  conflicts with the template is an error. Calls accumulate:

      testaferro.config("freedos", platform="dos")
      testaferro.config("msdos", platform="dos",
                        boot_image="msdos-boot.img")

  `start()`/`stop()` stay pure lifecycle; `start(boot_image=...)`
  remains as a compatibility shorthand declaring the default DOS
  machine. The local text config file (Configuration below) is the
  declarative twin of `config()`: one section per machine.
- **Machine templates.** A test machine may be declared from a
  blueprint template: a `MachineSpec`, a mapping, a whole blueprint
  document, or a path to a `.rlqb`. The template is reusable
  configuration, not shared run state: reliquary materializes a fresh
  machine from it for every backend session, so concurrent and
  sequential invocations remain isolated. **Which media that copies
  is the blueprint's own business** — reliquary's per-drive
  `materialize` mode (`new`, `copy`, `difference`, `use`) decides,
  and testaferro no longer duplicates media itself. The template's
  platform participates in the `platform=` resolution above.
  `boot_image=` is the compatibility shorthand for a generated
  one-drive template and cannot be combined with an explicit
  template.
- **Boot images.** Every test machine has exactly one boot image;
  only the media type varies — floppy, hard disk, CD (USB: open
  question) — defaulted by the platform (dos: floppy). The image is
  supplied ready (`boot_image=`) or downloaded (the dos default).
  Container formats beyond raw (e.g. qcow2) are reliquary's business to
  detect. How non-DOS platforms obtain or build boot media is
  reliquary's concern.
- **Machine configuration.** Reliquary's blueprint is the one
  configuration authority. It owns machine topology (drives, boot
  order, memory, cpus), platform-specific controls as those workflows
  arrive in reliquary, and backend controls (`backend-settings`).
  Testaferro carries the authored JSON through untouched and relies
  on reliquary for normalization and validation instead of mirroring
  its schema — a new blueprint field is expressible the day
  reliquary ships it, without a testaferro change.
- **Selection.** A suite runs on a test machine. It names one
  explicitly (`guest_suite(exe, machine="msdos")`), names a
  platform (`platform="dos"`) when that resolves to a single
  machine, or lets inference decide: the executable's format maps
  to its *native* candidate platforms (today MZ → {dos}). Running a
  format on a higher platform that also supports it is always an
  explicit choice, never inferred. Candidates are intersected with
  the configured machines' platforms; a unique machine wins, an
  ambiguous or empty result raises listing the choices. Zero config
  keeps working: an MZ suite with nothing configured gets an
  implicit default dos machine (the downloaded FreeDOS image) — a
  platform offers such an implicit machine only when it can
  self-provision without options.
- **Runner.** Reliquary is the sole guest-machine provider across
  platforms. There is no `runner=` override or testaferro runner
  contract. A prebuilt `Backend` remains the custom escape hatch for
  callers with a wholly different execution mechanism.
- **Landed.** `testaferro.config()` accumulates named blueprint
  templates, `guest_suite(..., platform=, machine=)` selects them,
  `binfmt.Format.platform` names inferred platforms, and the facade's
  binding table keys by platform name. An optional per-project
  `testaferro.ini` is the declarative twin of `config()`: one section
  per machine, loaded by `load_config()` and by `guest_suite()` via an
  upward search from the call site. Further platform bindings wait on
  reliquary.

## Suite specification document

A single JSON document that describes how a test machine is built and
carries the media it needs — testaferro's own spec, a **superset of a
reliquary blueprint** plus its media definitions.

**Much of this has since landed by another route.** When the
`MachineConfig` layer disappeared, `config()` / `testaferro.ini` moved
onto blueprints directly, so a declaration already *is* an authored
blueprint: `machine_config=` accepts a whole blueprint document or a
path to a `.rlqb`, media specs may sit beside the machine in it, and
testaferro passes all of it through for reliquary to resolve and
hash-verify. The insertion problem is solved too, though not as
written below. What remains genuinely open is narrower than the
original framing, and is called out per item.

Agreed shape:

- **Nested blueprint, not a flat merge.** Reliquary's blueprint
  schema is closed (`additionalProperties: false`), so testaferro's
  extra keys cannot sit beside the blueprint's. The document has its
  own top-level keys; a `blueprint` key carries the reliquary design,
  as either an inline blueprint object (itself a valid `.rlqb`) or a
  name/path reference to a blueprint reliquary already resolves.

  **The example below has lost its example.** `media` was the
  testaferro key that justified nesting; in reliquary's current model
  media specs are part of the blueprint document itself, so they are
  reliquary's keys, not testaferro's. The structural argument stands
  — a closed schema does admit no foreign keys — but nothing
  currently needs to sit beside the blueprint, which is what the
  final bullet asks about. Retained as written for the shape:

      {
        "blueprint": {
          "platform": "dos",
          "memory": "32M",
          "drives": {
            "hdd0": {"size": "20M"},
            "hdd1": { ... hostdir drive ... }
          },
          "boot": ["hdd0"]
        },
        "media": { ... }
      }

      // or reference an existing blueprint by name:
      { "blueprint": "freedos-1.4-plain", "media": { ... } }

- **Media definitions — landed.** Media specs live in the blueprint
  document itself in reliquary's current model (`.rlqm` retired), so
  a declaration carries them beside its machine. testaferro passes
  them through for resolution and hash-verified fetching and mirrors
  none of reliquary's media schema. The default FreeDOS boot floppy
  is one such definition: a remote zip pinned by hash, with the
  bootable image named as a child inside it.
- **Insertion — landed, but testaferro supplies the drive.** The
  original design assumed the blueprint would *define* a hostdir drive
  for testaferro to copy into. In practice testaferro **adds one
  itself**,
  at the lowest free disk slot, and stages the executable there before
  the machine boots. That is strictly better for the consumer: a
  declaration says nothing about testing, and a plain machine
  blueprint works unmodified. Two constraints came with it — the
  backend snapshots a host directory when the drive is attached, so
  staging cannot be lazy; and testaferro must name the drive letter
  the guest will give it, which means locally mirroring reliquary's
  DOS letter-assignment rule until reliquary exposes that mapping.
- **Insertion — later: a specified insertion point.** When reliquary
  is more mature, replace the testaferro-supplied hostdir drive with an
  explicit insertion point in the document (e.g. a slot plus a guest
  directory such as `hdd0:\TESTS\`). Writing into an image drive is
  testaferro's own offline work — reliquary blesses writes to a
  stopped machine's `drives/` but provides no FAT writer
  (mtools/pyfatfs-class dependency), and `insert_media()` covers only
  floppy and cdrom slots, never `hdd`. Deferred until then.
- **Executable and type bind at the call site, not in the
  document.** The spec describes the machine and insertion point and
  stays reusable across suites; each suite supplies its own
  executable and framework:

      guest_suite("tests/vring.exe",
                  spec="dos-cpputest.tfj",
                  exe_type="cpputest")

  `exe_type` selects the guest unit-test framework adapter; only
  `cpputest` is supported so far (testaferro's pluggable aspect). It
  maps to the existing framework adapter that `QemuSuiteBackend`
  already defaults to.

- **Resolved — reconciliation with the landed `config()` model.**
  This was open while `config()` targeted `MachineConfig` and the
  spec document targeted blueprints: two declarations of the same
  thing against two reliquary layers. `MachineConfig` is gone, both
  now mean the same thing, and the question no longer arises.
- **Open — what is actually left.** With declarations already being
  blueprints, the residue is whether testaferro needs a document of
  its *own* at all. It would buy: testaferro-specific keys beside the
  blueprint (the reason for nesting rather than merging, since
  reliquary's schema is closed), and the `spec=` / `exe_type=`
  spelling above. Against: a second document format to explain and
  version, when `machine_config=` already takes a `.rlqb`. Decide by
  naming a key that must live beside the blueprint and cannot be a
  `guest_suite()` argument — if none appears, this section retires.

## Consumer entry points

Two entry points onto one execution path. The **embedded pytest
facade** (`guest_suite()`) is the project's primary goal: a consumer
surfaces its guest suite as ordinary pytest items in its own test
tree. A **command-line entry** serves the step before that — trying a
suite against a guest machine without first writing anything into the
consumer project. They are not parallel products: they share as much
code and execution path as can be shared.

Agreed shape:

- **The CLI runs pytest; it does not report for itself.** `testaferro
  run tests/vring16.exe` resolves the backend, generates a one-line
  test module, and hands it to `pytest.main()`, forwarding whatever
  follows `--`. So the CLI exercises the embedded path rather than
  approximating it: `-k`, `-v`, `-x`, `--tb`, `--lf` and third-party
  plugins all come free, and there is no second reporter to drift.
  A hand-written pytest-alike reporter is rejected on purpose —
  divergence between what the CLI shows and what the consumer gets
  after embedding would defeat the CLI's only reason to exist.
- **The shared seam is backend resolution.**
  `facade._dispatched_backend()` — config search, platform
  validation, format classification, machine selection, binding
  import, option validation — moves into the core as the single place
  where "an executable plus options" becomes a `Backend`. Both entry
  points call it. Extracting it is the first implementation step,
  since today it is fused to the pytest entry point (it takes
  `search_from`, which `guest_suite()` computes from the caller's
  stack frame). Afterwards the entry points differ in three known
  places only:
  - **config search origin** — the caller's file when embedded, the
    current directory from the CLI;
  - **session lifecycle** — a consumer conftest calls
    `start()`/`stop()`; the CLI wraps its own run;
  - **enumeration** — embedded consumers usually pass a host-built
    twin as `enumerator=`; the CLI enumerates in the guest unless
    given `--enumerate-with`, and in-guest enumeration is the
    lossier path (agentless capture returns the visible screen, so a
    long list loses its head).
- **Flag/keyword parity.** Every CLI flag is the kebab-case spelling
  of a `guest_suite()` keyword, and every keyword is expressible on
  the command line: `--machine` ↔ `machine=`, `--framework` ↔
  `framework=`, `--boot-image` ↔ `boot_image=`, `--enumerate-with` ↔
  `enumerator=`. The CLI then teaches the API — what you typed to try
  a suite is what you write when you embed it — and the rule
  disciplines future growth: a keyword that cannot be spelled on the
  command line is a keyword worth questioning.
- **Deliberate asymmetry: exploration-only flags.** A few flags exist
  only on the CLI, because they concern trying a suite out rather
  than defining tests: `--list` (enumerate and stop), `--keep` (leave
  the run home behind for inspection instead of sweeping it), and
  `--snippet` (print the test module to paste into the consumer
  project). `--snippet` is what makes the two entry points literally
  one path: the CLI's output is the embedded form.
- **One CLI, subcommands.** `run` is one verb of the same executable
  that carries the lifecycle commands under Lifecycle below
  (`shutdown` and cache management). A `[project.scripts]` console
  entry is needed; there is none today. CONTRIBUTING's rule that
  pytest is imported lazily in `facade.py` becomes "confined to
  `facade.py` and the CLI module".
- **Open — what a machine name resolves to.** `--machine freedos` /
  `machine="freedos"` can mean the zero-configuration FreeDOS boot
  floppy that works today, or a named reliquary blueprint. The second
  reads better and is newly possible, but reliquary's codex `freedos`
  blueprint is an *install recipe* — a blank disk plus install and
  verify scripts — not a ready image, so it implies provisioning and
  machine reuse (see **Persistent machines** under Lifecycle):
  reinstalling FreeDOS per pytest run is not viable, and the binding
  currently sweeps its whole run home at `stop_session()`. It also
  means opting into reliquary's home-mode asset resolution, which the
  binding today deliberately avoids in favour of a hermetic
  per-session asset root. Unsettled; decided before this is built.

## Configuration

- **Local text config file — landed.** Optional per-project
  `testaferro.ini` with one section per test machine (optional
  platform, boot image, machine template path, or scalar/JSON
  blueprint fields). Carried through to reliquary, which validates
  it; `guest_suite()` loads the file by searching upward from the
  call site.

## Lifecycle

- **testaferro CLI** — e.g. `testaferro shutdown` to close
  persistent machines and manage caches. The same executable that
  carries `run` (see Consumer entry points above).
- **Persistent machines** — test machines that opt out of the sweep
  at `stop()`, keeping their VMs warm for reuse across pytest runs,
  shut down explicitly via the CLI.

## Reliquary integration

Reliquary is testaferro's only guest-machine provider and a declared
dependency, so testaferro integrates directly with its existing
blueprint and machine-lifecycle interface. There is no `runner=`
override, structural runner contract, conformance kit, or mirrored
configuration hierarchy. With one implementation, such a seam would
add translation work without providing variation or leverage — a
position the dev2 migration tested and did not overturn: the removal
of `Runner`/`MachineConfig` was absorbed in two modules.

Reliquary owns QEMU lifecycle, machine configuration and validation,
provisioning, guest control, completion detection, and all in-guest
mechanics — including any future guest OS beyond DOS. Testaferro owns
executable-to-platform and machine selection, durable caches,
isolated per-session reliquary homes, getting the suite executable
into the guest, pytest sessions and parallelism, test-framework
composition, batching, and result replay. Testaferro authors a
blueprint into a private home and has reliquary create and boot a
fresh machine from it for each backend session.

The existing prebuilt-`Backend` path remains the custom escape hatch;
it is already the appropriate seam for an execution mechanism other
than reliquary. `SuiteBackend` may retain its internal runner-callable
composition for locality and testing without turning that callable
into a public runner contract.

The abandoned `testaferro-runner-api` draft — protocol module, config
chain, conformance kit, and tests — remains archived in
[drafts/runner-api/](drafts/runner-api/) as historical reference, not
planned work. Reconsider extracting a runner seam only if a second
actual runner appears; derive any future interface from the concrete
implementations then.

### Internal binding naming

The platform concept already keeps QEMU out of the consumer's view
(consumers name platforms, never emulators); what remains is
whether the binding module `qemu.py` should be renamed for the
platform it binds (e.g. `dos`), leaving QEMU and reliquary entirely to
the binding implementation.

## Milestone: Parallelism (low priority)

All remaining parallelism work lives here. Multi-process parallelism
(pytest-xdist) already works across suites (`-n auto --dist
loadfile`; private homes/images make it safe). Items below are
parked as one low-priority milestone, listed in value order within
that milestone:

1. **Intra-suite sharding** — the item with real payoff. A middle
   backend operation between `run_all()` and `run_test()` ("run this
   subset in one boot"): CppUTest filter argv can select several
   tests per invocation, so a worker holding part of a suite boots
   once, not per test. Makes `--dist load` efficient on a single
   suite (~Nx wall clock for N workers) and softens `-k` narrowed
   selections in serial runs too. Touches `ResultBroker`, the
   `Backend` seam, and the CppUTest argv builders.
2. **QMP port collision check** — before leaning on parallel runs,
   verify (read-only) that reliquary's free-port selection is
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

## Out of scope by decision

Any guest-side agent/listener that handles execute requests inside a
VM belongs to reliquary, never to testaferro. Guest-OS platform
workflows beyond DOS (including former win9x install/cache plans)
belong in reliquary as well; testaferro only binds platforms reliquary
already supports.
