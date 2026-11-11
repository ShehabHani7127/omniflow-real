"""Draw the network map with the signalized intersections marked.

Design choices (they follow a written chart guide, not taste):

* Ordinary streets are a recessive light gray, so they give context without
  competing for attention. Line width grows with the number of lanes.
* Only two streets get a colour, because the study is about them: Woodland
  Blvd (blue) and New York Ave (orange). The two colours were checked with a
  colour-vision-deficiency validator.
* Signals are dark numbered discs with a white ring. The numbers match the
  ``signal_no`` column of the inventory table and the list beside the map, so
  the map never depends on colour alone.
* The map is drawn in metres with equal scale on both axes (true shape) and a
  scale bar instead of axis ticks.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to a file; no window needed

import matplotlib.pyplot as plt
import sumolib
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from omniflow.network.inventory import SignalRecord, short_street_name

# Colours from the chart guide's validated palette (light mode).
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
STREET_GRAY = "#c3c2b7"
HIGHLIGHT_STREETS = {
    "Woodland Blvd": ("#2a78d6", "Woodland Blvd (US 17-92)"),
    "New York Ave": ("#eb6834", "New York Ave (SR 44)"),
}


def plot_network_map(
    net_file: Path,
    records: list[SignalRecord],
    png_file: Path,
    *,
    title: str,
    subtitle: str,
    labels: dict[str, tuple[float, float]] | None = None,
) -> None:
    """Draw the network and its signals and save the figure as a PNG.

    Args:
        net_file: The SUMO network.
        records: The signal inventory (gives positions and numbers).
        png_file: Where to save the image.
        title: Figure title.
        subtitle: Smaller line under the title (data source, date).
        labels: Optional place names to write on the map, as
            ``{text: (lat, lon)}``. The text starts at that point and runs
            to the right.
    """
    # Start from matplotlib's own defaults and a font that ships with it, so
    # the figure does not depend on settings or fonts of the computer.
    with plt.style.context("default"), matplotlib.rc_context({"font.family": "DejaVu Sans"}):
        net = sumolib.net.readNet(str(net_file))
        fig = plt.figure(figsize=(11, 9.6), facecolor=SURFACE)
        ax = fig.add_axes((0.02, 0.07, 0.56, 0.81), facecolor=SURFACE)
        side = fig.add_axes((0.60, 0.07, 0.38, 0.81), facecolor=SURFACE)
        side.axis("off")

        _draw_streets(ax, net)
        _draw_signals(ax, net, records)
        for text, (lat, lon) in (labels or {}).items():
            x, y = net.convertLonLat2XY(lon, lat)
            ax.text(
                x,
                y,
                text,
                color=INK_SECONDARY,
                fontsize=9,
                style="italic",
                ha="left",
                va="center",
                zorder=3,
                bbox={"boxstyle": "round,pad=0.25", "fc": SURFACE, "ec": "none", "alpha": 0.9},
            )

        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        _scale_bar(ax, metres=250)
        _north_arrow(ax)
        _legend(fig)
        _signal_list(side, records)

        fig.text(0.02, 0.965, title, color=INK_PRIMARY, fontsize=14, fontweight="bold", va="top")
        fig.text(0.02, 0.928, subtitle, color=INK_SECONDARY, fontsize=9, va="top")
        png_file.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(png_file, dpi=200, facecolor=SURFACE)
        plt.close(fig)


def _draw_streets(ax: Axes, net: sumolib.net.Net) -> None:
    """Draw ordinary streets in gray, then the highlighted streets on top.

    Each line is the street's centreline from junction centre to junction
    centre (``getRawShape``). The lane-based shape (``getShape``) would be
    wrong for a map: it is offset to one side for each direction of travel
    and stops at the junction border, so a two-way street with many short
    blocks would look like a dotted chain.
    """
    for edge in net.getEdges():
        street = short_street_name(edge.getName())
        xs, ys = zip(*edge.getRawShape(), strict=True)
        lanes = edge.getLaneNumber()
        if street in HIGHLIGHT_STREETS:
            colour, width, layer = HIGHLIGHT_STREETS[street][0], 1.2 + 0.7 * lanes, 2
        else:
            colour, width, layer = STREET_GRAY, 0.6 + 0.5 * lanes, 1
        ax.plot(xs, ys, color=colour, lw=width, solid_capstyle="round", zorder=layer)


def _draw_signals(ax: Axes, net: sumolib.net.Net, records: list[SignalRecord]) -> None:
    """Draw each signal as a dark disc with a white ring and its number inside."""
    for record in records:
        x, y = net.convertLonLat2XY(record.lon, record.lat)
        ax.plot(x, y, marker="o", ms=13, mfc=INK_PRIMARY, mec=SURFACE, mew=1.5, zorder=4)
        ax.text(
            x,
            y,
            str(record.signal_no),
            color="#ffffff",
            fontsize=6 if record.signal_no < 10 else 5.2,
            fontweight="bold",
            ha="center",
            va="center",
            zorder=5,
        )


def _legend(fig: Figure) -> None:
    """Draw the legend below the map."""
    items = [
        Line2D([], [], color=colour, lw=3, label=label)
        for colour, label in HIGHLIGHT_STREETS.values()
    ]
    items.append(Line2D([], [], color=STREET_GRAY, lw=2, label="Other streets (width = lanes)"))
    items.append(
        Line2D(
            [],
            [],
            marker="o",
            ls="",
            ms=10,
            mfc=INK_PRIMARY,
            mec=SURFACE,
            label="Signalized intersection (number = list)",
        )
    )
    fig.legend(
        handles=items,
        loc="lower left",
        bbox_to_anchor=(0.02, 0.005),
        frameon=False,
        fontsize=8.5,
        labelcolor=INK_SECONDARY,
        ncols=2,
    )


def _signal_list(side: Axes, records: list[SignalRecord]) -> None:
    """Write the numbered list of intersections beside the map."""
    side.text(
        0.0,
        1.0,
        "Signalized intersections, north to south",
        color=INK_PRIMARY,
        fontsize=11,
        fontweight="bold",
        va="top",
        transform=side.transAxes,
    )
    step = min(0.045, 0.9 / max(len(records), 1))
    for i, record in enumerate(records):
        row = 0.95 - i * step
        side.text(
            0.0,
            row,
            f"{record.signal_no:>2}",
            color=INK_PRIMARY,
            fontsize=9.5,
            fontweight="bold",
            family="monospace",
            va="top",
            transform=side.transAxes,
        )
        side.text(
            0.07,
            row,
            record.name,
            color=INK_PRIMARY,
            fontsize=9.5,
            va="top",
            transform=side.transAxes,
        )


def _scale_bar(ax: Axes, metres: float) -> None:
    """Draw a scale bar of ``metres`` length in the lower-right corner."""
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    right = x1 - 0.03 * (x1 - x0)
    bottom = y0 + 0.02 * (y1 - y0)
    ax.plot([right - metres, right], [bottom, bottom], color=INK_SECONDARY, lw=2, zorder=6)
    ax.text(
        right - metres / 2,
        bottom + 0.01 * (y1 - y0),
        f"{metres:.0f} m",
        color=INK_SECONDARY,
        fontsize=8.5,
        ha="center",
        va="bottom",
        zorder=6,
    )


def _north_arrow(ax: Axes) -> None:
    """Draw a small north arrow in the upper-right corner."""
    ax.annotate(
        "N",
        xy=(0.95, 0.99),
        xytext=(0.95, 0.93),
        xycoords="axes fraction",
        ha="center",
        va="center",
        color=INK_SECONDARY,
        fontsize=10,
        fontweight="bold",
        arrowprops={"arrowstyle": "-|>", "color": INK_SECONDARY, "lw": 1.5},
    )
