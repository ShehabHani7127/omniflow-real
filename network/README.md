# network/ — the SUMO road network

Everything in this folder is either **generated** by
`scripts/m1_build_network.py` or a **hand-written input** to that script.

| Path | What it is | Who writes it |
|------|------------|---------------|
| `deland.net.xml` | The downtown DeLand road network for SUMO | generated: never edit by hand |
| `config/florida_speed_defaults.typ.xml` | 30 mph default for roads without a speed-limit tag in OpenStreetMap | hand-written, with its source |
| `patches/` | Evidence-based corrections to the network | hand-written; see `patches/README.md` |

To rebuild the network after changing an input:

```bash
uv run python scripts/m1_build_network.py
```

Rebuilding from the same inputs gives a byte-identical `deland.net.xml`, so
`git diff` shows exactly what a change did. A test and the CI workflow both
check this.

To look at the network in the SUMO window:

```bash
uv run sumo-gui -n network/deland.net.xml
```

The network is built from OpenStreetMap data, © OpenStreetMap contributors,
available under the Open Database License (ODbL).
