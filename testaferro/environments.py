# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Named test-environment declarations backed by reliquary blueprints.

A **test environment** is what a suite runs in, and naming one is the
whole of what a suite-facing consumer writes (P2): a standard
environment testaferro authors and names, or a custom one declared
here. A declaration is reusable configuration, not a running guest: it
is the authored blueprint document reliquary materializes afresh for
every backend session. testaferro carries the authored JSON through
untouched and mirrors none of reliquary's schema — validation happens
when reliquary parses it, and ``platform`` is one of the fields
passing through rather than a word testaferro speaks (P3).

``provider`` runs the other way: it is the one guest-related word
testaferro *does* speak, naming what actually runs the suite
(``reliquary`` today, the default and the only one built), and the
environment is the one place it is named (P1, P2, D11). So it never
reaches the blueprint — reliquary's document has no field for who is
reading it.

Declarations come from ``configure()`` / ``testaferro.config()`` or
from an optional per-project ``testaferro.ini`` — one section per
environment, the declarative twin of ``configure()``. ``load_config()``
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
# blueprint: which provider runs this environment, how long one guest
# command may take, and which files this environment's guest suites
# are. `provider` is testaferro's own word and reliquary's document
# has no field for it, which is exactly why it belongs here rather
# than passing through (P1, P3, D11).
_TESTAFERRO_KEYS = frozenset({"provider", "timeout", "suites"})

_environments = {}
# Standard-catalog documents materialized on first use: the documents
# are authored and immutable, so one name is always one declaration.
_standard = {}
# None until the first load/search; then the absolute path or False
# when a search found no file.
_loaded_config = None


class EnvironmentSpec:
    """One declared test environment: an authored reliquary blueprint.

    Immutable, and a template rather than a running guest — the
    binding writes it into a private reliquary home and creates a
    fresh machine from it per session. Blueprint fields are readable
    as attributes (``spec.platform``, ``spec.memory``,
    ``spec.drives``), with underscores standing in for the hyphens the
    blueprint spells (``spec.backend_settings``).

    ``provider``, ``timeout`` and ``suites`` are testaferro's own
    rather than blueprint fields: which provider runs this environment
    (``None`` until one is named, the default being resolution's to
    apply), how long one guest command may take, and the file-name
    masks saying which executables are this environment's guest
    suites — what a collection scan needs to know that a file is a
    suite at all, and which environment runs it.
    """

    __slots__ = ("_fields", "_media", "provider", "timeout", "suites")

    def __init__(self, machine, media=(), timeout=None, suites=(),
                 provider=None):
        fields = {_HYPHENATED.get(key, key): value
                  for key, value in machine.items()
                  if key not in ("type", "name")}
        fields.setdefault("platform", "dos")
        fields["platform"] = str(fields["platform"]).lower()
        object.__setattr__(self, "_fields", types.MappingProxyType(fields))
        object.__setattr__(self, "_media", tuple(dict(spec)
                                                 for spec in media))
        object.__setattr__(self, "provider", _provider(provider))
        object.__setattr__(self, "timeout", timeout)
        object.__setattr__(self, "suites", _masks(suites))

    def __getattr__(self, name):
        try:
            return self._fields[name.replace("_", "-")]
        except KeyError:
            raise AttributeError(
                f"{type(self).__name__!r} declares no {name!r}") from None

    def __setattr__(self, name, value):
        raise AttributeError("an environment declaration is immutable")

    def __repr__(self):
        return f"EnvironmentSpec({dict(self._fields)!r})"

    @property
    def fields(self):
        """The authored machine spec, without its type/name identity."""
        return self._fields

    @property
    def media(self):
        """Media specs authored beside the machine, if any."""
        return self._media

    def document(self, name):
        """The ``.rlqb`` document declaring this machine as ``name``."""
        machine = dict(self._fields)
        machine["type"] = "machine"
        machine["name"] = name
        return [machine, *(dict(spec) for spec in self._media)]


