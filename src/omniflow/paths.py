"""Standard folders of the repository, defined in one place.

The package is installed in "editable" mode (``uv sync`` does this), so the
code runs from the repository itself and these folders can be found relative
to this file.
"""

from __future__ import annotations

from pathlib import Path

#: The repository root (the folder that contains ``pyproject.toml``).
REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = REPO_ROOT / "data"
NETWORK_DIR = REPO_ROOT / "network"
RESULTS_DIR = REPO_ROOT / "results"

#: The frozen OpenStreetMap snapshot of the study area (milestone M1).
OSM_SNAPSHOT = DATA_DIR / "osm" / "deland_downtown.osm.xml.gz"
#: The SUMO network built from it.
DELAND_NET = NETWORK_DIR / "deland.net.xml"
#: Edge-type overrides used by netconvert.
SPEED_DEFAULTS_TYPE_FILE = NETWORK_DIR / "config" / "florida_speed_defaults.typ.xml"
#: Folder with evidence-based corrections to the network.
PATCH_DIR = NETWORK_DIR / "patches"
#: Generated tables, figures and reports of milestone M1.
M1_RESULTS_DIR = RESULTS_DIR / "m1_network"
