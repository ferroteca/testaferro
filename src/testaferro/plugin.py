# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""The pytest collection plugin: a guest suite is a file pytest
collects.

`pytest tests/SUITE.EXE` is a standard pytest execution — no wrapper,
no second executable, no second reporter to diverge from the real one
(D9). This plugin claims the executable and turns each test inside it
into an item under that file's node:

    tests/SUITE.EXE::Vring-Wraps

The plugin **auto-loads** through a `pytest11` entry point, so it
works the moment the distribution is installed (D13). What makes
installation-is-activation safe is the claiming policy rather than
the plugin being off:

- **A file named on the command line is always claimed** when
  classification or a declaration says a guest runs it. Naming a file
  says what was meant, so nothing else has to be inferred.
- **A tree scan claims only what was opted in** — a mask in pytest's
  own ini (`testaferro-suites`), or the `suites` masks of an
  environment declared in `testaferro.ini`. Landing in a venv
  therefore changes no existing run: with nothing opted in, a scan
  claims nothing.
- **A host-runnable format is claimed only by declaration.** The host
  build of a suite is a program this machine can run; inference
  cannot know that the situation demands a VM, so only the tester
  saying so claims it.
- **A headerless image is never claimed from a scan.** `.com`-style
  raw code carries nothing to prove (P7), and a scan that guessed
  would be claiming arbitrary files.

Options and ini keys are the declaration vocabulary in kebab-case,
one option per key (P16). The exceptions are the exploration-only
options, which concern trying a suite out rather than defining
tests: `--testaferro-keep-guest-home` preserves what the guest was
given, and enumerate-and-stop is pytest's own `--collect-only`.

