# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""The reliquary provider binding, for DOS guests.

Named for the provider it binds, which is the layer testaferro
actually talks to: everything in this module is a reliquary call, and
whatever the provider drives underneath is the provider's own
business — it has no name anywhere in this package (D16, P1, P2). The
module imported below is the provider distribution; this module is
`testaferro.reliquary`.

`suite_backend()` guards the door with `binfmt.classify()`: a DOS
program — plain MZ or a headerless/.com image — yields a
ReliquarySuiteBackend; anything else is rejected before any guest
work, with the format and architecture named. The framework adapter
defaults to testaferro.cpputest.

ReliquarySuiteBackend drives a reliquary machine on the caller's
behalf.
Each **guest session** — one guest up, from `start_guest()` to
`stop_guest()` — gets a fresh, disposable reliquary home under
testaferro's cache directory (LOCALAPPDATA or XDG_CACHE_HOME): the
declaration is written there as a blueprint, reliquary creates and
boots one machine from it, and every guest run is one `reliquary.exec`
against that machine. Guest homes sit inside the active **run**'s
area when `start()` opened one (`runs/run-*/guests/guest-*`) and
directly under the cache otherwise; the two spans and why neither is
called a "session" on its own are D15.

The suite reaches the guest on testaferro's own **work drive** — a
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
it instead, deterministically, because testaferro authors the whole
document** (`_letter_map()`): DOS gives a floppy `A:`/`B:` by
controller position and a hard disk `C:` onward by slot order, one
volume per disk, and every drive this binding ever declares — its own
system disk, its own work drive, a `machine_config` template passed
through unmodified — keeps to that shape by construction. Checked
against a real boot: the zero-configuration guest's system disk is
`C:` and its work-drive sibling is `D:`, exactly as computed, with
nothing shifted by a CD-ROM driver claiming a letter first (testaferro's
own FreeDOS install loads none).

**The write this module still asks `testaferro.at_rest` for is the
one case the work drive cannot cover on its own** — a `location=` a
consumer declared naming some *other* drive the machine carries, not
testaferro's own. Reading and writing a stopped machine's disk is not
execution, so that write is not the provider's to supply (F16, D23);
`at_rest` does it over remanence.
"""

from __future__ import annotations

import atexit
import json
import os
import shutil
import tempfile

import reliquary

from . import at_rest
from . import binfmt
from . import cache
from . import cpputest
from .suite import SuiteBackend


# The guest platforms this binding serves, and the one thing about
# itself a binding tells resolution: which provider runs which
# platform is a provider's own answer rather than a table kept
# upstream of it (P1, D11). Resolution reads this to refuse a
# declaration before importing anything further; `suite_backend()`
# guards the same ground for a caller who reached the binding
# directly, exactly as `binfmt` is shared between the two (D16).
PLATFORMS = ("dos",)

# The blueprint name testaferro writes into each session's private
# blueprints directory, and the machine created from it.
_BLUEPRINT_NAME = "testaferro"
# testaferro's own drive, a vvfat sibling of whatever else the
# machine declares — always present now (D108: reliquary no longer
# answers a drive-letter question at all, so there is nothing left
# to react to; the drive is simply always there instead).
_WORK_MEDIA_NAME = "testaferro-work"
_BOOT_MEDIA_NAME = "testaferro-boot"
# Where `_letter_map()` starts counting each drive family — DOS's own
# rule, not testaferro's: a floppy controller's drives take A:/B: by
# position, and a hard disk takes C: onward by slot order, neither
# ever read off anything.
_FLOPPY_BASE_LETTER = "A"
_HDD_BASE_LETTER = "C"
# What `program=` may say before the location is known. `{stem}` and
# `{name}` in the enumerator template are the precedent; this joins
# that vocabulary rather than inventing a second one (F4).
_LOCATION_PLACEHOLDER = "location"
# testaferro's installed FreeDOS system, shared by every guest session
# that declared nothing of its own.
_SYSTEM_MEDIA_NAME = "testaferro-freedos"
_DEFAULT_MEMORY = "32M"
# Seconds one guest command may take before reliquary gives up.
_DEFAULT_TIMEOUT = 120
_HDD_SLOTS = 4

# testaferro's own FreeDOS system, and the recipe that makes it.
#
# The recipe is authored here (P17): `assets/` holds the blueprint and
# the install script, so nothing about the environment testaferro
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
# belongs to whatever is being built — so this one is testaferro's
# answer for a guest suite: the guest will take a command. Bare stem,
# no `.rlqs`: `run_script()` resolves it against the session's own
# scripts directory (`_ASSETS`, pinned in `start_guest()`).
_READY_SCRIPT = "freedos-ready"
_READY_VAR = "ready"


def suite_backend(exe_path, framework=cpputest, enumerator=None,
                  boot_image=None, machine_config=None, timeout=None,
                  files=(), location=None, program=None):
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
    one-liner case: the executable alone, at testaferro's default
    location, run by its own name."""
    exe_path = os.fspath(exe_path)
    fmt = binfmt.classify(exe_path)
    if fmt.platform != "dos":
        raise ValueError(
            f"{os.path.basename(exe_path)} is {fmt.kind} executable; "
            "only DOS guest suites are supported")
    if machine_config is not None:
        from .environments import _coerce_machine_config

        machine_config = _coerce_machine_config(machine_config)
        if machine_config.platform != "dos":
            raise ValueError(
                "this binding runs DOS guests and needs a DOS machine "
                f"config, not {machine_config.platform!r}")
    if boot_image is not None and machine_config is not None:
        raise TypeError("boot_image and machine_config cannot be combined")
    return ReliquarySuiteBackend(exe_path, framework=framework,
                                 enumerator=enumerator,
                                 boot_image=boot_image,
                                 machine_config=machine_config,
                                 timeout=timeout, files=files,
                                 location=location, program=program)


