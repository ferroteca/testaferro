# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""The DOSBox-X provider binding, for DOS guests, batch-shaped.

Named for the provider it binds (D16), with the one spelling change
Python forces: a tester declares ``provider="dosbox-x"`` and the
hyphen becomes an underscore here, exactly as hyphenated declaration
keys are written in Python and INI. Everything in this module is a
DOSBox-X invocation; nothing DOSBox-X does inside is Testaferro's
vocabulary (P2).

**The shape is batch, not interactive, and that is the whole design**
(F20, D27). Reliquary's model is a machine that stays up with an
`exec()` per operation against it; DOSBox-X has no such channel and is
deliberately not given one. Each `Backend` operation is one DOSBox-X
invocation: a generated conf mounts this session's staged work
directory in `[autoexec]`, runs the suite argv with its output
redirected to a file on that drive, and exits. The host then reads
the file. Three consequences, each a simplification:

- **The screen transport disappears.** The redirected file is
  CppUTest's own bytes — blank lines, tabs, everything the screen
  path taught the grammar to tolerate (P9) arrives intact, decoded
  from the guest's own code page and nothing more.
- **Readiness does not apply.** `[autoexec]` runs after DOS is up by
  construction, so there is no boot to out-wait and no readiness
  script to run.
- **Nothing is written at rest.** The mounted host directory *is*
  the work drive, so `at_rest`, remanence and the letter map stay
  reliquary's business and none of this binding's. The staged set is
  gathered host-side before any invocation, exactly as the work
  drive's content is one binding over.

The same batch shape is why `guest_session()` is refused here rather
than offered badly: no guest state survives between invocations, and
a scripted interaction exists to build on exactly that state (U10,
D27).

`setup=` commands become `[autoexec]` lines ahead of the program, so
they run in **every** invocation — the batch model's spelling of
"once per guest session", each invocation being its own guest. A
command that fails has no `exec(check=True)` channel to report
through here; what it broke surfaces in the suite's own output.

The suite is staged into a disposable work directory under
Testaferro's cache (`guests/guest-*/work`, the same layout every
binding uses — D15, and `cache.release_guest_home()` decides keep or
sweep). The guest reads it at **`D:\\`** — the same letter the
default provider's work drive takes, beside its system disk, so that
a declared address (`location="D:\\TESTS"`, a `setup=` naming
`D:\\DRIVER.COM`) moves between providers unchanged (F21, D28).
DOSBox-X's own DOS needs no system drive and nothing is mounted at
`C:`; `{location}` stays the spelling that is portable to any
provider, whatever letter it serves.

