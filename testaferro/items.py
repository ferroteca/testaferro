# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: BSD-3-Clause
"""The pytest items testaferro produces: what one is called, and how
a guest failure reads.

Both entry points surface the same guest tests — the embedding facade
as parametrized cases under a `guest_suite()` call, the collection
plugin as items under the executable's own node — so the spellings
they share live here rather than in whichever one happened to need
them first.

This is a world-facing contract whether or not it looks like an API:
consumers write node ids into CI invocations and IDE run
configurations, so the two functions below are the fifth interface
made concrete.
"""

from __future__ import annotations


def item_id(test_id):
    """The name one guest test carries as a pytest item.

    A dash join, not `str(TestId)`: a dot inside an item name breaks
    IDE tree→target mapping (dots are hierarchy separators there),
    turning run-this-item into run-the-whole-file. The plugin's
    `suite.exe::Group-Name` and the facade's `[Group-Name]` are the
    same rule read under different parents.
    """
    return f"{test_id.group}-{test_id.name}"


def failure_text(outcome):
    """How a failed guest test reads.

    The guest side's own file, line and assertion message — what the
    machine that ran the test actually reported — never a traceback
    into testaferro, which would describe the courier rather than the
    failure. A guest that named no location gets no invented one.
    """
    where = f"{outcome.file}:{outcome.line}: " if outcome.file else ""
    return f"guest test failed: {where}{outcome.message}"
