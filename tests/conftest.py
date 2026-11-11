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


#: A hand-made OpenStreetMap extract: one signalized four-way intersection
#: ("Main Street" x "Oak Avenue") near DeLand. South Main Street runs on far
#: outside the test box, and a restriction says traffic coming from the north
#: may only go straight on.
TINY_OSM = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="omniflow-test">
  <node id="1" lat="29.0300" lon="-81.3000"><tag k="highway" v="traffic_signals"/></node>
  <node id="2" lat="29.0320" lon="-81.3000"/>
  <node id="3" lat="29.0280" lon="-81.3000"/>
  <node id="4" lat="29.0200" lon="-81.3000"/>
  <node id="5" lat="29.0300" lon="-81.2977"/>
  <node id="6" lat="29.0300" lon="-81.3023"/>
  <way id="10">
    <nd ref="1"/><nd ref="2"/>
    <tag k="highway" v="primary"/><tag k="name" v="North Main Street"/>
    <tag k="lanes" v="2"/><tag k="maxspeed" v="30 mph"/>
  </way>
  <way id="11">
    <nd ref="1"/><nd ref="3"/><nd ref="4"/>
    <tag k="highway" v="primary"/><tag k="name" v="South Main Street"/>
    <tag k="lanes" v="2"/><tag k="maxspeed" v="30 mph"/>
  </way>
  <way id="12">
    <nd ref="1"/><nd ref="5"/>
    <tag k="highway" v="residential"/><tag k="name" v="East Oak Avenue"/>
  </way>
  <way id="13">
    <nd ref="1"/><nd ref="6"/>
    <tag k="highway" v="residential"/><tag k="name" v="West Oak Avenue"/>
  </way>
  <relation id="20">
    <member type="way" ref="10" role="from"/>
    <member type="node" ref="1" role="via"/>
    <member type="way" ref="11" role="to"/>
    <tag k="type" v="restriction"/><tag k="restriction" v="only_straight_on"/>
  </relation>
</osm>
"""


@pytest.fixture(scope="session")
def tiny_osm_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Write ``TINY_OSM`` to a file once per test session."""
    path = tmp_path_factory.mktemp("osm") / "tiny.osm.xml"
    path.write_text(TINY_OSM, encoding="utf-8")
    return path
