"""Milestone 0 tests: SUMO runs a trivial example and obeys Python.

These tests protect the three assumptions the whole experiment protocol rests
on: runs are reproducible, both SUMO backends agree, and Python controls the
traffic light.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import sumolib

from omniflow.smoke import SMOKE_SIM_SECONDS, run_smoke_simulation
from omniflow.toy import TOY_INCOMING_LANES, TOY_TLS_ID

pytestmark = pytest.mark.sumo


def _vehicles_in_trip_report(tripinfo_file: Path) -> dict[str, tuple[float, str]]:
    """Map vehicle id -> (scheduled departure time, speed factor) from a SUMO trip report."""
    vehicles = {}
    for trip in ET.parse(tripinfo_file).getroot().iter("tripinfo"):
        # "depart" is when the vehicle really entered; "departDelay" is how long it had
        # to wait for room. Their difference is when it was *scheduled* to enter.
        scheduled = round(float(trip.attrib["depart"]) - float(trip.attrib["departDelay"]), 2)
        vehicles[trip.attrib["id"]] = (scheduled, trip.attrib["speedFactor"])
    return vehicles


def test_toy_network_has_one_signalized_four_way_intersection(toy_scenario):
    net = sumolib.net.readNet(str(toy_scenario.net_file))

    assert [tls.getID() for tls in net.getTrafficLights()] == [TOY_TLS_ID]
    incoming = {lane.getID() for edge in net.getNode("C").getIncoming() for lane in edge.getLanes()}
    assert incoming == set(TOY_INCOMING_LANES)


def test_all_vehicles_arrive_under_the_default_signal_plan(toy_scenario):
    result = run_smoke_simulation(toy_scenario, seed=42)

    assert result.departed > 100, "the toy demand should create a meaningful amount of traffic"
    assert result.arrived == result.departed
    assert result.sim_seconds == SMOKE_SIM_SECONDS
    assert 0 < result.mean_queue < 20


def test_same_seed_gives_exactly_the_same_result(toy_scenario):
    assert run_smoke_simulation(toy_scenario, seed=7) == run_smoke_simulation(toy_scenario, seed=7)


def test_different_seeds_give_different_traffic(toy_scenario):
    assert run_smoke_simulation(toy_scenario, seed=7) != run_smoke_simulation(toy_scenario, seed=8)


def test_libsumo_and_traci_backends_give_exactly_the_same_result(toy_scenario):
    in_process = run_smoke_simulation(toy_scenario, seed=42, backend="libsumo")
    over_socket = run_smoke_simulation(toy_scenario, seed=42, backend="traci")

    assert in_process == over_socket


def test_python_controls_the_traffic_light(toy_scenario):
    normal = run_smoke_simulation(toy_scenario, seed=42)
    north_south_held_green = run_smoke_simulation(toy_scenario, seed=42, hold_phase=0)

    # Same seed means the same vehicles try to enter. With east-west starved,
    # fewer of them can finish and far more of them stand in a queue.
    assert north_south_held_green.arrived < normal.arrived
    assert north_south_held_green.mean_queue > 2 * normal.mean_queue


def test_same_seed_means_same_vehicles_whatever_the_signal_does(toy_scenario, tmp_path):
    """Fairness rule: the controller must not change which traffic it is tested on."""
    normal_report = tmp_path / "normal.tripinfo.xml"
    held_report = tmp_path / "held.tripinfo.xml"
    run_smoke_simulation(toy_scenario, seed=42, tripinfo_file=normal_report)
    run_smoke_simulation(toy_scenario, seed=42, hold_phase=0, tripinfo_file=held_report)

    normal = _vehicles_in_trip_report(normal_report)
    held = _vehicles_in_trip_report(held_report)

    assert len(normal) > 100
    for vehicle_id, schedule_and_speed_factor in held.items():
        assert normal[vehicle_id] == schedule_and_speed_factor


def test_vehicles_that_never_entered_are_missing_from_sumos_trip_report(toy_scenario, tmp_path):
    """The trap behind the delay definition in DESIGN.md section 8.2."""
    normal_report = tmp_path / "normal.tripinfo.xml"
    held_report = tmp_path / "held.tripinfo.xml"
    normal_run = run_smoke_simulation(toy_scenario, seed=42, tripinfo_file=normal_report)
    held_run = run_smoke_simulation(toy_scenario, seed=42, hold_phase=0, tripinfo_file=held_report)

    normal = _vehicles_in_trip_report(normal_report)
    held = _vehicles_in_trip_report(held_report)

    # Bad control blocks the entry roads, so some vehicles never get in ...
    assert held_run.departed < normal_run.departed
    # ... and SUMO's trip report simply has no line for them.
    assert len(held) == held_run.departed
    assert set(held) < set(normal)
