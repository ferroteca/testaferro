# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""The reliquary provider binding, for DOS guests.

Named for the provider it binds, which is the layer Testaferro
actually talks to: everything in this module is a reliquary call, and
whatever the provider drives underneath is the provider's own
business — it has no name anywhere in this package (D16, P1, P2). The
module imported below is the provider distribution; this module is
`testaferro.reliquary`.

`suite_backend()` guards the door with `binfmt.classify()`: a DOS
program — plain MZ or a headerless/.com image — yields a
ReliquarySuiteBackend; anything else is rejected before any guest
work, with the format and architecture named. The framework adapter
defaults to testaferro.cpputest. `guest_session()` names no
executable and needs no such guard: it hands back a GuestSession
whose `exec()` drives the guest one command at a time, for a
guest-driven test that is a linear script rather than a suite of
named cases (U10).

ReliquarySuiteBackend and GuestSession both drive a reliquary machine
on the caller's behalf, through the provisioning `_GuestLifecycle`
implements once for both rather than twice (F18).
Each **guest session** — one guest up, from `start_guest()` to
`stop_guest()` — gets a fresh, disposable reliquary home under
Testaferro's cache directory (LOCALAPPDATA or XDG_CACHE_HOME): the
declaration is written there as a blueprint, reliquary creates and
boots one machine from it, and every guest run is one `reliquary.exec`
against that machine. Guest homes sit inside the active **run**'s
area when `start()` opened one (`runs/run-*/guests/guest-*`) and
directly under the cache otherwise; the two spans and why neither is
called a "session" on its own are D15.

The suite reaches the guest on Testaferro's own **work drive** — a
vvfat medium (a host directory QEMU serves live as a FAT volume,
never materialized into an image), attached as a sibling of whatever
else the machine declares. It is `_gather()`ed *before* the machine
is even created, so the drive is never empty the moment it exists:
there is nothing to write into it at rest, only somewhere to boot
into. Zero configuration is seeded from the caller-supplied
`boot_image` or a cached FreeDOS image.

**Reliquary and remanence answer no drive-letter question at all any
more, by design rather than by gap** (0.1.0a2, D108 there; remanence's
own D57). `describe_drives` and the rest of the file-verb layer are
deleted outright, and remanence refuses the same question by name — a
fact about a booted guest, never a stopped image. **Testaferro answers
it instead, deterministically, because Testaferro authors the whole
document** (`_letter_map()`): DOS gives a floppy `A:`/`B:` by
controller position and a hard disk `C:` onward by slot order, one
volume per disk, and every drive this binding ever declares — its own
system disk, its own work drive, a `machine_config` template passed
through unmodified — keeps to that shape by construction. Checked
against a real boot: the zero-configuration guest's system disk is
`C:` and its work-drive sibling is `D:`, exactly as computed, with
nothing shifted by a CD-ROM driver claiming a letter first (Testaferro's
own FreeDOS install loads none).

**The write this module still asks `testaferro.at_rest` for is the
one case the work drive cannot cover on its own** — a `location=` a
consumer declared naming some *other* drive the machine carries, not
Testaferro's own. Reading and writing a stopped machine's disk is not
execution, so that write is not the provider's to supply (F16, D23);
`at_rest` does it over remanence.

