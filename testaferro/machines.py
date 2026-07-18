# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""Named test-machine declarations backed by relict configurations.

A declaration is reusable configuration, not a running machine. The
selected binding materializes it into a fresh relict home for every
backend session.
"""

from __future__ import annotations

import collections.abc
import json
import os

import relict


_machines = {}


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
    _machines.clear()
