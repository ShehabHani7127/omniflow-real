"""Tests for locating the pinned SUMO installation."""

from __future__ import annotations

import importlib.metadata
import os
import subprocess

import pytest

import omniflow
from omniflow import sumo_tools


def test_package_has_a_version():
    assert omniflow.__version__


def test_importing_omniflow_points_sumo_home_at_the_pinned_install():
    assert os.environ["SUMO_HOME"] == str(sumo_tools.sumo_home())


def test_activate_pinned_sumo_overrides_a_foreign_sumo_home(monkeypatch):
    monkeypatch.setenv("SUMO_HOME", "/some/other/sumo/from/an/old/install")
    assert sumo_tools.activate_pinned_sumo() == sumo_tools.sumo_home()
    assert os.environ["SUMO_HOME"] == str(sumo_tools.sumo_home())


@pytest.mark.parametrize("name", ["sumo", "netconvert", "duarouter"])
def test_sumo_binary_finds_core_programs(name):
    assert sumo_tools.sumo_binary(name).is_file()


def test_sumo_binary_ignores_a_foreign_sumo_home(monkeypatch):
    monkeypatch.setenv("SUMO_HOME", "/some/other/sumo/from/an/old/install")
    assert sumo_tools.sumo_home() in sumo_tools.sumo_binary("sumo").parents


def test_sumo_binary_rejects_unknown_program():
    with pytest.raises(FileNotFoundError, match="not-a-sumo-program"):
        sumo_tools.sumo_binary("not-a-sumo-program")


@pytest.mark.parametrize("tool", ["randomTrips.py", "routeSampler.py", "osmGet.py"])
def test_sumo_tool_finds_scripts_needed_by_later_milestones(tool):
    assert sumo_tools.sumo_tool(tool).is_file()


def test_sumo_tool_rejects_unknown_script():
    with pytest.raises(FileNotFoundError, match=r"noSuchTool\.py"):
        sumo_tools.sumo_tool("noSuchTool.py")


def test_sumo_version_matches_every_sumo_package():
    version = sumo_tools.sumo_version()
    for name in sumo_tools.SUMO_DISTRIBUTIONS:
        assert importlib.metadata.version(name) == version


def test_sumo_version_refuses_mixed_versions(monkeypatch):
    fake = {"eclipse-sumo": "1.28.0", "sumolib": "1.28.0", "traci": "1.27.0", "libsumo": "1.28.0"}
    monkeypatch.setattr(importlib.metadata, "version", fake.__getitem__)
    with pytest.raises(RuntimeError, match="mixed versions"):
        sumo_tools.sumo_version()


@pytest.mark.sumo
def test_the_sumo_program_itself_reports_the_pinned_version():
    completed = subprocess.run(
        [str(sumo_tools.sumo_binary("sumo")), "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert sumo_tools.sumo_version() in completed.stdout.splitlines()[0]


def test_get_connection_rejects_unknown_backend():
    with pytest.raises(ValueError, match="carrier-pigeon"):
        sumo_tools.get_connection("carrier-pigeon")  # type: ignore[arg-type]
