# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""At-rest access to a guest's own drives, over remanence.

Staging a suite into a stopped machine's disk, and reading it back
afterwards, is not *execution* — so it is not the execution
provider's work to supply (P1, F16, D23). This module is that seam,
and it is the only place `remanence` is imported (P11): everything
it can refuse is refused in this module's own vocabulary, so no
caller needs the dependency to catch a failure.

**A volume is addressed here, never a drive letter.** At rest there
are no letters: DOS assigns one at boot, from the system installed
on the disk, so a letter read off a stopped image is a prediction
of what that boot will do rather than a fact about it (D23; the
same conclusion reliquary reached in its own D107). What this
module takes is an image, a volume within it, and a path within
that volume. Which volume a guest will call `C:` is answered
elsewhere — by Testaferro guaranteeing it on a disk Testaferro
authored, or by asking the guest once it is up.

**The device type is declared, not sniffed.** A qcow2 file records
nothing about the drive that wrote it, and remanence refuses to
guess between the candidates rather than picking one — so the
declaration is made here, once, and it is the same one the guest's
own drives are: MBR-partitioned and CHS-addressed.

**8.3 is remanence's rule to enforce, and it does.** A name a DOS
guest could not type is refused naming the character or the length
that broke it, never mangled into something typeable, so nothing
here re-checks what the dependency already checks better.
"""

from __future__ import annotations

import os

import remanence


# What Testaferro's guest drives are, declared because the image
# does not say: a hard disk carrying an MBR, addressed in CHS.
DEVICE_TYPE = "mbr-sector-hd"

# The separator inside a volume. DOS's, because a DOS guest is what
# reads the result back — remanence accepts either, and writing the
# guest's own is what keeps a refusal's message readable to whoever
# declared the address.
SEPARATOR = "\\"


class AtRestError(Exception):
    """A refusal from the at-rest layer, in Testaferro's vocabulary.

    Wraps whatever the dependency refused so the seam holds: a
    caller catches this and never imports remanence to do it.
    """


def split_address(address):
    """Split a guest address into its drive letter and volume path.

    ``"D:\\TESTS"`` yields ``("D", "TESTS")`` and ``"D:\\"`` yields
    ``("D", "")``, the volume root. The letter is returned rather
    than resolved — this module places nothing by it — because the
    caller who knows which volume that letter names is the one who
    can say, and a wrong letter is the consumer's own word to
    correct.
    """
    text = str(address).strip()
    if len(text) < 2 or text[1] != ":" or not text[0].isalpha():
        raise AtRestError(
            f"{address!r} is not a guest address: Testaferro expects "
            "a drive letter, a colon, and a path — \"D:\\\\TESTS\"")
    letter = text[0].upper()
    path = text[2:].replace("/", SEPARATOR).strip(SEPARATOR)
    return letter, path


def _join(*parts):
    """Join volume-relative path parts, dropping the empty ones."""
    return SEPARATOR.join(part for part in parts if part)


def _volume(medium, volume):
    """The addressed volume of an opened medium.

    Volumes are counted over the partitions that actually bear a
    filesystem, in partition order, so the index means the same
    thing whatever a disk carries beside them.
    """
    spaces = [space for space in
              (partition.filesystem() for partition in medium.partitions())
              if space is not None]
    if not spaces:
        raise AtRestError(
            "this disk carries no filesystem Testaferro can read; "
            "remanence claims FAT12 and FAT16 over an MBR")
    try:
        return spaces[volume]
    except IndexError:
        raise AtRestError(
            f"this disk has {len(spaces)} volume(s) and Testaferro was "
            f"asked for volume {volume}") from None


class _Opened:
    """One image open for the length of one operation.

    Remanence takes no lock of its own and answers the handle's own
    question about writability, so the intent is declared at the
    open and the whole operation runs inside it. Writes buffer until
    `commit()`, which stands on remanence's own undo journal — an
    interrupted commit is reconciled at the image's next open, so
    there is nothing for this module to unwind.
    """

    def __init__(self, image, volume, writable):
        self._session = remanence.Session()
        try:
            discovery = remanence.discover_media(
                os.fspath(image), writable=writable)
            self._medium = self._session.load_discovery_as(
                discovery, DEVICE_TYPE)
            self.space = _volume(self._medium, volume)
        except remanence.Error as error:
            self._session.__exit__(None, None, None)
            raise AtRestError(str(error)) from error
        except Exception:
            self._session.__exit__(None, None, None)
            raise

    def commit(self):
        self._medium.commit()

    def close(self):
        self._session.__exit__(None, None, None)


def put_tree(source, image, path, *, volume=0):
    """Copy a host directory's contents into a guest volume.

    The **contents** of host directory ``source`` land at ``path``
    in the volume — ``""`` puts them at its root, which is the only
    shape a root can take, having no name of its own to nest under.
    Directories are created as needed, ``path`` itself included,
    existing files are overwritten, and nothing already there is
    removed first: this is a copy, never a mirror. Returns the
    volume-relative paths written, sorted.
    """
    origin = os.path.abspath(os.fspath(source))
    if not os.path.isdir(origin):
        raise AtRestError(f"no such directory: {origin}")
    written = []
    opened = _Opened(image, volume, writable=True)
    try:
        for directory, _subdirectories, files in os.walk(origin):
            relative = os.path.relpath(directory, origin)
            parts = ([] if relative == os.curdir
                     else relative.split(os.sep))
            here = _join(path, *parts)
            if here:
                opened.space.make_directory(here)
            for name in sorted(files):
                with open(os.path.join(directory, name), "rb") as handle:
                    opened.space.write_file(_join(here, name),
                                            handle.read())
                written.append(_join(here, name))
        opened.commit()
    except remanence.Error as error:
        raise AtRestError(str(error)) from error
    finally:
        opened.close()
    return sorted(written)


def get_tree(image, path, destination, *, volume=0):
    """Retrieve a guest volume's directory tree to the host, whole.

    The mirror of :func:`put_tree`: the **contents** of ``path`` in
    the volume land in host directory ``destination``, which is
    created if it does not exist. Returns the host paths written,
    sorted.
    """
    target = os.path.abspath(os.fspath(destination))
    if os.path.exists(target) and not os.path.isdir(target):
        raise AtRestError(
            f"{target} is a file; retrieval writes a directory tree")
    written = []
    opened = _Opened(image, volume, writable=False)
    try:
        os.makedirs(target, exist_ok=True)
        _retrieve(opened.space, path, target, written)
    except remanence.Error as error:
        raise AtRestError(str(error)) from error
    finally:
        opened.close()
    return sorted(written)


def _retrieve(space, path, target, written):
    """Copy one guest directory to the host, then its children.

    Depth-first over `entries()`, which reports each name with the
    kind that decides whether it is descended into or read.
    """
    for entry in space.entries(path):
        inside = _join(path, entry.name)
        landing = os.path.join(target, entry.name)
        if entry.kind == "directory":
            os.makedirs(landing, exist_ok=True)
            _retrieve(space, inside, landing, written)
        else:
            with open(landing, "wb") as handle:
                handle.write(space.read_file(inside))
            written.append(landing)