def configure(name, machine_config=None, template=None, boot_image=None,
              **options):
    """Declare a named test environment and return its EnvironmentSpec.

    ``machine_config`` (or its ``template`` spelling) accepts an
    EnvironmentSpec, a mapping (a blueprint machine spec, or a whole
    blueprint document), or the path to a ``.rlqb``. Without one, the
    remaining options are the blueprint's own machine fields —
    ``platform``, ``memory``, ``drives``, ``boot`` and friends — which
    pass through untouched for reliquary to validate (P3).

    ``provider`` names what actually runs this environment's guests —
    ``reliquary`` today, the default and the only one built (P1, D11).
    It, ``timeout`` and ``suites`` are testaferro's own rather than
    blueprint fields, so they may be said beside a complete template
    as well as beside constructed fields.
    """
    if not isinstance(name, str) or not name:
        raise ValueError("environment name must be a non-empty string")
    if name in _environments:
        raise ValueError(f"test environment {name!r} is already configured")
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
        machine_config = EnvironmentSpec(fields, media,
                                         timeout=options.get("timeout"),
                                         suites=options.get("suites", ()),
                                         provider=options.get("provider"))
    else:
        machine_config = _coerce_machine_config(machine_config)
        if own:
            # A template is the provider's own document, so it says
            # nothing about which provider reads it, about timeouts, or
            # about which files are suites: those are said here — as a
            # fresh spec rather than a mutation, an EnvironmentSpec
            # being immutable and often shared between names.
            machine_config = EnvironmentSpec(
                dict(machine_config.fields), machine_config.media,
                timeout=own.get("timeout", machine_config.timeout),
                suites=own.get("suites", machine_config.suites),
                provider=own.get("provider", machine_config.provider))

    _environments[name] = machine_config
    return machine_config


def _provider(value):
    """Normalize a declared ``provider`` name, or None when unsaid.

    Case-folding here is testaferro's own vocabulary being tidied, not
    a provider's document being touched (P3): ``provider`` is a word
    this project defines and reliquary's blueprint has no field for.
    Unsaid stays None — which provider a nameless environment gets is
    resolution's answer, said in one place rather than defaulted here
    and again there.
    """
    if value is None:
        return None
    return str(value).strip().lower()


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
    the natural thing to write for an environment needing a single
    named medium.
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
    """The declared environment names and immutable configurations."""
    return dict(_environments)


def select(name=None, inferred=None):
    """Select a test environment, or return None for DOS's
    zero-configuration default. Raises ValueError for absent or
    ambiguous choices.

    A **name** resolves against the project's declarations first and
    the standard catalog second (D10), so a project may declare its
    own environment under a standard name and get its own. With no
    name, the platform ``inferred`` from the executable's own format
    matches declarations only: the catalog is reached by asking for
    it, never by falling into it, which is what keeps zero
    configuration zero (P8).
    """
    if name is not None:
        declared = _environments.get(name)
        if declared is None:
            declared = _standard_environment(name)
        if declared is None:
            raise ValueError(
                f"unknown test environment {name!r}; configured: "
                f"{_choices(_environments)}; standard: "
                f"{_choices(catalog.STANDARD)}")
        return name, declared

    if inferred is None:
        return None
    wanted = str(inferred).lower()
    matches = [(declared_name, declared)
               for declared_name, declared in _environments.items()
               if declared.platform == wanted]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(
            f"more than one configured test environment runs {wanted} "
            "executables: "
            + ", ".join(declared_name for declared_name, _ in matches)
            + "; name the one this suite wants")
    if not _environments and wanted == "dos":
        return None
    raise ValueError(
        f"no configured test environment runs {wanted} executables; "
        f"configured: {_choices(_environments)}")


def _standard_environment(name):
    """The standard catalog's environment of that name, or None.

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
    """Load environment declarations from a local ``testaferro.ini``.

    With ``path``, read that file (a missing file is an error). With
    ``path`` omitted, search upward from ``search_from`` (default:
    the current directory) for ``testaferro.ini`` and load it when
    found; a fruitless search is a no-op and returns None.

    Each section is one test environment — the same options as
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
        configure(name, **_section_options(parser[name], base_dir))


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


def _coerce_machine_config(value):
    if isinstance(value, EnvironmentSpec):
        return value
    if isinstance(value, collections.abc.Mapping):
        return _from_document(value)
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
        return _from_document(document)
    if isinstance(value, collections.abc.Sequence):
        return _from_document(list(value))
    raise TypeError(
        "machine_config must be an EnvironmentSpec, a blueprint "
        "mapping, a blueprint document, or a path to one")


def _from_document(document):
    """Build a declaration from an authored blueprint or machine spec.

    A ``.rlqb`` document is a list of specs; a lone spec object is the
    document of one, which is also how a bare machine spec arrives from
    ``configure()``. Exactly one machine must be present — a
    declaration names one test environment.
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
            f"an environment declaration needs exactly one machine "
            f"spec, found {len(machines)}")
    return EnvironmentSpec(dict(machines[0]), media)


def _choices(values):
    return ", ".join(values) if values else "(none)"


def _clear_for_tests():
    """Clear declarations; private support for isolated unit tests."""
    global _loaded_config
    _environments.clear()
    _loaded_config = None
