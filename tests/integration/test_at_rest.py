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

**Why cover it here at all.** Reliquary's at-rest answers are
machine input that testaferro *acts* on: a letter map places the
suite, a refusal decides whether a run fails now or fails as a
missing program inside a guest. That combination — high variability,
wide blast radius — is what earns pinned coverage rather than one
end-to-end run that happens to pass. A provider change that moves
these answers should fail here, naming the fact that moved, rather
than surfacing as a guest that mysteriously will not run its suite.

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
        import reliquary

        from testaferro import reliquary as binding

        cls.reliquary = reliquary
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
                self.reliquary.destroy_machine(self.machine,
                                               context=self.context)
            except Exception:
                pass
        import shutil

        shutil.rmtree(self.home, ignore_errors=True)

    def _create(self, drives=None, boot=("hdd0",)):
        """Author a thin blueprint and materialize it. No boot."""
        document = [{
            "type": "machine", "name": "atrest", "platform": "dos",
            "memory": "32M",
            "drives": drives or {"hdd0": {
                "type": "media", "name": "system",
                "location": {"local": self.system},
                "materialize": "difference"}},
            "boot": list(boot),
        }]
        path = os.path.join(self.blueprints, "atrest.rlqb")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        self.context = self.reliquary.Context(
            home_dir=self.home, cache_dir=os.path.join(self.home, "cache"),
            blueprints_dir=self.blueprints)
        self.machine = self.reliquary.create_machine(
            "atrest", context=self.context)
        return self.machine

    def _staged(self, *names):
        """A host directory holding files to stage."""
        source = tempfile.mkdtemp(dir=self.home)
        for name in names:
            with open(os.path.join(source, name), "wb") as handle:
                handle.write(b"content of " + name.encode("ascii"))
        return source


class DriveReportTests(AtRestFixture):
    """What `describe_drives` says about the installed system."""

    def test_the_installed_system_reports_one_fat16_volume_at_c(self):
        # The fact the whole placement rests on: testaferro's own
        # FreeDOS is a single FAT16 volume, and the guest calls it C:.
        machine = self._create()

        report = self.reliquary.describe_drives(machine=machine,
                                                context=self.context)

        letters = report["mapping"]["letters"]
        self.assertEqual(letters["C"]["drive"], "hdd0")
        self.assertEqual(letters["C"]["volume"], 0)
        self.assertEqual(report["mapping"]["undetermined"], [])
        geometry = report["drives"][0]["geometry"]
        self.assertEqual(geometry["backing"], "qcow2")
        self.assertEqual(
            [volume["filesystem"] for volume in geometry["volumes"]],
            ["FAT16"])

    def test_a_created_machine_answers_before_it_has_ever_booted(self):
        # The window F4 stages in. If this ever stops being true the
        # whole design moves, so it is stated rather than assumed.
        machine = self._create()

        state = self.reliquary.load_machine_state(machine,
                                                  context=self.context)

        self.assertEqual(state["phase"], "ready")

    def test_testaferro_defaults_the_location_to_c_tests(self):
        # testaferro's own policy, applied to a real map rather than a
        # stubbed one: last letter, `\TESTS` under it.
        machine = self._create()

        location = self.binding._default_location(machine, self.context)

        self.assertEqual(location, "C:\\TESTS")


