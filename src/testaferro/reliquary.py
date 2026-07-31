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

The suite reaches the guest by being **staged at rest** (F4): the set
is gathered host-side, then written into the machine's own drives
with `put_files()` between `create_machine()` and `start_machine()`,
at a **location** the consumer either declared or testaferro chose
off the drive map. A machine offering no writable room of its own
falls back to a host-directory drive testaferro appends — which is
all that survives of D5, and an implementation detail rather than
the promise. Zero configuration is seeded from the caller-supplied
`boot_image` or a cached FreeDOS image.
"""

from __future__ import annotations

import atexit
import json
import os
import shutil
import tempfile

import reliquary

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
# The host-directory drive carrying the suite executable to the guest
# — the **fallback** since F4, used only for a machine offering no
# writable room of its own. Staging is otherwise at rest, into a drive
# the machine already has.
_WORK_MEDIA_NAME = "testaferro-work"
_BOOT_MEDIA_NAME = "testaferro-boot"
# The directory a defaulted location puts the staged set in, under the
# last letter of the guest's drive map. Eight characters and no dot,
# because DOS 8.3 is what has to read it back.
_STAGED_DIR = "TESTS"
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
# The readiness script and the variable its last step sets. Reliquary
# ships no readiness script on purpose — what "ready" means belongs to
# whatever is being built — so this one is testaferro's answer for a
# guest suite: the guest will take a command.
_READY_SCRIPT = os.path.join(_ASSETS, "freedos-ready.rlqs")
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
    the guest address they land at (`D:\\TESTS`); `program` is the
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
        context = _context(home, _ASSETS, scripts=_ASSETS)
        machine = reliquary.create_machine(_FREEDOS_BLUEPRINT,
                                           context=context)
        try:
            reliquary.run_script("install", machine=machine,
                                 context=context)
            state = reliquary.load_machine_state(machine, context)
            installed = state["drives"]["hdd0"]["path"]
            shutil.copy(installed, partial)
        finally:
            try:
                reliquary.destroy_machine(machine, context=context)
            except Exception:
                # The whole home goes with this block regardless; a
                # machine that will not tear down must not also cost
                # us the image we just spent an install on.
                pass
    os.replace(partial, destination)


def _context(home, blueprints, scripts=None):
    """A reliquary context pinned to one disposable testaferro home.

    The pinned directories keep the resolution hermetic: only what
    testaferro wrote for this run, never the user's own reliquary home
    or the built-in codex.

    **The second half of that used to be testaferro's to pin, and is
    now the provider's to guarantee.** Through 0.1.0.dev4 this passed
    `autoseed=False`, so a host process that turned the process-global
    on could not reach in. 0.1.0.dev6 deleted autoseeding outright
    (D88 there) rather than defaulting it: the blueprints and scripts
    directories are the sole sources, and a name they do not hold is
    refused. So the knob is gone because the hazard is, and what this
    pinned per session is now structural.

    `scripts` is pinned only where one is actually run — building the
    default image — and points at testaferro's own `assets/` for the
    same reason the blueprints directory does.
    """
    return reliquary.Context(home_dir=home,
                             cache_dir=os.path.join(home, "cache"),
                             blueprints_dir=blueprints,
                             scripts_dir=scripts)


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


def _placed_letter(key, machine, context):
    """Ask the created machine what letter its work drive got.

    **Inference is retired here** (D78 upstream). Through 0.1.0.dev4
    testaferro derived the letter while authoring the blueprint, from
    `platform_dos.drive_letters()` over the declared drives alone.
    0.1.0.dev5 ended that: a disk takes one letter per volume it
    *actually holds*, read off the image at rest, so the declaration
    stopped being enough to answer from and the derivation stopped
    being possible before materialization. 0.1.0.dev6 supplies the
    answer instead — `describe_drives()` reports a created machine's
    drives and the letter map over them (D83 there).

    So the question moves to the one moment it can be answered: after
    `create_machine()`, when images exist to read, and before
    `start_machine()`, while reliquary will still read them. What the
    guest is told is what the provider placed — never a rule
    testaferro keeps a copy of, which is exactly the mirror D78
    deleted upstream.

    A drive left unplaced is refused **carrying reliquary's own
    reason**, not a summary of it: an unreadable disk ahead of this
    one shifts every letter behind it, and the specific refusal is
    the only thing that says which disk and why. A suite run off the
    wrong drive fails as a missing program and says nothing at all.
    """
    report = reliquary.describe_drives(machine=machine, context=context)
    mapping = report.get("mapping") or {}
    for letter, placed in (mapping.get("letters") or {}).items():
        if placed.get("drive") == key:
            return letter
    for entry in mapping.get("undetermined") or ():
        if entry.get("drive") == key:
            raise ValueError(
                f"reliquary left {key} without a letter, so testaferro "
                "cannot tell the guest where its suite is: "
                f"{entry.get('reason')} [{entry.get('id')}]")
    raise ValueError(
        f"reliquary's drive report names no letter and no refusal for "
        f"{key}, which testaferro declared as its work drive")


def _default_location(machine, context):
    """Choose where a run lands when nobody said (F4, P8).

    **The facts are the provider's and the choice is testaferro's.**
    `describe_drives()` says which letters this machine actually has;
    the policy applied over them is the last letter — the drive
    testaferro appended when it appended one, the boot disk's own
    volume when it did not — with the staged set in a directory under
    it that testaferro names. Last rather than first because the
    system disk is what a machine declares first and what a guest
    boots from: landing on top of somebody's `C:\\` root is the one
    place a default must not put a stranger's files.

    Nothing is inferred: a letter that appears here was read off a
    materialized image, and a machine whose letters cannot be
    determined refuses rather than defaulting onto a guess.
    """
    report = reliquary.describe_drives(machine=machine, context=context)
    mapping = report.get("mapping") or {}
    letters = sorted((mapping.get("letters") or {}))
    if not letters:
        undetermined = mapping.get("undetermined") or ()
        if undetermined:
            entry = undetermined[0]
            raise ValueError(
                "testaferro cannot choose where to put this suite: "
                f"{entry.get('reason')} [{entry.get('id')}]. Declare "
                "location= with a guest address to say where it goes")
        raise ValueError(
            "this machine has no drive testaferro can stage onto; "
            "declare location= with a guest address, or give the "
            "machine a drive to put the suite on")
    return f"{letters[-1]}:\\{_STAGED_DIR}"


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
        self._ctx = None
        self._machine = None
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
        # `put_files` copies a tree and the set keeps its shape under
        # the location.
        self._gather(work)
        # The boot image is staged host-side too, and for a different
        # reason: what boots is testaferro's copy, so the tester's own
        # file is read and never written (P5).
        boot = self._stage_boot_image()

        self._ctx = _context(self._home, blueprints)
        try:
            self._create(blueprints, boot, work=None)
            # Between create and start: the drive images exist to be
            # read and written, and reliquary will still touch them at
            # rest. Everything below happens in that window, so a
            # placement that cannot work fails before any boot rather
            # than as a missing program in the guest.
            self._place(work, blueprints, boot)
            reliquary.start_machine(self._machine, context=self._ctx)
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
        """Author this session's blueprint and materialize it."""
        document, key = self._blueprint(work, boot)
        with open(os.path.join(blueprints, _BLUEPRINT_NAME + ".rlqb"),
                  "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        self._machine = reliquary.create_machine(
            _BLUEPRINT_NAME, context=self._ctx)
        _machine_started(self)
        return key

    def _place(self, work, blueprints, boot):
        """Settle the location and stage the set at it, at rest.

        **The address is stated once, staged against, and spelled.**
        A declared address is validated by the staging itself:
        `put_files` resolves it against the actual disk at the one
        moment the answer exists, and a wrong one fails here with
        reliquary's own refusal naming the cause (P11 by inheritance)
        — never smoothed over, because the consumer named that address
        and is the only one who can correct it.

        A **defaulted** address may fall back, and only a defaulted
        one. Where the chosen drive turns out to be one reliquary
        cannot write at rest — an unreadable disk, a FAT it does not
        claim, a backend without the capability — testaferro appends
        the directory-source drive D5 used to supply and stages there
        instead. That is the drive surviving as an implementation
        detail for a machine offering no writable room, exactly as far
        as the design allows: the surface promises a location, never a
        drive.
        """
        declared = self._declared_location
        location = declared or _default_location(self._machine, self._ctx)
        try:
            reliquary.put_files(work, location, machine=self._machine,
                                context=self._ctx)
        except reliquary.ReliquaryError:
            if declared is not None:
                raise
            location = self._fall_back_to_work_drive(work, blueprints, boot)
        self._location = location

    def _fall_back_to_work_drive(self, work, blueprints, boot):
        """Append testaferro's own drive and stage onto that instead.

        The machine is recreated rather than amended: a drive is
        chosen at materialization, and reliquary refuses to regenerate
        one on an existing machine — rightly, since that is how a
        stale image would go unnoticed. Nothing is lost by starting
        again, because none of this has booted.
        """
        reliquary.destroy_machine(self._machine, context=self._ctx)
        _running.discard(self)
        self._machine = None
        key = self._create(blueprints, boot, work=work)
        letter = _placed_letter(key, self._machine, self._ctx)
        # The drive testaferro just added is a host directory the
        # backend serves whole, so the set is already at its root:
        # staging it a second time would copy it into itself.
        return f"{letter}:\\"

    def stop_guest(self):
        if self._home is None:
            return
        _running.discard(self)
        try:
            if self._machine is not None:
                reliquary.stop_machine(self._machine,
                                       context=self._ctx)
                self._retrieve_if_kept()
        finally:
            # The machine's own cache lives under this home, so the
            # sweep takes the whole guest session with it.
            cache.release_guest_home(self._home)
            self._home = None
            self._ctx = None
            self._machine = None
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
        wrote somewhere reliquary cannot read back, must not turn
        inspection into a failed test run. The home is kept either way,
        and it is the machine's images that are the fallback evidence.
        """
        if not cache.keeping_guest_homes() or self._location is None:
            return
        try:
            reliquary.get_files(self._location,
                                os.path.join(self._home, "retrieved"),
                                machine=self._machine, context=self._ctx)
        except reliquary.ReliquaryError:
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
        `execute_script()` is synchronous, so the script's last step
        has already run by the time it returns; reading the variable
        holds the script to the contract rather than waiting for it.
        """
        reliquary.execute_script(reliquary.load_script(_READY_SCRIPT),
                                 machine_id=self._machine,
                                 context=self._ctx)
        if reliquary.get_machine_var(_READY_VAR, machine=self._machine,
                                     context=self._ctx) is None:
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
        rows = reliquary.exec(command, machine=self._machine,
                              context=self._ctx,
                              timeout=self._timeout)
        return "\n".join(rows) + "\n"

    def _blueprint(self, work, boot=None):
        """The blueprint document for this backend session.

        The declaration, or the zero-configuration default. Every
        drive is authored JSON passed through to reliquary, which owns
        materialization: a declaration stays a template because
        reliquary materializes a fresh machine from it each session.

        **`work` is normally `None` now.** Through F4's predecessor
        every session appended a host-directory drive here, because
        that was the only way bytes reached a guest; staging happens
        at rest instead, into a drive the machine already has. A path
        arrives only on the fallback path, for a machine offering no
        writable room of its own, and then this appends the drive as
        it always did.

        `work` and `boot` are both **already staged** — locations,
        not sources. Nothing is copied here: this authors a document,
        and a document that copied files would be doing it after the
        point where the backend snapshots them.

        Returns the document and the appended drive's **key**, or
        `None` when none was appended. A key is what the caller asks
        the created machine about (`_placed_letter`); it used to
        return a letter, and inference is what 0.1.0.dev6 retired.
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