# The active testaferro run opened by start(), or None: its
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
    """Open a testaferro run: one boot-image choice serving every
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
    active. `clear_downloads=True` also removes testaferro's built
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
        cached = os.path.join(cache.cache_root(), _FREEDOS_IMAGE_NAME)
        for path in (cached, cached + ".part"):
            if os.path.exists(path):
                os.remove(path)


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
    """testaferro's own FreeDOS system, built once and kept.

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
    """Install FreeDOS once, from testaferro's own authored recipe.

    Everything happens inside a disposable home under the cache and
    against a context pinned to `assets/`, so the codex is no more an
    input here than it is anywhere else (P17, D6). The machine is
    destroyed afterwards and only its disk survives, moved into place
    atomically so a killed build leaves no half-installed system to be
    mistaken for a finished one.
    """
    os.makedirs(cache.cache_root(), exist_ok=True)
    partial = destination + ".part"
    with tempfile.TemporaryDirectory(
            prefix="build-", dir=cache.cache_root()) as home:
        session = _open_session(home, _ASSETS, scripts=_ASSETS)
        machine = session.create_machine(_FREEDOS_BLUEPRINT)
        try:
            session.run_script("install", machine=machine)
            state = session.load_machine_state(machine)
            installed = state["drives"]["hdd0"]["path"]
            shutil.copy(installed, partial)
        finally:
            try:
                session.destroy_machine(machine)
            except Exception:
                # The whole home goes with this block regardless; a
                # machine that will not tear down must not also cost
                # us the image we just spent an install on.
                pass
    os.replace(partial, destination)


def _open_session(home, blueprints, scripts=None):
    """A reliquary session pinned to one disposable testaferro home.

    The pinned directories keep resolution hermetic: only what
    testaferro wrote for this run, never the user's own reliquary home
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
    building the default image — and points at testaferro's own
    `assets/` for the same reason the blueprints directory does.
    """
    context = reliquary.Context(home_dir=home,
                                cache_dir=os.path.join(home, "cache"),
                                blueprints_dir=blueprints,
                                scripts_dir=scripts)
    return reliquary.Session(context)