class StagingTests(AtRestFixture):
    """Writing into a stopped machine's disk, which is how a suite
    reaches the guest since F4."""

    def test_the_staged_set_lands_at_the_address_and_is_listed_there(self):
        machine = self._create()
        source = self._staged("SUITE.EXE", "CASE.DAT")

        written = self.reliquary.put_files(source, "C:\\TESTS",
                                           machine=machine,
                                           context=self.context)

        self.assertEqual(sorted(written),
                         ["C:\\TESTS\\CASE.DAT", "C:\\TESTS\\SUITE.EXE"])
        listed = self.reliquary.list_files("C:\\TESTS", machine=machine,
                                           context=self.context)
        self.assertEqual(sorted(entry["address"] for entry in listed),
                         ["C:\\TESTS\\CASE.DAT", "C:\\TESTS\\SUITE.EXE"])

    def test_the_location_directory_is_created_rather_than_required(self):
        # `C:\TESTS` does not exist on a fresh FreeDOS install, and
        # testaferro never creates it itself — staging does, which is
        # what lets a defaulted location name a directory nobody made.
        machine = self._create()

        with self.assertRaises(self.reliquary.ReliquaryError):
            self.reliquary.list_files("C:\\TESTS", machine=machine,
                                      context=self.context)

        self.reliquary.put_files(self._staged("SUITE.EXE"), "C:\\TESTS",
                                 machine=machine, context=self.context)

        self.assertTrue(self.reliquary.list_files(
            "C:\\TESTS", machine=machine, context=self.context))

    def test_restaging_adds_without_removing_what_a_run_left(self):
        # A copy, never a mirror. It matters here because a second
        # guest session over the same disk must not delete the results
        # of the first — which is what `--keep-guest-home` retrieves.
        machine = self._create()
        self.reliquary.put_files(self._staged("SUITE.EXE"), "C:\\TESTS",
                                 machine=machine, context=self.context)
        self.reliquary.put_files(self._staged("RESULTS.TXT"), "C:\\TESTS",
                                 machine=machine, context=self.context)

        listed = [entry["name"] for entry in self.reliquary.list_files(
            "C:\\TESTS", machine=machine, context=self.context)]

        self.assertEqual(sorted(listed), ["RESULTS.TXT", "SUITE.EXE"])

    def test_what_was_staged_comes_back_byte_for_byte(self):
        # The retrieval `--testaferro-keep-guest-home` performs.
        machine = self._create()
        source = self._staged("SUITE.EXE")
        self.reliquary.put_files(source, "C:\\TESTS", machine=machine,
                                 context=self.context)
        back = os.path.join(self.home, "retrieved")

        self.reliquary.get_files("C:\\TESTS", back, machine=machine,
                                 context=self.context)

        self.assertEqual(
            Path(back, "SUITE.EXE").read_bytes(),
            Path(source, "SUITE.EXE").read_bytes())

    def test_a_declared_address_on_a_drive_that_is_not_there_refuses(self):
        # F4's validation-by-staging: a wrong location fails here,
        # before any boot, carrying reliquary's own words and id — not
        # as a missing program in a guest that started anyway.
        machine = self._create()

        with self.assertRaises(self.reliquary.ReliquaryError) as caught:
            self.reliquary.put_files(self._staged("SUITE.EXE"),
                                     "E:\\HARNESS", machine=machine,
                                     context=self.context)

        # The **rule id** is the stable handle, so it is what gets
        # pinned; the prose may be reworded and this should not care.
        self.assertEqual(caught.exception.rule_id,
                         "drive.letter-not-declared")
        message = str(caught.exception)
        self.assertIn("E:\\HARNESS", message)
        # And it names the letters the machine does have, which is the
        # half a consumer acts on.
        self.assertIn("C: (hdd0)", message)


class UnreadableDriveTests(AtRestFixture):
    """A disk reliquary cannot read, which is what the fallback is
    for — and the case a stubbed report can only imitate."""

    def _junk_disk(self):
        """A drive image that is not a filesystem at all."""
        path = os.path.join(self.home, "JUNK.IMG")
        with open(path, "wb") as handle:
            handle.write(b"not a filesystem" * 1024)
        return {"hdd0": {"type": "media", "name": "junk",
                         "location": {"local": path},
                         "materialize": "use"}}

    def test_an_unreadable_disk_is_named_undetermined_with_its_reason(self):
        # D78's honesty carried into the report: the disk is not
        # silently skipped, and the entry says which one and why.
        machine = self._create(drives=self._junk_disk())

        report = self.reliquary.describe_drives(machine=machine,
                                                context=self.context)

        self.assertEqual(report["mapping"]["letters"], {})
        undetermined = report["mapping"]["undetermined"]
        self.assertEqual([entry["drive"] for entry in undetermined],
                         ["hdd0"])
        self.assertTrue(undetermined[0]["reason"])
        self.assertTrue(undetermined[0]["id"])

    def test_testaferro_refuses_to_default_onto_a_disk_it_cannot_read(self):
        # Rather than guessing a letter. The refusal carries
        # reliquary's own reason and points at the way out.
        machine = self._create(drives=self._junk_disk())

        with self.assertRaises(ValueError) as caught:
            self.binding._default_location(machine, self.context)

        self.assertIn("location=", str(caught.exception))

    def test_an_appended_directory_drive_is_placed_behind_the_bad_disk(self):
        # The fallback's other half: once testaferro adds its own
        # drive, that drive still needs a letter — and an unreadable
        # disk ahead of it means it does not get one, which is why the
        # fallback appends *and* re-reads rather than assuming.
        drives = self._junk_disk()
        source = self._staged("SUITE.EXE")
        drives["hdd1"] = {"type": "media", "name": "work",
                          "location": {"local": source},
                          "materialize": "use"}
        machine = self._create(drives=drives)

        with self.assertRaises(ValueError) as caught:
            self.binding._placed_letter("hdd1", machine, self.context)

        # The blocking disk answers for the drive behind it — the
        # specific refusal survives the indirection (P11).
        self.assertIn("hdd1", str(caught.exception))
