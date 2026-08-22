# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""The lifecycle CLI: verbs over machines and caches, never over test
runs (F2, D9).

    testaferro list                 what is kept, and where
    testaferro shutdown NAME...     stop a persistent machine left up
    testaferro destroy NAME...      discard a persistent machine
    testaferro clean [--system]     sweep what killed runs left behind

Running tests is pytest's own command line and nothing here touches
it: D9 retired the wrapper, and what survives is the one thing pytest
has no verb for — the state a run leaves on this host on purpose.
`persist=` asks for a machine to outlive its runs, and U8 asks that
whatever outlives them be enumerable and removable (P5); these verbs
are that enumeration and that removal. Each one is a thin presentation
of a binding function (`testaferro.reliquary.persistent_machines()`,
`shutdown()`, `destroy()`, `clean()`), so the embedding API can do the
same things without a shell.

Installed as the `testaferro` console script (`[project.scripts]`),
which is the only executable this distribution adds to a PATH.
"""

from __future__ import annotations

import argparse
import sys


def main(argv=None):
    """Entry point. Returns the process exit status."""
    parser = _parser()
    args = parser.parse_args(argv)
    if args.verb is None:
        parser.print_help()
        return 2
    # The binding is imported here and not above: `--help` must not
    # cost a provider import, and every verb below is reliquary's.
    from . import cache
    from . import reliquary as binding

    try:
        return args.run(args, binding, cache)
    except LookupError as error:
        print(f"testaferro: {error}", file=sys.stderr)
        return 1


def _parser():
    parser = argparse.ArgumentParser(
        prog="testaferro",
        description="Lifecycle verbs over the machines and caches "
                    "testaferro keeps on this host. Running a suite is "
                    "pytest's own command line: pytest tests/SUITE.EXE")
    verbs = parser.add_subparsers(dest="verb", metavar="VERB")

    listing = verbs.add_parser(
        "list", help="list the persistent machines kept here, with the "
                     "phase each is recorded in, and where the cache is")
    listing.set_defaults(run=_list)

    shutdown = verbs.add_parser(
        "shutdown", help="stop a persistent machine a run left up — "
                         "one that died with it running, typically")
    shutdown.add_argument("names", nargs="+", metavar="NAME")
    shutdown.set_defaults(run=_shutdown)

    destroy = verbs.add_parser(
        "destroy", help="destroy a persistent machine: stop it if "
                        "running, discard its disks, remove its home")
    destroy.add_argument("names", nargs="+", metavar="NAME")
    destroy.set_defaults(run=_destroy)

    clean = verbs.add_parser(
        "clean", help="sweep run and guest homes killed runs left "
                      "behind; persistent machines are never touched")
    clean.add_argument(
        "--system", action="store_true",
        help="also drop the installed FreeDOS system disk, which the "
             "next zero-configuration run rebuilds (minutes)")
    clean.set_defaults(run=_clean)
    return parser


def _list(args, binding, cache):
    print(f"cache: {cache.cache_root()}")
    machines = binding.persistent_machines()
    if not machines:
        print("no persistent machines are kept")
        return 0
    width = max(len(found.name) for found in machines)
    for found in machines:
        phase = found.phase or "(no machine)"
        print(f"{found.name:<{width}}  {phase:<12}  {found.home}")
    return 0


def _shutdown(args, binding, cache):
    for name in args.names:
        if binding.shutdown(name):
            print(f"{name}: stopped")
        else:
            print(f"{name}: not running")
    return 0


def _destroy(args, binding, cache):
    for name in args.names:
        binding.destroy(name)
        print(f"{name}: destroyed")
    return 0


def _clean(args, binding, cache):
    removed = binding.clean(system=args.system)
    for path in removed:
        print(f"removed {path}")
    if not removed:
        print("nothing to clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
