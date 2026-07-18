# Roadmap

Parked and planned direction for testaferro, agreed in design
discussion and deliberately not built yet. Maintenance guidance for
the current code lives in [AGENTS.md](AGENTS.md); this file records
where the project wants to go and the design decisions already made
for getting there.

**Top priority:** the runner contract (Runner seams below) — a
*soft contract*: documented convention plus structural typing, not
a published package. It is the foundation the rest builds on —
relict's interface adoption, the platform/test-machine
configuration work, and every future runner all target it.

## Platforms and test machines

Two separated concepts, and the consumer-facing vocabulary for
everything guest-related; runners and emulators stay implementation
details.

- A **platform** is a *type* — the OS family a suite is built for:
  "dos", "win3x", "win9x", "winnt", "linux", ... A platform knows
  which binary formats it can run, its default runner, its option
  schema, and its default boot-image media type.
- A **test machine** is a *runner instance*: a runner constructed
  from its config — an instance of that runner's config type, boot
  image included (Config types below) — carrying its platform
  type. Several machines may share a platform — FreeDOS and MS-DOS
  machines are both "dos"; Windows 95 and 98 machines are both
  "win9x".

Agreed shape:

- **`testaferro.config(machine, platform=..., **options)`**
  declares one test machine: it constructs an instance of the
  platform's default runner (or the `runner=` override) from the
  options, validated against that runner's config type. Calls
  accumulate:

      testaferro.config("freedos", platform="dos")
      testaferro.config("msdos", platform="dos",
                        boot_image="msdos-boot.img")
      testaferro.config("win98", platform="win9x",
                        install_media=..., product_key=...)

  `start()`/`stop()` stay pure lifecycle; `start(boot_image=...)`
  remains as a compatibility shorthand declaring the default DOS
  machine. The local text config file (Configuration below) is the
  declarative twin of `config()`: one section per machine.
- **Boot images.** Every test machine has exactly one boot image;
  only the media type varies — floppy, hard disk, CD (USB: open
  question) — defaulted by the platform (dos: floppy; win9x: hard
  disk). The image is supplied ready (`boot_image=`), downloaded
  (the dos default), or built from install media (win9x).
  Container formats beyond raw (e.g. qcow2) are the runner's
  business to detect.
