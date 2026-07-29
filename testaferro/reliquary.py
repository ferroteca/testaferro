# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
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
called a "session" on its own are D15. The suite executable reaches the guest on a
work drive whose media is located at a host directory (vvfat is how
such a media attaches), which testaferro adds to the blueprint and
stages before boot. Zero configuration is seeded from the
caller-supplied `boot_image` or a cached FreeDOS image.
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
# The host-directory drive carrying the suite executable to the guest.
_WORK_MEDIA_NAME = "testaferro-work"
_BOOT_MEDIA_NAME = "testaferro-boot"
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
                  boot_image=None, machine_config=None, timeout=None):
    """Interrogate the referenced suite executable and return the
    backend matching its format — a ReliquarySuiteBackend for a DOS
    program. Raises FileNotFoundError for a missing file and
    ValueError for a provably non-DOS executable (e.g. the suite's
    host build passed by mistake).

    `timeout` is seconds one guest command may take, and overrides
    what a declaration says: it is the caller speaking about this
    run, and a declaration speaks about the environment."""
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
                                 timeout=timeout)


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

    The blueprints directory and `autoseed=False` keep the resolution
    hermetic: only what testaferro wrote for this run, never the user's
    own reliquary home or the built-in codex. Autoseeding is off by
    default in the embedding API; pinning it says so per session, so a
    host process that turned the process-global on cannot reach in.

    `scripts` is pinned only where one is actually run — building the
    default image — and points at testaferro's own `assets/` for the
    same reason the blueprints directory does.
    """
    return reliquary.Context(home_dir=home,
                             cache_dir=os.path.join(home, "cache"),
                             blueprints_dir=blueprints,
                             scripts_dir=scripts,
                             autoseed=False)


def _work_drive(drives):
    """Place testaferro's work drive and ask what letter it gets.

    The slot is testaferro's to choose — the lowest free disk — and
    the **letter is reliquary's to say**. Since 0.1.0.dev4
    `platform_dos.drive_letters()` places every drive rather than only
    the first disk, so the local mirror of that rule is gone and this
    asks instead. The assumption underneath it (one volume per hard
    disk) did not disappear; it moved to the party that owns it, which
    is the whole of what P1 asks for.

    A letter reliquary will not determine — mixed controller types
    leave even the first disk unplaceable — is refused here rather
    than guessed at, because a suite run off the wrong drive fails as
    a missing program and says nothing about why.
    """
    from reliquary import platform_dos

    used = sorted({int(key[len("hdd"):] or 0)
                   for key in drives if key.startswith("hdd")})
    free = [slot for slot in range(_HDD_SLOTS) if slot not in used]
    if not free:
        raise ValueError(
            "the machine declares every disk slot; testaferro needs one "
            "free slot for the work drive that carries the suite "
            "executable into the guest")
    key = f"hdd{free[0]}"
    state = {name: _drive_state(name) for name in (*drives, key)}
    if key in platform_dos.undetermined_letters(state):
        raise ValueError(
            f"this machine's drives leave {key} without a determined "
            "letter, so testaferro cannot tell the guest where its "
            "suite is; declare one fewer controller type, or name the "
            "drive testaferro should use")
    for letter, placed in platform_dos.drive_letters(state).items():
        if placed == key:
            return key, letter
    raise ValueError(
        f"reliquary placed no letter for {key}")


def _drive_state(key):
    """A blueprint drive key as reliquary records it on a machine.

    Medium and slot are what `drive_letters()` reads, and a blueprint
    key already carries both — `hdd1` is the second disk by its own
    name — so this is a spelling change rather than a second opinion.
    """
    medium = key.rstrip("0123456789")
    return {"medium": medium, "slot": int(key[len(medium):] or 0)}


class ReliquarySuiteBackend(SuiteBackend):
    def __init__(self, exe_path, framework=cpputest, enumerator=None,
                 boot_image=None, machine_config=None, timeout=None):
        self._boot_image = (None if boot_image is None
                            else os.fspath(boot_image))
        self._home = None
        self._ctx = None
        self._machine = None
        self._letter = None
        self._machine_config = machine_config
        # Nearest speaker wins: this call, then the declaration, then
        # the default.
        declared = (None if machine_config is None
                    else machine_config.timeout)
        self._timeout = next(
            (value for value in (timeout, declared) if value is not None),
            _DEFAULT_TIMEOUT)
        super().__init__(os.fspath(exe_path), run=self._run_in_guest,
                         framework=framework, enumerator=enumerator)

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
        # the backend snapshots the host directory when the drive is
        # attached, so the executable is staged before the machine
        # boots, not on the first run.
        shutil.copy2(self._exe, os.path.join(work, self._program()))
        # And the boot image for the same reason, one drive over: what
        # boots is testaferro's copy, so the tester's own file is read
        # and never written (P5).
        boot = self._stage_boot_image()

        document, self._letter = self._blueprint(work, boot)
        with open(os.path.join(blueprints, _BLUEPRINT_NAME + ".rlqb"),
                  "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        self._ctx = _context(self._home, blueprints)
        try:
            self._machine = reliquary.create_machine(
                _BLUEPRINT_NAME, context=self._ctx)
            _machine_started(self)
            reliquary.start_machine(self._machine, context=self._ctx)
            self._wait_ready()
        except BaseException:
            self.stop_guest()
            raise

    def stop_guest(self):
        if self._home is None:
            return
        _running.discard(self)
        try:
            if self._machine is not None:
                reliquary.stop_machine(self._machine,
                                       context=self._ctx)
        finally:
            # The machine's own cache lives under this home, so the
            # sweep takes the whole guest session with it.
            cache.release_guest_home(self._home)
            self._home = None
            self._ctx = None
            self._machine = None
            self._letter = None

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

    def _program(self):
        """The suite's guest-side command name."""
        return os.path.basename(self._exe)

    def _run_in_guest(self, exe_path, args):
        if self._home is None:
            raise RuntimeError("no guest session: guest runs happen "
                               "between start_guest and stop_guest")
        # The framework hands over argv tokens; DOS takes one command
        # line, so this is where tokens become one — the guest-OS
        # aspect, which is why it lives here and not in the adapter.
        command = f"{self._letter}:\\{self._program()}"
        if args:
            command += " " + " ".join(args)
        rows = reliquary.exec(command, machine=self._machine,
                              context=self._ctx,
                              timeout=self._timeout)
        return "\n".join(rows) + "\n"

    def _blueprint(self, work, boot=None):
        """The blueprint document for this backend session.

        The declaration (or the zero-configuration default) plus
        testaferro's own work drive, which is how the suite executable
        reaches the guest. Every drive is authored JSON passed through
        to reliquary, which owns materialization: a declaration stays
        a template because reliquary materializes a fresh machine from
        it each session.

        `work` and `boot` are both **already staged** — locations,
        not sources. Nothing is copied here: this authors a document,
        and a document that copied files would be doing it after the
        point where the backend snapshots them.
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
                # shares. The work drive lands beside it and the guest
                # calls it D:, which is the first time testaferro's
                # one-volume-per-disk assumption is worth anything.
                drives["hdd0"] = {
                    "type": "media",
                    "name": _SYSTEM_MEDIA_NAME,
                    "location": {"local": _cached_default_image()},
                    "materialize": "difference",
                }
                fields.setdefault("boot", ["hdd0"])
        key, letter = _work_drive(drives)
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
        return [fields, *media], letter

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