**A persistent machine is the one guest that is not disposable**
(F2, U8, D30). A declaration naming `persist="<name>"` gets its home
at `machines/<name>` under the cache instead of a fresh `guest-*`
directory: the machine is created there once — its system disk a
`copy` rather than a `difference` overlay, so it depends on nothing
the cache may later drop — and every guest session after that boots
the same disks. `stop_guest()` stops it and sweeps nothing; what
persists is the machine's own drives (`C:`, or a tester's floppy),
while the work drive is Testaferro's staging and is rebuilt per
session like any other. Destroying is a verb of the lifecycle CLI
(`testaferro destroy`), never a side effect of a run. One machine
serves one guest session at a time: a later backend in this process
closes the earlier holder's session and boots the same disks for
itself — a reboot between suites, because a suite reaches the guest
on a work drive QEMU reads once at boot — and a machine another
process has running is refused by name, with `testaferro shutdown`
named as the door.
"""

from __future__ import annotations

import atexit
import glob
import json
import os
import shutil
import tempfile
import typing

import reliquary

from . import at_rest
from . import binfmt
from . import cache
from . import cpputest
from . import placement
from .backend import Availability, GuestOutputError
from .suite import SuiteBackend


# The guest platforms this binding serves, and the one thing about
# itself a binding tells resolution: which provider runs which
# platform is a provider's own answer rather than a table kept
# upstream of it (P1, D11). Resolution reads this to refuse a
# declaration before importing anything further; `suite_backend()`
# guards the same ground for a caller who reached the binding
# directly, exactly as `binfmt` is shared between the two (D16).
PLATFORMS = ("dos",)


def discover():
    """The backends reliquary could drive on this host, each found or
    not, in reliquary's own priority order.

    Pure pass-through of reliquary's host probe: the names are
    reliquary's (`qemu`, `virtualbox`, ...), reported as data and
    never interpreted here, since which one a machine gets is decided
    inside the blueprint and is reliquary's business. Probing only —
    nothing is selected, and no machine is touched.
    """
    return tuple(
        Availability(provider="reliquary", backend=found.backend,
                     available=found.available, executable=found.executable,
                     version=found.version, detail=found.detail)
        for found in reliquary.backends.discover())


# The blueprint name Testaferro writes into each session's private
# blueprints directory, and the machine created from it.
_BLUEPRINT_NAME = "testaferro"
# Testaferro's own drive, a vvfat sibling of whatever else the
# machine declares — always present now (D108: reliquary no longer
# answers a drive-letter question at all, so there is nothing left
# to react to; the drive is simply always there instead).
_WORK_MEDIA_NAME = "testaferro-work"
_BOOT_MEDIA_NAME = "testaferro-boot"
# Where `_letter_map()` starts counting each drive family — DOS's own
# rule, not Testaferro's: a floppy controller's drives take A:/B: by
# position, and a hard disk takes C: onward by slot order, neither
# ever read off anything.
_FLOPPY_BASE_LETTER = "A"
_HDD_BASE_LETTER = "C"
# Testaferro's installed FreeDOS system, shared by every guest session
# that declared nothing of its own.
_SYSTEM_MEDIA_NAME = "testaferro-freedos"
_DEFAULT_MEMORY = "32M"
# Seconds one guest command may take before reliquary gives up.
_DEFAULT_TIMEOUT = 120
_HDD_SLOTS = 4

# Testaferro's own FreeDOS system, and the recipe that makes it.
#
# The recipe is authored here (P17): `assets/` holds the blueprint and
# the install script, so nothing about the environment Testaferro
# offers by name is resolved out of the provider's own codex at run
# time. What the recipe *produces* is a plain installed FreeDOS system
# on a disk, kept in the cache and reused — an install is a price paid
# once, and never a price a test run pays (D10).
#
# The image this replaced was FreeDOS 1.4's FloppyEdition boot floppy,
# which boots its *installer* and never reaches a DOS prompt: zero
# configuration could not have worked, and nothing had looked until an
# integration run did.
_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "assets")
_FREEDOS_BLUEPRINT = "freedos"
_FREEDOS_IMAGE_NAME = "freedos.qcow2"
# The readiness script's label and the variable its last step sets.
# Reliquary ships no readiness script on purpose — what "ready" means
# belongs to whatever is being built — so this one is Testaferro's
# answer for a guest suite: the guest will take a command. Bare stem,
# no `.rlqs`: `run_script()` resolves it against the session's own
# scripts directory (`_ASSETS`, pinned in `start_guest()`).
_READY_SCRIPT = "freedos-ready"
_READY_VAR = "ready"


def suite_backend(exe_path, framework=cpputest, enumerator=None,
                  boot_image=None, machine_config=None, timeout=None,
                  files=(), location=None, program=None, setup=(),
                  persist=None):
    """Interrogate the referenced suite executable and return the
    backend matching its format — a ReliquarySuiteBackend for a DOS
    program. Raises FileNotFoundError for a missing file and
    ValueError for a provably non-DOS executable (e.g. the suite's
    host build passed by mistake).

    `timeout` is seconds one guest command may take, and overrides
    what a declaration says: it is the caller speaking about this
    run, and a declaration speaks about the environment.

    `files`, `location` and `program` are **test placement** (F4),
    and each overrides a declaration for the same reason. `files` is
    host paths staged into the guest beside the suite; `location` is
    the guest address they land at (e.g. `D:\\`); `program` is the
    guest address of what to run, in which `{location}` stands for
    the location however it was settled. Saying none of them is the
    one-liner case: the executable alone, at Testaferro's default
    location, run by its own name.

    `setup` is **harness prep** (F9), the same override rule again:
    guest commands run in order, once per guest session — after the
    readiness wait and before anything else, an enumeration boot
    included — for a TSR or driver the suite needs resident before
    the framework ever takes over. A suite that declares none runs
    exactly as before.

    `persist` names a **persistent machine** (F2): one kept under that
    name between runs rather than swept after each guest session, the
    same override rule once more. None is the disposable guest."""
    exe_path = os.fspath(exe_path)
    fmt = binfmt.classify(exe_path)
    if fmt.platform != "dos":
        raise ValueError(
            f"{os.path.basename(exe_path)} is {fmt.kind} executable; "
            "only DOS guest suites are supported")
    machine_config = _checked_machine_config(machine_config)
    if boot_image is not None and machine_config is not None:
        raise TypeError("boot_image and machine_config cannot be combined")
    return ReliquarySuiteBackend(exe_path, framework=framework,
                                 enumerator=enumerator,
                                 boot_image=boot_image,
                                 machine_config=machine_config,
                                 timeout=timeout, files=files,
                                 location=location, program=program,
                                 setup=setup, persist=persist)


def guest_session(boot_image=None, machine_config=None, timeout=None,
                  files=(), setup=(), persist=None):
    """Return a GuestSession: the same zero-configuration guest
    provisioning `suite_backend()` draws on, reached without a suite
    executable to interrogate or place (U10, F18) — a context manager
    handing back a guest whose `exec()` runs one command at a time,
    for a guest-driven test that is a linear script rather than a
    suite of named cases.

    `boot_image`, `machine_config`, `timeout`, `files`, `setup` and
    `persist` are the same options `suite_backend()` takes, with the
    same validation and the same nearest-speaker override rule."""
    machine_config = _checked_machine_config(machine_config)
    if boot_image is not None and machine_config is not None:
        raise TypeError("boot_image and machine_config cannot be combined")
    return GuestSession(boot_image=boot_image, machine_config=machine_config,
                        timeout=timeout, files=files, setup=setup,
                        persist=persist)


def read_document(path):
    """An authored `.rlqb` on disk, as a declaration.

    The blueprint dialect is JSON5 (comments, trailing commas,
    unquoted keys), so it is read the way reliquary reads it
    (0.1.0a2, D102 — reliquary's own JSONC dialect retired in favor
    of published JSON5). This lives in the binding because the format
    is the provider's (F21): a declaration naming a path hands it to
    whichever provider it declared, and this is reliquary's answer.
    """
    from reliquary import json5reader

    from .environments import _from_document

    with open(path, encoding="utf-8") as handle:
        document = json5reader.load(handle)
    return _from_document(document)


def _checked_machine_config(machine_config):
    """The declaration, validated for this binding, or None."""
    if machine_config is None:
        return None
    from .environments import _coerce_machine_config

    machine_config = _coerce_machine_config(machine_config,
                                            read=read_document)
    if machine_config.platform != "dos":
        raise ValueError(
            "this binding runs DOS guests and needs a DOS machine "
            f"config, not {machine_config.platform!r}")
    return machine_config


# The active Testaferro run opened by start(), or None: its
# disposable directory (holding the staged boot image and every guest
# home) plus the recorded image choice, staged lazily on first use.
# A *run* is the outer span — one image choice shared by many suites,
# usually one pytest run — and it holds many guest sessions (D15).
_run_area = None

# Backends holding a booted machine right now. A machine outlives the
# call that started it, so an interpreter that goes down between
# start_guest() and stop_guest() would otherwise leave the guest
# running — and sweeping its home would pull the disk out from under
# it. Every exit path stops machines before deleting anything.
_running = set()
_sweep_registered = False

# The backend holding each persistent machine open in this process,
# by name (F2). One machine serves one guest session at a time — its
# work drive is read once at boot, so a second suite's staged set can
# only reach it by a reboot — and this is how the later holder finds
# the earlier one to close its session cleanly first.
_holders = {}


class PersistentMachine(typing.NamedTuple):
    """One persistent machine as `persistent_machines()` reports it:
    its declared name, the phase reliquary records for it (`ready`,
    `running`, a transitional phase, or None for a home holding no
    machine at all), and the directory it lives in."""

    name: str
    phase: typing.Optional[str]
    home: str


def _machine_started(backend):
    """Record a backend whose machine is now running."""
    global _sweep_registered
    _running.add(backend)
    if not _sweep_registered:
        atexit.register(_stop_running_machines)
        _sweep_registered = True


def _stop_running_machines():
    """Stop every machine still running, best effort.

    Called before any sweep and again at interpreter exit. One
    backend failing to stop must not strand the others, so failures
    are swallowed here; the machine's own home is removed regardless.
    """
    for backend in list(_running):
        try:
            backend.stop_guest()
        except Exception:
            _running.discard(backend)


def start(boot_image=None):
    """Open a Testaferro run: one boot-image choice serving every
    suite until stop(). The image itself — `boot_image` or the cached
    default — is staged lazily on the first guest use, so calling
    this from a conftest costs nothing when no guest test runs. An
    atexit failsafe sweeps the run if stop() is never called."""
    global _run_area
    if _run_area is not None:
        raise RuntimeError("a testaferro run is already active")
    root = os.path.join(cache.cache_root(), "runs")
    os.makedirs(root, exist_ok=True)
    _run_area = {
        "dir": tempfile.mkdtemp(prefix="run-", dir=root),
        "boot_image": (None if boot_image is None
                       else os.fspath(boot_image)),
    }
    # failsafe: sweep at interpreter exit if the caller never calls
    # stop(); an explicit stop() unregisters this again
    atexit.register(stop)


def stop(clear_downloads=False):
    """Close the run opened by start(), sweeping its whole area —
    staged image and every guest home. Safe to call with no run
    active. `clear_downloads=True` also removes Testaferro's built
    FreeDOS system, so the next zero-configuration run installs a
    fresh one — which is minutes rather than the seconds the name
    suggests, this being an install and no longer a download."""
    global _run_area
    atexit.unregister(stop)
    # Machines first: the guest homes about to be swept are the disks
    # those guests are running from.
    _stop_running_machines()
    if _run_area is not None:
        # The guest homes live inside this directory, so the same
        # sweep-or-keep answer has to govern it.
        cache.release_guest_home(_run_area["dir"])
        _run_area = None
    if clear_downloads:
        _remove_system()


def _remove_system():
    """Drop the installed FreeDOS system and any partial a killed
    build left behind, one per builder (`_build_default_image`).
    Returns what was removed. Safe with persistent machines in place:
    each holds a *copy* of the system disk, never an overlay on this
    file (F2)."""
    cached = os.path.join(cache.cache_root(), _FREEDOS_IMAGE_NAME)
    removed = []
    for path in [cached, *glob.glob(cached + ".*.part")]:
        if os.path.exists(path):
            os.remove(path)
            removed.append(path)
    return removed


def persistent_machines():
    """Every persistent machine this host keeps, by name (F2, U8).

    What persists, where, enumerable (P5): one entry per directory
    under `machines/`, each with the phase reliquary records for the
    machine inside — so a run that died with one up shows `running`
    here, which is what `testaferro shutdown` is for.
    """
    root = cache.machines_root()
    if not os.path.isdir(root):
        return ()
    return tuple(
        PersistentMachine(name, _recorded_phase(os.path.join(root, name)),
                          os.path.join(root, name))
        for name in sorted(os.listdir(root))
        if os.path.isdir(os.path.join(root, name)))


def shutdown(name):
    """Stop the named persistent machine if it is recorded running.

    Returns whether anything was stopped; a machine already at rest
    is left as it is. A run that died leaves its machine recorded
    `running` whether or not its process survived it, and reliquary's
    own stop reconciles either case — an unreachable VM counts as
    stopped. Raises LookupError for a name nothing was kept under.
    """
    home = _persistent_home(name)
    holder = _holders.get(name)
    if holder is not None:
        holder.stop_guest()
        return True
    session = _open_session(home, os.path.join(home, "blueprints"))
    stopped = False
    for state in session.list_machines():
        if state.get("phase") in ("running", "stopping"):
            session.stop_machine(state["id"])
            stopped = True
    return stopped


def destroy(name):
    """Destroy the named persistent machine: stop it if running, let
    reliquary dispose of it, and remove its home — the one act that
    discards what `persist=` asked to keep, and deliberately a verb
    of its own rather than anything a run does (F2, U8). Raises
    LookupError for a name nothing was kept under."""
    home = _persistent_home(name)
    shutdown(name)
    session = _open_session(home, os.path.join(home, "blueprints"))
    for state in session.list_machines():
        session.destroy_machine(state["id"])
    shutil.rmtree(home)


def clean(system=False):
    """Sweep what killed runs left behind; with `system=True`, the
    installed FreeDOS system too. Returns the paths removed.

    A run area, a lone guest home or a half-finished build is stale
    unless a machine inside it is recorded running — that one is
    somebody's, and stays. Persistent machines are never touched
    here: they are kept on purpose, and `destroy()` is their verb.
    """
    root = cache.cache_root()
    removed = []
    for run in _subdirectories(os.path.join(root, "runs")):
        guests = _subdirectories(os.path.join(run, "guests"))
        if not any(_in_use(home) for home in guests):
            shutil.rmtree(run, ignore_errors=True)
            removed.append(run)
    for home in _subdirectories(os.path.join(root, "guests")):
        if not _in_use(home):
            shutil.rmtree(home, ignore_errors=True)
            removed.append(home)
    for build in sorted(glob.glob(os.path.join(root, "build-*"))):
        if os.path.isdir(build) and not _in_use(build):
            shutil.rmtree(build, ignore_errors=True)
            removed.append(build)
    if system:
        removed.extend(_remove_system())
    return tuple(removed)


def _persistent_home(name):
    home = os.path.join(cache.machines_root(), name)
    if not os.path.isdir(home):
        kept = ", ".join(found.name for found in persistent_machines())
        raise LookupError(
            f"no persistent machine is kept as {name!r}; kept: "
            + (kept or "(none)"))
    return home


def _recorded_phase(home):
    """The phase reliquary records for the machine a home holds, or
    None when it holds none — or is no reliquary home at all."""
    try:
        session = _open_session(home, os.path.join(home, "blueprints"))
        states = session.list_machines()
    except (reliquary.ReliquaryError, OSError, ValueError):
        return None
    return states[0].get("phase") if states else None


def _in_use(home):
    """Whether a guest home is somebody's right now: held by a backend
    in this process, or holding a machine recorded running."""
    if any(backend._home == home for backend in _running):
        return True
    return _recorded_phase(home) in ("running", "stopping")


def _subdirectories(path):
    if not os.path.isdir(path):
        return []
    return sorted(os.path.join(path, name) for name in os.listdir(path)
                  if os.path.isdir(os.path.join(path, name)))


def _run_image():
    """The run's staged copy of the boot image it was opened with.

    Only reached when `start(boot_image=…)` named one: a run staging
    the default system disk would be copying a file no guest session
    writes to anyway, each of them layering its own overlay instead.
    """
    image = os.path.join(_run_area["dir"], "boot.img")
    if not os.path.exists(image):
        shutil.copy(_run_area["boot_image"], image)
    return image


def _cached_default_image():
    """Testaferro's own FreeDOS system, built once and kept.

    The first call installs FreeDOS from the recipe in `assets/` and
    keeps the resulting disk under the cache; every call after that is
    a path lookup. A guest session never installs anything — it
    layers a fresh overlay over this disk and leaves it as it found
    it.
    """
    cached = os.path.join(cache.cache_root(), _FREEDOS_IMAGE_NAME)
    if not os.path.exists(cached):
        _build_default_image(cached)
    return cached


def _build_default_image(destination):
    """Install FreeDOS once, from Testaferro's own authored recipe.

    Everything happens inside a disposable home under the cache and
    against a context pinned to `assets/`, so the codex is no more an
    input here than it is anywhere else (P17, D6). The machine is
    destroyed afterwards and only its disk survives, moved into place
    atomically so a killed build leaves no half-installed system to be
    mistaken for a finished one.

    **The partial file is this build's own.** Two processes can find
    the system missing at the same moment — under xdist every worker
    collects, and on a machine that has never built it each one
    installs it (U5). Nothing locks: the claim is isolation, and a
    second install costs minutes rather than correctness. What it must
    not cost is the disk itself, which a *shared* partial name did —
    the second build's move took the first build's partial out from
    under it. So each build stages into a partial named for itself,
    and whichever finishes first is the disk: a build that arrives to
    find one already in place discards its own rather than replacing
    a file the winner's guest may by then have open, both being the
    same recipe's answer.
    """
    os.makedirs(cache.cache_root(), exist_ok=True)
    handle, partial = tempfile.mkstemp(
        prefix=os.path.basename(destination) + ".", suffix=".part",
        dir=os.path.dirname(destination))
    os.close(handle)
    with tempfile.TemporaryDirectory(
            prefix="build-", dir=cache.cache_root()) as home:
        session = _open_session(home, _ASSETS, scripts=_ASSETS)
        machine = session.create_machine(_FREEDOS_BLUEPRINT)
        try:
            session.run_script("install", machine=machine)
            state = session.load_machine_state(machine)
            installed = state["drives"]["hdd0"]["path"]
            shutil.copy(installed, partial)
        except BaseException:
            os.remove(partial)
            raise
        finally:
            try:
                session.destroy_machine(machine)
            except Exception:
                # The whole home goes with this block regardless; a
                # machine that will not tear down must not also cost
                # us the image we just spent an install on.
                pass
    if os.path.exists(destination):
        os.remove(partial)
        return
    os.replace(partial, destination)


def _open_session(home, blueprints, scripts=None):
    """A reliquary session pinned to one disposable Testaferro home.

    The pinned directories keep resolution hermetic: only what
    Testaferro wrote for this run, never the user's own reliquary home
    or the built-in codex — a `Session` refuses construction without a
    home at all (`dir.unassigned`), so there is no process-global left
    to fence off (0.1.0dev6's `autoseed` deletion carried this the
    rest of the way).

    **The session is the only door now** (0.1.0a2, P26): every
    module-level verb this binding used to call —
    `create_machine`, `start_machine`, `stop_machine`, `run_script`,
    `exec`, the rest — is a method on the object this returns, opened
    once per disposable home and threaded through the calls that
    follow. `scripts` is pinned only where one is actually run —
    building the default image — and points at Testaferro's own
    `assets/` for the same reason the blueprints directory does.
    """
    context = reliquary.Context(home_dir=home,
                                cache_dir=os.path.join(home, "cache"),
                                blueprints_dir=blueprints,
                                scripts_dir=scripts)
    return reliquary.Session(context)


def _work_slot(drives):
    """Choose the disk slot Testaferro's work drive will occupy.

    The slot is Testaferro's to choose — the lowest free disk — and
    that is *all* this decides. **The letter is reliquary's to say,
    and is no longer asked for here**, because at this point there is
    nothing to ask about: this authors a document, and a letter is a
    fact about a machine that does not exist yet.
    """
    used = sorted({int(key[len("hdd"):] or 0)
                   for key in drives if key.startswith("hdd")})
    free = [slot for slot in range(_HDD_SLOTS) if slot not in used]
    if not free:
        raise ValueError(
            "the machine declares every disk slot; testaferro needs one "
            "free slot for the work drive that carries the suite "
            "executable into the guest")
    return f"hdd{free[0]}"


def _letter_map(drives):
    """The DOS drive letter for every drive this document declares.

    **Deterministic, because Testaferro authors the whole document**
    (0.1.0a2, D108 — reliquary's own drive-letter report is deleted
    outright, and remanence refuses the same question by design, its
    own D57: a fact about a booted guest, never a stopped image). DOS
    assigns a floppy controller's drives `A:`/`B:` by position, and a
    hard disk `C:` onward by slot order — one volume per disk, which
    holds by construction for every drive this binding ever declares:
    its own system disk and its own work drive are each exactly one
    FAT volume, and a `machine_config` declaration is expected to keep
    that shape too, since Testaferro cannot look inside a disk it did
    not build to check.

    Through 0.1.0.dev4 Testaferro inferred every letter exactly this
    way, and 0.1.0.dev5 killed the practice: a *declared* disk could
    hold more volumes than it declared, so reading the real answer was
    the only honest one once reliquary offered it. 0.1.0a2 withdrew
    that offer for good — this is not a fallback for its absence, it
    is the position the project now holds: the assumption inference
    always rested on is one Testaferro states and owns, not one it
    pretends to have confirmed.

    Checked against a real boot (FreeDOS 1.4, one hard disk plus a
    vvfat sibling): the system disk answers `C:` and the sibling `D:`,
    matching this computation exactly, with nothing shifted by a
    CD-ROM driver claiming a letter first — Testaferro's own FreeDOS
    install loads none.
    """
    letters = {}
    floppies = sorted(
        (key for key in drives if key.startswith("floppy")),
        key=lambda key: int(key[len("floppy"):] or 0))
    for index, key in enumerate(floppies):
        letters[chr(ord(_FLOPPY_BASE_LETTER) + index)] = key
    hdds = sorted(
        (key for key in drives if key.startswith("hdd")),
        key=lambda key: int(key[len("hdd"):] or 0))
    for index, key in enumerate(hdds):
        letters[chr(ord(_HDD_BASE_LETTER) + index)] = key
    return letters


def _drive_image(key, machine, session):
    """The host image path backing one of a created machine's drives.

    The **out-of-band door**, which the provider names as the
    sanctioned route to a stopped machine's disks rather than as a
    fallback: the machine's own recorded state carries each drive's
    materialized path, and `list_machines()` is what reports it —
    unaffected by 0.1.0a2's drive-report deletion, which took the
    *contents* of a volume out of reliquary's hands, not the bookkeeping
    over where each drive's own image lives.
    """
    for state in session.list_machines():
        if state.get("id") != machine:
            continue
        drive = (state.get("drives") or {}).get(key) or {}
        path = drive.get("path")
        if path is None:
            raise ValueError(
                f"drive {key} of machine {machine} records no image "
                "path, so testaferro cannot open it to stage the suite")
        return path
    raise ValueError(f"machine {machine} is not in the provider's own "
                     "list, so testaferro cannot find its drives")


def _resolve_volume(address, machine, session, drives):
    """The image and volume a guest address names, for an at-rest write.

    **One computation for every drive now, Testaferro's own or
    declared alike** (D23, D108): `_letter_map()` answers deterministically
    from the document, so there is no report left to ask and no split
    between "guaranteed" and "looked up" any more — a letter the
    document does not carry is refused naming the one thing that is
    certain, the address itself.
    """
    letter, path = at_rest.split_address(address)
    key = _letter_map(drives).get(letter)
    if key is None:
        raise ValueError(
            f"this machine has no {letter}:, so testaferro cannot put "
            f"the suite at {address!r}")
    return _drive_image(key, machine, session), 0, path


def _default_location(drives, work_key):
    """Where a run lands when nobody said (F4, P8): Testaferro's own
    work drive, at whatever letter `_letter_map()` computes for it.

    Its root, not a subdirectory — F4's original *last letter of the
    map* policy put a default under `\\TESTS` because the target might
    be a stranger's `C:\\` root; the work drive is never that, since
    nothing but this session's own staged set ever lives on it.
    """
    letters = _letter_map(drives)
    letter = next(letter for letter, key in letters.items()
                  if key == work_key)
    return f"{letter}:\\"


class _GuestLifecycle:
    """The guest-session provisioning `ReliquarySuiteBackend` and
    `GuestSession` both draw on, rather than each carrying its own
    copy (U10, F18): the cached image or a declared machine, a fresh
    disposable overlay, host files staged onto the work drive before
    boot, the readiness wait, harness prep (F9), and the teardown
    that sweeps it all away again.

    `exe_path` is the one thing that tells the two apart, and it is
    optional here for exactly that reason: `ReliquarySuiteBackend`
    stages its suite executable beside `files=`, and `GuestSession`
    stages none — a scripted guest interaction has no suite
    executable to place, only what `files=` names."""

    def __init__(self, exe_path=None, boot_image=None, machine_config=None,
                 timeout=None, files=(), location=None, program=None,
                 setup=(), persist=None):
        self._exe = exe_path
        self._boot_image = (None if boot_image is None
                            else os.fspath(boot_image))
        self._home = None
        self._session = None
        self._machine = None
        self._drives = None
        self._work_key = None
        self._location = None
        self._machine_config = machine_config
        # Nearest speaker wins: this call, then the declaration, then
        # the default. The same rule for all of them, so a consumer
        # never has to remember which options overrule a declaration.
        self._timeout = self._nearest(timeout, "timeout", _DEFAULT_TIMEOUT)
        self._declared_location = self._nearest(location, "location")
        self._declared_program = self._nearest(program, "program")
        staged = self._nearest(files or None, "files") or ()
        self._files = tuple(os.fspath(path) for path in staged)
        staged_setup = self._nearest(setup or None, "setup") or ()
        self._setup = tuple(str(command) for command in staged_setup)
        # The persistent machine's name, validated where the word is
        # defined (environments._machine_name) so a name typed at a
        # call is held to the same rule as one declared.
        from .environments import _machine_name

        self._persist = _machine_name(self._nearest(persist, "persist"))

    def _nearest(self, given, name, default=None):
        """This call, then the declaration, then the default."""
        return placement.nearest(given, self._machine_config, name,
                                 default)

    @property
    def location(self):
        """Where this suite's harness landed, in the guest's terms.

        The **placement reported** (F4): one question, one vocabulary,
        one answer — a guest address like `C:\\TESTS`, the same terms a
        declaration uses, so what you could have declared is what you
        are told. And the same answer whether the consumer stated it
        or Testaferro chose it: who chose is deliberately not part of
        it, which is the courtesy Testaferro asks of the provider one
        seam down, applied at its own surface.

        Refuses before the location is settled rather than guessing.
        A declared address settles the moment a guest session opens; a
        defaulted one settles once the provider's drive map is read,
        which is also inside `start_guest()` — so in practice this
        answers for the length of a guest session and refuses outside
        one.
        """
        if self._location is None:
            raise RuntimeError(
                "this suite has not been placed yet: the location is "
                "settled when a guest session opens, so ask between "
                "start_guest() and stop_guest()")
        return self._location

    def start_guest(self):
        if self._persist is not None:
            # A persistent machine's home is its own, named, and kept
            # (F2). One guest session at a time: an earlier holder in
            # this process is closed first — its session is over, its
            # disks are not — and the work drive is rebuilt from this
            # session's staged set, a directory QEMU reads once at
            # boot and never again.
            holder = _holders.get(self._persist)
            if holder is not None and holder is not self:
                holder.stop_guest()
            self._home = os.path.join(cache.machines_root(), self._persist)
            _holders[self._persist] = self
            shutil.rmtree(os.path.join(self._home, "work"),
                          ignore_errors=True)
        else:
            # A guest home sits inside the active run's area, or
            # directly under the cache when no run was opened: a guest
            # belonging to no run still needs somewhere disposable to
            # live.
            area = _run_area["dir"] if _run_area else cache.cache_root()
            guests = os.path.join(area, "guests")
            os.makedirs(guests, exist_ok=True)
            self._home = tempfile.mkdtemp(prefix="guest-", dir=guests)
        blueprints = os.path.join(self._home, "blueprints")
        work = os.path.join(self._home, "work")
        os.makedirs(blueprints, exist_ok=True)
        os.makedirs(work)
        # The host side of the staged set: the suite executable, plus
        # whatever `files=` named, gathered into one directory because
        # `at_rest.put_tree` copies a tree and the set keeps its shape
        # under the location.
        self._gather(work)
        # The boot image is staged host-side too, and for a different
        # reason: what boots is Testaferro's copy, so the tester's own
        # file is read and never written (P5).
        boot = self._stage_boot_image()

        # scripts=_ASSETS: `run_script()` now resolves a label against
        # a scripts directory rather than taking an already-loaded
        # script object by path (0.1.0a2 dropped `load_script()` with
        # the rest of the module-level API), so the readiness script
        # `_wait_ready()` runs has to be reachable through this
        # session's own scripts directory.
        self._session = _open_session(self._home, blueprints,
                                      scripts=_ASSETS)
        try:
            if not self._reopen(blueprints):
                self._create(blueprints, boot, work)
            # Between create and start: the drive images exist to be
            # read and written, and reliquary will still touch them at
            # rest. A declared address that cannot work fails here,
            # before any boot, rather than as a missing program in the
            # guest — Testaferro's own work drive needs nothing
            # written to it at all, its content having arrived with
            # `_gather()` before the machine ever existed.
            self._place(work)
            self._session.start_machine(self._machine)
            self._wait_ready()
            self._run_setup()
        except BaseException:
            self.stop_guest()
            raise

    def _reopen(self, blueprints):
        """Take up the machine a persistent home already holds, if it
        holds one. Returns whether it did.

        The document it was created from is read back rather than
        re-authored: the machine *is* that document materialized, and
        a declaration that has changed since takes effect only after
        `testaferro destroy` — re-authoring would describe drives the
        machine does not have. A machine recorded running belongs to
        another process, or to a run that died with it up; either way
        it is refused by name rather than stopped from under whoever
        has it, and the refusal names the verb that frees it.
        """
        if self._persist is None:
            return False
        states = self._session.list_machines()
        if not states:
            return False
        machine = states[0]["id"]
        phase = self._session.load_machine_state(machine).get("phase")
        if phase in ("running", "stopping"):
            raise RuntimeError(
                f"persistent machine {self._persist!r} is recorded "
                f"{phase}: another run may be using it, and a run that "
                "died leaves it so; if nothing is, free it with "
                f"`testaferro shutdown {self._persist}`")
        with open(os.path.join(blueprints, _BLUEPRINT_NAME + ".rlqb"),
                  encoding="utf-8") as handle:
            document = json.load(handle)
        self._machine = machine
        _machine_started(self)
        self._drives = document[0]["drives"]
        self._work_key = next(
            key for key, drive in self._drives.items()
            if drive.get("name") == _WORK_MEDIA_NAME)
        return True

    def _gather(self, work):
        """Collect the staged set into one host directory.

        The suite executable, when there is one — a `GuestSession`
        names none — plus each `files=` entry beside it
        (`placement.gather()`, shared with every binding that stages).
        """
        placement.gather(work, self._files, exe_path=self._exe)

    def _create(self, blueprints, boot, work):
        """Author this session's blueprint and materialize it.

        `work` is always the real staging directory now: Testaferro's
        own drive is a permanent fixture of every session's document,
        never appended reactively.
        """
        document, key = self._blueprint(work, boot)
        with open(os.path.join(blueprints, _BLUEPRINT_NAME + ".rlqb"),
                  "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        self._machine = self._session.create_machine(_BLUEPRINT_NAME)
        _machine_started(self)
        self._drives = document[0]["drives"]
        self._work_key = key

    def _place(self, work):
        """Settle the location, and write to it only where it is not
        already there.

        **The address is stated once, staged against, and spelled.**
        A declared address is validated by the resolution itself: a
        wrong one fails here, before any boot, naming the cause —
        never smoothed over, because the consumer named that address
        and is the only one who can correct it.

        **Testaferro's own work drive needs no write at all.** It is a
        vvfat medium serving `work` live, and `_gather()` already put
        the staged set there before this method — or the machine
        itself — existed. Only a declared address naming some *other*
        drive still needs `at_rest.put_tree`, over remanence, because
        that drive is not live-served (F16, D23).
        """
        declared = self._declared_location
        location = declared or _default_location(
            self._drives, self._work_key)
        image, volume, path = _resolve_volume(
            location, self._machine, self._session, self._drives)
        letter, _ = at_rest.split_address(location)
        if _letter_map(self._drives).get(letter) != self._work_key:
            at_rest.put_tree(work, image, path, volume=volume)
        self._location = location

    def stop_guest(self):
        if self._home is None:
            return
        _running.discard(self)
        try:
            if self._machine is not None:
                self._session.stop_machine(self._machine)
                self._retrieve_if_kept()
        finally:
            if self._persist is not None:
                # Shutting down is not destroying (U8): the home and
                # the disks in it stay exactly where they are, and
                # only the hold on them is given up.
                if _holders.get(self._persist) is self:
                    del _holders[self._persist]
            else:
                # The machine's own cache lives under this home, so
                # the sweep takes the whole guest session with it.
                cache.release_guest_home(self._home)
            self._home = None
            self._session = None
            self._machine = None
            self._drives = None
            self._work_key = None
            self._location = None

    def _retrieve_if_kept(self):
        """Pull the staged location back out for an inspected home.

        **What `--testaferro-keep-guest-home` keeps had to change with
        F4.** It used to keep a host directory the guest wrote through
        directly; staging now lands inside a drive image, so keeping
        the home alone would keep everything except the thing worth
        looking at. So when the tester asked to see it, the location
        comes back to `retrieved/` — read at rest after the stop, which
        is also why it holds what the *run wrote* rather than only what
        was staged.

        Best-effort by design: a guest that repartitioned its disk, or
        wrote somewhere that cannot be read back, must not turn
        inspection into a failed test run. The home is kept either way,
        and it is the machine's images that are the fallback evidence.
        """
        if not cache.keeping_guest_homes() or self._location is None:
            return
        try:
            image, volume, path = _resolve_volume(
                self._location, self._machine, self._session,
                self._drives)
            at_rest.get_tree(image, path,
                             os.path.join(self._home, "retrieved"),
                             volume=volume)
        except (at_rest.AtRestError, ValueError,
                reliquary.ReliquaryError):
            pass

    def _wait_ready(self):
        """Block until the guest will take a command.

        `start_machine()` launches a machine; it does not wait for the
        guest inside it, and never claimed to. Reliquary ships no
        readiness script deliberately — what "ready" means belongs to
        whatever is being built — and the channel it provides is a
        **machine variable**: a script of the caller's own sets one as
        its last step, and the host reads it back. Variables are
        cleared at every start, so finding it set says *this* boot got
        there.

        Skipping this is what made the first guest command of every
        run come back as the boot's own output: the guest was still
        running its startup files, so what was typed at it went
        nowhere.

        **The variable is confirmation here, not a poll.** Reliquary's
        own description of this pattern polls, because its CLI runs
        the script and reads the variable from two separate processes.
        `run_script()` is synchronous, so the script's last step has
        already run by the time it returns; reading the variable
        holds the script to the contract rather than waiting for it.
        """
        self._session.run_script(_READY_SCRIPT, machine=self._machine)
        if self._session.get_machine_var(
                _READY_VAR, machine=self._machine) is None:
            raise RuntimeError(
                "the guest never reported itself ready, so nothing it "
                "shows can be trusted to be an answer")

    def _run_setup(self):
        """Run this session's declared `setup=` commands, in order.

        Once per **guest session** (D15), an enumeration boot
        included: a suite whose TSR must be resident to run needs it
        resident to enumerate too. After the readiness wait and before
        anything else — the same guest a first test would see, never
        a bare boot the framework adapter is asked to make sense of.

        Failure is the provider's to detect, never Testaferro's to
        parse (`exec(check=True)`, F9): a command that signals failure
        stops this loop and raises `GuestOutputError` in the shape
        every guest exchange fails in — naming the command, since
        that is the one thing certain about a probe reliquary itself
        could not show a screen for. The `except BaseException` this
        is called under ends the session: one report, not one per
        test the missing TSR would otherwise have doomed.

        **Weighed and declined: pre-boot validation of `setup`
        against `files`.** Refusing a command whose first token names
        no staged file and no known shell builtin would need a
        builtin vocabulary Testaferro kept on the shell's behalf,
        varying by DOS flavor and shell version — the kind of mirror
        `_letter_map()`'s own history argues against — and would
        refuse legitimate commands naming programs on the system
        disk, a tester's own boot floppy, or `PATH`. Keeping `files=`
        and `setup=` in agreement is the caller's own obligation; a
        typo surfaces as a loud setup failure here rather than a
        pre-boot refusal that would just as often be wrong.
        """
        for command in self._setup:
            try:
                self._session.exec(command, machine=self._machine,
                                   timeout=self._timeout, check=True)
            except reliquary.RunFailure as error:
                raise GuestOutputError(str(error), argv=(command,)) from error

    def _blueprint(self, work, boot=None):
        """The blueprint document for this backend session.

        The declaration, or the zero-configuration default. Every
        drive is authored JSON passed through to reliquary, which owns
        materialization: a declaration stays a template because
        reliquary materializes a fresh machine from it each session.

        `work` and `boot` are both **already staged** — locations,
        not sources. Nothing is copied here: this authors a document,
        and a document that copied files would be doing it after the
        point where the backend snapshots them.

        Returns the document and the work drive's own **key**, or
        `None` when `work` is not given (tests composing a document
        with no work drive at all). `_create()` keeps the key as
        `self._work_key`, which `_place()`/`_default_location()` read
        `_letter_map()` against to find where DOS put it — Testaferro's
        own answer now, not the provider's (0.1.0a2, D108).
        """
        spec = self._machine_config
        fields = dict(spec.fields) if spec is not None else {}
        fields.setdefault("platform", "dos")
        fields.setdefault("memory", _DEFAULT_MEMORY)
        drives = dict(fields.get("drives") or {})
        if not drives:
            image = boot
            if image is not None:
                # A tester's own boot floppy (U3), booted as given.
                drives["floppy0"] = {
                    "type": "media",
                    "name": _BOOT_MEDIA_NAME,
                    "location": {"local": image},
                    "materialize": "use",
                }
                fields.setdefault("boot", ["floppy0"])
            else:
                # Zero configuration: Testaferro's own installed
                # FreeDOS system. **Layered, never used in place** —
                # every guest session gets its own overlay, so a guest
                # writing to C: cannot reach the one copy each of them
                # shares. A persistent machine takes a *copy* instead
                # (F2): its C: is the disk state being kept, and an
                # overlay would tie that to a cache file `clean
                # --system` may drop. The work drive lands beside it
                # in the next slot.
                drives["hdd0"] = {
                    "type": "media",
                    "name": _SYSTEM_MEDIA_NAME,
                    "location": {"local": _cached_default_image()},
                    "materialize": ("copy" if self._persist is not None
                                    else "difference"),
                }
                fields.setdefault("boot", ["hdd0"])
        key = None
        if work is not None:
            key = _work_slot(drives)
            drives[key] = {
                "type": "media",
                "name": _WORK_MEDIA_NAME,
                "location": {"local": work},
                "materialize": "use",
            }
        fields["drives"] = drives
        fields["type"] = "machine"
        fields["name"] = _BLUEPRINT_NAME
        media = list(spec.media) if spec is not None else []
        return [fields, *media], key

    def _declared_boot_image(self):
        """A boot image somebody actually asked for, or None.

        This call's own first, then the one the run was opened with —
        staged into the run's area so every suite boots the same
        bytes. None means nobody said, which is the zero-configuration
        path and not a defaulted floppy: what runs then is
        Testaferro's own installed system, and it is a disk.
        """
        if self._boot_image is not None:
            return self._boot_image
        if _run_area is not None and _run_area["boot_image"]:
            return _run_image()
        return None

    def _stage_boot_image(self):
        """This guest's own copy of the declared boot image, or None.

        **The tester's image is read and never written** (P5), so what
        boots is Testaferro's copy inside this guest's home — staged
        before boot exactly as the suite executable is, and for the
        same reason: a drive attached in place is one the guest may
        write to, and DOS writes to A: for reasons of its own. Before
        this, a suite that did so edited the image its tester handed
        over. Copying per guest session also stops two suites in one
        run sharing a floppy either of them can change.
        """
        image = self._declared_boot_image()
        if image is None:
            return None
        staged = os.path.join(self._home, "boot.img")
        if self._persist is not None and os.path.exists(staged):
            # A persistent machine's floppy is one of the disks being
            # kept: what the guest wrote to it last session is the
            # point, so the copy is made once and then left alone.
            return staged
        shutil.copy2(image, staged)
        return staged


class ReliquarySuiteBackend(_GuestLifecycle, SuiteBackend):
    def __init__(self, exe_path, framework=cpputest, enumerator=None,
                 boot_image=None, machine_config=None, timeout=None,
                 files=(), location=None, program=None, setup=(),
                 persist=None):
        exe_path = os.fspath(exe_path)
        _GuestLifecycle.__init__(self, exe_path, boot_image=boot_image,
                                 machine_config=machine_config,
                                 timeout=timeout, files=files,
                                 location=location, program=program,
                                 setup=setup, persist=persist)
        SuiteBackend.__init__(self, exe_path, run=self._run_in_guest,
                              framework=framework, enumerator=enumerator,
                              argv_budget=self._argv_budget)

    def _exe_name(self):
        """The suite executable's own name, as the guest will see it."""
        return os.path.basename(self._exe)

    def _argv_budget(self):
        """Characters of argv one exchange can carry (F3).

        Two limits, the tighter one governing: the program's own
        argument tail (`placement.ARGUMENT_TAIL_LIMIT`), and the line
        this binding types at COMMAND.COM, whose input buffer takes
        126 characters — program, space and arguments together. Only
        known once the location has settled, which is why the
        composition asks rather than being told at construction.
        """
        command = placement.resolve_program(self._declared_program,
                                            self.location,
                                            self._exe_name())
        return min(placement.ARGUMENT_TAIL_LIMIT,
                   _DOS_COMMAND_LINE_LIMIT - len(command) - 1)

    def _run_in_guest(self, exe_path, args):
        if self._home is None:
            raise RuntimeError("no guest session: guest runs happen "
                               "between start_guest and stop_guest")
        # The framework hands over argv tokens; DOS takes one command
        # line, so this is where tokens become one — the guest-OS
        # aspect, which is why it lives here and not in the adapter.
        #
        # **The address staged against is the address spelled.** Both
        # come off the same settled location, so the command cannot
        # name somewhere the files did not go.
        command = placement.resolve_program(self._declared_program,
                                            self.location,
                                            self._exe_name())
        if args:
            command += " " + " ".join(args)
        rows = self._session.exec(command, machine=self._machine,
                                  timeout=self._timeout)
        return "\n".join(_logical_lines(rows)) + "\n"


