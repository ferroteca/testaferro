# Roadmap

Parked and planned direction for testaferro, agreed in design
discussion and deliberately not built yet. Maintenance guidance for
the current code lives in [AGENTS.md](AGENTS.md); this file records
where the project wants to go and the design decisions already made
for getting there.

**Top priority:** platform/test-machine configuration, built directly
on relict's existing `Runner`/`MachineConfig` interface. Relict is the
only runner; testaferro does not maintain a second, hypothetical runner
contract around it.

## Platforms and test machines

Two separated concepts, and the consumer-facing vocabulary for
everything guest-related; relict and QEMU stay implementation details.

- A **platform** is a *type* — the OS family a suite is built for:
  "dos", "win3x", "win9x", "winnt", "linux", ... A platform knows
  which binary formats it can run and its default boot-image media
  type.
- A **test machine** is a configured relict `Runner`: its
  `MachineConfig`, boot media included, carries its platform type.
  Several machines may share a platform — FreeDOS and MS-DOS machines
  are both "dos"; Windows 95 and 98 machines are both "win9x".

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
      testaferro.config("win98", platform="win9x",
                        install_media=..., product_key=...)

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
  question) — defaulted by the platform (dos: floppy; win9x: hard
  disk). The image is supplied ready (`boot_image=`), downloaded
  (the dos default), or built from install media (win9x).
  Container formats beyond raw (e.g. qcow2) are relict's
  business to detect.
- **Machine configuration.** Relict's `MachineConfig` is the one
  configuration authority. It owns generic controls (boot media, run
  timeout), platform-specific controls as those workflows arrive
  (win9x install media, media hash, product key), and QEMU controls
  (binary, machine type, memory, extra arguments). Testaferro passes
  configuration through and relies on relict for normalization and
  validation instead of mirroring its schema.
- **Selection.** A suite runs on a test machine. It names one
  explicitly (`guest_suite(exe, machine="msdos")`), names a
  platform (`platform="dos"`) when that resolves to a single
  machine, or lets inference decide: the executable's format maps
  to its *native* candidate platforms (MZ → {dos}; NE → {win3x};
  PE x86 → {win9x, winnt}) — running a format on a higher platform
  that also supports it (MZ under win9x, NE under win9x) is always
  an explicit choice, never inferred. Candidates are intersected
  with the configured machines' platforms; a unique
  machine wins, an ambiguous or empty result raises listing the
  choices. Zero config keeps working: an MZ suite with nothing
  configured gets an implicit default dos machine (the downloaded
  FreeDOS image) — a platform offers such an implicit machine only
  when it can self-provision without options.
- **Runner.** Relict is the sole runner across platforms. There is no
  `runner=` override or testaferro runner contract. A prebuilt
  `Backend` remains the custom escape hatch for callers with a wholly
  different execution mechanism.
- **First step.** The current unreleased seam predates this
  vocabulary: `guest_suite(..., guest=, **guest_options)` and
  `binfmt.Format.guest` are renamed into the platform/machine
  terms, and the facade's binding table keys by platform name.

## Parallelism

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
   verify (read-only) that relict's free-port selection is
   collision-safe when several VMs start concurrently.
3. **Download lock** — two cold-cache workers can both download the
   default boot image; `.part` + `os.replace` keeps it correct but
   duplicates the fetch. A lock file in the cache would serialize it.
   Will matter far more for the Windows 95 installed-image cache
   below, where the duplicated work would be a full unattended
   install, not a fetch.
4. **Enumeration per worker** — each xdist worker imports the test
   modules, so guest-side enumeration (no `enumerator=`) costs a
   boot per worker. Document the `enumerator=` recommendation or
   cache enumeration keyed on the executable's hash.
5. **xdist_group auto-marking** — would let `--dist loadgroup` keep
   multi-suite files whole; deferred (unregistered marks warn when
   xdist is absent) and likely moot once sharding lands.

## Windows 9x platform

Fully designed; deferred indefinitely. With the platform seam in
place (above), adding the platform breaks no API: a rejection
simply becomes support. A complete draft of the binding and its
fake-execution unit tests is archived in
[drafts/win95/](drafts/win95/) — written before the
platform/`config()` naming and the universal boot-image concept (it
says `guest=`, `qemu95.start()`, and `hdd_image=`), but still the
reference for the install, caching, and session mechanics.

When revived:

- `binfmt` maps a Windows x86 PE (machine 0x014C) to candidate
  platforms {win9x, winnt}, and the facade's platform table gains
  "win9x" with its binding module.
- The binding mirrors the DOS one and uses a win9x workflow added to
  relict. Relict's machine configuration gains the install media,
  hash, and product-key controls; its workflow performs the one-time
  unattended install from the configured CD ISO into the hard-disk
  boot image, stages the executable on the vvfat guest drive, boots
  the image, detects completion via guest-initiated shutdown (Windows
  9x has no text screen to scrape), and returns the redirected log.
  Testaferro selects and materializes the configured machine but does
  not define a parallel runner interface.
- The environment is declared on the test machine
  (`testaferro.config(name, platform="win9x", ...)`) or overridden
  per suite — a ready boot image (`boot_image=`, a hard-disk
  image, which never combines with the install options) or install
  media (`install_media=` ISO path, or `media_url=` with mandatory
  `media_sha256=` verifying the download). The installed image is
  cached under `cache_root()/win9x/`, keyed by media identity
  (local ISO digest, or the declared hash) + product key — machines
  declaring the same media share the cached install.
- `testaferro.stop()` sweeps win9x machines' session state but
  never clears the installed-image cache — rebuilding costs a full
  reinstall, so clearing it is an explicit maintenance action (a
  natural job for the future CLI), not a side effect of `stop()`.
- Win9x machines accept DOS MZ executables too, but only by
  explicitly naming the machine or `platform="win9x"` (compat
  testing), since inference maps MZ to "dos".

## Configuration

- **Local text config file** — the declarative twin of
  `testaferro.config()` (Platforms and test machines above): an
  optional per-project file with one section per test machine
  (optional platform, boot image, machine template, or install media),
  all normalized and validated through relict's machine
  configuration, so test code names only the suite executable and
  testaferro resolves machines from config; plus relict's own local
  configuration where needed.

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
mechanics. Testaferro owns executable-to-platform and machine
selection, durable caches, materializing isolated runner homes,
pytest sessions and parallelism, test-framework composition, batching,
and result replay. Relict's runner binds a home at construction;
testaferro creates a fresh runner from the selected machine template
for each backend session.

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

## Out of scope by decision

Any guest-side agent/listener that handles execute requests inside a
VM belongs to relict, never to testaferro.
