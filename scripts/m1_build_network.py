"""Milestone 1 entry point: build the downtown DeLand road network.

Run it from the repository root::

    uv run python scripts/m1_build_network.py

What it does, in order:

1. Uses the frozen OpenStreetMap snapshot in ``data/osm/`` and checks its
   fingerprint. (It downloads a new snapshot only with ``--refresh-osm``.)
2. Builds the SUMO network ``network/deland.net.xml`` with netconvert.
3. Loads the network in SUMO to prove it has no errors.
4. Writes the signal inventory, the comparison with the FDOT list, the map,
   a summary and a field checklist to ``results/m1_network/``.

Rebuilding from the same snapshot gives a byte-identical network, so running
this script must not change any committed file.
"""

from __future__ import annotations

import argparse
import sys

from omniflow.network.area import DELAND_STUDY_AREA, EXPECTED_SIGNALS
from omniflow.network.build import build_network, check_network_loads
from omniflow.network.inventory import (
    compare_with_expected,
    read_signal_inventory,
    write_expected_csv,
    write_inventory_csv,
)
from omniflow.network.osm import download_snapshot, named_area_center, verify_snapshot
from omniflow.network.plot import plot_network_map
from omniflow.network.report import render_field_checklist, render_summary
from omniflow.paths import DELAND_NET, M1_RESULTS_DIR, OSM_SNAPSHOT, PATCH_DIR, REPO_ROOT
from omniflow.sumo_tools import sumo_version


def main() -> int:
    """Build the network and its reports; return a process exit code."""
    parser = argparse.ArgumentParser(description="Build the downtown DeLand SUMO network (M1).")
    parser.add_argument(
        "--refresh-osm",
        action="store_true",
        help="Download a NEW OpenStreetMap snapshot first. The map will differ slightly "
        "from the committed one, so every later result can change. Use deliberately.",
    )
    args = parser.parse_args()

    print("OmniFlow M1: build the downtown DeLand network")
    if args.refresh_osm or not OSM_SNAPSHOT.is_file():
        print(f"  Downloading OpenStreetMap data for {DELAND_STUDY_AREA.as_lon_lat_string()} ...")
        download_snapshot(DELAND_STUDY_AREA, OSM_SNAPSHOT)
    meta = verify_snapshot(OSM_SNAPSHOT)
    snapshot_name = OSM_SNAPSHOT.relative_to(REPO_ROOT).as_posix()
    print(f"  Snapshot      : {snapshot_name} (downloaded {meta['downloaded_at_utc']}, verified)")

    build = build_network(OSM_SNAPSHOT, DELAND_NET, DELAND_STUDY_AREA, PATCH_DIR)
    print(f"  Network       : {DELAND_NET.relative_to(REPO_ROOT).as_posix()}")
    print(f"  netconvert    : {build.warning_count} warnings, {len(build.patches)} patches applied")

    load = check_network_loads(DELAND_NET)
    print(
        f"  SUMO load     : OK ({load.seconds_simulated} s simulated, "
        f"{len(load.warnings)} warnings)"
    )

    records = read_signal_inventory(DELAND_NET)
    matches = compare_with_expected(records, EXPECTED_SIGNALS)
    write_inventory_csv(records, M1_RESULTS_DIR / "signals.csv")
    write_expected_csv(matches, M1_RESULTS_DIR / "expected_signals.csv")

    campus = named_area_center(OSM_SNAPSHOT, "Stetson University")
    plot_network_map(
        DELAND_NET,
        records,
        M1_RESULTS_DIR / "network_map.png",
        title=f"Downtown DeLand digital twin: {len(records)} signalized intersections",
        subtitle=(
            f"SUMO network built from the OpenStreetMap snapshot of "
            f"{str(meta['downloaded_at_utc'])[:10]}. "
            "Map data (c) OpenStreetMap contributors, ODbL."
        ),
        labels={"Stetson University": campus} if campus else None,
    )
    summary = render_summary(
        snapshot_name=snapshot_name,
        snapshot_meta=meta,
        bbox=DELAND_STUDY_AREA,
        net_file=DELAND_NET,
        build=build,
        load=load,
        records=records,
        matches=matches,
        sumo_version=sumo_version(),
    )
    (M1_RESULTS_DIR / "summary.md").write_text(summary, encoding="utf-8", newline="\n")
    (M1_RESULTS_DIR / "field_checklist.md").write_text(
        render_field_checklist(records), encoding="utf-8", newline="\n"
    )

    found = sum(m.signal is not None for m in matches)
    print(f"  Signals       : {len(records)} signalized intersections")
    print(f"  FDOT list     : {found} of {len(matches)} found in the network")
    print(f"  Reports       : {M1_RESULTS_DIR.relative_to(REPO_ROOT).as_posix()}/")
    for record in records:
        print(f"    {record.signal_no:>2}  {record.name}")
    print("Done. Open the network in the SUMO window with:")
    print(f"  uv run sumo-gui -n {DELAND_NET.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
