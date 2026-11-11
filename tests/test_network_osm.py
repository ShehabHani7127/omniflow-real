"""Tests for downloading, freezing and clipping OpenStreetMap data (no network access)."""

from __future__ import annotations

import gzip
import json
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

import pytest

from omniflow.network.area import BoundingBox
from omniflow.network.osm import (
    clip_to_bbox,
    download_snapshot,
    inside_runs,
    meta_path,
    named_area_center,
    summarize_osm,
    verify_snapshot,
)

TEST_BOX = BoundingBox(south=29.025, west=-81.305, north=29.035, east=-81.295)
FIXED_TIME = datetime(2026, 11, 11, 12, 0, 0, tzinfo=UTC)


def fake_fetch(body: bytes):
    """Return a fetch function that records the URL and returns ``body``."""
    calls = []

    def fetch(url: str) -> bytes:
        calls.append(url)
        return body

    fetch.calls = calls
    return fetch


def test_summarize_counts_elements_and_reads_the_licence():
    xml = b'<osm license="ODbL"><node id="1"/><node id="2"/><way id="3"/></osm>'
    summary = summarize_osm(xml)
    assert (summary.nodes, summary.ways, summary.relations) == (2, 1, 0)
    assert summary.attributes["license"] == "ODbL"


@pytest.mark.parametrize("body", [b"You requested too many nodes", b"<html></html>"])
def test_summarize_rejects_anything_that_is_not_osm(body):
    with pytest.raises(ValueError):
        summarize_osm(body)


def test_download_writes_snapshot_and_provenance(tmp_path, tiny_osm_file):
    tiny = tiny_osm_file.read_bytes()
    fetch = fake_fetch(tiny)
    target = tmp_path / "tiny.osm.xml.gz"

    meta = download_snapshot(TEST_BOX, target, fetch=fetch, now=lambda: FIXED_TIME)

    assert fetch.calls == [
        "https://api.openstreetmap.org/api/0.6/map?bbox=-81.305,29.025,-81.295,29.035"
    ]
    assert gzip.decompress(target.read_bytes()) == tiny
    assert meta["downloaded_at_utc"] == "2026-11-11T12:00:00Z"
    assert (meta["nodes"], meta["ways"], meta["relations"]) == (6, 4, 1)
    assert json.loads(meta_path(target).read_text()) == meta
    assert verify_snapshot(target) == meta


def test_same_download_gives_a_byte_identical_file(tmp_path, tiny_osm_file):
    first, second = tmp_path / "a.osm.xml.gz", tmp_path / "b.osm.xml.gz"
    for target in (first, second):
        download_snapshot(TEST_BOX, target, fetch=fake_fetch(tiny_osm_file.read_bytes()))
    assert first.read_bytes() == second.read_bytes()


def test_download_refuses_a_wrong_file_name(tmp_path, tiny_osm_file):
    with pytest.raises(ValueError, match=r"\.osm\.xml\.gz"):
        download_snapshot(
            TEST_BOX, tmp_path / "x.xml", fetch=fake_fetch(tiny_osm_file.read_bytes())
        )


def test_verify_detects_a_changed_snapshot(tmp_path, tiny_osm_file):
    tiny = tiny_osm_file.read_bytes()
    target = tmp_path / "tiny.osm.xml.gz"
    download_snapshot(TEST_BOX, target, fetch=fake_fetch(tiny))
    target.write_bytes(gzip.compress(tiny.replace(b"Oak", b"Elm")))
    with pytest.raises(ValueError, match="changed after download"):
        verify_snapshot(target)


@pytest.mark.parametrize(
    ("flags", "runs"),
    [
        ([], []),
        ([False, False], []),
        ([True, True, True], [(0, 3)]),
        ([False, True, True, False, True], [(1, 3), (4, 5)]),
    ],
)
def test_inside_runs(flags, runs):
    assert inside_runs(flags) == runs


def test_clipping_cuts_a_road_back_at_the_edge_of_the_box(tiny_osm_file):
    clipped, stats = clip_to_bbox(tiny_osm_file.read_bytes(), TEST_BOX)
    root = ET.fromstring(clipped)

    node_ids = {n.get("id") for n in root.iter("node")}
    assert "4" not in node_ids  # the far end of South Main Street lies outside
    south_main = next(w for w in root.iter("way") if w.get("id") == "11")
    assert [nd.get("ref") for nd in south_main.iter("nd")] == ["1", "3"]
    assert (stats.nodes_kept, stats.nodes_removed) == (5, 1)
    assert (stats.roads_shortened, stats.roads_removed, stats.roads_split) == (1, 0, 0)
    assert len(root.findall("relation")) == 1  # relations are kept unchanged


def test_clipping_keeps_the_longest_piece_of_a_road_that_leaves_and_returns():
    xml = b"""<osm>
      <node id="1" lat="0.1" lon="0.1"/><node id="2" lat="0.2" lon="0.2"/>
      <node id="3" lat="5.0" lon="5.0"/>
      <node id="4" lat="0.3" lon="0.3"/><node id="5" lat="0.4" lon="0.4"/>
      <node id="6" lat="0.5" lon="0.5"/>
      <way id="9"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="5"/><nd ref="6"/>
        <tag k="highway" v="residential"/></way>
      <way id="8"><nd ref="3"/><nd ref="1"/><tag k="highway" v="residential"/></way>
      <way id="7"><nd ref="1"/><nd ref="2"/><nd ref="3"/><tag k="building" v="yes"/></way>
    </osm>"""
    box = BoundingBox(south=0.0, west=0.0, north=1.0, east=1.0)

    clipped, stats = clip_to_bbox(xml, box)
    ways = {
        w.get("id"): [nd.get("ref") for nd in w.iter("nd")]
        for w in ET.fromstring(clipped).iter("way")
    }

    assert ways["9"] == ["4", "5", "6"]  # the longer of the two inside pieces
    assert "8" not in ways  # only one point inside: removed
    assert (stats.roads_split, stats.roads_removed, stats.roads_shortened) == (1, 1, 1)


def test_named_area_center(tmp_path):
    xml = b"""<osm>
      <node id="1" lat="1.0" lon="10.0"/><node id="2" lat="3.0" lon="12.0"/>
      <way id="5"><nd ref="1"/><nd ref="2"/><tag k="name" v="Campus"/></way>
    </osm>"""
    path = tmp_path / "a.osm.xml.gz"
    path.write_bytes(gzip.compress(xml))
    assert named_area_center(path, "Campus") == (2.0, 11.0)
    assert named_area_center(path, "Nowhere") is None
