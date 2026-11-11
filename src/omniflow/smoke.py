"""Milestone 0 smoke test: prove that Python can run and control SUMO.

A *smoke test* is the simplest possible end-to-end check ("switch it on and
see whether smoke comes out"). It does not measure anything scientific. It
only proves that the tool chain works on this machine:

* ``netconvert`` can build a network,
* SUMO can simulate it,
* Python can read the simulation state every second (**observe**), and
* Python can command the traffic light (**act**).

Observe-then-act, once per time step, is exactly the loop that the
reinforcement learning controller will run in later milestones.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from omniflow.sumo_tools import Backend, get_connection, sumo_binary
from omniflow.toy import TOY_DEMAND_SECONDS, TOY_INCOMING_LANES, TOY_TLS_ID, ToyScenario

#: Simulated seconds per smoke run: the demand period plus time to clear out.
SMOKE_SIM_SECONDS = TOY_DEMAND_SECONDS + 300


@dataclass(frozen=True)
class SmokeResult:
    """What happened in one smoke-test simulation.

    Every field is fully determined by the scenario, the seed and the control
    rule, so two runs with the same inputs must produce *equal* results.

    Attributes:
        departed: Number of vehicles that entered the network.
        arrived: Number of vehicles that finished their trip.
        halted_vehicle_seconds: Sum over every simulated second of the number
            of vehicles standing still (slower than 0.1 m/s) on the lanes
            leading into the intersection.
        sim_seconds: Number of simulated seconds.
    """

    departed: int
    arrived: int
    halted_vehicle_seconds: int
    sim_seconds: int

    @property
    def mean_queue(self) -> float:
        """Average number of vehicles standing in a queue at any moment."""
        return self.halted_vehicle_seconds / self.sim_seconds


def run_smoke_simulation(
    scenario: ToyScenario,
    *,
    seed: int = 42,
    backend: Backend = "libsumo",
    hold_phase: int | None = None,
    tripinfo_file: Path | None = None,
) -> SmokeResult:
    """Simulate the toy intersection once, stepping SUMO from Python.

    Args:
        scenario: The toy network and demand files.
        seed: Random seed for SUMO. Same seed, same traffic, same result.
        backend: ``"libsumo"`` (fast, in-process) or ``"traci"`` (socket).
        hold_phase: If ``None``, the traffic light runs its built-in fixed
            plan. If a phase index is given, Python forces the light to stay
            in that phase for the whole run. Phase 0 is "north-south green",
            so east-west traffic is never served. This is deliberately bad
            control; it exists to prove that Python really commands the
            signal.
        tripinfo_file: If given, SUMO writes its own trip report to this
            file: one record for every vehicle that entered the network,
            including those still driving when the run ends. A vehicle that
            never managed to enter gets no record at all.

    Returns:
        Counts describing what happened in the simulation.
    """
    conn = get_connection(backend)
    command = [
        str(sumo_binary("sumo")),
        "--net-file", str(scenario.net_file),
        "--route-files", str(scenario.route_file),
        "--seed", str(seed),
        "--no-step-log", "true",
        # SUMO normally "teleports" a vehicle that has been stuck for 300 s.
        # Disabled here so that a starved approach visibly stays stuck.
        "--time-to-teleport", "-1",
    ]  # fmt: skip
    if tripinfo_file is not None:
        command += [
            "--tripinfo-output", str(tripinfo_file),
            "--tripinfo-output.write-unfinished", "true",
        ]  # fmt: skip

    departed = 0
    arrived = 0
    halted_vehicle_seconds = 0

    conn.start(command)
    try:
        for _ in range(SMOKE_SIM_SECONDS):
            if hold_phase is not None:
                # ACT: re-select the phase every second so it never ends.
                conn.trafficlight.setPhase(TOY_TLS_ID, hold_phase)
            conn.simulationStep()  # advance the simulation by one second
            # OBSERVE: read what happened during that second.
            departed += conn.simulation.getDepartedNumber()
            arrived += conn.simulation.getArrivedNumber()
            halted_vehicle_seconds += sum(
                conn.lane.getLastStepHaltingNumber(lane) for lane in TOY_INCOMING_LANES
            )
    finally:
        conn.close()

    return SmokeResult(
        departed=departed,
        arrived=arrived,
        halted_vehicle_seconds=halted_vehicle_seconds,
        sim_seconds=SMOKE_SIM_SECONDS,
    )