def _work_slot(drives):
    """Choose the disk slot testaferro's work drive will occupy.

    The slot is testaferro's to choose — the lowest free disk — and
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

    **Deterministic, because testaferro authors the whole document**
    (0.1.0a2, D108 — reliquary's own drive-letter report is deleted
    outright, and remanence refuses the same question by design, its
    own D57: a fact about a booted guest, never a stopped image). DOS
    assigns a floppy controller's drives `A:`/`B:` by position, and a
    hard disk `C:` onward by slot order — one volume per disk, which
    holds by construction for every drive this binding ever declares:
    its own system disk and its own work drive are each exactly one
    FAT volume, and a `machine_config` declaration is expected to keep
    that shape too, since testaferro cannot look inside a disk it did
    not build to check.

    Through 0.1.0.dev4 testaferro inferred every letter exactly this
    way, and 0.1.0.dev5 killed the practice: a *declared* disk could
    hold more volumes than it declared, so reading the real answer was
    the only honest one once reliquary offered it. 0.1.0a2 withdrew
    that offer for good — this is not a fallback for its absence, it
    is the position the project now holds: the assumption inference
    always rested on is one testaferro states and owns, not one it
    pretends to have confirmed.

    Checked against a real boot (FreeDOS 1.4, one hard disk plus a
    vvfat sibling): the system disk answers `C:` and the sibling `D:`,
    matching this computation exactly, with nothing shifted by a
    CD-ROM driver claiming a letter first — testaferro's own FreeDOS
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

    **One computation for every drive now, testaferro's own or
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
    """Where a run lands when nobody said (F4, P8): testaferro's own
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


def _resolve_program(program, location, exe_name):
    """The guest address of what to run, defaulted or declared.

    Defaulted it is the staged executable under the location, which
    is the whole of the one-liner case. Declared it is the consumer's
    own address, with `{location}` substituted — the location is
    settled by now whether they stated it or testaferro chose it, and
    that is precisely what makes one placeholder enough.
    """
    if program is None:
        return _join(location, exe_name)
    try:
        return program.format(**{_LOCATION_PLACEHOLDER: location})
    except KeyError as error:
        raise ValueError(
            f"program={program!r} names {{{error.args[0]}}}, which "
            f"testaferro does not substitute; it knows "
            f"{{{_LOCATION_PLACEHOLDER}}}") from None


def _join(location, name):
    """Join a guest directory address to a name, DOS-style."""
    return location.rstrip("\\") + "\\" + name


