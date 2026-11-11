"""The study area: which part of DeLand the digital twin covers.

The area is a *bounding box*: a rectangle on the map given by two latitudes
(south and north edge) and two longitudes (west and east edge). Everything the
project simulates lies inside this rectangle.

Why this rectangle (found in a survey of OpenStreetMap data, 2026-11-11):

* North edge, about 300 m north of Woodland Blvd at Plymouth Ave: includes
  the whole Stetson University campus, which OpenStreetMap places between
  Wisconsin Ave and just north of Pennsylvania Ave.
* South edge, about 330 m south of Woodland Blvd at Voorhis Ave: the south end
  of downtown.
* West edge, about 280 m west of New York Ave at Clara Ave, and east edge
  about 400 m east of New York Ave at Amelia Ave: the New York Ave (SR 44)
  crossing with its neighbouring signals, plus the parallel streets that
  drivers use to go around Woodland (Florida Ave, Amelia Ave, Garfield Ave).

The margins matter: queues form on the roads *leading into* a signal, so each
outermost signal needs a few hundred metres of approach road inside the box.

International Speedway Blvd (US 92, about 1.3 km north of Plymouth Ave) and
Beresford Ave (about 1.2 km south of Voorhis Ave) are left out. Including them
would double the area for two intersections that are not downtown.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoundingBox:
    """A rectangle on the map, in degrees (WGS84, the system GPS uses).

    Attributes:
        south: Latitude of the south edge.
        west: Longitude of the west edge (negative in the Americas).
        north: Latitude of the north edge.
        east: Longitude of the east edge.
    """

    south: float
    west: float
    north: float
    east: float

    def __post_init__(self) -> None:
        """Reject boxes that are impossible or upside down.

        Raises:
            ValueError: If a coordinate is out of range or the edges are
                in the wrong order.
        """
        if not (-90 <= self.south < self.north <= 90):
            raise ValueError(f"Need -90 <= south < north <= 90, got {self.south}, {self.north}")
        if not (-180 <= self.west < self.east <= 180):
            raise ValueError(f"Need -180 <= west < east <= 180, got {self.west}, {self.east}")

    def as_lon_lat_string(self) -> str:
        """Return ``"west,south,east,north"``.

        This is the order both the OpenStreetMap API (``bbox=...``) and
        ``netconvert --keep-edges.in-geo-boundary`` expect: the lower-left
        corner first, then the upper-right corner, each as longitude,latitude.
        """
        return f"{self.west},{self.south},{self.east},{self.north}"

    def contains(self, lat: float, lon: float) -> bool:
        """Return whether the point (``lat``, ``lon``) lies inside the box."""
        return self.south <= lat <= self.north and self.west <= lon <= self.east

    @property
    def area_square_degrees(self) -> float:
        """Size of the box in square degrees.

        The OpenStreetMap API refuses boxes above 0.25 square degrees (and
        any request with more than 50,000 map points).
        """
        return (self.north - self.south) * (self.east - self.west)


#: The downtown DeLand study area used by the whole project.
DELAND_STUDY_AREA = BoundingBox(south=29.0215, west=-81.3105, north=29.0455, east=-81.2950)


@dataclass(frozen=True)
class ExpectedSignal:
    """A signalized intersection that an outside source says exists.

    Attributes:
        street_a: First street, in the short form used by the inventory
            (for example ``"Woodland Blvd"``).
        street_b: Second street.
        source: Where the claim comes from.
    """

    street_a: str
    street_b: str
    source: str


_FDOT_439881_5 = (
    "FDOT project 439881-5 list of signalized intersections on US 17-92, "
    "found by web search on 2026-11-11 (page not opened directly; to be checked)"
)

#: Signals on Woodland Blvd inside the study area according to FDOT.
#: (The same list also names International Speedway Blvd, outside the area.)
EXPECTED_SIGNALS: tuple[ExpectedSignal, ...] = tuple(
    ExpectedSignal("Woodland Blvd", cross_street, _FDOT_439881_5)
    for cross_street in (
        "Plymouth Ave",
        "Pennsylvania Ave",
        "Minnesota Ave",
        "Wisconsin Ave",
        "Rich Ave",
        "Indiana Ave",
        "New York Ave",
        "Howry Ave",
        "Voorhis Ave",
    )
)