#: The DOS text console is 80 columns wide, and the console — not
#: reliquary — is what wraps: a longer line lands on the screen as a
#: full row plus a remainder row, split wherever column 80 fell.
_DOS_CONSOLE_WIDTH = 80

#: What COMMAND.COM will take as one typed line: a 128-byte buffered
#: read, 127 characters at most with the carriage return — 126 of
#: text. This is the line this binding types, program and all.
_DOS_COMMAND_LINE_LIMIT = 126


def _logical_lines(rows):
    """Reconstruct logical output lines from captured screen rows.

    The guest-OS aspect again, like the argv joining above: a DOS
    console teletype hard-wraps at 80 columns, so one printed line
    longer than that arrives as several rows, split mid-token — which
    once made a CppUTest failure header unrecognizable and the
    failure it announced read back as a pass. A row of exactly the
    console width therefore continues on the row after it.

    Two limits, both consequences of what the capture keeps
    (`exec()` returns rows blank-dropped and right-trimmed):

    - A wrap falling on a space right-trims the full row below 80
      and the evidence is gone: that line stays split. The framework
      grammar's failure-count check is what turns the consequence
      into a refusal instead of a silent pass.
    - A line of exactly 80 characters leaves its newline as a blank
      row, which the capture drops, so it is indistinguishable from
      a wrap and joins the line after it. The damage surfaces as a
      missing test or summary — loud — rather than as a wrong result.
    """
    lines = []
    current = ""
    for row in rows:
        current += row
        if len(row) != _DOS_CONSOLE_WIDTH:
            lines.append(current)
            current = ""
    if current:
        lines.append(current)
    return lines


