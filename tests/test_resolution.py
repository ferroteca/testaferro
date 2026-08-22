# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Tests for the backend-resolution seam.

Every case here calls resolve_backend() directly, with no pytest
entry point above it: the seam is what each entry point shares, so
its rules are proved where they live.
"""

from pathlib import Path
from unittest import mock

import pytest

from testaferro.backend import TestId

from helpers import (FakeBackend, OUTCOMES, new_format_exe_bytes,
                      plain_dos_exe_bytes, requires_reliquary)


class _ResolutionCase:
    """Declarations cleared, a DOS executable to hand, and the DOS
    binding's factory patched so nothing boots."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, clean_environments):
        self.tmp_path = tmp_path

    def _exe(self, content=None):
        path = self.tmp_path / "SUITE.EXE"
        path.write_bytes(plain_dos_exe_bytes() if content is None
                         else content)
        return path

    def _resolved(self, *args, **kwargs):
        """Resolve, with the DOS binding standing in for a real guest,
        and report the options it was handed."""
        from testaferro.resolution import resolve_backend

        with mock.patch("testaferro.reliquary.suite_backend",
                        return_value=FakeBackend(OUTCOMES)) as factory:
            backend = resolve_backend(*args, **kwargs)
        return backend, factory


@requires_reliquary
class BackendResolutionTests(_ResolutionCase):
    def test_the_executables_format_selects_the_binding(self):
        def enumerator():
            return [TestId("Vring", "Wraps")]

        exe = self._exe()

        backend, factory = self._resolved(exe, enumerator=enumerator)

        factory.assert_called_once_with(exe, enumerator=enumerator)
        assert isinstance(backend, FakeBackend)

    def test_declared_environment_supplies_its_configuration(self):
        import testaferro

        image = self.tmp_path / "msdos.img"
        image.write_bytes(b"msdos")
        machine_config = testaferro.config("msdos", boot_image=image)
        exe = self._exe()

        _, factory = self._resolved(exe, environment="msdos")

        factory.assert_called_once_with(exe, machine_config=machine_config)

    def test_a_standard_name_resolves_from_the_catalog(self):
        # Nothing declared: "freedos" is Testaferro's own, and it
        # carries only a platform, so the binding boots exactly what
        # zero configuration boots (D10, U9).
        from testaferro import catalog

        exe = self._exe()

        _, factory = self._resolved(exe, environment="freedos")

        machine_config = factory.call_args.kwargs["machine_config"]
        assert machine_config.platform == "dos"
        assert dict(machine_config.fields) == {"platform": "dos"}
        assert "freedos" in catalog.STANDARD

    def test_a_declaration_wins_over_the_standard_name(self):
        import testaferro

        declared = testaferro.config("freedos", memory=64)
        exe = self._exe()

        _, factory = self._resolved(exe, environment="freedos")

        factory.assert_called_once_with(exe, machine_config=declared)

    def test_unknown_environment_names_both_sources(self):
        from testaferro.resolution import resolve_backend

        exe = self._exe()

        with pytest.raises(
                ValueError,
                match=r"unknown test environment 'msdos'.*standard: freedos"):
            resolve_backend(exe, environment="msdos")

    def test_a_named_environment_rejects_a_second_template(self):
        import testaferro
        from testaferro import environments
        from testaferro.resolution import resolve_backend

        testaferro.config("freedos")
        exe = self._exe()

        with pytest.raises(TypeError, match="cannot be combined"):
            resolve_backend(exe, environment="freedos",
                            machine_config=environments.EnvironmentSpec({}))

    def test_the_ini_search_starts_where_the_caller_says(self):
        # The seam knows nothing about how it was reached: an entry
        # point names the directory, and the facade's call site is
        # only one way to arrive at one.
        exe = self._exe()

        with mock.patch("testaferro.environments.load_config") as load:
            self._resolved(exe, search_from=str(self.tmp_path))

        assert load.call_args.kwargs["search_from"] == str(self.tmp_path)

    def test_unsupported_format_is_rejected_before_any_guest(self):
        from testaferro.resolution import resolve_backend

        header = bytearray(0x40)
        header[0:4] = b"\x7fELF"
        header[4] = 2
        header[5] = 1
        header[0x12:0x14] = (0x3E).to_bytes(2, "little")

        with pytest.raises(
                ValueError, match=r"ELF x86-64.*no test environment here runs"):
            resolve_backend(self._exe(bytes(header)))

    def test_pe_is_rejected_naming_format_and_architecture(self):
        from testaferro.resolution import resolve_backend

        machine = (0x014C).to_bytes(2, "little")
        exe = self._exe(new_format_exe_bytes(b"PE\0\0" + machine))

        with pytest.raises(
                ValueError,
                match=r"Windows x86 \(PE\).*no test environment here runs"):
            resolve_backend(exe)

    def test_an_environment_the_provider_cannot_run_is_rejected(self):
        # The platform reaching here is a blueprint field the tester
        # wrote (P3), so the refusal names the environment that
        # declared it rather than an option nobody typed — and names
        # the provider refusing it, the platforms being the provider's
        # own answer rather than a table kept in the seam.
        import testaferro
        from testaferro.resolution import resolve_backend

        testaferro.config("warp", platform="os2")

        with pytest.raises(
                ValueError,
                match=(r"test environment 'warp' declares platform 'os2', "
                       r"which the 'reliquary' provider does not run; it "
                       r"runs: dos")):
            resolve_backend(self._exe(), environment="warp")

    def test_a_wrong_option_names_what_the_environment_runs_on(self):
        from testaferro.resolution import resolve_backend

        with pytest.raises(
                TypeError,
                match="this environment runs 'dos' on 'reliquary'"):
            resolve_backend(self._exe(), guest_image="OTHER.IMG")


