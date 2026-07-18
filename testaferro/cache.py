# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""testaferro's durable filespace, shared by the guest bindings."""

from __future__ import annotations

import os


def cache_root():
    """testaferro's own filespace: each guest binding's image cache
    plus its disposable per-session runner homes (under runs/; stale
    ones from killed processes can be deleted freely)."""
    if os.name == "nt":
        base = (os.environ.get("LOCALAPPDATA")
                or os.path.join(os.path.expanduser("~"),
                                "AppData", "Local"))
    else:
        base = (os.environ.get("XDG_CACHE_HOME")
                or os.path.join(os.path.expanduser("~"), ".cache"))
    return os.path.join(base, "testaferro")
