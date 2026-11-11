"""Turn the frozen OpenStreetMap snapshot into a SUMO road network.

The work is done by SUMO's ``netconvert`` program. This module decides *which
options* it gets (each with a one-line reason), runs it, applies any patch
files, and checks that SUMO can load the result.
"""

from __future__ import annotations

import gzip
import re
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from omniflow.network.area import BoundingBox
from omniflow.network.osm import ClipStats, clip_to_bbox, write_gzip_deterministic
from omniflow.paths import REPO_ROOT, SPEED_DEFAULTS_TYPE_FILE
from omniflow.sumo_tools import sumo_binary, sumo_home, sumo_version


@dataclass(frozen=True)
class NetconvertOption:
    """One ``netconvert`` command-line option and why it is used.

    Attributes:
        flag: The option name, for example ``"--junctions.join"``.
        value: Its value, or ``None`` for an on/off option.
        reason: One line explaining the choice.
    """

    flag: str
    value: str | None
    reason: str

    def as_args(self) -> list[str]:
        """Return the option as command-line arguments.

        A value is attached with ``=`` because some values start with a minus
        sign (western longitudes), which would otherwise look like an option.
        """
        return [self.flag] if self.value is None else [f"{self.flag}={self.value}"]


#: The option set used to build the DeLand network. Starting point: the
#: recommendations in SUMO's OpenStreetMap import guide. Cutting the network to
#: the study area is not an option here: the OSM data is clipped first.
NETCONVERT_OPTIONS: tuple[NetconvertOption, ...] = (
    NetconvertOption(
        "--keep-edges.by-vclass", "passenger",
        "Keep only roads that cars may use. This drops footways, paths and, with SUMO's "
        "default type map, service roads (parking aisles, driveways).",
    ),
    NetconvertOption(
        "--keep-edges.components", "1",
        "Keep only the largest connected piece of road, so no isolated fragments remain "
        "after cutting.",
    ),
    NetconvertOption(
        "--geometry.remove", None,
        "Merge road pieces that OSM splits only to draw curves; fewer, longer edges.",
    ),
    NetconvertOption(
        "--junctions.join", None,
        "OSM often draws one intersection as several close points; merge them into one.",
    ),
    NetconvertOption(
        "--tls.guess-signals", None,
        "Where OSM puts signal markers on the approaches instead of on the intersection, "
        "move them to the intersection.",
    ),
    NetconvertOption(
        "--tls.join", None,
        "Signals very close together become one controller, as in a real cabinet.",
    ),
    NetconvertOption(
        "--tls.discard-simple", None,
        "Drop signals where no movements conflict (for example mid-block pedestrian "
        "signals: pedestrians are not simulated).",
    ),
    NetconvertOption(
        "--osm.turn-lanes", None,
        "Use OSM turn-lane arrows (turn:lanes) to decide which lane may turn where.",
    ),
    NetconvertOption(
        "--no-turnarounds.except-deadend", None,
        "U-turns only at dead ends: none at signals or median openings. OSM's 'no U-turn' "
        "rules on Woodland near Pennsylvania and Minnesota Ave cannot be imported, and "
        "mid-block U-turns are rare downtown.",
    ),
    NetconvertOption(
        "--roundabouts.guess", None,
        "Recognise roundabouts so their right-of-way rules are correct.",
    ),
    NetconvertOption(
        "--junctions.corner-detail", "5",
        "Draw rounded junction corners: realistic turning paths and nicer pictures.",
    ),
    NetconvertOption(
        "--output.street-names", None,
        "Keep street names, so signals can be named after their cross streets.",
    ),
    NetconvertOption(
        "--output.original-names", None,
        "Keep OSM IDs, so every edge can be traced back to the map.",
    ),
)  # fmt: skip


def type_files() -> list[Path]:
    """Return the edge-type files, in the order netconvert must load them.

    First SUMO's own OSM type map (lanes, priorities, permissions per road
    class), then our Florida speed defaults, which override only the speed of
    roads without a maxspeed tag.
    """
    return [
        sumo_home() / "data" / "typemap" / "osmNetconvert.typ.xml",
        SPEED_DEFAULTS_TYPE_FILE,
    ]