- **Config types.** A machine's options form a three-level
  extension chain: the *generic runner config* (options every
  runner understands — the boot image, a run timeout) is extended
  by each *platform's config* (win9x adds `install_media`,
  `media_url`/`media_sha256`, `product_key`; dos currently adds
  nothing), which is extended by each *runner's own config* (a
  QEMU-based runner can expose its emulator knobs — binary path,
  extra arguments). A machine's `config()` options are validated
  against its runner's config type — so a runner override also
  changes exactly what is configurable, without changing the
  platform vocabulary. The chain is conceptual, realized
  structurally: each runner declares its options in its own config
  type, matching the documented generic and platform schemas
  (Runner seams below) — runners import nothing to conform, and
  never import testaferro.
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
- **Runners.** Every platform has a default runner class (dos →
  relict's; win9x → the runner sketched below). A machine picks
  a different one at declaration (`runner=` in its `config()`
  call, or per suite for a one-off anonymous machine) — any class
  satisfying the runner interface (Runner seams below).
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
   verify (read-only) that the runner's free-port selection is
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
fake-runner unit tests is archived in
[drafts/win95/](drafts/win95/) — written before the
platform/`config()` naming and the universal boot-image concept (it
says `guest=`, `qemu95.start()`, and `hdd_image=`), but still the
reference for the install, caching, and session mechanics.

When revived:

- `binfmt` maps a Windows x86 PE (machine 0x014C) to candidate
  platforms {win9x, winnt}, and the facade's platform table gains
  "win9x" with its binding module.
- The binding mirrors the DOS one, backed by a win9x runner
  package (name to be decided; an optional extra — never a hard
  dependency) whose runner class satisfies the runner contract
  (Runner seams below): its config type extends the win9x platform config
  (install media, hash, product key); `.provision(dist_dir)`
  performs the one-time unattended install from the configured CD
  ISO into the boot image (a hard-disk image; nothing configured —
  error); `.run(exe_path, args, home)` stages the exe on the vvfat
  guest drive, boots that image, detects completion via
  guest-initiated shutdown (Windows 9x has no text screen to
  scrape), and returns the redirected log.
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
  (platform, boot image or install media), validated by the same
  config-type chain as `config()` calls, so test code names only
  the suite executable and testaferro resolves machines from
  config; plus runner-specific local config owned by the runner
  package itself.

## Lifecycle

- **testaferro CLI** — e.g. `testaferro shutdown` to close
  persistent machines and manage caches.
- **Persistent machines** — test machines that opt out of the sweep
  at `stop()`, keeping their VMs warm for reuse across pytest runs,
  shut down explicitly via the CLI.

## Runner seams

### The runner interface

The contract the `runner=` override (Platforms and test machines
above) accepts, and the shape platform bindings program against
instead of hand-mirroring one package.

Decided: the contract is *soft* — this section is its canonical
definition, and conformance is structural (duck typing plus each
side's own tests), enforced by no shared package. A separate spec
package (`testaferro-runner-api`) was fully drafted and then
deliberately stood down as over-engineering for a one-author,
two-runner ecosystem; the draft — protocol module, config chain,
conformance kit, and their tests — is archived in
[drafts/runner-api/](drafts/runner-api/) (the package's
`__init__.py` archived as `runner_api.py`; reference material, not
live code).
testaferro is the authority on the supported platform set (dos
today; win9x, win3x, winnt, and linux are possible future
candidates). When testaferro implements the contract, it does so
in one import-clean, stdlib-only module with no testaferro
internals, so promoting the contract into a published spec package
remains a mechanical move. The trigger to revisit: the first
runner not written by the project author, or a second facade
driving the same runners.

A runner package exports a *runner class* satisfying the contract.
Constructing it with a config — an instance of that runner's
config type (Config types above) — yields the object testaferro
calls a test machine:

- **`Runner(config)`** — the instance carries configuration only
  (boot image source, install media, emulator knobs) plus its
  **`platform`** type; it holds no per-run state, so one instance
  may serve concurrent runs.
- **`.provision(dist_dir) -> None`** — ensure the boot image
  exists at `dist_dir`/`boot.img`, per the instance's config (dos:
  download the default FreeDOS image; win9x: the one-time
  unattended install from the configured media). Whatever the
  media type (floppy, hard disk, CD; USB an open question) or
  container format, the runner knows how to attach and boot what
  it provisioned — testaferro caches, keys, and stages that one
  file without knowing what kind of image it is. Deterministic
  given the config; raises when the environment is unobtainable
  (e.g. no media configured and no default exists). Cache-unaware:
  durable caching, and deciding whether provisioning is needed at
  all, is testaferro's job.
- **`.run(exe_path, args, home) -> str`** — the full agentless
  lifecycle in the given home directory: stage the (8.3-named)
  executable on the guest-visible drive, boot the environment image
  from the home's dist, execute with output redirected to the
  shared drive, detect completion, and return the log text
  uninterpreted. Per-run state lives in the home, which stays an
  explicit parameter (decided earlier): no process-global state,
  so runs are concurrency-safe within one process.

Division of labor: testaferro owns durable caches, per-run home
staging, sessions, and parallelism; the runner owns emulation,
guest control, completion detection, and all in-guest mechanics
(including any guest-side listener — see Out of scope).

Migration: partly landed — relict (quemados's successor as the DOS
runner) ships explicit-`home` operations
(`run_guest_program(..., home=)`, `download(home=)`) alongside its
module surface, so the DOS binding's private `_home`-bracketing
shim is deleted and every call names its run home directly. relict
also exports a `Runner`/`MachineConfig` surface, but shaped
differently from the contract above (the home is bound at
construction and provisioning is internal, rather than
`Runner(config)` with `.provision(dist_dir)` and
`.run(..., home)`); reconciling the two shapes remains open. The
interface starts minimal on purpose; persistent machines
(Lifecycle above) may later add optional operations for keeping a
VM up across runs.

### Internal binding naming

The platform concept already keeps QEMU out of the consumer's view
(consumers name platforms, never emulators); what remains is
whether the binding module `qemu.py` should be renamed for the
platform it binds (e.g. `dos`), leaving QEMU entirely to the
runners.

## Out of scope by decision

Any guest-side agent/listener that handles execute requests inside a
VM belongs to the runner packages, never to testaferro.
