"""Tests on the committed DeLand data: snapshot, network and inventory agree.

These protect the reproducibility promise: the committed network must be
exactly what the build script makes from the committed snapshot.
"""

from __future__ import annotations

import csv

import pytest

from omniflow.network.area import DELAND_STUDY_AREA, EXPECTED_SIGNALS
from omniflow.network.build import build_network, check_network_loads
from omniflow.network.inventory import compare_with_expected, read_signal_inventory
from omniflow.network.osm import verify_snapshot
from omniflow.paths import DELAND_NET, M1_RESULTS_DIR, OSM_SNAPSHOT, PATCH_DIR

pytestmark = pytest.mark.sumo


def test_committed_snapshot_is_unchanged_since_download():
    meta = verify_snapshot(OSM_SNAPSHOT)
    assert "OpenStreetMap" in str(meta["copyright"])


def test_rebuilding_from_the_snapshot_reproduces_the_committed_network(tmp_path):
    rebuilt = tmp_path / "deland.net.xml"
    build_network(OSM_SNAPSHOT, rebuilt, DELAND_STUDY_AREA, PATCH_DIR)
    assert rebuilt.read_bytes() == DELAND_NET.read_bytes(), (
        "The committed network is out of date: run scripts/m1_build_network.py"
    )


def test_committed_network_loads_in_sumo_without_warnings():
    assert check_network_loads(DELAND_NET, seconds=10).warnings == ()


def test_committed_inventory_matches_the_network():
    fresh = read_signal_inventory(DELAND_NET)
    with (M1_RESULTS_DIR / "signals.csv").open(encoding="utf-8") as handle:
        committed = list(csv.DictReader(handle))
    assert [r["tls_id"] for r in committed] == [r.tls_id for r in fresh]
    assert [r["name"] for r in committed] == [r.name for r in fresh]


def test_every_fdot_listed_woodland_signal_is_in_the_network():
    matches = compare_with_expected(read_signal_inventory(DELAND_NET), EXPECTED_SIGNALS)
    assert [m.expected.street_b for m in matches if m.signal is None] == []


def test_woodland_and_new_york_allows_only_straight_movements():
    """OSM tags 'only straight on' on all four approaches (relations 392814-392817)."""
    [signal] = [
        r for r in read_signal_inventory(DELAND_NET) if r.name == "Woodland Blvd & New York Ave"
    ]
    assert (signal.left, signal.right, signal.uturn) == (0, 0, 0)
    assert signal.straight == 4
