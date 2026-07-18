# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Named test-machine declarations backed by relict configurations.

A declaration is reusable configuration, not a running machine. The
selected binding materializes it into a fresh relict home for every
backend session.

Declarations come from ``configure()`` / ``testaferro.config()`` or
from an optional per-project ``testaferro.ini`` — one section per
machine, the declarative twin of ``configure()``. ``load_config()``
reads that file; ``guest_suite()`` searches upward from the call site
so test modules can name only the suite executable.
"""

from __future__ import annotations

import collections.abc
import configparser
import json
import os

import relict


CONFIG_FILENAME = "testaferro.ini"

# Path-valued options resolved relative to the config file directory.
_PATH_KEYS = frozenset({"boot_image", "machine_config", "template"})
# MachineConfig fields whose INI values are JSON (not bare strings).
_JSON_KEYS = frozenset({"drives", "qemu_args", "machine"})
_INT_KEYS = frozenset({"memory"})
_FLOAT_KEYS = frozenset({"timeout"})

_machines = {}
# None until the first load/search; then the absolute path or False
# when a search found no file.
_loaded_config = None


def configure(name, platform=None, machine_config=None, template=None,
              boot_image=None, **options):
    """Declare a named test machine and return its MachineConfig.

    ``machine_config`` (or its ``template`` spelling) accepts the same
    relict forms as its one-shot helpers: a MachineConfig, a versioned
    mapping, or a machine-document path. Without one, the remaining
    options are passed to ``relict.MachineConfig``. ``platform`` is an
    optional consistency check for a supplied configuration and a
    convenient field when constructing one here.
    """
    if not isinstance(name, str) or not name:
        raise ValueError("machine name must be a non-empty string")
    if name in _machines:
        raise ValueError(f"test machine {name!r} is already configured")
    if machine_config is not None and template is not None:
        raise TypeError("pass either machine_config or template, not both")
    if template is not None:
        machine_config = template
    if machine_config is not None and (options or boot_image is not None):
        raise TypeError(
            "machine_config is a complete template; pass its options "
            "when creating the template")
    if boot_image is not None and "drives" in options:
        raise TypeError("boot_image and drives cannot be combined")

    if machine_config is None:
        fields = dict(options)
        if boot_image is not None:
            fields["drives"] = {"floppy": os.fspath(boot_image)}
        if platform is not None:
            fields["platform"] = platform
        machine_config = relict.MachineConfig(**fields)
    else:
        machine_config = _coerce_machine_config(machine_config, platform)
        if (platform is not None
                and machine_config.platform != str(platform).lower()):
            raise ValueError(
                f"machine {name!r} declares platform "
                f"{machine_config.platform!r}, not {platform!r}")

    _machines[name] = machine_config
    return machine_config


def configured():
    """The declared machine names and immutable configurations."""
    return dict(_machines)


def select(name=None, platform=None, inferred=None):
    """Select a declared test machine, or return None for DOS's
    zero-configuration default. Raises ValueError for absent or
    ambiguous choices.
    """
    if name is not None:
        try:
            machine_config = _machines[name]
        except KeyError:
            raise ValueError(
                f"unknown test machine {name!r}; configured: "
                + _choices(_machines)) from None
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


def load_config(path=None, *, search_from=None):
    """Load machine declarations from a local ``testaferro.ini``.

    With ``path``, read that file (a missing file is an error). With
    ``path`` omitted, search upward from ``search_from`` (default:
    the current directory) for ``testaferro.ini`` and load it when
    found; a fruitless search is a no-op and returns None.

    Each section is one test machine — the same options as
    ``configure()``. Relative ``boot_image``, ``machine_config``, and
    ``template`` paths resolve from the file's directory. Structured
    ``MachineConfig`` fields (``drives``, ``qemu_args``, ``machine``)
    accept JSON values. Idempotent for a repeated load of the same
    path or a repeated empty search.
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
    if key in _INT_KEYS:
        return int(stripped, 10)
    if key in _FLOAT_KEYS:
        return float(stripped)
    # Allow JSON for any value that looks like a structured literal,
    # so future MachineConfig fields stay expressible without a
    # parser change.
    if stripped[:1] in "[{":
        return json.loads(stripped)
    return raw


def _resolve_path(base_dir, value):
    if os.path.isabs(value):
        return value
    return os.path.abspath(os.path.join(base_dir, value))


def _coerce_machine_config(value, platform=None):
    if isinstance(value, relict.MachineConfig):
        return value
    if isinstance(value, collections.abc.Mapping):
        overrides = ({"platform": platform}
                     if platform is not None and "platform" not in value
                     else {})
        return relict.MachineConfig.from_mapping(value, **overrides)
    if isinstance(value, (str, os.PathLike)):
        path = os.fspath(value)
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
        overrides = ({"platform": platform}
                     if platform is not None
                     and "platform" not in document else {})
        return relict.MachineConfig.from_file(path, **overrides)
    raise TypeError(
        "machine_config must be a relict.MachineConfig, mapping, or path")


def _choices(values):
    return ", ".join(values) if values else "(none)"


def _clear_for_tests():
    """Clear declarations; private support for isolated unit tests."""
    global _loaded_config
    _machines.clear()
    _loaded_config = None