**Enumeration prefers a host-built twin**
(`--testaferro-enumerator`), because reading the list out of the
guest costs a boot per suite — multiplied by every xdist worker,
which is the twin's whole case (U5) — and a long list can lose its
head to the guest's screen. A guest-read list therefore says it may
be short rather than passing itself off as complete (U4).
"""

from __future__ import annotations

import fnmatch
import os
import pathlib
import subprocess
import warnings

import pytest

from . import binfmt
from . import cache
from . import cpputest
from . import environments
from .backend import GuestOutputError
from .facade import ResultBroker
from .items import failure_text, guest_output_text, item_id
from .resolution import resolve_backend


class GuestEnumerationWarning(UserWarning):
    """A suite's test list came out of the guest, so it may be short.

    Raised rather than swallowed because a trial that silently shows
    fewer tests than exist is worse than a noisy one (U4). Filter it
    to accept the doubt, or declare a host-built twin to remove it.
    """


class GuestTestFailure(Exception):
    """A guest test failed, carrying the guest's own report. Never
    shown as a traceback: see GuestTestItem.repr_failure."""


# The declaration vocabulary, kebab-cased. Each name is both
# `--testaferro-<name>` and the ini key `testaferro-<name>`, declared
# from one list so the two spellings cannot drift (P16).
_SETTINGS = (
    ("environment", "name of the test environment claimed suites run "
                    "in"),
    ("provider", "name of the provider that runs claimed suites; a "
                 "named environment carries its own"),
    ("boot-image", "boot image for the zero-configuration environment"),
    ("machine-config", "path to a machine document (.rlqb) claimed "
                       "suites run on"),
    ("enumerator", "host-built twin that enumerates a suite, as a "
                   "path template: build/host/{stem}.exe"),
    ("timeout", "seconds one guest command may take before the "
                "provider gives up"),
    ("files", "host files staged into the guest beside the suite, "
              "comma-separated"),
    ("location", "guest address the suite is staged at: D:\\TESTS"),
    ("program", "guest address of what to run there; {location} "
                "stands for the staged location"),
)
# Settings naming a file, resolved from the rootdir when relative.
_PATH_SETTINGS = frozenset({"boot-image", "machine-config"})
# Settings naming several files, each resolved the same way.
_PATH_LIST_SETTINGS = frozenset({"files"})
# Settings the binding wants as a number rather than as text.
_FLOAT_SETTINGS = frozenset({"timeout"})

# What DOS itself executes by name: COMMAND.COM runs .COM and .EXE
# images. It is the only evidence available about a file whose
# content proves nothing — and the reason pytest's own test modules,
# which prove nothing either, are not mistaken for guest programs.
_EXECUTABLE_SUFFIXES = frozenset({".com", ".exe"})

# Suites holding a running execution guest right now, stopped when
# the pytest session ends (pytest_sessionfinish).
_live = []


def pytest_addoption(parser):
    group = parser.getgroup("testaferro", "guest test suites")
    for name, help_text in _SETTINGS:
        group.addoption(f"--testaferro-{name}", dest=_dest(name),
                        default=None, metavar=name.upper(),
                        help=help_text)
        parser.addini(f"testaferro-{name}", help_text, default=None)
    group.addoption("--testaferro-keep-guest-home",
                    dest="testaferro_keep_guest_home",
                    action="store_true", default=False,
                    help="keep each guest session's home for "
                         "inspection instead of sweeping it")
    suites_help = ("file-name masks a tree scan claims as guest "
                   "suites")
    group.addoption("--testaferro-suites", dest="testaferro_suites",
                    action="append", default=[], metavar="MASK",
                    help=suites_help + "; repeatable, and one value "
                         "may list several")
    parser.addini("testaferro-suites", suites_help, type="args",
                  default=[])


def pytest_configure(config):
    # Declarations first: a testaferro.ini beside the project selects
    # the same environment embedding would (U4), and anchoring the
    # search at the rootdir rather than at each collected file keeps
    # every xdist worker's answer the same (U5).
    environments.load_config(search_from=str(config.rootpath))
    if config.getoption("testaferro_keep_guest_home", False):
        cache.keep_guest_homes(True)


def pytest_collect_file(file_path, parent):
    if not _claimed(parent.config, file_path):
        return None
    return GuestSuiteFile.from_parent(parent, path=file_path)


def pytest_sessionfinish(session, exitstatus):
    """Stop every execution guest this run started. (The hook's own
    name is pytest's session, not ours — which is the collision D15
    is about.)

    At session finish rather than through `config.add_cleanup`,
    because config cleanups run *after* the terminal summary: a guest
    home kept for inspection would then be reported before the guest
    that made it had even been stopped, and the most interesting one
    would be missing from the list entirely. One backend failing to
    stop must not strand the others; the binding's own atexit failsafe
    is what still covers a machine left running.
    """
    while _live:
        try:
            _live.pop().backend.stop_guest()
        except Exception:
            pass


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    homes = cache.kept_guest_homes()
    if not homes:
        return
    terminalreporter.write_sep("-", "testaferro guest homes kept")
    for home in homes:
        terminalreporter.write_line(home)


class GuestSuiteFile(pytest.File):
    """One suite executable, and the guest tests inside it."""

    def collect(self):
        backend = _backend_for(self.config, self.path)
        twin = _twin_for(self.config, self.path)
        # Enumeration is the first contact with the guest, so it is
        # where a broken setup shows up — and a collector says so
        # through CollectError rather than by letting an exception
        # escape, which would print Testaferro's own frames for
        # something that went wrong somewhere else entirely.
        try:
            if twin is None:
                # No twin: the list has to be read out of the guest,
                # which is a boot, and a boot is what the twin exists
                # to avoid.
                try:
                    backend.start_guest()
                    ids = list(backend.list_tests())
                finally:
                    backend.stop_guest()
                # Plain ASCII on purpose: this lands on a terminal, and
                # the guest side of this project is a console world.
                warnings.warn(
                    f"{self.path.name}: test list read inside the guest, "
                    "so it may be short - a long list can lose its head "
                    "to the guest's screen. Declare a host-built twin "
                    "with --testaferro-enumerator (or "
                    "testaferro-enumerator) for a faithful list.",
                    GuestEnumerationWarning)
            else:
                ids = list(backend.list_tests())
        except GuestOutputError as error:
            raise pytest.Collector.CollectError(
                guest_output_text(error)) from None
        except RuntimeError as error:
            # The host-built twin's own refusals, which arrive already
            # said in full — it is a host program, so there is no guest
            # screen to show.
            raise pytest.Collector.CollectError(str(error)) from None
        suite = _Suite(backend, ResultBroker(backend, ids))
        for test_id in ids:
            yield GuestTestItem.from_parent(
                self, name=item_id(test_id), test_id=test_id, suite=suite)


class GuestTestItem(pytest.Item):
    """One guest test, as a pytest item under its executable."""

    def __init__(self, *, test_id, suite, **kwargs):
        super().__init__(**kwargs)
        self._test_id = test_id
        self._suite = suite
        self._outcome = None

    def runtest(self):
        self._suite.start_execution()
        try:
            outcome = self._suite.broker.outcome(self._test_id,
                                                 self._selected())
        except LookupError as error:
            raise GuestTestFailure(str(error)) from None
        except GuestOutputError as error:
            raise GuestTestFailure(guest_output_text(error)) from None
        self._outcome = outcome
        if not outcome.passed:
            raise GuestTestFailure(failure_text(outcome))

    def repr_failure(self, excinfo, style=None):
        """The guest's own report, not a traceback into Testaferro."""
        if isinstance(excinfo.value, GuestTestFailure):
            return str(excinfo.value)
        return super().repr_failure(excinfo, style=style)

    def reportinfo(self):
        """Where this item is. The guest's source when the guest named
        a file that is really there beside the executable, and the
        executable itself otherwise — never a location invented to
        fill the field."""
        outcome = self._outcome
        if outcome is not None and outcome.file:
            source = self.path.parent / outcome.file
            if source.is_file():
                return source, max(outcome.line - 1, 0), self.name
        return self.path, None, self.name

    def _selected(self):
        """This suite's test ids that survived pytest's selection."""
        return [item._test_id for item in self.session.items
                if isinstance(item, GuestTestItem)
                and item._suite is self._suite]


