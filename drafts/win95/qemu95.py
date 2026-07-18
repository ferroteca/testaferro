# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""The QEMU/Windows 95 guest binding.

`suite_backend()` guards the door with `binfmt.classify()`: a Windows
x86 (PE) executable — or a DOS program to compatibility-test under
Windows 95 — yields a Qemu95SuiteBackend; anything Windows 95
provably cannot run is rejected with the format and architecture
named. The framework adapter defaults to testaferro.cpputest.

Windows 95 has no downloadable default environment: the caller must
supply one, either per suite or once per session via `start()`. The
choice is a ready bootable hard-disk image (`hdd_image=`, used as-is;
each run still gets a private copy) or install media — a Windows 95
CD ISO path (`install_media=`) or a download URL (`media_url=`,
which requires `media_sha256=` so the download is verified and the
cache keyed by content) — plus any `product_key=` the unattended
install needs. From install media the runner builds an installed
hard-disk image exactly once; testaferro caches that image durably
under `cache_root()/win95/`, keyed by the media identity and product
key, so later sessions skip the (slow) install. The cached image
survives `testaferro.stop(clear_downloads=True)` — rebuildable only
at the cost of a full reinstall, it is cleared only by an explicit
`testaferro.qemu95.stop(clear_downloads=True)`.

Only this module imports quemados95, an *optional* dependency
(`pip install testaferro[win95]`). The surface it relies on mirrors
quemados:

- `_home` / `set_home(path)` / `home()` / `dist_dir()` — the
  process-global home directory the runner works in;
- `hdd_image() -> str` — `home/dist/hdd.img`, the installed Windows
  95 hard-disk image (the analog of `quemados.boot_image()`);
- `install(media=None, media_url=None, media_sha256=None,
  product_key=None)` — ensure `hdd_image()` exists: no-op when
  present, otherwise obtain the CD ISO (local path, or download
  verified against `media_sha256`) and run the unattended install
  into a fresh image; raises ValueError when the image is absent and
  no media source is given (there is no default);
- `run_guest_program(exe_path, args="") -> str` — the full agentless
  lifecycle: stage the executable (8.3-named) on the vvfat guest
  drive, boot `hdd_image()`, run the program with output redirected
  to a log on that drive, detect completion via guest-initiated
  shutdown, and return the log text uninterpreted. However the
  runner arranges execution inside the guest (e.g. a listener baked
  into the installed image) is its own business, not testaferro's.
