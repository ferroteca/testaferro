# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""The at-rest surface testaferro stages through, against a real disk.

**Integration by fixture cost, not by slowness.** These need
testaferro's installed FreeDOS system — a genuine FAT16 volume in a
qcow2, built once by an install nothing here may repeat (P10) — so
they sit on this side of the line. What they do *not* need is a
boot: everything below happens between `create_machine()` and the
machine's first start, which is the window F4's staging lives in.
One case costs a couple of seconds, which is what makes covering
this surface properly affordable.

**Why cover it here at all.** What testaferro does with a real disk
is *act* on it: a resolution places the suite, a refusal decides
whether a run fails now or fails as a missing program inside a
guest. That combination — high variability, wide blast radius — is
what earns pinned coverage rather than one end-to-end run that
happens to pass. A dependency change that moves these answers should
fail here, naming the fact that moved, rather than surfacing as a
guest that mysteriously will not run its suite.

**What proves the guarantee, and what cannot.** The system disk's
letter is *computed* (`_letter_map`, D108), not read off a drive map
that no longer exists. Half of that is provable here: the installed
system carries **exactly one** FAT16 volume, matching the assumption
`_letter_map` rests every hard disk's letter on. The other half —
that DOS actually calls it `C:` — is a fact about a booted guest, and
it is `test_guest_run.py` that proves it. Neither half is assumed in
the file that states it.

The blueprint each case authors is deliberately thin: one drive over
the built system, layered `difference` so no case can write into the
copy the others share.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

ASKED = bool(os.environ.get("TESTAFERRO_INTEGRATION"))

requires_guest = unittest.skipUnless(
    ASKED, "set TESTAFERRO_INTEGRATION=1 to build and read a real disk")


@requires_guest
class AtRestFixture(unittest.TestCase):
    """A created, never-booted machine over the installed system."""

    @classmethod
    def setUpClass(cls):
        from testaferro import at_rest
        from testaferro import reliquary as binding

        cls.at_rest = at_rest
        cls.binding = binding
        # The install happens at most once for the whole run, and is
        # cached across runs — every case below layers over it.
        cls.system = binding._cached_default_image()

    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="atrest-")
        self.addCleanup(self._sweep)
        self.blueprints = os.path.join(self.home, "blueprints")
        os.makedirs(self.blueprints)
        self.machine = None

    def _sweep(self):
        if self.machine is not None:
            try:
                self.session.destroy_machine(self.machine)
            except Exception:
                pass
        import shutil

        shutil.rmtree(self.home, ignore_errors=True)

    def _create(self, drives=None, boot=("hdd0",)):
        """Author a thin blueprint and materialize it. No boot."""
        self.drives = drives or {"hdd0": {
            "type": "media", "name": "system",
            "location": {"local": self.system},
            "materialize": "difference"}}
        document = [{
            "type": "machine", "name": "atrest", "platform": "dos",
            "memory": "32M",
            "drives": self.drives,
            "boot": list(boot),
        }]
        path = os.path.join(self.blueprints, "atrest.rlqb")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        self.session = self.binding._open_session(self.home, self.blueprints)
        self.machine = self.session.create_machine("atrest")
        return self.machine

    def _staged(self, *names):
        """A host directory holding files to stage."""
        source = tempfile.mkdtemp(dir=self.home)
        for name in names:
            with open(os.path.join(source, name), "wb") as handle:
                handle.write(b"content of " + name.encode("ascii"))
        return source

    def _put(self, machine, source, address="C:\\TESTS"):
        """Stage a host directory at a guest address, as `_place` does."""
        image, volume, path = self.binding._resolve_volume(
            address, machine, self.session, self.drives)
        return self.at_rest.put_tree(source, image, path, volume=volume)

    def _listing(self, machine, address="C:\\TESTS"):
        """What is at an address, by retrieving it. Names only.

        There is no at-rest listing verb and none is added for a
        test: retrieval is the operation testaferro actually
        performs, so reading a result back the way the product does
        is the stronger check anyway.
        """
        image, volume, path = self.binding._resolve_volume(
            address, machine, self.session, self.drives)
        back = tempfile.mkdtemp(dir=self.home)
        written = self.at_rest.get_tree(image, path, back, volume=volume)
        return sorted(os.path.relpath(name, back) for name in written)