class GuestSession(_GuestLifecycle):
    """The guest handle a scripted interaction drives directly (U10):
    the same zero-configuration provisioning `guest_suite()` gives
    every suite — a cached image, a disposable per-session overlay,
    host files staged in — reached with no suite executable, no
    framework adapter, and nothing for one to parse.

    A context manager: entering opens the guest session (`start_guest`)
    and returns this handle; leaving sweeps it (`stop_guest`), whether
    the script's own assertions passed or one of them raised.

        with testaferro.guest_session() as guest:
            guest.exec("DRIVER.COM /install")
            guest.exec("RUNNER.EXE")

    Driving the guest interactively — reacting to what is on screen
    rather than just running one command and reading its result — is
    not what this offers: `exec()` alone is the whole of it, and
    widening that waits for a script that actually needs it (F18).
    """

    def __enter__(self):
        self.start_guest()
        return self

    def __exit__(self, *exc_info):
        self.stop_guest()
        return False

    def exec(self, command, timeout=None, check=False):
        """Run one guest command and return its output — mirrors
        `reliquary.Session.exec()`'s own contract, since that is
        precisely what a scripted guest interaction needs and a suite
        abstraction has no room for. `timeout` overrides this
        session's own for this command alone; `check=True` raises
        `reliquary.RunFailure` naming the command when it signalled
        failure, exactly as `reliquary.Session.exec()` does."""
        if self._home is None:
            raise RuntimeError(
                "no guest session: exec() runs between __enter__ and "
                "__exit__ (or start_guest() and stop_guest())")
        return self._session.exec(
            command, machine=self._machine,
            timeout=self._timeout if timeout is None else timeout,
            check=check)
