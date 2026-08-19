<!--
SPDX-FileCopyrightText: 2026 Paul Galbraith
SPDX-License-Identifier: GPL-3.0-only
-->

# Pledged features

> **Status:** pledged — owed by the project, and not yet delivered.
> The project will do these and says nothing about when: **the
> absence of order is uniform**, and whoever picks work up picks
> whatever they like. The one ordering that binds runs *inside* a
> feature — the work items delivering it have to be done to complete
> it.

**F-numbers are the handles of work, so they evaporate on delivery**:
the item stops existing, its number retires unreused, and gaps in the
sequence are history rather than a promise. **A feature here fits in
one sprint** — the bound bites at the pledge, which is why the large
and shapeless entries stay in
[../proposed/FEATURES.md](../proposed/FEATURES.md). Every entry cites
what demands it.

## F18 — `guest_session()`, a lower-level guest primitive

Serves **U10** (pledged). `guest_suite()` is deliberately shaped
around one thing: a suite executable that self-enumerates and
self-reports named sub-tests — the CppUTest model,
`list_tests()`/`run_test()`/`run_all()` under the hood, via a
framework adapter's `list_argv()`/`run_all_argv()`/`parse_run()`
grammar (U1, U6). That shape does not fit a guest-driven test that is
a linear script instead: no natural `Group.Name` decomposition,
nothing to enumerate, nothing for an adapter to parse.

`ReliquarySuiteBackend` (`testaferro/reliquary.py`) already has
everything a scripted test needs, entirely internally: the
zero-config FreeDOS guest built once and cached, a fresh disposable
copy-on-write overlay per guest session, host files staged onto a
live vvfat work drive (`files=`), and `reliquary.Session.exec()` to
run one guest command and read its output back (U2). None of it is
reachable except by going through the suite/framework abstraction —
there is no way today to get a live guest handle and call `.exec()`
a few times in a row from a plain pytest test.

`guest_session()` is a context manager exposing that provisioning
directly, taking the same `files=`/`environment=`/`machine_config=`
`guest_suite()` already does, and handing back a guest handle
whose `exec(command, timeout=None)` mirrors
`reliquary.Session.exec()`'s contract. The provisioning internals —
image cache, overlay, vvfat staging, readiness wait — are shared with
`guest_suite()` rather than duplicated; this is a refactor of
`ReliquarySuiteBackend`'s existing internals into a shape both
entry points draw on, not a second implementation living beside the
first. Whether the handle also carries `send_text()`/`wait_text()`/
`screen_text()`, for interactive-style driving that reacts to guest
state rather than just running one command and reading its result —
mirroring what `reliquary.Session` already exposes at that level — is
open; the minimal shape is `exec()` alone.

Purely additive: `guest_suite()` stays the right tool for anything
shaped as a suite of named tests. Joins the embedding API, the first
interface, and lands through the interface-change rule on that
ground alone — no principle or use case needs to change to admit it,
only U10, pledged alongside this feature.

Nothing here waits on a provider capability the way F9 did: the
whole of it is Testaferro's own refactor and one new entry point, so
the debt is entirely Testaferro's own to pay, not gated on anything
outside it.