class InstalledSystemTests(AtRestFixture):
    """What testaferro's own FreeDOS disk actually is."""

    def test_the_installed_system_carries_exactly_one_fat16_volume(self):
        """The fact the guaranteed location rests on (F16, D23).

        One volume is what makes `C:` the only letter DOS can hand
        out, so the guarantee is not a guess about a machine — it is
        a statement about a disk testaferro built. A second volume
        appearing here would break the guarantee silently, which is
        why this is pinned rather than assumed.
        """
        machine = self._create()
        image = self.binding._drive_image("hdd0", machine, self.session)

        import remanence

        with remanence.Session() as session:
            medium = session.load_discovery_as(
                remanence.discover_media(image, writable=False),
                self.at_rest.DEVICE_TYPE)
            volumes = [partition.filesystem()
                       for partition in medium.partitions()]
            kinds = [space.kind for space in volumes if space is not None]

        self.assertEqual(kinds, ["FAT16"])

    def test_a_created_machine_answers_before_it_has_ever_booted(self):
        # The window F4 stages in. If this ever stops being true the
        # whole design moves, so it is stated rather than assumed.
        machine = self._create()

        state = self.session.load_machine_state(machine)

        self.assertEqual(state["phase"], "ready")

    def test_the_system_disk_defaults_without_reading_anything(self):
        machine = self._create()

        self.assertEqual(
            self.binding._default_location(self.drives, work_key="hdd0"),
            "C:\\")

    def test_the_resolution_finds_the_layered_image_and_its_volume(self):
        """What `_place` hands to the at-rest write.

        The image is the machine's **own** difference layer, not the
        shared system underneath it — every guest session writes into
        its own overlay, and staging into the shared copy would reach
        every other session (P5).
        """
        machine = self._create()

        image, volume, path = self.binding._resolve_volume(
            "C:\\TESTS", machine, self.session, self.drives)

        self.assertEqual((volume, path), (0, "TESTS"))
        self.assertTrue(os.path.isfile(image))
        self.assertNotEqual(os.path.abspath(image),
                            os.path.abspath(self.system))


class StagingTests(AtRestFixture):
    """Writing into a stopped machine's disk, which is how a suite
    reaches the guest since F4 — and testaferro's own work since
    F16."""

    def test_the_staged_set_lands_at_the_address(self):
        machine = self._create()
        source = self._staged("SUITE.EXE", "CASE.DAT")

        written = self._put(machine, source)

        self.assertEqual(written,
                         ["TESTS\\CASE.DAT", "TESTS\\SUITE.EXE"])
        self.assertEqual(self._listing(machine),
                         ["CASE.DAT", "SUITE.EXE"])

    def test_the_location_directory_is_created_rather_than_required(self):
        # `C:\TESTS` does not exist on a fresh FreeDOS install, and
        # testaferro never creates it itself — staging does, which is
        # what lets a defaulted location name a directory nobody made.
        machine = self._create()

        with self.assertRaises(self.at_rest.AtRestError):
            self._listing(machine)

        self._put(machine, self._staged("SUITE.EXE"))

        self.assertEqual(self._listing(machine), ["SUITE.EXE"])

    def test_restaging_adds_without_removing_what_a_run_left(self):
        # A copy, never a mirror. It matters here because a second
        # guest session over the same disk must not delete the results
        # of the first — which is what `--keep-guest-home` retrieves.
        machine = self._create()
        self._put(machine, self._staged("SUITE.EXE"))
        self._put(machine, self._staged("RESULTS.TXT"))

        self.assertEqual(self._listing(machine),
                         ["RESULTS.TXT", "SUITE.EXE"])

    def test_what_was_staged_comes_back_byte_for_byte(self):
        # The retrieval `--testaferro-keep-guest-home` performs.
        machine = self._create()
        source = self._staged("SUITE.EXE")
        self._put(machine, source)
        image, volume, path = self.binding._resolve_volume(
            "C:\\TESTS", machine, self.session, self.drives)
        back = os.path.join(self.home, "retrieved")

        self.at_rest.get_tree(image, path, back, volume=volume)

        self.assertEqual(
            Path(back, "SUITE.EXE").read_bytes(),
            Path(source, "SUITE.EXE").read_bytes())

    def test_a_subdirectory_keeps_its_shape_through_both_directions(self):
        """The set keeps its shape under the location (F4).

        `files=` may name a directory, so the walk and its mirror
        have to agree about nesting on a real FAT volume rather than
        only against the unit tier's fake.
        """
        machine = self._create()
        source = self._staged("SUITE.EXE")
        os.makedirs(os.path.join(source, "DATA"))
        with open(os.path.join(source, "DATA", "CASE.DAT"), "wb") as handle:
            handle.write(b"nested")

        self._put(machine, source)

        self.assertEqual(self._listing(machine),
                         [os.path.join("DATA", "CASE.DAT"), "SUITE.EXE"])

    def test_a_name_a_dos_guest_could_not_type_is_refused(self):
        """8.3 is the dependency's rule, and it is enforced here.

        testaferro re-checks nothing, so this is the case that says
        the inherited refusal is real — and that it arrives in
        testaferro's own vocabulary rather than the dependency's.
        """
        machine = self._create()
        source = self._staged("SUITE.EXE")
        with open(os.path.join(source, "toolongname.exe"), "wb") as handle:
            handle.write(b"x")

        with self.assertRaises(self.at_rest.AtRestError) as caught:
            self._put(machine, source)

        self.assertIn("8.3", str(caught.exception))


