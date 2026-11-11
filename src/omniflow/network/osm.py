"""Download and freeze an OpenStreetMap extract.

OpenStreetMap (OSM) is a map of the world that volunteers edit every day. That
is great for freshness and bad for reproducibility: the same download a month
later gives a slightly different map, so a slightly different network and
slightly different results. The fix is to download **once**, commit the file,
and record exactly where and when it came from (its *provenance*).

The download uses the official OSM API "map" call. It returns every map point
(node) in the box, every way (road, building outline, ...) that uses one of
those points, and every relation (for example a turn restriction) that uses
them. Ways that cross the edge of the box come back complete, so roads are
not cut in the middle of a block.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from omniflow.network.area import BoundingBox

#: The official OpenStreetMap API endpoint for a map extract.
OSM_API_MAP_URL = "https://api.openstreetmap.org/api/0.6/map?bbox={bbox}"

#: The OSM API asks clients to identify themselves. Deliberately generic:
#: no personal names or e-mail addresses are sent.
USER_AGENT = "omniflow-real/0.1 (traffic simulation research)"

#: A function that takes a URL and returns the response body.
Fetcher = Callable[[str], bytes]


@dataclass(frozen=True)
class OsmSummary:
    """What an OSM extract contains.

    Attributes:
        nodes: Number of map points.
        ways: Number of ways (roads, building outlines, ...).
        relations: Number of relations (turn restrictions, routes, ...).
        attributes: Attributes of the ``<osm>`` root element, such as the
            copyright and licence notice.
    """

    nodes: int
    ways: int
    relations: int
    attributes: dict[str, str]


def fetch_url(url: str, timeout_s: float = 180.0) -> bytes:
    """Download ``url`` and return the response body.

    Raises:
        RuntimeError: If the server answers with an error. The OSM API
            explains errors in plain text (for example "You requested too
            many nodes"), so that text is included in the message.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"OSM API error {error.code} for {url}: {detail}") from error


def summarize_osm(xml_bytes: bytes) -> OsmSummary:
    """Count the elements of an OSM XML document.

    Raises:
        ValueError: If the bytes are not an OSM XML document.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as error:
        raise ValueError(f"Not valid XML: {error}") from error
    if root.tag != "osm":
        raise ValueError(f"Expected an <osm> document, got <{root.tag}>")
    return OsmSummary(
        nodes=len(root.findall("node")),
        ways=len(root.findall("way")),
        relations=len(root.findall("relation")),
        attributes=dict(root.attrib),
    )


def sha256_hex(data: bytes) -> str:
    """Return the SHA-256 fingerprint of ``data`` as 64 hexadecimal characters.

    A fingerprint (hash) changes completely if even one byte changes, so it
    proves that a file is exactly the one that was downloaded.
    """
    return hashlib.sha256(data).hexdigest()


def write_gzip_deterministic(data: bytes, path: Path) -> None:
    """Write ``data`` gzip-compressed, so that equal data gives an equal file.

    A normal gzip file also stores the time it was written and the original
    file name, so compressing the same data twice (or under another name)
    gives two different files. Storing time zero and no name removes both
    differences.
    """
    with (
        path.open("wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz,
    ):
        gz.write(data)


def download_snapshot(
    bbox: BoundingBox,
    osm_file: Path,
    *,
    fetch: Fetcher = fetch_url,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, object]:
    """Download the OSM extract for ``bbox`` and freeze it with its provenance.

    Writes two files: the extract itself (gzip-compressed, ``osm_file``) and a
    provenance file next to it (same name with ``.meta.json`` instead of
    ``.xml.gz``).

    Args:
        bbox: The area to download.
        osm_file: Where to write the extract. Must end in ``.osm.xml.gz``.
        fetch: Function that downloads a URL. Tests replace it so they never
            touch the network.
        now: Function returning the current time. Tests replace it.

    Returns:
        The provenance record that was written.

    Raises:
        ValueError: If ``osm_file`` has the wrong name or the server did not
            return an OSM document.
    """
    if not osm_file.name.endswith(".osm.xml.gz"):
        raise ValueError(f"OSM snapshot file name must end in .osm.xml.gz, got {osm_file.name}")
    url = OSM_API_MAP_URL.format(bbox=bbox.as_lon_lat_string())
    downloaded_at = now()
    data = fetch(url)
    summary = summarize_osm(data)

    osm_file.parent.mkdir(parents=True, exist_ok=True)
    write_gzip_deterministic(data, osm_file)
    meta: dict[str, object] = {
        "source_url": url,
        "bbox": {"south": bbox.south, "west": bbox.west, "north": bbox.north, "east": bbox.east},
        "downloaded_at_utc": downloaded_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha256_uncompressed": sha256_hex(data),
        "bytes_uncompressed": len(data),
        "nodes": summary.nodes,
        "ways": summary.ways,
        "relations": summary.relations,
        "copyright": summary.attributes.get("copyright", ""),
        "attribution": summary.attributes.get("attribution", ""),
        "license": summary.attributes.get("license", ""),
    }
    meta_path(osm_file).write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return meta


def meta_path(osm_file: Path) -> Path:
    """Return the provenance file that belongs to an OSM snapshot file."""
    return osm_file.with_name(osm_file.name.removesuffix(".xml.gz") + ".meta.json")


def verify_snapshot(osm_file: Path) -> dict[str, object]:
    """Check that a committed snapshot is exactly the file that was downloaded.

    Returns:
        The provenance record.

    Raises:
        ValueError: If the fingerprint does not match the provenance record.
    """
    meta = json.loads(meta_path(osm_file).read_text(encoding="utf-8"))
    with gzip.open(osm_file, "rb") as gz:
        actual = sha256_hex(gz.read())
    if actual != meta["sha256_uncompressed"]:
        raise ValueError(
            f"{osm_file} was changed after download: fingerprint {actual} "
            f"does not match {meta['sha256_uncompressed']}"
        )
    return meta


def named_area_center(osm_file: Path, name: str) -> tuple[float, float] | None:
    """Return the (lat, lon) centre of a named area in an OSM snapshot.

    Used to place labels such as "Stetson University" on the map. The centre
    is the average of all points of the area's outline: good enough for a
    label, not for measuring anything.

    Args:
        osm_file: A ``.osm.xml.gz`` snapshot.
        name: The exact OSM ``name`` of a way or relation.

    Returns:
        The centre, or ``None`` if no element with that name has points in
        the snapshot.
    """
    with gzip.open(osm_file, "rb") as gz:
        root = ET.fromstring(gz.read())
    points = {
        n.get("id"): (float(n.get("lat", 0)), float(n.get("lon", 0))) for n in root.iter("node")
    }
    way_nodes = {w.get("id"): [nd.get("ref") for nd in w.iter("nd")] for w in root.iter("way")}

    def has_name(element: ET.Element) -> bool:
        return any(t.get("k") == "name" and t.get("v") == name for t in element.iter("tag"))

    refs: list[str] = []
    for way in root.iter("way"):
        if has_name(way):
            refs += way_nodes[way.get("id", "")]
    for relation in root.iter("relation"):
        if has_name(relation):
            for member in relation.iter("member"):
                if member.get("type") == "way":
                    refs += way_nodes.get(member.get("ref", ""), [])
    coords = [points[r] for r in refs if r in points]
    if not coords:
        return None
    return sum(c[0] for c in coords) / len(coords), sum(c[1] for c in coords) / len(coords)


#: OSM road classes that cars may use (the ones the network keeps). Service
#: roads, footways and paths are excluded: SUMO's type map bars cars from them.
CAR_ROAD_CLASSES = frozenset(
    {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
     "residential", "living_street", "motorway_link", "trunk_link", "primary_link",
     "secondary_link", "tertiary_link"}
)  # fmt: skip


@dataclass(frozen=True)
class ClipStats:
    """What clipping an OSM extract to the study area changed.

    Road counts cover car roads only (``CAR_ROAD_CLASSES``). Buildings,
    footways and other ways are clipped too, but they do not become part of
    the network.

    Attributes:
        nodes_kept: Map points inside the box.
        nodes_removed: Map points outside the box.
        roads_shortened: Roads that crossed the edge of the box and were cut
            back to their inside part.
        roads_removed: Roads with fewer than two points inside the box.
        roads_split: Roads that left the box and came back in. Only their
            longest inside piece is kept, so this should be zero; the build
            report shows it.
    """

    nodes_kept: int
    nodes_removed: int
    roads_shortened: int
    roads_removed: int
    roads_split: int


def inside_runs(flags: list[bool]) -> list[tuple[int, int]]:
    """Return the ``(start, end)`` index ranges of consecutive ``True`` values.

    ``end`` is exclusive, like in ``range``.

    >>> inside_runs([False, True, True, False, True])
    [(1, 3), (4, 5)]
    """
    runs: list[tuple[int, int]] = []
    start = None
    for i, flag in enumerate([*flags, False]):  # the extra False closes a final run
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            runs.append((start, i))
            start = None
    return runs


def clip_to_bbox(xml_bytes: bytes, bbox: BoundingBox) -> tuple[bytes, ClipStats]:
    """Cut an OSM extract down to the points inside ``bbox``.

    The OSM API returns every way that has at least one point in the box,
    complete. A street that runs a kilometre past the edge of the box without
    meeting another street therefore arrives whole, and netconvert would keep
    it. Clipping keeps the network to exactly the study area: each way keeps
    only its points inside the box, so roads end at their last map point
    inside it.

    Relations (for example turn restrictions) are kept unchanged; netconvert
    ignores, with a warning, any that refer to removed ways.

    Returns:
        The clipped OSM XML and statistics about what was changed.
    """
    root = ET.fromstring(xml_bytes)
    inside: dict[str, bool] = {}
    for node in root.findall("node"):
        is_inside = bbox.contains(float(node.get("lat", "nan")), float(node.get("lon", "nan")))
        inside[node.get("id", "")] = is_inside
        if not is_inside:
            root.remove(node)

    shortened = removed = split = 0
    for way in root.findall("way"):
        is_road = any(
            tag.get("k") == "highway" and tag.get("v") in CAR_ROAD_CLASSES
            for tag in way.findall("tag")
        )
        refs = way.findall("nd")
        runs = inside_runs([inside.get(nd.get("ref", ""), False) for nd in refs])
        start, end = max(runs, key=lambda run: run[1] - run[0], default=(0, 0))
        if end - start < 2:
            root.remove(way)
            removed += is_road
            continue
        split += is_road and len(runs) > 1
        if end - start < len(refs):
            shortened += is_road
            for nd in refs[:start] + refs[end:]:
                way.remove(nd)

    kept_nodes = sum(inside.values())
    stats = ClipStats(
        nodes_kept=kept_nodes,
        nodes_removed=len(inside) - kept_nodes,
        roads_shortened=shortened,
        roads_removed=removed,
        roads_split=split,
    )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), stats
