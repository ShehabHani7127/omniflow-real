"""A tiny one-intersection scenario for smoke tests and fast unit tests.

The real project simulates downtown DeLand. That network is big and slow to
load, so tests need something small that runs in well under a second. This
module builds the smallest interesting traffic problem: one four-way
intersection with one traffic light::

                 N
                 |
           W --- C --- E        C = signalized intersection
                 |              every road: 200 m, one lane per direction
                 S

It follows the same two steps as the real pipeline, just in miniature:

1. describe the roads in plain XML and let ``netconvert`` build the network;
2. describe the traffic demand in a routes file.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from omniflow.sumo_tools import sumo_binary

#: ID of the single traffic light in the toy network.
TOY_TLS_ID = "C"

#: Seconds during which new vehicles enter the toy network.
TOY_DEMAND_SECONDS = 600

#: Lanes that lead into the intersection (where queues form).
TOY_INCOMING_LANES: tuple[str, ...] = ("N_C_0", "E_C_0", "S_C_0", "W_C_0")

_NODES_XML = """\
<nodes>
    <node id="C" x="0" y="0" type="traffic_light"/>
    <node id="N" x="0" y="200"/>
    <node id="E" x="200" y="0"/>
    <node id="S" x="0" y="-200"/>
    <node id="W" x="-200" y="0"/>
</nodes>
"""

# speed is in metres per second: 13.89 m/s = 50 km/h (about 31 mph).
_EDGES_XML = """\
<edges>
    <edge id="N_C" from="N" to="C" numLanes="1" speed="13.89"/>
    <edge id="C_N" from="C" to="N" numLanes="1" speed="13.89"/>
    <edge id="E_C" from="E" to="C" numLanes="1" speed="13.89"/>
    <edge id="C_E" from="C" to="E" numLanes="1" speed="13.89"/>
    <edge id="S_C" from="S" to="C" numLanes="1" speed="13.89"/>
    <edge id="C_S" from="C" to="S" numLanes="1" speed="13.89"/>
    <edge id="W_C" from="W" to="C" numLanes="1" speed="13.89"/>
    <edge id="C_W" from="C" to="W" numLanes="1" speed="13.89"/>
</edges>
"""

# period="exp(r)" means: vehicles arrive at random (a Poisson process) with an
# average of r vehicles per second. Which random arrivals you get depends on
# the simulation seed, so a different seed is a different "day" of traffic.
_ROUTES_XML = f"""\
<routes>
    <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="5.0" maxSpeed="15"/>
    <flow id="north_south" type="car" from="N_C" to="C_S" begin="0" end="{TOY_DEMAND_SECONDS}" period="exp(0.10)"/>
    <flow id="south_north" type="car" from="S_C" to="C_N" begin="0" end="{TOY_DEMAND_SECONDS}" period="exp(0.10)"/>
    <flow id="east_west" type="car" from="E_C" to="C_W" begin="0" end="{TOY_DEMAND_SECONDS}" period="exp(0.08)"/>
    <flow id="west_east" type="car" from="W_C" to="C_E" begin="0" end="{TOY_DEMAND_SECONDS}" period="exp(0.08)"/>
    <flow id="north_left" type="car" from="N_C" to="C_E" begin="0" end="{TOY_DEMAND_SECONDS}" period="exp(0.02)"/>
</routes>
"""  # noqa: E501  (XML rows are easier to read on one line each)


@dataclass(frozen=True)
class ToyScenario:
    """Paths of the files that define the toy scenario.

    Attributes:
        net_file: The road network built by ``netconvert``.
        route_file: The traffic demand (which vehicles drive where, and when).
    """

    net_file: Path
    route_file: Path


def build_toy_scenario(out_dir: Path) -> ToyScenario:
    """Build the toy network and demand files inside ``out_dir``.

    Args:
        out_dir: Folder to write the files into. Created if it is missing.

    Returns:
        The paths of the generated network and route files.

    Raises:
        RuntimeError: If ``netconvert`` fails to build the network.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    nodes_file = out_dir / "toy.nod.xml"
    edges_file = out_dir / "toy.edg.xml"
    net_file = out_dir / "toy.net.xml"
    route_file = out_dir / "toy.rou.xml"

    nodes_file.write_text(_NODES_XML, encoding="utf-8")
    edges_file.write_text(_EDGES_XML, encoding="utf-8")
    route_file.write_text(_ROUTES_XML, encoding="utf-8")

    command = [
        str(sumo_binary("netconvert")),
        "--node-files", str(nodes_file),
        "--edge-files", str(edges_file),
        "--output-file", str(net_file),
        "--no-turnarounds", "true",  # no U-turns: keeps the toy junction simple
    ]  # fmt: skip
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not net_file.is_file():
        raise RuntimeError(f"netconvert failed:\n{completed.stdout}\n{completed.stderr}")

    return ToyScenario(net_file=net_file, route_file=route_file)