class DeclaredAddressTests(AtRestFixture):
    """A location the consumer named, resolved against a real disk."""

    def test_a_letter_the_machine_does_not_have_refuses(self):
        # F4's validation-by-staging, kept: a wrong location fails
        # before any boot, not as a missing program in a guest that
        # started anyway. The one drive it *does* have is named.
        machine = self._create()

        with self.assertRaises(ValueError) as caught:
            self._put(machine, self._staged("SUITE.EXE"),
                      address="E:\\HARNESS")

        self.assertIn("no E:", str(caught.exception))

    def test_a_declared_machines_own_letter_resolves(self):
        # The capability 0.1.0a2 took away and _letter_map gives back
        # (D108): a machine testaferro did not build zero-config
        # still resolves its own declared disk deterministically —
        # this fixture's own thin blueprint stands in for one.
        machine = self._create()

        written = self._put(machine, self._staged("SUITE.EXE"),
                            address="C:\\HARNESS")

        self.assertEqual(written, ["HARNESS\\SUITE.EXE"])
        self.assertEqual(self._listing(machine, address="C:\\HARNESS"),
                         ["SUITE.EXE"])


class UnreadableDriveTests(AtRestFixture):
    """A disk that cannot be read at rest — a declared address naming
    one still fails closed, cleanly, before any boot."""

    def _junk_disk(self):
        """A drive image that is not a filesystem at all."""
        path = os.path.join(self.home, "JUNK.IMG")
        with open(path, "wb") as handle:
            handle.write(b"not a filesystem" * 1024)
        return {"hdd0": {"type": "media", "name": "junk",
                         "location": {"local": path},
                         "materialize": "use"}}

    def test_an_unreadable_disk_refuses_the_write_by_name(self):
        """remanence's refusal, in testaferro's vocabulary.

        A fake cannot prove this about a real disk — only a genuine
        FAT-blind image, opened for real, raises the type `at_rest`
        translates.
        """
        machine = self._create(drives=self._junk_disk())

        with self.assertRaises(self.at_rest.AtRestError):
            self._put(machine, self._staged("SUITE.EXE"))

    def test_the_letter_map_ignores_whether_a_disk_can_be_read(self):
        # `_letter_map` is pure declaration arithmetic (0.1.0a2,
        # D108): a junk disk ahead of testaferro's work drive still
        # gives the work drive D:, since nothing here reads any disk
        # to answer the question — only PlacedLetterTests (unit tier)
        # needs proving this positional rule at all, but a junk disk
        # actually materialized is worth pinning here too.
        drives = self._junk_disk()
        drives["hdd1"] = {"type": "media", "name": "work",
                          "location": {"local": self._staged("SUITE.EXE")},
                          "materialize": "use"}

        self.assertEqual(self.binding._letter_map(drives),
                         {"C": "hdd0", "D": "hdd1"})