**A dosbox-x environment goes as deep as DOSBox-X does** (P2, F21).
Every declared field beside Testaferro's own words is a conf
**section** — `cpu={"cycles": "max"}`, `dosbox={"machine": "vga"}` —
and a `machine_config=` path is a whole `.conf`, DOSBox-X's own INI.
Both are carried untouched into the generated conf ahead of
`[autoexec]`, for DOSBox-X to validate; Testaferro reads none of
them and writes into none of them (P3). `[autoexec]` is the one
section Testaferro owns — the batch shape *is* that section — so a
declaration supplying its own is refused naming that, as is
`boot_image=`: DOSBox-X can `BOOT` a floppy image, but a booted DOS
runs no `[autoexec]`, and the batch shape has no way back in.
"""

from __future__ import annotations

import atexit
import collections.abc
import configparser
import os
import shutil
import subprocess
import tempfile

from . import binfmt
from . import cache
from . import cpputest
from . import placement
from .backend import Availability, GuestOutputError
from .suite import SuiteBackend


# The guest platforms this binding serves — the one thing about
# itself a binding tells resolution (P1, D11), exactly as the
# reliquary binding does.
PLATFORMS = ("dos",)

# The one drive this binding serves: the mounted work directory, at
# the letter the default provider's work drive gets (D28), so an
# address declared for one provider holds on the other.
_WORK_LETTER = "D"
# The one conf section Testaferro writes, and so the one a
# declaration may not: the batch shape is this section.
_OWN_SECTION = "autoexec"
# Where each invocation's redirected output lands, at the work
# drive's root. A `files=` entry of the same name would be
# overwritten by the first run's redirect, which is why the name is
# Testaferro-shaped rather than something a suite would stage.
_OUTPUT_NAME = "TSTFERRO.OUT"
# What a DOS program writes: the guest's own code page, every byte of
# which maps, so decoding never fails and never guesses.
_GUEST_ENCODING = "cp437"
# Seconds one guest invocation may take before it is killed.
_DEFAULT_TIMEOUT = 120

# What resolution's `provider="dosbox-x"` runs: the emulator found on
# PATH, or at the conventional Windows install locations when the
# installer did not add itself to PATH.
_EXECUTABLE = "dosbox-x"


def _windows_locations():
    """The installer's default (`C:\\DOSBox-X`), then the Program
    Files directories Windows itself names — `%PROGRAMFILES%` and,
    for a 32-bit DOSBox-X on a 64-bit host, `%PROGRAMFILES(X86)%` —
    read at lookup rather than assumed, since the system drive and
    the directories' names are both the host's to say. Only PATH is
    left off Windows, where neither variable exists."""
    locations = [r"C:\DOSBox-X\dosbox-x.exe"]
    for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        program_files = os.environ.get(variable)
        if program_files:
            candidate = os.path.join(program_files, "DOSBox-X",
                                     "dosbox-x.exe")
            if candidate not in locations:
                locations.append(candidate)
    return tuple(locations)

# Backends holding a staged guest home right now. No process outlives
# an invocation here — `subprocess.run()` waits — but a home would
# outlive an interpreter that dies between start_guest() and
# stop_guest(), so every exit path sweeps the same way the reliquary
# binding's does (P6's shape, minus the machines it exists for).
_open = set()
_sweep_registered = False


def suite_backend(exe_path, framework=cpputest, enumerator=None,
                  machine_config=None, boot_image=None, timeout=None,
                  files=(), location=None, program=None, setup=()):
    """Interrogate the referenced suite executable and return the
    backend matching its format — a DosboxXSuiteBackend for a DOS
    program. Raises FileNotFoundError for a missing file and
    ValueError for a provably non-DOS executable.

    `timeout`, `files`, `location`, `program` and `setup` are the
    same Testaferro-own words the reliquary binding takes, with the
    same nearest-speaker override rule (F4, F9).

    `machine_config` is a DOSBox-X environment: Testaferro's own
    words beside conf sections in DOSBox-X's own vocabulary, or the
    path to a whole `.conf` (F21). The sections pass through for
    DOSBox-X to validate (P3); the one refused is `[autoexec]`, which
    is Testaferro's to write. `boot_image=` is refused with the
    reason: a booted DOS runs no `[autoexec]`, so the batch shape
    could never get back in to run the suite.
    """
    exe_path = os.fspath(exe_path)
    fmt = binfmt.classify(exe_path)
    if fmt.platform != "dos":
        raise ValueError(
            f"{os.path.basename(exe_path)} is {fmt.kind} executable; "
            "only DOS guest suites are supported")
    if boot_image is not None:
        raise ValueError(
            "the dosbox-x provider takes no boot_image: a DOS booted "
            "from an image runs no [autoexec], which is the only way "
            "this binding's batch invocation has of running the suite; "
            "a boot image runs on the 'reliquary' provider")
    machine_config = _checked_machine_config(machine_config)
    return DosboxXSuiteBackend(exe_path, framework=framework,
                               enumerator=enumerator,
                               machine_config=machine_config,
                               timeout=timeout, files=files,
                               location=location, program=program,
                               setup=setup)


def guest_session(**options):
    """Refused, with the reason (U10, D27): each guest operation here
    is one DOSBox-X invocation that starts, runs and exits, so no
    guest state survives between `exec()` calls — and persistent
    state is the very thing a scripted guest interaction exists to
    build on. Relaunching per command would discard it silently,
    which is worse than saying no. The `reliquary` provider's guest
    stays up between commands and serves guest sessions.
    """
    raise ValueError(
        "the dosbox-x provider runs suites only: each guest operation "
        "is one dosbox-x invocation that starts, runs and exits, so no "
        "guest state survives between commands for a scripted "
        "interaction to build on; guest sessions run on the "
        "'reliquary' provider")


def read_document(path):
    """An authored DOSBox-X `.conf` on disk, as a declaration.

    DOSBox-X's own INI: each section becomes a field holding that
    section's keys, read with nothing interpolated, nothing
    case-folded and nothing required to have a value — the file is
    DOSBox-X's to validate, and this reads only enough of it to carry
    it (P3). Comments do not survive, exactly as a blueprint's do
    not. What is checked is what the binding refuses anyway, so a
    bad document fails at declaration rather than at the first run
    (P7).
    """
    parser = configparser.ConfigParser(interpolation=None,
                                       allow_no_value=True, strict=False)
    parser.optionxform = str
    with open(path, encoding="utf-8") as handle:
        parser.read_file(handle, source=path)
    sections = {name: dict(parser[name]) for name in parser.sections()}
    _checked_sections(sections)
    from .environments import EnvironmentSpec

    return EnvironmentSpec(sections)


def _checked_machine_config(machine_config):
    """The declaration, validated for this binding, or None.

    A dosbox-x environment declares Testaferro's own words —
    `provider`, `timeout`, `suites`, `files`, `location`, `program`,
    `setup` — its `platform`, and conf sections (F21). A field that
    is not a section, or blueprint `media` beside the machine, is
    another provider's document (P3): DOSBox-X reads none of it, and
    dropping an authored field silently would be worse than refusing
    it.
    """
    if machine_config is None:
        return None
    from .environments import _coerce_machine_config

    machine_config = _coerce_machine_config(machine_config,
                                            read=read_document)
    if machine_config.platform != "dos":
        raise ValueError(
            "this binding runs DOS guests and needs a DOS machine "
            f"config, not {machine_config.platform!r}")
    if machine_config.media:
        raise ValueError(
            "a dosbox-x environment declares conf sections; this "
            "declaration's media belong to another provider's document, "
            "which dosbox-x does not read")
    _checked_sections({name: value
                       for name, value in machine_config.fields.items()
                       if name != "platform"})
    return machine_config


def _checked_sections(sections):
    """Refuse what this binding cannot carry: a field that is not a
    section, and the one section that is Testaferro's own."""
    foreign = sorted(name for name, value in sections.items()
                     if not isinstance(value, collections.abc.Mapping))
    if foreign:
        raise ValueError(
            "a dosbox-x environment's fields are conf sections — each "
            "a mapping of that section's keys; this declaration's "
            + ", ".join(foreign)
            + " belong to another provider's document, which dosbox-x "
            "does not read")
    if _OWN_SECTION in sections:
        raise ValueError(
            f"a dosbox-x environment cannot declare [{_OWN_SECTION}]: "
            "that section is how testaferro mounts the work drive, runs "
            "the suite and exits, so it is the one section testaferro "
            "writes itself; commands to run ahead of the suite are "
            "declared as setup=")