"""

from __future__ import annotations

import atexit
import hashlib
import os
import shutil
import tempfile

import quemados95

from . import binfmt
from . import cache
from . import cpputest
from .suite import SuiteBackend


def suite_backend(exe_path, framework=cpputest, enumerator=None,
                  hdd_image=None, install_media=None, media_url=None,
                  media_sha256=None, product_key=None):
    """Interrogate the referenced suite executable and return a
    Qemu95SuiteBackend for a Windows 95-runnable program — a Windows
    x86 (PE) executable, or a DOS program to compatibility-test
    under Windows 95. Raises FileNotFoundError for a missing file,
    ValueError for anything Windows 95 provably cannot run, and
    ValueError for an invalid environment choice (`hdd_image=`
    combined with install media; `media_url=` without its hash)."""
    exe_path = os.fspath(exe_path)
    fmt = binfmt.classify(exe_path)
    if fmt.guest is None:
        raise ValueError(
            f"{os.path.basename(exe_path)} is {fmt.kind} executable; "
            "Windows 95 cannot run it")
    return Qemu95SuiteBackend(exe_path, framework=framework,
                              enumerator=enumerator,
                              hdd_image=hdd_image,
                              install_media=install_media,
                              media_url=media_url,
                              media_sha256=media_sha256,
                              product_key=product_key)


def _checked_choice(hdd_image, install_media, media_url,
                    media_sha256, product_key):
    """Validate and normalize one guest-environment choice: a ready
    bootable image, or install media (a URL only together with the
    hash that verifies it), or nothing — deferring to the session's
    choice. Returns (hdd_image, media) with paths normalized."""
    media = (install_media, media_url, media_sha256, product_key)
    if hdd_image is not None:
        if any(value is not None for value in media):
            raise ValueError(
                "hdd_image= is a ready environment; the install "
                "media options do not combine with it")
        return os.fspath(hdd_image), media
    if media_url is not None and media_sha256 is None:
        raise ValueError(
            "media_url= requires media_sha256=: the download is "
            "verified against it, and it identifies the cached "
            "installed image")
    return None, (None if install_media is None
                  else os.fspath(install_media),
                  media_url, media_sha256, product_key)


# The active Windows 95 session opened by start(), or None: its
# disposable directory (holding the staged hard-disk image and every
# run home) plus the recorded environment choice, staged lazily on
# first use.
_session = None


def start(hdd_image=None, install_media=None, media_url=None,
          media_sha256=None, product_key=None):
    """Open a Windows 95 session: one environment choice — a ready
    `hdd_image`, or install media — serving every suite until
    stop(). The image is staged lazily on the first guest use
    (installing from media only when no cached image matches), so
    calling this from a conftest costs nothing when no guest test
    runs. An atexit failsafe sweeps the session if stop() is never
    called."""
    global _session
    if _session is not None:
        raise RuntimeError(
            "a testaferro Windows 95 session is already active")
    hdd_image, media = _checked_choice(
        hdd_image, install_media, media_url, media_sha256,
        product_key)
    root = os.path.join(cache.cache_root(), "win95", "sessions")
    os.makedirs(root, exist_ok=True)
    _session = {
        "dir": tempfile.mkdtemp(prefix="session-", dir=root),
        "hdd_image": hdd_image,
        "media": media,
    }
    # failsafe: sweep at interpreter exit if the caller never calls
    # stop(); an explicit stop() unregisters this again
    atexit.register(stop)


def stop(clear_downloads=False):
    """Close the session opened by start(), sweeping its whole area —
    staged image and every run home. Safe to call with no session
    active. `clear_downloads=True` also removes every cached
    installed image, forcing a full reinstall from media next time —
    deliberately not reachable from `testaferro.stop()`."""
    global _session
    atexit.unregister(stop)
    if _session is not None:
        shutil.rmtree(_session["dir"], ignore_errors=True)
        _session = None
    if clear_downloads:
        root = os.path.join(cache.cache_root(), "win95")
        if os.path.isdir(root):
            for name in os.listdir(root):
                if name.startswith("installed-"):
                    os.remove(os.path.join(root, name))


def _session_image():
    """The active session's staged hard-disk image, staging it on
    first use from the recorded ready image or the cached install of
    the recorded media."""
    image = os.path.join(_session["dir"], "hdd.img")
    if not os.path.exists(image):
        shutil.copy(_session["hdd_image"]
                    or _cached_installed_image(*_session["media"]),
                    image)
    return image


def _media_key(install_media, media_url, media_sha256, product_key):
    """The cache key identifying one installed image: the media's
    content digest — computed from a local ISO, or supplied as
    `media_sha256` for a URL — plus the product key, which shapes
    the install."""
    digest = hashlib.sha256()
    if install_media is not None:
        with open(install_media, "rb") as media:
            for chunk in iter(lambda: media.read(1 << 20), b""):
                digest.update(chunk)
    else:
        digest.update(media_sha256.lower().encode())
    digest.update(b"\0" + (product_key or "").encode())
    return digest.hexdigest()[:12]


def _cached_installed_image(install_media=None, media_url=None,
                            media_sha256=None, product_key=None):
    """testaferro's cached installed Windows 95 image for the given
    media, built through quemados95.install() on first use."""
    if install_media is None and media_url is None:
        raise ValueError(
            "a Windows 95 environment is required (there is no "
            "default): pass hdd_image= or install media "
            "(install_media= or media_url=) to guest_suite() or "
            "testaferro.qemu95.start()")
    root = os.path.join(cache.cache_root(), "win95")
    key = _media_key(install_media, media_url, media_sha256,
                     product_key)
    cached = os.path.join(root, f"installed-{key}.img")
    if not os.path.exists(cached):
        os.makedirs(root, exist_ok=True)
        with tempfile.TemporaryDirectory(
                prefix="install-", dir=root) as home:
            previous = quemados95._home
            quemados95.set_home(home)
            try:
                quemados95.install(media=install_media,
                                   media_url=media_url,
                                   media_sha256=media_sha256,
                                   product_key=product_key)
                shutil.copy(quemados95.hdd_image(), cached + ".part")
            finally:
                quemados95._home = previous
        os.replace(cached + ".part", cached)
    return cached


class Qemu95SuiteBackend(SuiteBackend):
    def __init__(self, exe_path, framework=cpputest, enumerator=None,
                 hdd_image=None, install_media=None, media_url=None,
                 media_sha256=None, product_key=None):
        self._hdd_image, self._media = _checked_choice(
            hdd_image, install_media, media_url, media_sha256,
            product_key)
        self._home = None
        super().__init__(os.fspath(exe_path), run=self._run_in_guest,
                         framework=framework, enumerator=enumerator)

    def start_session(self):
        area = (_session["dir"] if _session
                else os.path.join(cache.cache_root(), "win95"))
        runs = os.path.join(area, "runs")
        os.makedirs(runs, exist_ok=True)
        self._home = tempfile.mkdtemp(prefix="run-", dir=runs)
        dist = os.path.join(self._home, "dist")
        os.makedirs(dist)
        if self._hdd_image is not None:
            source = self._hdd_image
        elif any(value is not None for value in self._media):
            source = _cached_installed_image(*self._media)
        elif _session:
            source = _session_image()
        else:
            # no environment anywhere: ValueError with the options
            source = _cached_installed_image()
        shutil.copy(source, os.path.join(dist, "hdd.img"))

    def stop_session(self):
        if self._home is not None:
            shutil.rmtree(self._home, ignore_errors=True)
            self._home = None

    def _run_in_guest(self, exe_path, args):
        if self._home is None:
            raise RuntimeError("no active session: guest runs happen "
                               "between start_session and stop_session")
        # save/restore the raw value (set_home cannot express None);
        # the DOS binding brackets quemados._home the same way
        previous = quemados95._home
        quemados95.set_home(self._home)
        try:
            return quemados95.run_guest_program(exe_path, args)
        finally:
            quemados95._home = previous