class _Suite:
    """One executable's backend and broker, shared by its items, with
    the execution guest started lazily by the first item that runs and
    stopped when the pytest session ends."""

    def __init__(self, backend, broker):
        self.backend = backend
        self.broker = broker
        self._started = False

    def start_execution(self):
        if self._started:
            return
        try:
            self.backend.start_guest()
        except BaseException:
            self.backend.stop_guest()
            raise
        _live.append(self)
        self._started = True


def _claimed(config, path):
    """Whether this file is a guest suite Testaferro should collect.

    The claiming policy, in one place. Its load-bearing distinction is
    that `binfmt`'s "dos" verdict has two very different strengths: a
    plain MZ header *proves* a DOS program, while a headerless file
    only says nothing proves otherwise — which is equally true of a
    test module, a README, and every other file pytest walks past. So
    proof claims a file, and the absence of proof never does on its
    own.
    """
    named = _named_on_command_line(config, path)
    if not named and not _opted_in(config, path.name):
        return False
    try:
        fmt = binfmt.classify(path)
    except OSError:
        return False
    if fmt is binfmt.HEADERLESS:
        # Nothing in the content to go on, so the name is all there
        # is. A scan never guesses from it; a file someone named is
        # claimed when it is called what DOS itself would execute, or
        # when a declaration says outright that a guest runs it.
        return named and (_told(config, path.name)
                          or path.suffix.lower() in _EXECUTABLE_SUFFIXES)
    if fmt.platform is not None:
        return True
    # A format no guest claims — the host build of the suite, most
    # likely. Only the tester saying which guest runs it makes it ours.
    return _told(config, path.name)


def _told(config, filename):
    """Whether the tester said outright that a guest runs this file,
    rather than leaving it to be inferred."""
    return (_declared_environment(filename) is not None
            or _setting(config, "environment") is not None)


def _opted_in(config, filename):
    """Whether a tree scan was told this file is a guest suite."""
    return (_matches(filename, _suite_masks(config))
            or _declared_environment(filename) is not None)


def _suite_masks(config):
    """Every mask opted in for this run: the command line's and the
    ini's together, since a mask names files rather than choosing
    between them — a trial adding one on the command line keeps what
    the project already declared."""
    masks = []
    for value in config.getoption("testaferro_suites", []) or []:
        masks.extend(environments._masks(value))
    masks.extend(config.getini("testaferro-suites") or [])
    return masks


def _named_on_command_line(config, path):
    """Whether this exact file is one of the arguments pytest was
    given, node-id selectors and all."""
    invocation = config.invocation_params
    for arg in invocation.args:
        candidate = str(arg).split("::", 1)[0]
        if not candidate or candidate.startswith("-"):
            continue
        try:
            if os.path.samefile(
                    os.path.join(str(invocation.dir), candidate),
                    str(path)):
                return True
        except OSError:
            continue
    return False