def netconvert_command(osm_file: Path, net_file: Path) -> list[str]:
    """Return the full ``netconvert`` command that builds the network."""
    command = [
        str(sumo_binary("netconvert")),
        f"--osm-files={osm_file}",
        f"--type-files={','.join(str(p) for p in type_files())}",
        f"--output-file={net_file}",
    ]
    for option in NETCONVERT_OPTIONS:
        command += option.as_args()
    return command


#: File-name endings of patch files, and the netconvert option that loads each.
PATCH_KINDS: dict[str, str] = {
    ".nod.xml": "--node-files",
    ".edg.xml": "--edge-files",
    ".con.xml": "--connection-files",
    ".tll.xml": "--tllogic-files",
}


def find_patches(patch_dir: Path) -> dict[str, list[Path]]:
    """Return the patch files in ``patch_dir``, grouped by netconvert option."""
    found: dict[str, list[Path]] = {}
    if patch_dir.is_dir():
        for path in sorted(patch_dir.iterdir()):
            for ending, flag in PATCH_KINDS.items():
                if path.name.endswith(ending):
                    found.setdefault(flag, []).append(path)
    return found


@dataclass
class BuildReport:
    """What happened while building the network.

    Attributes:
        net_file: The finished network.
        clip: What clipping the OSM data to the study area changed.
        warnings: Every warning netconvert printed, in order.
        patches: The patch files that were applied.
    """

    net_file: Path
    clip: ClipStats | None = None
    warnings: list[str] = field(default_factory=list)
    patches: list[Path] = field(default_factory=list)

    def warning_kinds(self) -> Counter[str]:
        """Count warnings by kind; numbers and quoted IDs are replaced by ``#``.

        netconvert prints only the first few warnings of each kind, followed
        by a line such as ``Warning: 7 total messages of type: ...``. Those
        summary lines give the true count of their kind, so they are used
        instead of counting the printed lines.
        """
        counts: Counter[str] = Counter()
        totals: dict[str, int] = {}
        for warning in self.warnings:
            match = _AGGREGATE.match(warning)
            if match:
                template = match.group(2).replace("%", "#")
                totals[_warning_kind("Warning: " + template)] = int(match.group(1))
            else:
                counts[_warning_kind(warning)] += 1
        for kind, total in totals.items():
            counts[kind] = max(counts[kind], total)
        return counts

    @property
    def warning_count(self) -> int:
        """Total number of warnings, including the ones netconvert did not print."""
        return sum(self.warning_kinds().values())


_AGGREGATE = re.compile(r"^Warning: (\d+) total messages of type: (.*)$")


def _warning_kind(warning: str) -> str:
    """Reduce a warning to its general kind, so similar warnings can be counted."""
    text = re.sub(r"'[^']*'", "'#'", warning)
    return re.sub(r"-?\d+(\.\d+)?", "#", text)


def _run(command: list[str]) -> list[str]:
    """Run a SUMO program and return its warning lines.

    Raises:
        RuntimeError: If the program fails or reports an error.
    """
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    lines = (completed.stdout + completed.stderr).splitlines()
    errors = [line for line in lines if line.startswith("Error")]
    if completed.returncode != 0 or errors:
        raise RuntimeError(
            f"{Path(command[0]).name} failed (exit code {completed.returncode}):\n"
            + "\n".join(errors or lines[-20:])
        )
    return [line for line in lines if line.startswith("Warning")]


def _display_path(path: Path) -> str:
    """Return ``path`` relative to the repository (or SUMO) folder, with ``/``.

    Absolute paths differ from one computer to the next (and on Windows they
    contain the user's name), so they must not end up in committed files.
    """
    # SUMO first: the pinned SUMO lives inside the repository's .venv folder,
    # whose layout differs between Windows, macOS and Linux.
    for base, label in ((sumo_home(), "<SUMO_HOME>/"), (REPO_ROOT, "")):
        try:
            return label + path.resolve().relative_to(base.resolve()).as_posix()
        except ValueError:
            continue
    return path.name


