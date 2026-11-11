"""Find and talk to the SUMO simulator that is pinned for this project.

Why this module exists
----------------------
Simulation results depend on the exact SUMO version. This project installs a
pinned SUMO from PyPI (the ``eclipse-sumo`` package), so everybody who follows
the README runs the *same* simulator.

The trap: many SUMO helper libraries look at the ``SUMO_HOME`` environment
variable first. If you once installed a different SUMO on your laptop, that
variable would silently send them to the wrong version. Every function here
therefore resolves paths from the pip-installed package and never trusts a
``SUMO_HOME`` that was set outside this project.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Literal

import sumo as _sumo_package  # the pip-installed simulator ("eclipse-sumo")

Backend = Literal["libsumo", "traci"]
"""How Python talks to SUMO.

* ``"libsumo"``: SUMO runs *inside* the Python process. Fast. No GUI.
* ``"traci"``: SUMO runs as a separate program and Python talks to it over a
  network socket. Slower, but it can drive ``sumo-gui`` so you can watch.

Both expose the same functions and (as the tests prove) give the same results.
"""

#: The SUMO Python packages that must all have exactly the same version.
SUMO_DISTRIBUTIONS: tuple[str, ...] = ("eclipse-sumo", "sumolib", "traci", "libsumo")


def sumo_home() -> Path:
    """Return the root folder of the pinned, pip-installed SUMO."""
    return Path(_sumo_package.SUMO_HOME)


def activate_pinned_sumo() -> Path:
    """Point ``SUMO_HOME`` at the pinned SUMO for this Python process.

    Third-party code (``sumolib``, ``sumo-rl`` and SUMO's own tool scripts)
    reads ``SUMO_HOME`` from the environment. Setting it here means that code
    uses the same simulator version as we do. The change only affects the
    current process and the programs it starts, not your shell.

    Returns:
        The folder that ``SUMO_HOME`` now points to.
    """
    home = sumo_home()
    os.environ["SUMO_HOME"] = str(home)
    return home


def sumo_binary(name: str = "sumo") -> Path:
    """Return the full path of a SUMO program such as ``sumo`` or ``netconvert``.

    Args:
        name: Program name without a file extension.

    Returns:
        Path to the executable inside the pinned SUMO installation.

    Raises:
        FileNotFoundError: If the pinned installation has no such program.
    """
    suffix = ".exe" if sys.platform == "win32" else ""
    path = sumo_home() / "bin" / f"{name}{suffix}"
    if not path.is_file():
        available = sorted(p.stem for p in (sumo_home() / "bin").iterdir())
        raise FileNotFoundError(
            f"SUMO program {name!r} not found at {path}. Available: {', '.join(available)}"
        )
    return path


def sumo_tool(relative_path: str) -> Path:
    """Return the full path of a script from SUMO's ``tools`` folder.

    Args:
        relative_path: Path inside ``tools``, for example ``"randomTrips.py"``
            or ``"net/net2geojson.py"``.

    Returns:
        Path to the tool script inside the pinned SUMO installation.

    Raises:
        FileNotFoundError: If the pinned installation has no such tool.
    """
    path = sumo_home() / "tools" / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"SUMO tool {relative_path!r} not found at {path}")
    return path


def sumo_version() -> str:
    """Return the version of the pinned SUMO, for example ``"1.28.0"``.

    Raises:
        RuntimeError: If the SUMO Python packages do not all share one
            version. Mixed versions can produce subtly different results, so
            we refuse to continue instead of guessing.
    """
    versions = {name: importlib.metadata.version(name) for name in SUMO_DISTRIBUTIONS}
    if len(set(versions.values())) != 1:
        raise RuntimeError(
            f"SUMO packages have mixed versions: {versions}. "
            "Run `uv sync --locked` to restore the pinned environment."
        )
    return versions["eclipse-sumo"]


def get_connection(backend: Backend = "libsumo") -> ModuleType:
    """Return the Python module used to control a SUMO simulation.

    Args:
        backend: ``"libsumo"`` (fast, in-process) or ``"traci"`` (socket).

    Returns:
        The ``libsumo`` or ``traci`` module. Both offer the same API, e.g.
        ``start()``, ``simulationStep()``, ``trafficlight`` and ``close()``.

    Raises:
        ValueError: If ``backend`` is not one of the two supported names.
    """
    if backend not in ("libsumo", "traci"):
        raise ValueError(f"Unknown backend {backend!r}; use 'libsumo' or 'traci'.")
    activate_pinned_sumo()
    return importlib.import_module(backend)
