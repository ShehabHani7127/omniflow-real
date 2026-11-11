"""Tests for building a SUMO network from OSM data, on the hand-made extract.

The tiny extract (see ``conftest.py``) has one signalized intersection of
"Main Street" and "Oak Avenue"; South Main Street runs on far outside the test
box; and traffic from the north may only go straight on.
"""

from __future__ import annotations

import gzip

import pytest
import sumolib

from omniflow.network.area import BoundingBox
from omniflow.network.build import (
    NETCONVERT_OPTIONS,
    BuildReport,
    build_network,
    check_network_loads,
    find_patches,
    netconvert_command,
    provenance_header,
    replace_header,
    type_files,
)
from omniflow.network.inventory import read_signal_inventory
from omniflow.paths import REPO_ROOT

TEST_BOX = BoundingBox(south=29.025, west=-81.305, north=29.035, east=-81.295)


def test_every_option_has_a_reason():
    assert all(len(option.reason) > 20 for option in NETCONVERT_OPTIONS)
    assert len({option.flag for option in NETCONVERT_OPTIONS}) == len(NETCONVERT_OPTIONS)


def test_options_with_negative_values_are_attached_with_equals(tmp_path):
    command = netconvert_command(tmp_path / "in.osm.xml", tmp_path / "out.net.xml")
    assert "--keep-edges.components=1" in command


def test_florida_speed_defaults_load_after_sumos_type_map():
    sumo_types, florida = type_files()
    assert sumo_types.name == "osmNetconvert.typ.xml"
    assert florida.name == "florida_speed_defaults.typ.xml"
    assert sumo_types.is_file()
    assert florida.is_file()


def test_header_has_no_absolute_paths_and_no_double_dash(tmp_path):
    header = provenance_header(REPO_ROOT / "data" / "osm" / "x.osm.xml.gz", TEST_BOX, [])
    assert "--" not in header.removeprefix("<!--").removesuffix("-->")
    assert str(REPO_ROOT) not in header
    assert "data/osm/x.osm.xml.gz" in header
    assert "<SUMO_HOME>/data/typemap/osmNetconvert.typ.xml" in header


def test_replace_header_swaps_only_the_first_comment():
    body = '\n<net a="1">\n<!-- keep -->\n</net>'
    xml = '<?xml version="1.0"?>\n<!-- old, 2026-11-11 /home/me -->' + body
    assert replace_header(xml, "<!-- new -->") == '<?xml version="1.0"?>\n<!-- new -->' + body
    with pytest.raises(ValueError):
        replace_header("<net/>", "<!-- new -->")


def test_find_patches_groups_files_by_kind(tmp_path):
    for name in ("b.edg.xml", "a.edg.xml", "x.con.xml", "README.md"):
        (tmp_path / name).write_text("<x/>")
    found = find_patches(tmp_path)
    assert [p.name for p in found["--edge-files"]] == ["a.edg.xml", "b.edg.xml"]
    assert [p.name for p in found["--connection-files"]] == ["x.con.xml"]
    assert find_patches(tmp_path / "missing") == {}


def test_repeated_warnings_are_counted_by_their_true_total():
    report = BuildReport(
        net_file=None,  # type: ignore[arg-type]
        warnings=[
            "Warning: No way found for reference '1' in relation '2'",
            "Warning: No way found for reference '3' in relation '4'",
            "Warning: 7 total messages of type: No way found for reference '%' in relation '%'",
            "Warning: Found sharp turn with radius 8.47 at the start of edge 'e1'.",
        ],
    )
    kinds = report.warning_kinds()
    assert kinds["Warning: No way found for reference '#' in relation '#'"] == 7
    assert kinds["Warning: Found sharp turn with radius # at the start of edge '#'."] == 1
    assert report.warning_count == 8


@pytest.fixture(scope="module")
def tiny_net(tiny_osm_file, tmp_path_factory):
    net_file = tmp_path_factory.mktemp("net") / "tiny.net.xml.gz"
    report = build_network(tiny_osm_file, net_file, TEST_BOX)
    return net_file, report


@pytest.mark.sumo
def test_tiny_network_builds_and_loads_in_sumo(tiny_net):
    net_file, report = tiny_net
    assert report.clip is not None
    assert report.clip.roads_shortened == 1
    assert check_network_loads(net_file, seconds=10).warnings == ()


@pytest.mark.sumo
def test_clipping_keeps_the_network_inside_the_box(tiny_net):
    net_file, _ = tiny_net
    net = sumolib.net.readNet(str(net_file))
    for node in net.getNodes():
        lon, lat = net.convertXY2LonLat(*node.getCoord())
        assert TEST_BOX.contains(lat, lon), node.getID()


@pytest.mark.sumo
def test_streets_get_names_speeds_and_the_turn_restriction(tiny_net):
    net_file, _ = tiny_net
    [signal] = read_signal_inventory(net_file)

    assert signal.name == "Main St & Oak Ave"  # the more important street first
    assert signal.approaches == 4
    net = sumolib.net.readNet(str(net_file))
    oak = [e for e in net.getEdges() if "Oak" in e.getName()]
    assert oak
    assert all(e.getSpeed() == pytest.approx(13.41) for e in oak)  # Florida 30 mph default
    from_north = next(e for e in net.getEdges() if e.getName() == "North Main Street"
                      and e.getToNode().getType() == "traffic_light")  # fmt: skip
    directions = {c.getDirection() for cs in from_north.getOutgoing().values() for c in cs}
    assert directions == {"s"}  # only_straight_on from the north


@pytest.mark.sumo
def test_building_twice_gives_byte_identical_files(tiny_osm_file, tmp_path):
    first, second = tmp_path / "a.net.xml.gz", tmp_path / "b.net.xml.gz"
    build_network(tiny_osm_file, first, TEST_BOX)
    build_network(tiny_osm_file, second, TEST_BOX)
    assert first.read_bytes() == second.read_bytes()
    assert b"generated on" not in gzip.decompress(first.read_bytes())
