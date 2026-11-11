"""Milestone 0 entry point: check that SUMO runs and obeys Python on this machine.

Run it from the repository root::

    uv run python scripts/m0_smoke_test.py

It builds a one-intersection toy network, simulates it a few times and checks
three things that the whole project relies on:

1. Reproducibility: the same seed gives exactly the same result.
2. Backend equivalence: the fast ``libsumo`` backend and the ``traci`` socket
   backend give exactly the same result.
3. Control: when Python holds the signal on north-south green, east-west
   traffic gets stuck. That can only happen if Python commands the light.

The numbers printed here describe a toy intersection. They are NOT results
about DeLand and must never be quoted as such.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from omniflow.smoke import SmokeResult, run_smoke_simulation
from omniflow.sumo_tools import Backend, sumo_home, sumo_version
from omniflow.toy import ToyScenario, build_toy_scenario

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT / "results" / "raw" / "m0_smoke"


def _timed_run(
    label: str,
    scenario: ToyScenario,
    seed: int,
    backend: Backend,
    hold_phase: int | None = None,
) -> SmokeResult:
    """Run one smoke simulation, print a one-line summary and return the result."""
    start = time.perf_counter()
    result = run_smoke_simulation(scenario, seed=seed, backend=backend, hold_phase=hold_phase)
    seconds = time.perf_counter() - start
    print(
        f"  {label:<32} departed={result.departed:>4}  arrived={result.arrived:>4}  "
        f"mean queue={result.mean_queue:5.2f} veh  (took {seconds:.2f} s)"
    )
    return result


def _check(description: str, passed: bool) -> bool:
    """Print one PASS/FAIL line and return ``passed``."""
    print(f"  [{'PASS' if passed else 'FAIL'}] {description}")
    return passed


def main() -> int:
    """Run the smoke test and return a process exit code (0 means success)."""
    parser = argparse.ArgumentParser(description="OmniFlow milestone 0 smoke test.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Folder for the generated toy network files (default: %(default)s).",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42).")
    args = parser.parse_args()
    seed: int = args.seed

    print("OmniFlow M0 smoke test")
    print(f"  SUMO version : {sumo_version()}")
    print(f"  SUMO location: {sumo_home()}")
    scenario = build_toy_scenario(args.out_dir)
    print(f"  Toy network  : {scenario.net_file}")

    print()
    print("Simulations (one four-way intersection, 15 simulated minutes each):")
    first = _timed_run(f"libsumo, seed {seed}", scenario, seed, "libsumo")
    again = _timed_run(f"libsumo, seed {seed} again", scenario, seed, "libsumo")
    other = _timed_run(f"libsumo, seed {seed + 1}", scenario, seed + 1, "libsumo")
    held = _timed_run("libsumo, north-south held green", scenario, seed, "libsumo", hold_phase=0)
    print("  (traci may print 'Retrying in 1 seconds' while SUMO starts up: that is normal)")
    socket = _timed_run(f"traci, seed {seed}", scenario, seed, "traci")

    print()
    print("Checks:")
    all_arrived = 0 < first.departed == first.arrived
    stranded = held.arrived < first.arrived and held.mean_queue > first.mean_queue
    checks = [
        _check("vehicles entered the network and all of them arrived", all_arrived),
        _check("same seed gives exactly the same result (reproducible)", first == again),
        _check("a different seed gives different traffic", first != other),
        _check("libsumo and traci give exactly the same result", first == socket),
        _check("holding north-south green strands east-west traffic", stranded),
    ]

    print()
    if not all(checks):
        print("SOME CHECKS FAILED. Copy everything above and ask for help.")
        return 1
    print("ALL CHECKS PASSED.")
    print("To watch the toy intersection in the SUMO window, run:")
    print(f'  uv run sumo-gui -n "{scenario.net_file}" -r "{scenario.route_file}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