def _sections(machine_config):
    """The declared conf sections, in declaration order, or none."""
    if machine_config is None:
        return ()
    return tuple((name, value)
                 for name, value in machine_config.fields.items()
                 if name != "platform")


def _find_executable():
    """Where DOSBox-X is, or a refusal naming where was looked.

    PATH first, then the conventional Windows install locations —
    DOSBox-X's installer does not add itself to PATH, and asking the
    tester to configure a path Testaferro can find is a poor trade
    for two well-known candidates.
    """
    found = shutil.which(_EXECUTABLE)
    if found is not None:
        return found
    locations = _windows_locations()
    for candidate in locations:
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(
        "dosbox-x was not found on PATH"
        + (" or at " + ", ".join(locations) if locations else "")
        + "; install DOSBox-X or add it to PATH to use "
        "provider='dosbox-x'")


def discover():
    """Whether DOSBox-X is on this host: the one external dependency
    this binding has, found where `_find_executable()` looks, or the
    refusal it would have raised carried as the detail instead."""
    try:
        found = _find_executable()
    except FileNotFoundError as missing:
        return (Availability(provider="dosbox-x", backend="dosbox-x",
                             available=False, detail=str(missing)),)
    return (Availability(provider="dosbox-x", backend="dosbox-x",
                         available=True, executable=found,
                         detail="found at " + found),)


def _split_address(address):
    """A guest address's drive letter and the path under it."""
    text = str(address).strip()
    if len(text) < 2 or text[1] != ":" or not text[0].isalpha():
        raise ValueError(
            f"location {address!r} does not start with a drive letter")
    return text[0].upper(), text[2:].strip("\\")


def _conf(work, commands, sections=()):
    """The conf one invocation runs: the declared sections, then
    mount, run, exit.

    Pure text, unit-testable with nothing launched (P10). The
    declared `sections` — `(name, keys)` pairs in declaration order —
    are written first and as authored, for DOSBox-X to validate
    (P3); then the `[autoexec]` section mounts the staged work
    directory as the work drive, switches to it, runs the given
    command lines in order, and exits DOSBox-X — which with `-silent`
    is the whole visible life of the invocation.
    """
    lines = []
    for name, keys in sections:
        lines.append(f"[{name}]")
        for key, value in keys.items():
            lines.append(key if value is None else f"{key}={_value(value)}")
        lines.append("")
    lines.extend([f"[{_OWN_SECTION}]",
                  "@echo off",
                  f'mount {_WORK_LETTER.lower()} "{work}"',
                  f"{_WORK_LETTER}:"])
    lines.extend(commands)
    lines.append("exit")
    return "\n".join(lines) + "\n"


