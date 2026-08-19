# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Tests for testaferro.guest_session(), the embedding entry point for
a scripted guest interaction (U10): resolution is proved in
test_resolution.py's GuestSessionResolutionTests, and the guest
provisioning itself in test_reliquary.py's GuestSessionTests. What is
this module's own is the one thing only a call from a caller's module
can supply — the call site testaferro.ini search starts from, the
same as guest_suite()'s own (test_facade.py).
"""

import importlib.util
from pathlib import Path
import unittest
from unittest import mock

RELIQUARY_AVAILABLE = importlib.util.find_spec("reliquary") is not None


@unittest.skipUnless(RELIQUARY_AVAILABLE, "reliquary is not installed")
class GuestSessionEntryPointTests(unittest.TestCase):
    def setUp(self):
        from testaferro import environments

        environments._clear_for_tests()
        self.addCleanup(environments._clear_for_tests)

    def test_searches_for_ini_from_the_call_site(self):
        import testaferro

        with mock.patch("testaferro.environments.load_config") as load:
            with mock.patch("testaferro.reliquary.guest_session",
                            return_value="a guest session"):
                testaferro.guest_session()

        load.assert_called_once()
        self.assertEqual(
            Path(load.call_args.kwargs["search_from"]).resolve(),
            Path(__file__).resolve().parent)

    def test_options_reach_the_binding_untouched(self):
        import testaferro

        with mock.patch("testaferro.reliquary.guest_session",
                        return_value="a guest session") as factory:
            session = testaferro.guest_session(files=["DRIVER.COM"])

        factory.assert_called_once_with(files=["DRIVER.COM"])
        self.assertEqual(session, "a guest session")


if __name__ == "__main__":
    unittest.main()
