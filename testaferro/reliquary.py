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


# The blueprint name testaferro writes into each session's private
# blueprints directory, and the machine created from it.
_BLUEPRINT_NAME = "testaferro"
# The host-directory drive carrying the suite executable to the guest.
_WORK_MEDIA_NAME = "testaferro-work"
_BOOT_MEDIA_NAME = "testaferro-boot"
_DEFAULT_MEMORY = "32M"
# Seconds one guest command may take before reliquary gives up.
_DEFAULT_TIMEOUT = 120
_HDD_SLOTS = 4

# FreeDOS 1.4's FloppyEdition, from which x86BOOT.img (a ready-to-boot
# 1.44M floppy image) is extracted; a reliquary media definition,
# fetched and hash-verified through reliquary.fetch_media().
_FREEDOS_FLOPPY_MEDIA_NAME = "freedos-boot-floppy"
_FREEDOS_FLOPPY_MEDIA_DEFINITION = [
    {
        "type": "media",
        "name": "freedos-floppy-edition",
        "location": "https://download.freedos.org/1.4/FD14-FloppyEdition.zip",
        "sha256": ("45b1fa7c52dd996c3bfa5e352ffcd410781b952a6ad629f"
                  "15a4c9ec4bbaefc5a"),
        "children": [
            {
                "type": "media",
                "name": _FREEDOS_FLOPPY_MEDIA_NAME,
                "path": "144m/x86BOOT.img",
                "sha256": ("552f7cbb0625960c050a3e682a4d2121cc2ffdfa9dc9d59"
                          "2ccd49edf179333dc"),
            },
        ],
    },
]


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
        from .machines import _coerce_machine_config

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
    active. `clear_downloads=True` also removes the cached default
    boot image, forcing a fresh download next time."""
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
        cached = os.path.join(cache.cache_root(), "boot.img")
        for path in (cached, cached + ".part"):
            if os.path.exists(path):
                os.remove(path)


def _run_image():
    """The active run's staged boot image, staging it on first use
    from the recorded choice or the cached default."""
    image = os.path.join(_run_area["dir"], "boot.img")
    if not os.path.exists(image):
        shutil.copy(_run_area["boot_image"] or _cached_default_image(),
                    image)
    return image


def _cached_default_image():
    """testaferro's cached copy of the default boot image: FreeDOS
    1.4's floppy-edition boot floppy, fetched and hash-verified
    through reliquary.fetch_media() on first use."""
    cached = os.path.join(cache.cache_root(), "boot.img")
    if not os.path.exists(cached):
        os.makedirs(cache.cache_root(), exist_ok=True)
        with tempfile.TemporaryDirectory(
                prefix="download-", dir=cache.cache_root()) as home:
            blueprints = os.path.join(home, "blueprints")
            os.makedirs(blueprints)
            definition = os.path.join(blueprints, "freedos-floppy.rlqb")
            with open(definition, "w", encoding="utf-8") as handle:
                json.dump(_FREEDOS_FLOPPY_MEDIA_DEFINITION, handle)
            payload = reliquary.fetch_media(
                _FREEDOS_FLOPPY_MEDIA_NAME,
                _context(home, blueprints))
            shutil.copy(payload, cached + ".part")
        os.replace(cached + ".part", cached)
    return cached


def _context(home, blueprints):
    """A reliquary context pinned to one disposable testaferro home.

    The blueprints directory and `autoseed=False` keep the resolution
    hermetic: only what testaferro wrote for this run, never the user's
    own reliquary home or the built-in codex. Autoseeding is off by
    default in the embedding API; pinning it says so per session, so a
    host process that turned the process-global on cannot reach in.
    """
    return reliquary.Context(home_dir=home,
                             cache_dir=os.path.join(home, "cache"),
                             blueprints_dir=blueprints,
                             autoseed=False)


def _work_drive(drives):
    """Place testaferro's work drive and name the letter DOS gives it.

    The work drive takes the lowest free disk slot, so its letter is
    its own position among the declared disks: floppies take A:/B: by
    slot and hard disks C: onward in slot order.

    As of reliquary 0.1.0.dev3 that rule is testaferro's alone past
    the first disk. `platform_dos.drive_letters()` determines a letter
    for the *first* hard disk and no other, because every later one
    depends on how many volumes the disks before it carry — a fact a
    blueprint does not declare. Where the work drive lands first
    (every zero-configuration run) the letter is reliquary's own; past
    it testaferro assumes one volume per declared disk, and a machine
    whose declared disk the guest partitioned in two would run the
    suite off the wrong drive.
    """
    used = sorted({int(key[len("hdd"):] or 0)
                   for key in drives if key.startswith("hdd")})
    free = [slot for slot in range(_HDD_SLOTS) if slot not in used]
    if not free:
        raise ValueError(
            "the machine declares every disk slot; testaferro needs one "
            "free slot for the work drive that carries the suite "
            "executable into the guest")
    slot = free[0]
    letter = chr(ord("C") + sorted(used + [slot]).index(slot))
    return f"hdd{slot}", letter


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

        document, self._letter = self._blueprint(work)
        with open(os.path.join(blueprints, _BLUEPRINT_NAME + ".rlqb"),
                  "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        self._ctx = _context(self._home, blueprints)
        try:
            self._machine = reliquary.create_machine(
                _BLUEPRINT_NAME, context=self._ctx)
            _machine_started(self)
            reliquary.start_machine(self._machine, context=self._ctx)
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

    def _blueprint(self, work):
        """The blueprint document for this backend session.

        The declaration (or the zero-configuration default) plus
        testaferro's own work drive, which is how the suite executable
        reaches the guest. Every drive is authored JSON passed through
        to reliquary, which owns materialization: a declaration stays
        a template because reliquary materializes a fresh machine from
        it each session.
        """
        spec = self._machine_config
        fields = dict(spec.fields) if spec is not None else {}
        fields.setdefault("platform", "dos")
        fields.setdefault("memory", _DEFAULT_MEMORY)
        drives = dict(fields.get("drives") or {})
        if not drives:
            drives["floppy0"] = {
                "type": "media",
                "name": _BOOT_MEDIA_NAME,
                "location": {"local": self._boot_media_path()},
                "materialize": "use",
            }
            fields.setdefault("boot", ["floppy0"])
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

    def _boot_media_path(self):
        """The image the zero-configuration machine boots: this
        backend's own choice, the run's staged image, or the
        cached default."""
        if self._boot_image is not None:
            return self._boot_image
        return _run_image() if _run_area else _cached_default_image()