def _declared_environment(filename):
    """The declared environment whose `suites` masks claim this file
    name, or None. Two environments claiming one file is ambiguous
    rather than first-wins: the tester has to say which."""
    matches = [name for name, spec in environments.configured().items()
               if _matches(filename, spec.suites)]
    if len(matches) > 1:
        raise pytest.UsageError(
            f"{filename} is claimed by more than one test environment: "
            + ", ".join(sorted(matches)))
    return matches[0] if matches else None


def _matches(filename, masks):
    """Mask matching, case-insensitively on every host: a DOS file
    name does not distinguish case, and a project checked in must
    collect the same suites wherever it is cloned."""
    name = filename.lower()
    return any(fnmatch.fnmatchcase(name, str(mask).lower())
               for mask in masks)


def _backend_for(config, path):
    """Resolve one claimed executable to its backend, through the same
    seam the embedding API uses."""
    options = {}
    for name in _PATH_SETTINGS:
        value = _setting(config, name)
        if value is not None:
            options[name.replace("-", "_")] = _rooted(config, value)
    for name in _FLOAT_SETTINGS:
        value = _setting(config, name)
        if value is not None:
            try:
                options[name.replace("-", "_")] = float(value)
            except (TypeError, ValueError):
                raise pytest.UsageError(
                    f"--testaferro-{name} takes a number of seconds, "
                    f"not {value!r}") from None
    for name in _PATH_LIST_SETTINGS:
        value = _setting(config, name)
        if value is not None:
            options[name.replace("-", "_")] = tuple(
                _rooted(config, part.strip())
                for part in str(value).split(",") if part.strip())
    # Guest addresses, passed through as written: what a valid one is
    # belongs to the guest platform, and Testaferro never rewrites a
    # host path into one (P17).
    for name in ("location", "program"):
        value = _setting(config, name)
        if value is not None:
            options[name] = value
    twin = _twin_for(config, path)
    if twin is not None:
        options["enumerator"] = _twin_enumerator(twin)
    return resolve_backend(
        str(path),
        # The command line beats the file it is run against: a
        # declaration claims a file, an option claims this run.
        environment=(_setting(config, "environment")
                     or _declared_environment(path.name)),
        # Only for suites no environment claimed: an environment names
        # its own provider, and resolution refuses the pair rather than
        # letting an option overrule a declaration it did not read.
        provider=_setting(config, "provider"),
        search_from=str(config.rootpath), **options)


def _twin_for(config, path):
    """The host-built twin enumerating this suite, or None.

    The template names where a suite's twin lives — `{stem}` and
    `{name}` stand for the executable's own — so one setting serves a
    whole tree. A template that resolves to nothing falls back to the
    guest rather than failing: not every suite in a tree need have a
    twin built.
    """
    template = _setting(config, "enumerator")
    if not template:
        return None
    twin = pathlib.Path(_rooted(
        config, template.format(stem=path.stem, name=path.name)))
    return twin if twin.is_file() else None


def _twin_enumerator(twin):
    """Enumerate by running the host-built twin here, on the host.

    The twin is the same suite built for this machine, so it answers
    the framework's own list argv with the same list — no guest, no
    boot, and nothing that a screenful of output can truncate.
    """
    def enumerate_tests():
        completed = subprocess.run(
            [str(twin), *cpputest.list_argv()],
            capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(
                f"host-built twin {twin} failed to enumerate "
                f"(exit {completed.returncode}): "
                f"{completed.stderr.strip() or completed.stdout.strip()}")
        try:
            return cpputest.parse_list(completed.stdout)
        except ValueError as error:
            raise RuntimeError(
                f"host-built twin {twin} did not print a test list: "
                f"{error}\nWhat it printed:\n{completed.stdout.strip()}"
            ) from None

    return enumerate_tests


def _setting(config, name):
    """One setting's value: the command line first, then pytest's ini,
    then nothing. Both spellings are the same setting (P16)."""
    value = config.getoption(_dest(name), None)
    if value is not None:
        return value
    return config.getini(f"testaferro-{name}") or None


def _rooted(config, value):
    """A setting naming a file resolves from the rootdir when it is
    relative, so one ini serves every directory pytest is run from."""
    if os.path.isabs(value):
        return value
    return os.path.join(str(config.rootpath), value)


def _dest(name):
    return "testaferro_" + name.replace("-", "_")
