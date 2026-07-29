# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""The contract between guest-OS runners and the harnesses that
drive them.

A *runner* package (one per guest OS family) exports a runner class
implementing the `Runner` protocol. Constructing it with a config —
an instance of that runner's config type — yields a *test machine*:
an object that can provision its bootable environment and run guest
programs in it. Callers hold and name machines; runners own
emulation, guest control, and completion detection.

This spec *defines* the supported platforms: `PLATFORMS` maps each
platform name to its config type, and a runner's `platform` must
come from it. Configs form a three-level extension chain:

- `RunnerConfig` — options every runner understands (a ready boot
  image, a run timeout);
- a platform config extends it (`DosConfig`; the platform set grows
  only by spec releases);
- each runner's own config type extends its platform's with the
  runner's private knobs.

The division of labor this contract encodes: the caller owns
durable caching, per-run home staging, sessions, and parallelism;
the runner owns emulation, guest control, completion detection, and
all in-guest mechanics. A machine carries configuration only —
never per-run state, which lives in the explicitly passed home
directory — so one machine may serve concurrent runs.

Conformance is declared explicitly: implement the protocol, extend
the config types, and run the checks in
`testaferro_runner_api.conformance` from the runner's own test
suite. Everything here is standard-library only.
"""

from __future__ import annotations

import dataclasses
from typing import Dict, Optional, Protocol, Type, runtime_checkable

#: A machine's boot image lives under this name inside a dist
#: directory, whatever its media type (floppy, hard disk, CD) or
#: container format. Callers cache and stage the file without
#: knowing its kind; only the runner knows how to boot it.
BOOT_IMAGE_NAME = "boot.img"

#: The directory inside a run home that holds the boot image:
#: `run()` boots `<home>/<DIST_DIR_NAME>/<BOOT_IMAGE_NAME>`, which
#: the caller stages before the run.
DIST_DIR_NAME = "dist"


@dataclasses.dataclass(frozen=True)
class RunnerConfig:
    """Options every runner understands.

    `boot_image` is the path of a ready boot image to use as-is, in
    place of whatever the runner would download or build. `timeout`
    is the seconds allowed for one guest run; None means the
    runner's default.
    """

    boot_image: Optional[str] = None
    timeout: Optional[float] = None


@dataclasses.dataclass(frozen=True)
class DosConfig(RunnerConfig):
    """The dos platform's config: nothing beyond the generic
    options yet — a DOS runner can self-provision without any."""


#: The platforms this spec defines, each name mapped to its
#: platform config type — the authoritative set a runner's
#: `platform` must come from, and the type its config must be an
#: instance of. Grows only by spec releases; "dos" is the whole set
#: today (win9x, win3x, winnt, and linux are possible future
#: candidates).
PLATFORMS: Dict[str, Type[RunnerConfig]] = {"dos": DosConfig}


@runtime_checkable
class Runner(Protocol):
    """The runner contract. A runner package exports a class whose
    instances are test machines: `SomeRunner(config)`, where config
    is an instance of that runner's config type.

    A machine carries configuration only — no per-run state — and
    exposes the platform it targets (a name from PLATFORMS) and the
    config it was built from (an instance of that platform's config
    type; callers read it for cache keying)."""

    platform: str
    config: RunnerConfig

    def provision(self, dist_dir: str) -> None:
        """Ensure the boot image exists at BOOT_IMAGE_NAME inside
        `dist_dir`, per this machine's config: copy the configured
        ready image, download a default, or build one from install
        media. Never overwrite a present image. Deterministic given
        the config; raises when the environment is unobtainable
        (e.g. no media configured and no default exists).
        Cache-unaware — whether provisioning is needed at all is
        the caller's decision."""

    def run(self, exe_path: str, args: str, home: str) -> str:
        """Run one guest program to completion and return its
        output text uninterpreted. Boots
        `<home>/<DIST_DIR_NAME>/<BOOT_IMAGE_NAME>`, staged by the
        caller beforehand; keeps all per-run state under `home`, so
        concurrent runs with distinct homes are safe."""
