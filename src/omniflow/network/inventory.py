"""List the signalized intersections of a SUMO network.

For every traffic light the inventory records where it is, which streets meet
there, how big the intersection is, and which turning movements it allows.
This is the table you take on a field walk to check the digital twin against
the real streets.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import asdict, dataclass, fields
from pathlib import Path

import sumolib

from omniflow.network.area import ExpectedSignal

_DIRECTION_PREFIXES = ("North ", "South ", "East ", "West ")
_ABBREVIATIONS = {
    "Boulevard": "Blvd",
    "Avenue": "Ave",
    "Street": "St",
    "Road": "Rd",
    "Drive": "Dr",
    "Place": "Pl",
    "Court": "Ct",
    "Lane": "Ln",
}

#: The corridor street; it is named first in every intersection name.
CORRIDOR_STREET = "Woodland Blvd"


def short_street_name(name: str) -> str:
    """Shorten an OSM street name the way it would appear on a street sign.

    Drops the direction prefix (DeLand addresses are "North Woodland
    Boulevard" north of New York Ave and "South Woodland Boulevard" south of
    it, but it is one street) and abbreviates the street type.

    >>> short_street_name("North Woodland Boulevard")
    'Woodland Blvd'
    """
    name = name.strip()
    for prefix in _DIRECTION_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break
    words = name.split()
    if words and words[-1] in _ABBREVIATIONS:
        words[-1] = _ABBREVIATIONS[words[-1]]
    return " ".join(words)


@dataclass(frozen=True)
class SignalRecord:
    """One signalized intersection.

    Attributes:
        signal_no: Number used on the map, counted from north to south.
        name: Readable name, for example ``"Woodland Blvd & New York Ave"``.
        tls_id: The traffic light's ID in the SUMO network.
        streets: All street names at the intersection, joined by ``" / "``.
        lat: Latitude of the intersection.
        lon: Longitude of the intersection.
        junctions: Number of SUMO junctions this light controls (more than one
            when OSM drew one intersection as several points).
        approaches: Number of roads leading into the intersection.
        incoming_lanes: Number of lanes leading into it.
        signal_links: Number of lane-to-lane movements the light controls.
        straight: Movements that go straight on.
        left: Left-turn movements.
        right: Right-turn movements.
        uturn: U-turn movements.
        phases: Phases in the signal program netconvert generated.
        green_phases: Phases among them that give green to some movement.
        cycle_s: Length of that program's cycle in seconds. (A placeholder
            program: realistic timings are designed in milestone M3.)
    """

    signal_no: int
    name: str
    tls_id: str
    streets: str
    lat: float
    lon: float
    junctions: int
    approaches: int
    incoming_lanes: int
    signal_links: int
    straight: int
    left: int
    right: int
    uturn: int
    phases: int
    green_phases: int
    cycle_s: float

    @property
    def street_set(self) -> set[str]:
        """The street names as a set."""
        return set(self.streets.split(" / ")) if self.streets else set()


def _intersection_name(edges: list[sumolib.net.edge.Edge]) -> tuple[str, str]:
    """Return ``(name, all streets)`` for the edges that meet at an intersection.

    The corridor street comes first, then the other streets in order of road
    importance (SUMO priority), then alphabetically.
    """
    priority: dict[str, int] = {}
    for edge in edges:
        street = short_street_name(edge.getName())
        if street:
            priority[street] = max(priority.get(street, 0), edge.getPriority())
    ordered = sorted(
        priority, key=lambda s: (s != CORRIDOR_STREET, -priority[s], s)
    )  # fmt: skip
    name = " & ".join(ordered[:2]) if ordered else "(unnamed)"
    return name, " / ".join(ordered)


#: SUMO's movement direction codes: s = straight, l/L = (partly) left,
#: r/R = (partly) right, t = turn around (U-turn).
_DIRECTION_GROUPS = {
    "s": "straight",
    "l": "left",
    "L": "left",
    "r": "right",
    "R": "right",
    "t": "uturn",
}


def read_signal_inventory(net_file: Path) -> list[SignalRecord]:
    """Build the inventory of every traffic light in a SUMO network.

    Args:
        net_file: A ``.net.xml`` or ``.net.xml.gz`` file with geo-coordinates
            (true for every network built from OpenStreetMap).

    Returns:
        One record per traffic light, numbered from north to south.
    """
    net = sumolib.net.readNet(str(net_file), withPrograms=True)
    rows = []
    for tls in net.getTrafficLights():
        controlled_edges = tls.getEdges()
        nodes = {edge.getToNode() for edge in controlled_edges}
        xs = [node.getCoord()[0] for node in nodes]
        ys = [node.getCoord()[1] for node in nodes]
        lon, lat = net.convertXY2LonLat(sum(xs) / len(xs), sum(ys) / len(ys))

        all_edges = [e for node in nodes for e in node.getIncoming() + node.getOutgoing()]
        name, streets = _intersection_name(all_edges)

        movements: Counter[str] = Counter()
        lanes = set()
        link_count = 0
        for links in tls.getLinks().values():
            for in_lane, out_lane, _via in links:
                link_count += 1
                lanes.add(in_lane.getID())
                for conn in in_lane.getEdge().getConnections(out_lane.getEdge()):
                    if conn.getFromLane() == in_lane and conn.getToLane() == out_lane:
                        movements[_DIRECTION_GROUPS.get(conn.getDirection(), "other")] += 1

        program = next(iter(tls.getPrograms().values()))
        phases = program.getPhases()
        greens = [p for p in phases if ("G" in p.state or "g" in p.state) and "y" not in p.state]
        rows.append(
            {
                "name": name,
                "tls_id": tls.getID(),
                "streets": streets,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "junctions": len(nodes),
                "approaches": len(controlled_edges),
                "incoming_lanes": len(lanes),
                "signal_links": link_count,
                "straight": movements["straight"],
                "left": movements["left"],
                "right": movements["right"],
                "uturn": movements["uturn"],
                "phases": len(phases),
                "green_phases": len(greens),
                "cycle_s": float(sum(p.duration for p in phases)),
            }
        )
    rows.sort(key=lambda r: (-r["lat"], r["lon"]))
    return [SignalRecord(signal_no=i, **row) for i, row in enumerate(rows, start=1)]


def write_inventory_csv(records: list[SignalRecord], csv_file: Path) -> None:
    """Write the inventory as a CSV table (one row per signal)."""
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    with csv_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=[f.name for f in fields(SignalRecord)], lineterminator="\n"
        )
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


@dataclass(frozen=True)
class ExpectedMatch:
    """Whether an intersection named by an outside source exists in the network.

    Attributes:
        expected: The intersection the source names.
        signal: The matching network signal, or ``None`` if there is none.
    """

    expected: ExpectedSignal
    signal: SignalRecord | None


def compare_with_expected(
    records: list[SignalRecord], expected: tuple[ExpectedSignal, ...]
) -> list[ExpectedMatch]:
    """Match a list of expected signals against the network's signals.

    A network signal matches when both expected street names meet there.
    """
    matches = []
    for item in expected:
        found = next((r for r in records if {item.street_a, item.street_b} <= r.street_set), None)
        matches.append(ExpectedMatch(expected=item, signal=found))
    return matches


def write_expected_csv(matches: list[ExpectedMatch], csv_file: Path) -> None:
    """Write the comparison with the outside list of signals as a CSV table."""
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    with csv_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["street_a", "street_b", "in_network", "signal_no", "tls_id", "source"])
        for m in matches:
            writer.writerow(
                [
                    m.expected.street_a,
                    m.expected.street_b,
                    "yes" if m.signal else "no",
                    m.signal.signal_no if m.signal else "",
                    m.signal.tls_id if m.signal else "",
                    m.expected.source,
                ]
            )
