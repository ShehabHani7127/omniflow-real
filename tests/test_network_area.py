"""Tests for the study-area bounding box."""

from __future__ import annotations

import pytest

from omniflow.network.area import DELAND_STUDY_AREA, EXPECTED_SIGNALS, BoundingBox


def test_string_is_west_south_east_north():
    box = BoundingBox(south=1.0, west=2.0, north=3.0, east=4.0)
    assert box.as_lon_lat_string() == "2.0,1.0,4.0,3.0"


@pytest.mark.parametrize(
    ("south", "west", "north", "east"),
    [
        (3.0, 0.0, 1.0, 1.0),  # south above north
        (0.0, 3.0, 1.0, 1.0),  # west east of east
        (-91.0, 0.0, 1.0, 1.0),  # latitude out of range
        (0.0, 0.0, 1.0, 181.0),  # longitude out of range
    ],
)
def test_impossible_boxes_are_rejected(south, west, north, east):
    with pytest.raises(ValueError):
        BoundingBox(south=south, west=west, north=north, east=east)


def test_contains_includes_edges_and_excludes_outside():
    box = BoundingBox(south=0.0, west=0.0, north=1.0, east=1.0)
    assert box.contains(0.5, 0.5)
    assert box.contains(0.0, 1.0)
    assert not box.contains(1.5, 0.5)
    assert not box.contains(0.5, -0.1)


def test_deland_area_is_within_the_osm_api_limit_and_covers_downtown():
    assert DELAND_STUDY_AREA.area_square_degrees < 0.25
    # Woodland Blvd at New York Ave, from the M1 survey of OSM data.
    assert DELAND_STUDY_AREA.contains(29.02808, -81.30343)


def test_expected_signals_name_their_source():
    assert EXPECTED_SIGNALS
    assert all(s.source and s.street_a and s.street_b for s in EXPECTED_SIGNALS)
