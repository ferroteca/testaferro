# Roadmap

Parked and planned direction for testaferro, agreed in design
discussion and deliberately not built yet. Maintenance guidance for
the current code lives in [AGENTS.md](AGENTS.md); this file records
where the project wants to go and the design decisions already made
for getting there.

Platform and test-machine configuration — `config()`, selection, and
the local `testaferro.ini` — is landed on relict's
`Runner`/`MachineConfig` interface. Relict remains the only runner.
Guest-OS workflows beyond DOS (install media, unattended setup,
platform-specific completion detection) belong in relict; testaferro
adds a thin binding when a platform is ready to surface through the
facade. Parallelism work is grouped below as a low-priority
milestone.

## Platforms and test machines

Two separated concepts, and the consumer-facing vocabulary for
everything guest-related; relict and QEMU stay implementation details.

- A **platform** is a *type* — the OS family a suite is built for:
  "dos", and later names as relict grows them. A platform knows
  which binary formats it can run and its default boot-image media
  type.
- A **test machine** is a configured relict `Runner`: its
  `MachineConfig`, boot media included, carries its platform type.
  Several machines may share a platform — FreeDOS and MS-DOS machines
  are both "dos".

Agreed shape:

- **`testaferro.config(machine, platform=None, **options)`**
  declares one test machine: it constructs a relict `MachineConfig`
  from the options or accepts a machine template (below), then creates
  the relict runner as needed. `platform=` remains available but is
  not mandatory: a machine config that declares its platform supplies
  it; otherwise the explicit argument, then relict's default, supplies
  it. An explicit platform that conflicts with the machine config is
  an error. Calls accumulate:

      testaferro.config("freedos", platform="dos")
      testaferro.config("msdos", platform="dos",
                        boot_image="msdos-boot.img")

  `start()`/`stop()` stay pure lifecycle; `start(boot_image=...)`
  remains as a compatibility shorthand declaring the default DOS
  machine. The local text config file (Configuration below) is the
  declarative twin of `config()`: one section per machine.
- **Machine templates.** A test machine may be declared from a
  relict machine template: its existing `MachineConfig`, including one
  loaded from a versioned machine document. The template is reusable
  configuration, not shared run state: it is duplicated/materialized
  into every fresh runner home, including copies of mutable media, so
  concurrent and sequential invocations remain isolated. Read-only
  media may be shared. The template's platform participates in the
  `platform=` resolution above. `boot_image=` is the compatibility
  shorthand for a generated one-drive template and cannot be combined
  with an explicit template.
- **Boot images.** Every test machine has exactly one boot image;
  only the media type varies — floppy, hard disk, CD (USB: open
  question) — defaulted by the platform (dos: floppy). The image is
  supplied ready (`boot_image=`) or downloaded (the dos default).
  Container formats beyond raw (e.g. qcow2) are relict's business to
  detect. How non-DOS platforms obtain or build boot media is
  relict's concern.
- **Machine configuration.** Relict's `MachineConfig` is the one
  configuration authority. It owns generic controls (boot media, run
  timeout), platform-specific controls as those workflows arrive in
  relict, and QEMU controls (binary, machine type, memory, extra
  arguments). Testaferro passes configuration through and relies on
  relict for normalization and validation instead of mirroring its
  schema.
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
- **Runner.** Relict is the sole runner across platforms. There is no
  `runner=` override or testaferro runner contract. A prebuilt
  `Backend` remains the custom escape hatch for callers with a wholly
  different execution mechanism.
- **Landed.** `testaferro.config()` accumulates named relict machine
  templates, `guest_suite(..., platform=, machine=)` selects them,
  `binfmt.Format.platform` names inferred platforms, and the facade's
  binding table keys by platform name. An optional per-project
  `testaferro.ini` is the declarative twin of `config()`: one section
  per machine, loaded by `load_config()` and by `guest_suite()` via an
  upward search from the call site. Further platform bindings wait on
  relict.

## Configuration

- **Local text config file — landed.** Optional per-project
  `testaferro.ini` with one section per test machine (optional
  platform, boot image, machine template path, or scalar/JSON
  `MachineConfig` fields). Normalized through relict's machine
  configuration; `guest_suite()` loads it by searching upward from
  the call site.

## Lifecycle

- **testaferro CLI** — e.g. `testaferro shutdown` to close
  persistent machines and manage caches.
- **Persistent machines** — test machines that opt out of the sweep
  at `stop()`, keeping their VMs warm for reuse across pytest runs,
  shut down explicitly via the CLI.

## Relict integration

Relict is testaferro's only runner and a declared dependency, so
testaferro integrates directly with its existing
`Runner`/`MachineConfig` interface. There is no `runner=` override,
structural runner contract, conformance kit, or mirrored configuration
hierarchy. With one implementation, such a seam would add translation
work without providing variation or leverage.

Relict owns QEMU lifecycle, machine configuration and validation,
provisioning, guest control, completion detection, and all in-guest
mechanics — including any future guest OS beyond DOS. Testaferro owns
executable-to-platform and machine selection, durable caches,
materializing isolated runner homes, pytest sessions and parallelism,
test-framework composition, batching, and result replay. Relict's
runner binds a home at construction; testaferro creates a fresh
runner from the selected machine template for each backend session.

The existing prebuilt-`Backend` path remains the custom escape hatch;
it is already the appropriate seam for an execution mechanism other
than relict. `SuiteBackend` may retain its internal runner-callable
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
platform it binds (e.g. `dos`), leaving QEMU and relict entirely to
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
   verify (read-only) that relict's free-port selection is
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
VM belongs to relict, never to testaferro. Guest-OS platform
workflows beyond DOS (including former win9x install/cache plans)
belong in relict as well; testaferro only binds platforms relict
already supports.