@requires_reliquary
class ProviderDispatchTests(_ResolutionCase):
    """Dispatch keys by provider, and the provider is declared.

    Reliquary is the default of the two bindings built (P1, D11, F20's
    delivery): the axis exists, refuses cleanly, and a declared
    `dosbox-x` reaches its own binding — through the same hyphen
    normalization declaration keys already get, `dosbox-x` not being
    a Python identifier (D16).
    """

    def test_nothing_named_takes_the_default_provider(self):
        exe = self._exe()

        _, factory = self._resolved(exe)

        # It resolved at all, through testaferro.reliquary — the
        # module patched above is the default provider's binding.
        factory.assert_called_once_with(exe)

    def test_naming_the_default_provider_changes_nothing(self):
        exe = self._exe()

        _, factory = self._resolved(exe, provider="reliquary")

        # `provider` is consumed by the seam, never handed onward: a
        # binding is not told which binding it is.
        factory.assert_called_once_with(exe)

    def test_the_provider_name_is_testaferros_own_to_normalize(self):
        # Case-folding our own vocabulary is not touching anyone's
        # document (P3), so a declaration may shout it.
        exe = self._exe()

        _, factory = self._resolved(exe, provider="  ReliQuary ")

        factory.assert_called_once_with(exe)

    def test_an_unknown_provider_is_refused_naming_what_exists(self):
        from testaferro.resolution import resolve_backend

        with pytest.raises(
                ValueError,
                match=(r"unknown provider 'vagrant'; testaferro binds: "
                       r"dosbox-x, reliquary")):
            resolve_backend(self._exe(), provider="vagrant")

    def test_a_declared_second_provider_selects_its_own_binding(self):
        # `dosbox-x` is how a declaration spells it; the module is
        # `dosbox_x`, hyphens having no Python spelling (D16).
        from testaferro.resolution import resolve_backend

        exe = self._exe()

        with mock.patch("testaferro.dosbox_x.suite_backend",
                        return_value=FakeBackend(OUTCOMES)) as factory:
            backend = resolve_backend(exe, provider="DOSBox-X")

        factory.assert_called_once_with(exe)
        assert isinstance(backend, FakeBackend)

    def test_the_standard_dosbox_x_environment_selects_its_binding(self):
        # A catalog name carries its provider like any declaration
        # (F21, P17): naming "dosbox-x" reaches the dosbox_x binding
        # with the authored declaration in hand.
        from testaferro.resolution import resolve_backend

        exe = self._exe()

        with mock.patch("testaferro.dosbox_x.suite_backend",
                        return_value=FakeBackend(OUTCOMES)) as factory:
            resolve_backend(exe, environment="dosbox-x")

        machine_config = factory.call_args.kwargs["machine_config"]
        assert machine_config.provider == "dosbox-x"
        assert machine_config.cpu == {"cycles": "max"}

    def test_an_unknown_provider_is_never_imported(self):
        # The name selects a sibling module (D16), so the set of known
        # providers is also the gate on what may become an import.
        from testaferro.resolution import resolve_backend

        with pytest.raises(ValueError):
            resolve_backend(self._exe(), provider="cache")

    def test_a_declared_environment_carries_its_own_provider(self):
        import testaferro

        image = self.tmp_path / "msdos.img"
        image.write_bytes(b"msdos")
        declared = testaferro.config("msdos", provider="reliquary",
                                     boot_image=image)
        exe = self._exe()

        _, factory = self._resolved(exe, environment="msdos")

        assert declared.provider == "reliquary"
        factory.assert_called_once_with(exe, machine_config=declared)

    def test_provider_and_a_named_environment_do_not_combine(self):
        # The environment is the one place a provider is named (P2),
        # so an option beside one is refused rather than ranked
        # against it.
        import testaferro
        from testaferro.resolution import resolve_backend

        testaferro.config("freedos")

        with pytest.raises(
                TypeError,
                match=r"provider cannot be combined with a named environment"):
            resolve_backend(self._exe(), environment="freedos",
                            provider="reliquary")

    def test_a_declared_provider_is_refused_when_unknown(self):
        import testaferro
        from testaferro.resolution import resolve_backend

        testaferro.config("msdos", provider="vagrant")

        with pytest.raises(ValueError, match="unknown provider"):
            resolve_backend(self._exe(), environment="msdos")


