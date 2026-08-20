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

from pathlib import Path
from unittest import mock

from helpers import requires_reliquary


@requires_reliquary
class GuestSessionEntryPointTests:
    def test_searches_for_ini_from_the_call_site(self, clean_environments):
        import testaferro

        with mock.patch("testaferro.environments.load_config") as load:
            with mock.patch("testaferro.reliquary.guest_session",
                            return_value="a guest session"):
                testaferro.guest_session()

        load.assert_called_once()
        assert (Path(load.call_args.kwargs["search_from"]).resolve()
                == Path(__file__).resolve().parent)

    def test_options_reach_the_binding_untouched(self, clean_environments):
        import testaferro

        with mock.patch("testaferro.reliquary.guest_session",
                        return_value="a guest session") as factory:
            session = testaferro.guest_session(files=["DRIVER.COM"])

        factory.assert_called_once_with(files=["DRIVER.COM"])
        assert session == "a guest session"
