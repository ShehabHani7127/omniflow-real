"""Tests for the signal inventory helpers."""

from __future__ import annotations

import csv

import pytest

from omniflow.network.area import ExpectedSignal
from omniflow.network.inventory import (
    SignalRecord,
    compare_with_expected,
    short_street_name,
    write_expected_csv,
    write_inventory_csv,
)
from omniflow.network.report import checks_for_the_field


@pytest.mark.parametrize(
    ("osm_name", "short"),
    [
        ("North Woodland Boulevard", "Woodland Blvd"),
        ("South Woodland Boulevard", "Woodland Blvd"),
        ("East New York Avenue", "New York Ave"),
        ("West Church Street", "Church St"),
        ("Woodland Boulevard", "Woodland Blvd"),
        ("Northridge Road", "Northridge Rd"),  # "North" only as a separate word
        ("", ""),
    ],
)
def test_short_street_name(osm_name, short):
    assert short_street_name(osm_name) == short


def record(no: int, streets: str, **overrides: int) -> SignalRecord:
    values = {
        "signal_no": no,
        "name": streets.replace(" / ", " & "),
        "tls_id": f"t{no}",
        "streets": streets,
        "lat": 29.0,
        "lon": -81.3,
        "junctions": 1,
        "approaches": 4,
        "incoming_lanes": 6,
        "signal_links": 12,
        "straight": 4,
        "left": 4,
        "right": 4,
        "uturn": 0,
        "phases": 4,
        "green_phases": 2,
        "cycle_s": 90.0,
    }
    values.update(overrides)
    return SignalRecord(**values)


def test_compare_with_expected_matches_both_street_names():
    records = [record(1, "Woodland Blvd / New York Ave"), record(2, "Woodland Blvd / Rich Ave")]
    expected = (
        ExpectedSignal("Woodland Blvd", "Rich Ave", "test"),
        ExpectedSignal("Woodland Blvd", "Howry Ave", "test"),
    )
    found, missing = compare_with_expected(records, expected)
    assert found.signal is records[1]
    assert missing.signal is None


def test_inventory_and_comparison_csv_files(tmp_path):
    records = [record(1, "Woodland Blvd / Rich Ave")]
    write_inventory_csv(records, tmp_path / "signals.csv")
    expected = (ExpectedSignal("Woodland Blvd", "Rich Ave", "test"),)
    write_expected_csv(compare_with_expected(records, expected), tmp_path / "expected.csv")

    with (tmp_path / "signals.csv").open(encoding="utf-8") as handle:
        [row] = list(csv.DictReader(handle))
    assert row["name"] == "Woodland Blvd & Rich Ave"
    assert row["cycle_s"] == "90.0"
    with (tmp_path / "expected.csv").open(encoding="utf-8") as handle:
        [match] = list(csv.DictReader(handle))
    assert (match["in_network"], match["signal_no"]) == ("yes", "1")


def test_field_checks_flag_turn_bans_t_junctions_and_single_lanes():
    notes = checks_for_the_field(
        [
            record(1, "A St / B St", left=0, right=0),
            record(2, "A St / C St", approaches=3),
            record(3, "A St / D St", incoming_lanes=4),
            record(4, "A St / E St"),
        ]
    )
    assert any(n.startswith("#1") and "no turns" in n for n in notes)
    assert any(n.startswith("#2") and "3 approaches" in n for n in notes)
    assert any(n.startswith("#3") and "one lane per approach" in n for n in notes)
    assert not any(n.startswith("#4") for n in notes)