class ReliquarySuiteBackend(SuiteBackend):
    def __init__(self, exe_path, framework=cpputest, enumerator=None,
                 boot_image=None, machine_config=None, timeout=None,
                 files=(), location=None, program=None):
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
        # the default. The same rule for all four, so a consumer never
        # has to remember which options overrule a declaration.
        declared = machine_config
        self._timeout = self._nearest(timeout, "timeout", _DEFAULT_TIMEOUT)
        self._declared_location = self._nearest(location, "location")
        self._declared_program = self._nearest(program, "program")
        staged = self._nearest(files or None, "files") or ()
        self._files = tuple(os.fspath(path) for path in staged)
        del declared
        super().__init__(os.fspath(exe_path), run=self._run_in_guest,
                         framework=framework, enumerator=enumerator)

    def _nearest(self, given, name, default=None):
        """This call, then the declaration, then the default."""
        declared = (None if self._machine_config is None
                    else getattr(self._machine_config, name, None))
        return next((value for value in (given, declared)
                     if value not in (None, ())), default)

    @property
    def location(self):
        """Where this suite's harness landed, in the guest's terms.

        The **placement reported** (F4): one question, one vocabulary,
        one answer — a guest address like `C:\\TESTS`, the same terms a
        declaration uses, so what you could have declared is what you
        are told. And the same answer whether the consumer stated it
        or testaferro chose it: who chose is deliberately not part of
        it, which is the courtesy testaferro asks of the provider one
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
        # A guest home sits inside the active run's area, or directly
        # under the cache when no run was opened: a guest belonging to
        # no run still needs somewhere disposable to live.
        area = _run_area["dir"] if _run_area else cache.cache_root()
        guests = os.path.join(area, "guests")
        os.makedirs(guests, exist_ok=True)
        self._home = tempfile.mkdtemp(prefix="guest-", dir=guests)
        blueprints = os.path.join(self._home, "blueprints")
        work = os.path.join(self._home, "work")
        os.makedirs(blueprints)
        os.makedirs(work)
        # The host side of the staged set: the suite executable, plus
        # whatever `files=` named, gathered into one directory because
        # `at_rest.put_tree` copies a tree and the set keeps its shape
        # under the location.
        self._gather(work)
        # The boot image is staged host-side too, and for a different
        # reason: what boots is testaferro's copy, so the tester's own
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
            self._create(blueprints, boot, work)
            # Between create and start: the drive images exist to be
            # read and written, and reliquary will still touch them at
            # rest. A declared address that cannot work fails here,
            # before any boot, rather than as a missing program in the
            # guest — testaferro's own work drive needs nothing
            # written to it at all, its content having arrived with
            # `_gather()` before the machine ever existed.
            self._place(work)
            self._session.start_machine(self._machine)
            self._wait_ready()
        except BaseException:
            self.stop_guest()
            raise

    def _gather(self, work):
        """Collect the staged set into one host directory.

        The suite executable always, plus each `files=` entry beside
        it. A named directory contributes its contents rather than
        itself, which is what makes `files=["fixtures"]` land the
        fixtures where a guest program will look for them instead of
        one directory deeper.
        """
        shutil.copy2(self._exe, os.path.join(work, self._exe_name()))
        for source in self._files:
            if os.path.isdir(source):
                shutil.copytree(source, work, dirs_exist_ok=True)
            else:
                shutil.copy2(source, os.path.join(
                    work, os.path.basename(source)))

    def _create(self, blueprints, boot, work):
        """Author this session's blueprint and materialize it.

        `work` is always the real staging directory now: testaferro's
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

        **testaferro's own work drive needs no write at all.** It is a
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
            # The machine's own cache lives under this home, so the
            # sweep takes the whole guest session with it.
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

    def _exe_name(self):
        """The suite executable's own name, as the guest will see it."""
        return os.path.basename(self._exe)

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
        command = _resolve_program(self._declared_program, self.location,
                                   self._exe_name())
        if args:
            command += " " + " ".join(args)
        rows = self._session.exec(command, machine=self._machine,
                                  timeout=self._timeout)
        return "\n".join(rows) + "\n"

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
        `_letter_map()` against to find where DOS put it — testaferro's
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
                # Zero configuration: testaferro's own installed
                # FreeDOS system. **Layered, never used in place** —
                # every guest session gets its own overlay, so a guest
                # writing to C: cannot reach the one copy each of them
                # shares. The work drive lands beside it in the next
                # slot; what the guest calls it is read off the created
                # machine, not assumed from the slot.
                drives["hdd0"] = {
                    "type": "media",
                    "name": _SYSTEM_MEDIA_NAME,
                    "location": {"local": _cached_default_image()},
                    "materialize": "difference",
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
        testaferro's own installed system, and it is a disk.
        """
        if self._boot_image is not None:
            return self._boot_image
        if _run_area is not None and _run_area["boot_image"]:
            return _run_image()
        return None

    def _stage_boot_image(self):
        """This guest's own copy of the declared boot image, or None.

        **The tester's image is read and never written** (P5), so what
        boots is testaferro's copy inside this guest's home — staged
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
        shutil.copy2(image, staged)
        return staged