def provenance_header(osm_file: Path, bbox: BoundingBox, patches: list[Path]) -> str:
    """Return the XML comment that replaces netconvert's own header.

    netconvert's header contains the build time and absolute file paths, so
    the same network built twice (or on two computers) would never be
    byte-identical. This fixed header records the same information without
    them.
    """
    lines = [
        f"Built by scripts/m1_build_network.py with Eclipse SUMO netconvert {sumo_version()}.",
        f"Input: {_display_path(osm_file)}, clipped to {bbox.as_lon_lat_string()}",
        "Map data (c) OpenStreetMap contributors, available under the ODbL.",
        f"Type files: {', '.join(_display_path(p) for p in type_files())}",
        "Options (written without their leading dashes):",
        *(f"    {o.flag.lstrip('-')} {o.value or ''}".rstrip() for o in NETCONVERT_OPTIONS),
        f"Patches: {', '.join(_display_path(p) for p in patches) if patches else 'none'}",
        "Do not edit this file by hand: rebuild it, and put corrections in network/patches/.",
    ]
    body = "\n".join(f"    {line}" for line in lines)
    if "--" in body:
        # XML forbids "--" inside a comment; SUMO would refuse to load the file.
        raise ValueError(f"Header text must not contain '--':\n{body}")
    return "<!--\n" + body + "\n-->"


def replace_header(net_xml: str, header: str) -> str:
    """Replace the first XML comment of a network file with ``header``.

    Raises:
        ValueError: If the file has no leading comment before ``<net``.
    """
    start = net_xml.find("<!--")
    end = net_xml.find("-->", start)
    net_tag = net_xml.find("<net ")
    if start == -1 or end == -1 or net_tag == -1 or not start < end < net_tag:
        raise ValueError("Expected a header comment before the <net> element")
    return net_xml[:start] + header + net_xml[end + len("-->") :]


def build_network(
    osm_file: Path, net_file: Path, bbox: BoundingBox, patch_dir: Path | None = None
) -> BuildReport:
    """Build the SUMO network from an OSM snapshot and apply patches.

    Args:
        osm_file: The frozen OSM snapshot (``.osm.xml`` or ``.osm.xml.gz``).
        net_file: Where to write the network. A name ending in ``.gz`` is
            written gzip-compressed.
        bbox: The study area; roads outside it are removed.
        patch_dir: Folder with patch files (see ``network/patches/README.md``).

    Returns:
        The warnings printed by netconvert and the patches applied.
    """
    net_file.parent.mkdir(parents=True, exist_ok=True)
    report = BuildReport(net_file=net_file)
    with tempfile.TemporaryDirectory() as tmp:
        # Step 1: clip the OSM data to the study area (see osm.clip_to_bbox).
        opener = gzip.open if osm_file.name.endswith(".gz") else open
        with opener(osm_file, "rb") as handle:
            clipped, report.clip = clip_to_bbox(handle.read(), bbox)
        clipped_file = Path(tmp) / "clipped.osm.xml"
        clipped_file.write_bytes(clipped)

        # Step 2: netconvert builds the network from the clipped data.
        raw = Path(tmp) / "raw.net.xml"
        report.warnings += _run(netconvert_command(clipped_file, raw))

        patches = find_patches(patch_dir) if patch_dir else {}
        if patches:
            # Step 3: load the network just built plus the patch files.
            patched = Path(tmp) / "patched.net.xml"
            command = [str(sumo_binary("netconvert")), f"--sumo-net-file={raw}"]
            for flag, files in patches.items():
                command.append(f"{flag}={','.join(str(f) for f in files)}")
                report.patches += files
            command.append(f"--output-file={patched}")
            report.warnings += _run(command)
            raw = patched

        text = replace_header(
            raw.read_text(encoding="utf-8"), provenance_header(osm_file, bbox, report.patches)
        )
    data = text.encode("utf-8")
    if net_file.name.endswith(".gz"):
        write_gzip_deterministic(data, net_file)
    else:
        net_file.write_bytes(data)
    return report


@dataclass(frozen=True)
class LoadCheck:
    """Result of loading the network in SUMO.

    Attributes:
        warnings: Warning lines SUMO printed while loading and running.
        seconds_simulated: How long the empty network was simulated.
    """

    warnings: tuple[str, ...]
    seconds_simulated: int


def check_network_loads(net_file: Path, seconds: int = 60) -> LoadCheck:
    """Load the network in SUMO and simulate it empty for a short while.

    This is the milestone's "the network loads in SUMO with no errors" check.
    No vehicles are needed: loading alone validates the network file, and
    running a minute also runs every traffic light program.

    Raises:
        RuntimeError: If SUMO reports an error.
    """
    warnings = _run(
        [
            str(sumo_binary("sumo")),
            f"--net-file={net_file}",
            f"--end={seconds}",
            "--no-step-log=true",
        ]
    )
    return LoadCheck(warnings=tuple(warnings), seconds_simulated=seconds)
