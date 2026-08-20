# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only

import pytest


@pytest.fixture
def clean_environments():
    """A cleared declaration registry, restored empty on exit too.

    `testaferro.config()` writes into a process-global registry
    (`testaferro.environments`); a case that declares one requests
    this fixture so the declaration cannot leak into the next test.
    """
    from testaferro import environments

    environments._clear_for_tests()
    yield
    environments._clear_for_tests()
