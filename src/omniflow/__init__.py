"""OmniFlow Real: AI traffic signal control for downtown DeLand, Florida.

The package is organised as a pipeline. Each sub-package is one stage:

* ``network``: build the road network from OpenStreetMap (milestone M1)
* ``demand``: generate traffic and calibrate it against real counts (M2)
* ``control``: fixed-time, actuated and RL signal controllers (M3, M4)
* ``metrics``: delay, queue, throughput, CO2 and statistics (M3)
* ``rl``: learning environment, training and evaluation (M4)
* ``vision``: count vehicles in intersection videos (M6)
* ``export``: write results as JSON for the web dashboard (M7)

See ``DESIGN.md`` for the full design and ``CLAUDE.md`` for the current status.
"""

from omniflow.sumo_tools import activate_pinned_sumo

__version__ = "0.1.0"

# Make every tool in this process use the pinned SUMO (see sumo_tools.py).
activate_pinned_sumo()
