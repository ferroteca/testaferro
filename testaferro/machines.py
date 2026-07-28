# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Named test-machine declarations backed by reliquary blueprints.

A declaration is reusable configuration, not a running machine: it is
the authored blueprint document reliquary materializes into a fresh
machine for every backend session. testaferro carries the authored
JSON through untouched and mirrors none of reliquary's schema —
validation happens when reliquary parses it.

Declarations come from ``configure()`` / ``testaferro.config()`` or
from an optional per-project ``testaferro.ini`` — one section per
machine, the declarative twin of ``configure()``. ``load_config()``
reads that file; the entry point searches upward from wherever it was
reached so test modules can name only the suite executable.

``select()`` is where a name becomes a declaration: the project's own
first, then the standard catalog testaferro curates (D10, and
``catalog.py``). Nothing else is consulted — never the user's
reliquary home (D6).
"""

from __future__ import annotations

import collections.abc
import configparser
import json
import os
import types

from . import catalog


CONFIG_FILENAME = "testaferro.ini"

# Path-valued options resolved relative to the config file directory.
_PATH_KEYS = frozenset({"boot_image", "machine_config", "template"})
# Blueprint fields whose INI values are JSON (not bare strings).
_JSON_KEYS = frozenset({"drives", "boot", "scripts", "media",
                        "control_planes", "backend_settings",
                        "parameters"})
_FLOAT_KEYS = frozenset({"timeout"})
# Blueprint fields whose names hyphenate: written with underscores as
# a Python keyword or an INI option, stored as the blueprint spells
# them.
_HYPHENATED = types.MappingProxyType({
    "control_planes": "control-planes",
    "backend_settings": "backend-settings",
})

# Options testaferro consumes itself rather than passing to the
# blueprint: how long one guest command may take, and which files
# this machine's guest suites are.
_TESTAFERRO_KEYS = frozenset({"timeout", "suites"})

_machines = {}
# Standard-catalog documents materialized on first use: the documents
# are authored and immutable, so one name is always one declaration.
_standard = {}
# None until the first load/search; then the absolute path or False
# when a search found no file.
_loaded_config = None


class MachineSpec:
    """One declared test machine: an authored reliquary blueprint.

    Immutable, and a template rather than a machine — the binding
    writes it into a private reliquary home and creates a fresh
    machine from it per session. Blueprint fields are readable as
    attributes (``spec.platform``, ``spec.memory``, ``spec.drives``),
    with underscores standing in for the hyphens the blueprint spells
    (``spec.backend_settings``).

    ``timeout`` and ``suites`` are testaferro's own rather than
    blueprint fields: how long one guest command may take, and the
    file-name masks saying which executables are this machine's guest
    suites — what a collection scan needs to know that a file is a
    suite at all, and which machine runs it.
    """

    __slots__ = ("_machine", "_media", "timeout", "suites")

    def __init__(self, machine, media=(), timeout=None, suites=()):
        fields = {_HYPHENATED.get(key, key): value
                  for key, value in machine.items()
                  if key not in ("type", "name")}
        fields.setdefault("platform", "dos")
        fields["platform"] = str(fields["platform"]).lower()
        object.__setattr__(self, "_machine", types.MappingProxyType(fields))
        object.__setattr__(self, "_media", tuple(dict(spec)
                                                 for spec in media))
        object.__setattr__(self, "timeout", timeout)
        object.__setattr__(self, "suites", _masks(suites))

    def __getattr__(self, name):
        try:
            return self._machine[name.replace("_", "-")]
        except KeyError:
            raise AttributeError(
                f"{type(self).__name__!r} declares no {name!r}") from None

    def __setattr__(self, name, value):
        raise AttributeError("a machine declaration is immutable")

    def __repr__(self):
        return f"MachineSpec({dict(self._machine)!r})"

    @property
    def fields(self):
        """The authored machine spec, without its type/name identity."""
        return self._machine

    @property
    def media(self):
        """Media specs authored beside the machine, if any."""
        return self._media

    def document(self, name):
        """The ``.rlqb`` document declaring this machine as ``name``."""
        machine = dict(self._machine)
        machine["type"] = "machine"
        machine["name"] = name
        return [machine, *(dict(spec) for spec in self._media)]


def configure(name, platform=None, machine_config=None, template=None,
              boot_image=None, **options):
    """Declare a named test machine and return its MachineSpec.

    ``machine_config`` (or its ``template`` spelling) accepts a
    MachineSpec, a mapping (a blueprint machine spec, or a whole
    blueprint document), or the path to a ``.rlqb``. Without one, the
    remaining options are the blueprint's own machine fields —
    ``memory``, ``drives``, ``boot`` and friends. ``platform`` is an
    optional consistency check for a supplied configuration and a
    convenient field when constructing one here.

    ``timeout`` and ``suites`` are testaferro's own rather than
    blueprint fields, so they may be said beside a complete template
    as well as beside constructed fields.
    """
    if not isinstance(name, str) or not name:
        raise ValueError("machine name must be a non-empty string")
    if name in _machines:
        raise ValueError(f"test machine {name!r} is already configured")
    if machine_config is not None and template is not None:
        raise TypeError("pass either machine_config or template, not both")
    if template is not None:
        machine_config = template
    own = {key: value for key, value in options.items()
           if key in _TESTAFERRO_KEYS}
    if machine_config is not None and (len(own) != len(options)
                                       or boot_image is not None):
        raise TypeError(
            "machine_config is a complete template; pass its options "
            "when creating the template")
    if boot_image is not None and "drives" in options:
        raise TypeError("boot_image and drives cannot be combined")

    if machine_config is None:
        fields = {key: value for key, value in options.items()
                  if key not in _TESTAFERRO_KEYS}
        # `media` is a document-level spec, not a machine field: it
        # declares media the drives refer to by name, and belongs
        # beside the machine rather than inside it.
        media = _media_specs(fields.pop("media", ()))
        if boot_image is not None:
            fields["drives"] = {"floppy0": _boot_media(boot_image)}
            fields.setdefault("boot", ["floppy0"])
        if platform is not None:
            fields["platform"] = platform
        machine_config = MachineSpec(fields, media,
                                     timeout=options.get("timeout"),
                                     suites=options.get("suites", ()))
    else:
        machine_config = _coerce_machine_config(machine_config, platform)
        if (platform is not None
                and machine_config.platform != str(platform).lower()):
            raise ValueError(
                f"machine {name!r} declares platform "
                f"{machine_config.platform!r}, not {platform!r}")
        if own:
            # A template says nothing about timeouts or which files
            # are suites, so those are said here — as a fresh spec
            # rather than a mutation, a MachineSpec being immutable
            # and often shared between names.
            machine_config = MachineSpec(
                dict(machine_config.fields), machine_config.media,
                timeout=own.get("timeout", machine_config.timeout),
                suites=own.get("suites", machine_config.suites))

    _machines[name] = machine_config
    return machine_config


def _masks(value):
    """Normalize declared ``suites`` masks to a tuple of patterns.

    One mask or several, and written either way: a list of strings,
    or one string separating them by commas or whitespace — the INI
    spelling and the natural Python one land in the same place.
    """
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(mask for mask in
                     value.replace(",", " ").split() if mask)
    return tuple(str(mask) for mask in value)


def _media_specs(value):
    """Normalize a declared ``media`` option to a list of specs.

    One spec or several: a lone mapping is the list of one, which is
    the natural thing to write for a machine needing a single named
    medium.
    """
    if isinstance(value, collections.abc.Mapping):
        return [value]
    if isinstance(value, (str, bytes)) or not isinstance(
            value, collections.abc.Iterable):
        raise TypeError(
            "media must be a blueprint media spec or a list of them")
    return list(value)


def _boot_media(boot_image):
    """The blueprint drive declaring a caller-supplied boot floppy."""
    return {
        "type": "media",
        "name": "testaferro-boot",
        "location": {"local": os.path.abspath(os.fspath(boot_image))},
        "materialize": "use",
    }


def configured():
    """The declared machine names and immutable configurations."""
    return dict(_machines)


def select(name=None, platform=None, inferred=None):
    """Select a test machine, or return None for DOS's
    zero-configuration default. Raises ValueError for absent or
    ambiguous choices.

    A **name** resolves against the project's declarations first and
    the standard catalog second (D10), so a project may declare its
    own machine under a standard name and get its own. A **platform**
    — given or inferred from the executable — matches declarations
    only: the catalog is reached by asking for it, never by falling
    into it, which is what keeps zero configuration zero (P8).
    """
    if name is not None:
        machine_config = _machines.get(name)
        if machine_config is None:
            machine_config = _standard_machine(name)
        if machine_config is None:
            raise ValueError(
                f"unknown test machine {name!r}; configured: "
                f"{_choices(_machines)}; standard: "
                f"{_choices(catalog.STANDARD)}")
        if (platform is not None
                and machine_config.platform != str(platform).lower()):
            raise ValueError(
                f"test machine {name!r} has platform "
                f"{machine_config.platform!r}, not {platform!r}")
        return name, machine_config

    wanted = platform if platform is not None else inferred
    if wanted is None:
        return None
    wanted = str(wanted).lower()
    matches = [(machine_name, machine_config)
               for machine_name, machine_config in _machines.items()
               if machine_config.platform == wanted]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(
            f"platform {wanted!r} matches multiple test machines: "
            + ", ".join(machine_name for machine_name, _ in matches))
    if not _machines and wanted == "dos":
        return None
    raise ValueError(
        f"no configured test machine for platform {wanted!r}; "
        f"configured: {_choices(_machines)}")


def _standard_machine(name):
    """The standard catalog's machine of that name, or None.

    The document is authored and never edited, so it is materialized
    once and shared: every resolution of one standard name yields the
    same immutable declaration, exactly as a declared name does.
    """
    document = catalog.STANDARD.get(name)
    if document is None:
        return None
    if name not in _standard:
        _standard[name] = _from_document(list(document))
    return _standard[name]


def load_config(path=None, *, search_from=None):
    """Load machine declarations from a local ``testaferro.ini``.

    With ``path``, read that file (a missing file is an error). With
    ``path`` omitted, search upward from ``search_from`` (default:
    the current directory) for ``testaferro.ini`` and load it when
    found; a fruitless search is a no-op and returns None.

    Each section is one test machine — the same options as
    ``configure()``. Relative ``boot_image``, ``machine_config``, and
    ``template`` paths resolve from the file's directory. Structured
    blueprint fields (``drives``, ``boot``, ``backend_settings`` and
    friends) accept JSON values. Idempotent for a repeated load of the
    same path or a repeated empty search.
    """
    global _loaded_config

    if path is not None:
        path = os.path.abspath(os.fspath(path))
        if _loaded_config == path:
            return path
        if _loaded_config is not None:
            raise RuntimeError(
                "project config already loaded"
                + (f" from {_loaded_config}"
                   if _loaded_config else " (no file found)"))
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        _load_ini(path)
        _loaded_config = path
        return path

    if _loaded_config is not None:
        return _loaded_config if _loaded_config else None

    start = os.getcwd() if search_from is None else os.fspath(search_from)
    found = _find_config(start)
    if found is None:
        _loaded_config = False
        return None
    _load_ini(found)
    _loaded_config = found
    return found


def _find_config(start):
    """Walk upward from start looking for CONFIG_FILENAME."""
    directory = os.path.abspath(start)
    if os.path.isfile(directory):
        directory = os.path.dirname(directory)
    while True:
        candidate = os.path.join(directory, CONFIG_FILENAME)
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(directory)
        if parent == directory:
            return None
        directory = parent


def _load_ini(path):
    parser = configparser.ConfigParser(interpolation=None)
    read = parser.read(path, encoding="utf-8")
    if not read:
        raise FileNotFoundError(path)
    base_dir = os.path.dirname(path)
    for name in parser.sections():
        options = _section_options(parser[name], base_dir)
        platform = options.pop("platform", None)
        configure(name, platform=platform, **options)


def _section_options(section, base_dir):
    if "machine_config" in section and "template" in section:
        raise TypeError(
            "pass either machine_config or template, not both")
    options = {}
    for key, raw in section.items():
        value = _parse_option(key, raw)
        if key in _PATH_KEYS and isinstance(value, str):
            value = _resolve_path(base_dir, value)
        options[key] = value
    return options


def _parse_option(key, raw):
    if key in _JSON_KEYS:
        return json.loads(raw)
    stripped = raw.strip()
    if key in _FLOAT_KEYS:
        return float(stripped)
    # Sizes are written either way — `memory = 32` and `memory = 32M`
    # are both blueprint-legal, so a bare integer stays an integer and
    # anything else passes through as authored.
    if stripped.lstrip("-").isdigit():
        return int(stripped, 10)
    # Allow JSON for any value that looks like a structured literal, so
    # future blueprint fields stay expressible without a parser change.
    if stripped[:1] in "[{":
        return json.loads(stripped)
    return raw


def _resolve_path(base_dir, value):
    if os.path.isabs(value):
        return value
    return os.path.abspath(os.path.join(base_dir, value))


def _coerce_machine_config(value, platform=None):
    if isinstance(value, MachineSpec):
        return value
    if isinstance(value, collections.abc.Mapping):
        return _from_document(value, platform)
    if isinstance(value, (str, os.PathLike)):
        # The .rlqb dialect (comments, trailing commas): a declaration
        # is authored blueprint JSON, so it is read the way reliquary
        # reads it. Imported here rather than at module scope so that
        # importing this module stays stdlib-cheap — the plugin
        # auto-loads into every pytest run, and a run that claims no
        # guest suite must not pay for reliquary.
        from reliquary import jsonc

        path = os.fspath(value)
        with open(path, encoding="utf-8") as handle:
            document = jsonc.load(handle)
        return _from_document(document, platform)
    if isinstance(value, collections.abc.Sequence):
        return _from_document(list(value), platform)
    raise TypeError(
        "machine_config must be a MachineSpec, a blueprint mapping, "
        "a blueprint document, or a path to one")


def _from_document(document, platform=None):
    """Build a declaration from an authored blueprint or machine spec.

    A ``.rlqb`` document is a list of specs; a lone spec object is the
    document of one, which is also how a bare machine spec arrives from
    ``configure()``. Exactly one machine must be present — a
    declaration names one test machine.
    """
    specs = document if isinstance(document, list) else [document]
    machines = [spec for spec in specs
                if isinstance(spec, collections.abc.Mapping)
                and spec.get("type", "media") == "machine"]
    media = [spec for spec in specs
             if isinstance(spec, collections.abc.Mapping)
             and spec.get("type", "media") != "machine"]
    if not machines and len(specs) == 1 and isinstance(
            specs[0], collections.abc.Mapping):
        # A bare machine spec, written without its `type` — the form
        # configure() itself builds and the natural one to hand-write.
        machines, media = [specs[0]], []
    if len(machines) != 1:
        raise ValueError(
            f"a machine declaration needs exactly one machine spec, "
            f"found {len(machines)}")
    fields = dict(machines[0])
    if platform is not None and "platform" not in fields:
        fields["platform"] = platform
    return MachineSpec(fields, media)


def _choices(values):
    return ", ".join(values) if values else "(none)"


def _clear_for_tests():
    """Clear declarations; private support for isolated unit tests."""
    global _loaded_config
    _machines.clear()
    _loaded_config = None
