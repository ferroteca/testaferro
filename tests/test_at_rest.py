# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Unit tests for the at-rest seam over remanence.

**The dependency is faked here, deliberately.** What this module
owns is the walk, the address, the volume choice and the refusal
vocabulary; what remanence owns is FAT, MBR and the 8.3 namespace,
and re-checking those against a fake would assert the fake. The
real round trip — a tree written into a guest's own drive image and
read back out of it — is the integration tier's, which is where a
disk image actually exists (P10).

The fake below is a filesystem, not a mock recorder: it holds the
directories and files it was given so a case asserts what *landed*
rather than which calls were made, and the one case that does look
at calls says why.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

from helpers import REMANENCE_AVAILABLE, requires_remanence

if REMANENCE_AVAILABLE:
    from testaferro import at_rest


class _Error(Exception):
    """Stands in for remanence.Error."""


class _Entry:
    def __init__(self, name, kind):
        self.name = name
        self.kind = kind


class _Space:
    """A FAT volume's namespace, as far as this module uses one."""

    def __init__(self, files=None):
        self.directories = {""}
        self.files = dict(files or {})
        for path in self.files:
            parent = path.rsplit("\\", 1)[0] if "\\" in path else ""
            self.directories.add(parent)

    def make_directory(self, path):
        self.directories.add(path)

    def write_file(self, path, contents):
        parent = path.rsplit("\\", 1)[0] if "\\" in path else ""
        if parent not in self.directories:
            raise _Error(f"invalid fat disk image: "
                         f"directory {parent!r} not found")
        self.files[path] = bytes(contents)

    def read_file(self, path):
        try:
            return self.files[path]
        except KeyError:
            raise _Error(f"invalid fat disk image: {path!r} not found") \
                from None

    def entries(self, path=""):
        if path not in self.directories:
            raise _Error(f"invalid fat disk image: {path!r} not found")
        prefix = f"{path}\\" if path else ""
        seen = []
        for name in sorted(self.files):
            if name.startswith(prefix) and "\\" not in name[len(prefix):]:
                seen.append(_Entry(name[len(prefix):], "file"))
        for name in sorted(self.directories):
            if (name and name.startswith(prefix)
                    and "\\" not in name[len(prefix):]):
                seen.append(_Entry(name[len(prefix):], "directory"))
        return seen


class _Partition:
    def __init__(self, space):
        self._space = space

    def filesystem(self):
        return self._space


class _Medium:
    def __init__(self, spaces):
        self._spaces = spaces
        self.commits = 0

    def partitions(self):
        return [_Partition(space) for space in self._spaces]

    def commit(self):
        self.commits += 1


class _Session:
    def __init__(self, medium, opened):
        self._medium = medium
        self._opened = opened

    def load_discovery_as(self, discovery, device):
        self._opened["device"] = device
        return self._medium

    def __exit__(self, *_exc):
        self._opened["closed"] = True
        return False


def _fake(spaces, *, on_discover=None):
    """A remanence stand-in over the given volumes.

    Returns the namespace patched into the module and a dict the
    cases read back: which device type was declared, whether the
    image was opened writable, and whether the session was closed.
    """
    opened = {"closed": False}
    medium = _Medium(spaces)

    def discover_media(path, *, writable):
        opened["path"] = path
        opened["writable"] = writable
        if on_discover is not None:
            on_discover()
        return object()

    namespace = mock.Mock()
    namespace.Error = _Error
    namespace.discover_media = discover_media
    namespace.Session = lambda: _Session(medium, opened)
    return namespace, opened, medium


@requires_remanence
class SplitAddressTests:
    """A guest address is split, never resolved (D23)."""

    def test_letter_and_path(self):
        assert at_rest.split_address("D:\\TESTS") == ("D", "TESTS")

    def test_root_has_no_path(self):
        assert at_rest.split_address("A:\\") == ("A", "")

    def test_letter_is_upper_and_separators_are_dos(self):
        assert (at_rest.split_address("d:/tests/deep")
                == ("D", "tests\\deep"))

    @pytest.mark.parametrize(
        "address", ["TESTS", "", ":", "1:\\TESTS", "\\TESTS"])
    def test_a_path_without_a_letter_is_refused(self, address):
        with pytest.raises(at_rest.AtRestError) as caught:
            at_rest.split_address(address)
        assert "guest address" in str(caught.value)


