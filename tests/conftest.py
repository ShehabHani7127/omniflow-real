"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from omniflow.toy import ToyScenario, build_toy_scenario


@pytest.fixture(scope="session")
def toy_scenario(tmp_path_factory: pytest.TempPathFactory) -> ToyScenario:
    """Build the one-intersection toy scenario once and share it between tests."""
    out_dir: Path = tmp_path_factory.mktemp("toy")
    return build_toy_scenario(out_dir)
