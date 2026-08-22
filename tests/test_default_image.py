# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Building the default system disk, when more than one process wants it.

Apart from `test_reliquary.py` because that file's module fixture makes
reaching `_build_default_image()` an error on the spot (P10), and what
these cases exercise *is* that function — with the provider stubbed
below it, so nothing boots and nothing installs. `_open_session()` is
the seam: everything under it is reliquary's, and everything above it
is Testaferro's own file handling, which is what U5 puts under load.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

from testaferro import cache
from helpers import RELIQUARY_AVAILABLE

if RELIQUARY_AVAILABLE:
    from testaferro import reliquary as binding

requires_reliquary = pytest.mark.skipif(
    not RELIQUARY_AVAILABLE, reason="reliquary is not installed")


class _FakeSession:
    """Enough of a reliquary session to 'install' a one-line disk."""

    def __init__(self, home, contents):
        self.home = home
        self.contents = contents

    def create_machine(self, blueprint):
        return "machine"

    def run_script(self, name, machine=None):
        pass

    def load_machine_state(self, machine):
        installed = os.path.join(self.home, "installed.qcow2")
        with open(installed, "wb") as disk:
            disk.write(self.contents)
        return {"drives": {"hdd0": {"path": installed}}}

    def destroy_machine(self, machine):
        pass


@requires_reliquary
class DefaultImageBuildTests:

    @pytest.fixture(autouse=True)
    def _cache(self, tmp_path):
        with mock.patch.object(cache, "cache_root",
                               return_value=str(tmp_path)):
            yield

    def test_a_build_leaves_only_the_finished_disk_behind(self):
        destination = os.path.join(cache.cache_root(), "freedos.qcow2")
        with mock.patch.object(
                binding, "_open_session",
                side_effect=lambda home, *a, **k:
                    _FakeSession(home, b"installed")):
            binding._build_default_image(destination)

        with open(destination, "rb") as disk:
            assert disk.read() == b"installed"
        assert os.listdir(cache.cache_root()) == ["freedos.qcow2"]

    def test_two_builds_racing_for_the_same_disk_both_finish(self):
        """Under xdist every worker collects, so on a machine that has
        never built the system two workers can find it missing at the
        same moment and both install it (U5). Neither knows about the
        other, and nothing locks — isolation, not locking, is the
        claim — so each build has to keep its own partial file: a
        shared `freedos.qcow2.part` had the second build's atomic move
        take the first build's partial out from under it. The first
        to finish is the disk, and the other discards its own rather
        than replace a file a guest may already have open."""
        destination = os.path.join(cache.cache_root(), "freedos.qcow2")
        sessions = []

        def open_session(home, *args, **kwargs):
            session = _FakeSession(home, b"first" if not sessions
                                   else b"second")
            sessions.append(session)
            return session

        real_copy = binding.shutil.copy

        def copy_then_let_the_other_finish(source, partial):
            real_copy(source, partial)
            if len(sessions) == 1:
                # The first build has written its partial and is about
                # to move it into place; the second build runs to
                # completion in between.
                binding._build_default_image(destination)

        with mock.patch.object(binding, "_open_session",
                               side_effect=open_session), \
                mock.patch.object(binding.shutil, "copy",
                                  side_effect=copy_then_let_the_other_finish):
            binding._build_default_image(destination)

        assert len(sessions) == 2
        # The second build ran to completion inside the first's copy
        # step, so it finished first, and the first kept its hands off.
        with open(destination, "rb") as disk:
            assert disk.read() == b"second"
        assert os.listdir(cache.cache_root()) == ["freedos.qcow2"]

    def test_clearing_downloads_sweeps_an_abandoned_partial(self):
        root = cache.cache_root()
        abandoned = os.path.join(root, "freedos.qcow2.k1ll3d.part")
        with open(abandoned, "wb") as partial:
            partial.write(b"half")
        with open(os.path.join(root, "freedos.qcow2"), "wb") as disk:
            disk.write(b"whole")

        binding.stop(clear_downloads=True)

        assert os.listdir(root) == []