@requires_remanence
class PutTreeTests:

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.source = tmp_path
        self.space = _Space()

    def _write(self, relative, data=b"x"):
        path = os.path.join(self.source, *relative.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)

    def test_contents_land_under_the_path(self):
        self._write("SUITE.EXE", b"MZ")
        self._write("SUB/INNER.TXT", b"in")
        namespace, _opened, medium = _fake([self.space])
        with mock.patch.object(at_rest, "remanence", namespace):
            written = at_rest.put_tree(self.source, "disk.qcow2", "TESTS")
        assert written == ["TESTS\\SUB\\INNER.TXT", "TESTS\\SUITE.EXE"]
        assert self.space.files["TESTS\\SUITE.EXE"] == b"MZ"
        assert self.space.files["TESTS\\SUB\\INNER.TXT"] == b"in"
        assert medium.commits == 1

    def test_the_root_takes_the_contents_directly(self):
        self._write("SUITE.EXE")
        namespace, _opened, _medium = _fake([self.space])
        with mock.patch.object(at_rest, "remanence", namespace):
            written = at_rest.put_tree(self.source, "disk.qcow2", "")
        assert written == ["SUITE.EXE"]

    def test_the_image_is_opened_writable_and_declared(self):
        self._write("SUITE.EXE")
        namespace, opened, _medium = _fake([self.space])
        with mock.patch.object(at_rest, "remanence", namespace):
            at_rest.put_tree(self.source, "disk.qcow2", "TESTS")
        assert opened["writable"]
        assert opened["device"] == at_rest.DEVICE_TYPE
        assert opened["closed"]

    def test_a_missing_source_is_refused_before_the_image_is_opened(self):
        namespace, opened, _medium = _fake([self.space])
        with mock.patch.object(at_rest, "remanence", namespace):
            with pytest.raises(at_rest.AtRestError):
                at_rest.put_tree(os.path.join(self.source, "nope"),
                                 "disk.qcow2", "TESTS")
        assert "path" not in opened

    def test_a_dependency_refusal_arrives_in_this_module_s_vocabulary(self):
        """The seam: a caller never imports remanence to catch this."""
        self._write("SUITE.EXE")
        namespace, _opened, _medium = _fake([self.space])

        def refuse(path, contents):
            raise _Error("'toolong.exe' has a 7-character base name")

        self.space.write_file = refuse
        with mock.patch.object(at_rest, "remanence", namespace):
            with pytest.raises(at_rest.AtRestError) as caught:
                at_rest.put_tree(self.source, "disk.qcow2", "TESTS")
        assert "base name" in str(caught.value)

    def test_the_session_closes_when_the_write_refuses(self):
        self._write("SUITE.EXE")
        namespace, opened, medium = _fake([self.space])

        def refuse(path, contents):
            raise _Error("no")

        self.space.write_file = refuse
        with mock.patch.object(at_rest, "remanence", namespace):
            with pytest.raises(at_rest.AtRestError):
                at_rest.put_tree(self.source, "disk.qcow2", "TESTS")
        assert opened["closed"]
        assert medium.commits == 0


@requires_remanence
class GetTreeTests:

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.destination = tmp_path

    def test_a_tree_comes_back_whole(self):
        space = _Space({"TESTS\\SUITE.EXE": b"MZ",
                        "TESTS\\SUB\\INNER.TXT": b"in",
                        "ELSEWHERE.TXT": b"no"})
        target = os.path.join(self.destination, "retrieved")
        namespace, opened, _medium = _fake([space])
        with mock.patch.object(at_rest, "remanence", namespace):
            written = at_rest.get_tree("disk.qcow2", "TESTS", target)
        assert (sorted(os.path.relpath(path, target) for path in written)
                == [os.path.join("SUB", "INNER.TXT"), "SUITE.EXE"])
        with open(os.path.join(target, "SUITE.EXE"), "rb") as handle:
            assert handle.read() == b"MZ"
        assert not opened["writable"]

    def test_a_file_destination_is_refused(self):
        space = _Space({"TESTS\\SUITE.EXE": b"MZ"})
        target = os.path.join(self.destination, "a-file")
        with open(target, "wb") as handle:
            handle.write(b"")
        namespace, _opened, _medium = _fake([space])
        with mock.patch.object(at_rest, "remanence", namespace):
            with pytest.raises(at_rest.AtRestError):
                at_rest.get_tree("disk.qcow2", "TESTS", target)


@requires_remanence
class VolumeChoiceTests:
    """Volumes are counted over the partitions that bear one."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.source = tmp_path
        with open(os.path.join(self.source, "SUITE.EXE"), "wb") as h:
            h.write(b"MZ")

    def test_the_second_volume_is_addressable(self):
        first, second = _Space(), _Space()
        namespace, _opened, _medium = _fake([first, second])
        with mock.patch.object(at_rest, "remanence", namespace):
            at_rest.put_tree(self.source, "disk.qcow2", "TESTS",
                             volume=1)
        assert "TESTS\\SUITE.EXE" in second.files
        assert first.files == {}

    def test_a_disk_with_no_filesystem_is_refused(self):
        namespace, _opened, _medium = _fake([])
        with mock.patch.object(at_rest, "remanence", namespace):
            with pytest.raises(at_rest.AtRestError) as caught:
                at_rest.put_tree(self.source, "disk.qcow2", "TESTS")
        assert "no filesystem" in str(caught.value)

    def test_a_volume_beyond_the_disk_is_refused_with_the_count(self):
        namespace, _opened, _medium = _fake([_Space()])
        with mock.patch.object(at_rest, "remanence", namespace):
            with pytest.raises(at_rest.AtRestError) as caught:
                at_rest.put_tree(self.source, "disk.qcow2", "TESTS",
                                 volume=3)
        assert "1 volume(s)" in str(caught.value)
        assert "volume 3" in str(caught.value)