def _value(value):
    """One conf value as DOSBox-X spells it. The host literal for a
    truth value (JSON's `true` in an INI, Python's `True` inline)
    becomes the conf's `true`/`false` — a spelling, not a reading,
    the same kind of exception P3 makes for hyphenated keys."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _opened(backend):
    """Record a backend whose guest home now exists."""
    global _sweep_registered
    _open.add(backend)
    if not _sweep_registered:
        atexit.register(_sweep_open)
        _sweep_registered = True


def _sweep_open():
    """Sweep every guest home still open, best effort."""
    for backend in list(_open):
        try:
            backend.stop_guest()
        except Exception:
            _open.discard(backend)


class DosboxXSuiteBackend(SuiteBackend):
    def __init__(self, exe_path, framework=cpputest, enumerator=None,
                 machine_config=None, timeout=None, files=(),
                 location=None, program=None, setup=()):
        exe_path = os.fspath(exe_path)
        SuiteBackend.__init__(self, exe_path, run=self._run_in_guest,
                              framework=framework, enumerator=enumerator)
        declaration = machine_config
        self._timeout = placement.nearest(timeout, declaration,
                                          "timeout", _DEFAULT_TIMEOUT)
        self._declared_program = placement.nearest(program, declaration,
                                                   "program")
        staged = placement.nearest(files or None, declaration,
                                   "files") or ()
        self._files = tuple(os.fspath(path) for path in staged)
        staged_setup = placement.nearest(setup or None, declaration,
                                         "setup") or ()
        self._setup = tuple(str(command) for command in staged_setup)
        self._sections = _sections(declaration)
        # The location settles at construction: there is no drive map
        # to read back, this binding serving exactly one drive. A
        # declared address naming any other letter is refused here,
        # before anything runs (P7).
        declared = placement.nearest(location, declaration, "location")
        if declared is None:
            self._subpath = ""
        else:
            letter, self._subpath = _split_address(declared)
            if letter != _WORK_LETTER:
                raise ValueError(
                    f"location {declared!r} names drive {letter}:, and "
                    f"this binding serves one drive — {_WORK_LETTER}:, "
                    "the mounted work directory")
        self._location = (f"{_WORK_LETTER}:\\{self._subpath}"
                          if self._subpath else f"{_WORK_LETTER}:\\")
        self._home = None
        self._work = None
        self._executable = None

    @property
    def location(self):
        """Where this suite's harness lands, in the guest's terms —
        the placement reported (F4), the same vocabulary a
        declaration uses. Settled at construction here: the work
        drive's letter is this binding's own constant, not a fact
        about a machine that has to exist first."""
        return self._location

    def start_guest(self):
        # Fail before any directory exists: no emulator, no session.
        executable = _find_executable()
        guests = os.path.join(cache.cache_root(), "guests")
        os.makedirs(guests, exist_ok=True)
        self._home = tempfile.mkdtemp(prefix="guest-", dir=guests)
        try:
            self._executable = executable
            self._work = os.path.join(self._home, "work")
            target = self._work
            if self._subpath:
                target = os.path.join(target,
                                      *self._subpath.split("\\"))
            os.makedirs(target)
            placement.gather(target, self._files, exe_path=self._exe)
            _opened(self)
        except BaseException:
            self.stop_guest()
            raise

    def stop_guest(self):
        if self._home is None:
            return
        _open.discard(self)
        # The same keep-or-sweep answer every guest home gets: the
        # policy is Testaferro's, not this binding's (D15), and a kept
        # home needs no retrieval pass — the work directory *is* the
        # drive, so what the run wrote is already host-side.
        cache.release_guest_home(self._home)
        self._home = None
        self._work = None
        self._executable = None

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
        command = placement.resolve_program(self._declared_program,
                                            self.location,
                                            self._exe_name())
        if args:
            command += " " + " ".join(args)
        redirected = (f"{command} > "
                      f"{_WORK_LETTER}:\\{_OUTPUT_NAME}")
        conf = os.path.join(self._home, "testaferro.conf")
        with open(conf, "w", encoding="utf-8") as handle:
            handle.write(_conf(self._work,
                               [*self._setup, redirected],
                               self._sections))
        try:
            result = subprocess.run(
                [self._executable, "-conf", conf, "-silent", "-nolog"],
                cwd=self._home, capture_output=True,
                timeout=self._timeout)
        except subprocess.TimeoutExpired:
            raise GuestOutputError(
                f"the guest did not finish within {self._timeout} "
                "seconds", argv=args) from None
        if result.returncode != 0:
            raise GuestOutputError(
                f"dosbox-x exited with status {result.returncode}",
                argv=args,
                output=result.stderr.decode(errors="replace"))
        output = os.path.join(self._work, _OUTPUT_NAME)
        if not os.path.isfile(output):
            raise GuestOutputError(
                "the guest left no output behind: nothing was "
                f"redirected to {_WORK_LETTER}:\\{_OUTPUT_NAME}",
                argv=args)
        with open(output, "rb") as handle:
            raw = handle.read()
        return raw.decode(_GUEST_ENCODING).replace("\r\n", "\n")
