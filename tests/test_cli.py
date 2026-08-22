# SPDX-FileCopyrightText: 2026 Paul Galbraith
# SPDX-License-Identifier: GPL-3.0-only
"""Unit tests for the lifecycle CLI (F2): each verb is a thin
presentation of a binding function, so what is tested here is the
presentation — the verb reaches the right function with the right
arguments, and says what happened — over a stand-in binding that
never opens a home. The functions themselves are tested with the
binding, in test_reliquary.py."""

import types

import pytest

from testaferro import cli


class _FakeBinding:
    def __init__(self, machines=(), running=()):
        self.machines = list(machines)
        self.running = set(running)
        self.calls = []

    def persistent_machines(self):
        return tuple(self.machines)

    def shutdown(self, name):
        self.calls.append(("shutdown", name))
        self._known(name)
        return name in self.running

    def destroy(self, name):
        self.calls.append(("destroy", name))
        self._known(name)

    def clean(self, system=False):
        self.calls.append(("clean", system))
        return ("X:/cache/runs/run-dead",) if not system else (
            "X:/cache/runs/run-dead", "X:/cache/freedos.qcow2")

    def _known(self, name):
        if name not in {found.name for found in self.machines}:
            raise LookupError(f"no persistent machine is kept as {name!r}")


class _FakeCache:
    @staticmethod
    def cache_root():
        return "X:/cache"


def _machine(name, phase="ready"):
    return types.SimpleNamespace(name=name, phase=phase,
                                 home=f"X:/cache/machines/{name}")


class CliTests:
    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch):
        self.binding = _FakeBinding(
            machines=[_machine("harness"), _machine("lab", "running")],
            running={"lab"})
        import testaferro

        # `main()` imports the binding lazily by attribute, so the
        # stand-in is installed on the package for the call's length.
        monkeypatch.setattr(testaferro, "reliquary", self.binding,
                            raising=False)
        monkeypatch.setattr(testaferro, "cache", _FakeCache, raising=False)
        monkeypatch.setitem(__import__("sys").modules,
                            "testaferro.reliquary", self.binding)
        monkeypatch.setitem(__import__("sys").modules,
                            "testaferro.cache", _FakeCache)

    def test_no_verb_prints_help_and_fails(self, capsys):
        assert cli.main([]) == 2
        assert "VERB" in capsys.readouterr().out

    def test_list_names_the_cache_and_every_machine_with_its_phase(
            self, capsys):
        assert cli.main(["list"]) == 0

        out = capsys.readouterr().out
        assert out.splitlines()[0] == "cache: X:/cache"
        assert "harness  ready" in out
        assert "lab      running" in out
        assert "X:/cache/machines/lab" in out

    def test_list_says_when_nothing_is_kept(self, capsys):
        self.binding.machines.clear()

        assert cli.main(["list"]) == 0
        assert "no persistent machines" in capsys.readouterr().out

    def test_shutdown_reports_stopped_or_not_running(self, capsys):
        assert cli.main(["shutdown", "lab", "harness"]) == 0

        out = capsys.readouterr().out
        assert "lab: stopped" in out
        assert "harness: not running" in out
        assert self.binding.calls == [("shutdown", "lab"),
                                      ("shutdown", "harness")]

    def test_destroy_reaches_the_binding_per_name(self, capsys):
        assert cli.main(["destroy", "harness"]) == 0

        assert self.binding.calls == [("destroy", "harness")]
        assert "harness: destroyed" in capsys.readouterr().out

    def test_an_unknown_name_fails_naming_it(self, capsys):
        assert cli.main(["destroy", "nobody"]) == 1

        assert "'nobody'" in capsys.readouterr().err

    def test_clean_lists_what_went_and_passes_system_through(self, capsys):
        assert cli.main(["clean"]) == 0
        assert self.binding.calls == [("clean", False)]
        assert "removed X:/cache/runs/run-dead" in capsys.readouterr().out

        assert cli.main(["clean", "--system"]) == 0
        assert self.binding.calls[-1] == ("clean", True)
        assert "freedos.qcow2" in capsys.readouterr().out
