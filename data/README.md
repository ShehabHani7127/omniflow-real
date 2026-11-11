# data/ — real-world inputs

Everything in this folder comes from the real world, not from a simulation.
Nothing here may be invented. If a value is not measured yet, it is marked as a
placeholder in the file itself.

| Folder    | What goes here                                                        | In git? | Filled in |
|-----------|-----------------------------------------------------------------------|---------|-----------|
| `osm/`    | The OpenStreetMap extract of downtown DeLand (one frozen snapshot)     | yes     | M1        |
| `counts/` | Traffic counts as CSV: FDOT counts and your own video counts           | yes     | M2, M6    |
| `videos/` | Your intersection videos                                               | **no**  | M6        |

Why videos are not committed: they are large, and they can show faces and
licence plates. Only the aggregated counts (numbers, no images) are published.

OpenStreetMap data is © OpenStreetMap contributors and is available under the
Open Database License (ODbL). The attribution is repeated in the main README.