@requires_reliquary
class GuestSessionResolutionTests(_ResolutionCase):
    """resolve_guest_session(): the same environment/provider seam as
    resolve_backend(), minus the executable it exists to classify
    (U10, F18) — every case here names none.
    """

    def _resolved(self, *args, **kwargs):
        from testaferro.resolution import resolve_guest_session

        with mock.patch("testaferro.reliquary.guest_session",
                        return_value="a guest session") as factory:
            session = resolve_guest_session(*args, **kwargs)
        return session, factory

    def test_nothing_named_takes_the_default_provider_with_no_options(self):
        session, factory = self._resolved()

        factory.assert_called_once_with()
        assert session == "a guest session"

    def test_files_and_other_options_pass_through_untouched(self):
        _, factory = self._resolved(files=["DRIVER.COM"], timeout=5)

        factory.assert_called_once_with(files=["DRIVER.COM"], timeout=5)

    def test_declared_environment_supplies_its_configuration(self):
        import testaferro

        image = self.tmp_path / "msdos.img"
        image.write_bytes(b"msdos")
        machine_config = testaferro.config("msdos", boot_image=image)

        _, factory = self._resolved(environment="msdos")

        factory.assert_called_once_with(machine_config=machine_config)

    def test_a_standard_name_resolves_from_the_catalog(self):
        from testaferro import catalog

        _, factory = self._resolved(environment="freedos")

        machine_config = factory.call_args.kwargs["machine_config"]
        assert machine_config.platform == "dos"
        assert "freedos" in catalog.STANDARD

    def test_unknown_environment_names_both_sources(self):
        from testaferro.resolution import resolve_guest_session

        with pytest.raises(
                ValueError,
                match=r"unknown test environment 'msdos'.*standard: freedos"):
            resolve_guest_session(environment="msdos")

    def test_a_named_environment_rejects_a_second_template(self):
        import testaferro
        from testaferro import environments
        from testaferro.resolution import resolve_guest_session

        testaferro.config("freedos")

        with pytest.raises(TypeError, match="cannot be combined"):
            resolve_guest_session(
                environment="freedos",
                machine_config=environments.EnvironmentSpec({}))

    def test_provider_and_a_named_environment_do_not_combine(self):
        import testaferro
        from testaferro.resolution import resolve_guest_session

        testaferro.config("freedos")

        with pytest.raises(
                TypeError,
                match=r"provider cannot be combined with a named environment"):
            resolve_guest_session(environment="freedos", provider="reliquary")

    def test_an_environment_the_provider_cannot_run_is_rejected(self):
        import testaferro
        from testaferro.resolution import resolve_guest_session

        testaferro.config("warp", platform="os2")

        with pytest.raises(
                ValueError,
                match=(r"test environment 'warp' declares platform 'os2', "
                       r"which the 'reliquary' provider does not run; it "
                       r"runs: dos")):
            resolve_guest_session(environment="warp")

    def test_an_unknown_provider_is_refused_naming_what_exists(self):
        from testaferro.resolution import resolve_guest_session

        with pytest.raises(
                ValueError,
                match=(r"unknown provider 'vagrant'; testaferro binds: "
                       r"dosbox-x, reliquary")):
            resolve_guest_session(provider="vagrant")

    def test_the_batch_provider_refuses_guest_sessions_with_the_reason(self):
        # The refusal is the binding's own voice (U10, D27): the seam
        # dispatches to it exactly as it would for a suite, and what
        # comes back is why this provider cannot serve a scripted
        # interaction — not a resolution error about a missing name.
        from testaferro.resolution import resolve_guest_session

        with pytest.raises(ValueError, match="runs suites only"):
            resolve_guest_session(provider="dosbox-x")

    def test_a_wrong_option_names_what_the_environment_runs_on(self):
        from testaferro.resolution import resolve_guest_session

        with pytest.raises(
                TypeError,
                match="this environment runs on 'reliquary'"):
            resolve_guest_session(guest_image="OTHER.IMG")

    def test_the_ini_search_starts_where_the_caller_says(self):
        with mock.patch("testaferro.environments.load_config") as load:
            self._resolved(search_from=str(self.tmp_path))

        assert load.call_args.kwargs["search_from"] == str(self.tmp_path)
