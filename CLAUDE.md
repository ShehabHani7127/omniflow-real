# CLAUDE.md — project memory for OmniFlow Real

Read this first in every session. Then read `DESIGN.md` (the plan) and the
latest section of `LEARNING.md`. Keep this file current: update **Current
status** at the end of every milestone.

## Goal

Build a data-calibrated digital twin of downtown DeLand, Florida (Woodland
Blvd / US 17-92 corridor from Stetson University through downtown, plus the
New York Ave / SR 44 crossing) in SUMO, and train multi-agent RL traffic
signal controllers that are compared **fairly** against realistic baselines
(fixed-time, actuated). Final output: reproducible results, a research-style
report, and a JSON export for the owner's existing OmniFlow web dashboard.

## Who you are working with, and the rules they set

The owner is a first-year Computer Science student at Stetson University,
early in learning to program. They must defend this project in technical
interviews and graduate school applications. Therefore:

1. **Production quality, but teach as you go.** After every milestone, append
   a section to `LEARNING.md`: simple language; what was built; why each
   design decision was made; the hardest bug or tradeoff; then 5
   interview-style questions.
2. **Never invent data or results.** If real data is missing, use clearly
   labelled placeholders and say exactly what to collect. Every number in
   `README.md` and `REPORT.md` must come from a script in this repo that
   anyone can rerun.
3. **One milestone at a time.** At the end of each: run the tests, commit with
   a clear message, update this file, write the `LEARNING.md` section, then
   **stop and summarize**. Do not start the next milestone without approval.
4. **Fair comparisons only:** same scenarios, same seeds, same simulation
   length for all controllers.
5. **Honest results**, including where RL does not beat the baselines, with
   an explanation.
6. If something is impossible in the current environment, say so clearly and
   give the exact command to run on the owner's own machine.

## Current status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0 Design, environment, lint, tests | **Done, approved 2026-11-11** | CI green on Linux (3.11, 3.12), Windows and macOS |
| M1 Network from OpenStreetMap | **Done. Waiting for the owner's approval of the study area and network.** | `scripts/m1_build_network.py`; 19 signals; all 9 FDOT-listed Woodland signals found; 73 tests pass |
| M2 Demand and calibration | Not started | Needs real counts from the owner; build on flagged placeholders first |
| M3 Baselines and metrics | Not started | |
| M4 Multi-agent RL | Not started | |
| M5 Stress tests | Not started | |
| M6 Vision counting | Not started | Needs the owner's videos |
| M7 Report, dashboard export, polish | Not started | Needs a sample of the dashboard's JSON |

**Next action:** wait for the owner to approve the M1 study area and network
(map: `results/m1_network/network_map.png`) and, ideally, to do the field walk
with `results/m1_network/field_checklist.md`. Then do M2 only. M2 can start
on synthetic demand before field corrections arrive; corrections become
patches in `network/patches/` and the network is rebuilt.

**CI:** `.github/workflows/ci.yml` runs lint, tests and the smoke test on
every push (Linux, Windows, macOS). The first run passed on all four jobs, and
the smoke test printed the same vehicle counts and mean queues on all three
operating systems. Check the run with the GitHub tools after every push and
keep it green.

### Owner's decisions on DESIGN.md (approved 2026-11-11)

- D1 Modelled hour: a normal weekday afternoon peak, about 4:30-5:30 pm, on a
  day when Stetson is in session.
- D2 Max-pressure is added as an extra baseline (M3).
- D3 10 test seeds (0-9); validation 100-104; training 1000+.
- D4 Generated SUMO files live under `network/`.
- D5 Keep the GitHub Actions CI workflow.
- D6 The owner's laptop runs **Windows**. Every command in README/LEARNING
  must work in Windows PowerShell; CI covers windows-latest.
- D7 The owner set the cloud environment's network access to Full.
  Result (2026-11-11): `api.openstreetmap.org` works; Overpass
  (`overpass-api.de` and its mirrors) still fails at the TLS handshake through
  the proxy. M1 therefore uses the OSM API `map` call, not Overpass.

## Commands

```bash
uv sync                                    # create .venv with the locked dependencies
uv run pytest                              # all tests (about 6 seconds)
uv run pytest -m "not sumo"                # skip tests that start SUMO
uv run ruff check . && uv run ruff format . # lint, then auto-format
uv run python scripts/m0_smoke_test.py     # M0: prove SUMO runs and obeys Python
uv run python scripts/m1_build_network.py  # M1: rebuild network + reports (byte-identical)
uv run sumo-gui -n network/deland.net.xml  # look at the network
uv sync --extra rl                         # add RL dependencies (M4+)
uv sync --extra vision                     # add vision dependencies (M6)
```

## Repository map

```
DESIGN.md      the plan: architecture, metrics, protocol, risks, open questions
LEARNING.md    one teaching section per milestone, for the owner
README.md      quickstart now; results and reproduction commands in M7
REPORT.md      research-style report (created in M7)
data/          real-world inputs: osm/, counts/, videos/ (videos are gitignored)
network/       deland.net.xml (generated), config/ (speed defaults), patches/ (evidence-based fixes)
results/       committed tables and figures; results/raw/ is gitignored
               m1_network/  signals.csv, expected_signals.csv, network_map.png,
                            summary.md, field_checklist.md (all generated by the M1 script)
scripts/       one entry point per milestone: mN_<name>.py
src/omniflow/  network/ demand/ control/ rl/ vision/ metrics/ export/  (one stage each)
               sumo_tools.py  find the pinned SUMO, choose libsumo or traci
               toy.py         one-intersection scenario for fast tests
               smoke.py       the M0 smoke simulation
               paths.py       every standard folder and file path, in one place
               network/       area.py (study box, FDOT list), osm.py (download, clip),
                              build.py (netconvert), inventory.py, plot.py, report.py
tests/         pytest; conftest.py provides toy_scenario and tiny_osm_file (a hand-made
               OSM extract with one signal, a turn restriction and a road leaving the box)
```

## Key decisions and their reasons

1. **SUMO is pinned to exactly 1.28.0**, installed from PyPI (`eclipse-sumo`,
   `sumolib`, `traci`, `libsumo`, all the same version). Simulation results
   depend on the simulator version.
2. **Always locate SUMO through `omniflow.sumo_tools`**, never through a
   `SUMO_HOME` from the shell. Importing `omniflow` sets `SUMO_HOME` to the
   pinned install for the process, so sumolib, sumo-rl and SUMO's tool scripts
   agree. A stale system SUMO would otherwise be used silently.
3. **uv + `pyproject.toml` + `uv.lock`.** The lockfile is the pin. Default
   Python 3.12 (`.python-version`); `requires-python >= 3.11`; tests pass on
   3.11, 3.12, 3.13.
4. **`libsumo` is the default backend** (in-process, fast). `traci` is kept
   for `sumo-gui` and debugging. A test proves both give identical results.
5. **Optional extras** `rl` and `vision` are installed only when needed.
   `ultralytics` is AGPL-3.0, so vision stays isolated in `omniflow.vision`.
6. **sumo-rl 1.4.5**: its PettingZoo wrapper crashes with PettingZoo >= 1.25
   (`agent_selector` was renamed to `AgentSelector`). Its core
   `SumoEnvironment(single_agent=False)` works with Gymnasium 1.4 and SUMO
   1.28. Plan: use only the core, behind `omniflow.rl.env`. It has no all-red,
   never enforces `max_green`, and uses one yellow time for all signals; our
   adapter must add those rules. It needs `SUMO_HOME` at import time, so
   import `omniflow` first.
7. **Metrics come only from SUMO's output files**, computed by one module for
   every controller. The cohort is defined by *scheduled* departure time.
   Delay = `timeLoss + departDelay`; vehicles that never entered are still
   counted (they have no tripinfo record). Every table shows the share of
   unfinished and not-inserted vehicles, plus teleports and collisions.
8. **Seeds** (decided, D3): training >= 1000, validation 100-104,
   test 0-9. Tune everything on validation seeds; touch test seeds once.
9. **Controllers share** phases, yellow, all-red, minimum green and maximum
   green. They differ only in when a green phase ends.
10. **RL plan** (to be finalised in M4): binary action keep/switch, observation
    described relative to the current phase, reward = minus the number of
    halted vehicles, PPO with one shared policy (Stable-Baselines3).
11. **Placeholders are loud**: `is_placeholder` column in count CSVs, and a
    warning banner in any output built from placeholder data.
12. **Evaluation inputs are frozen files in git** (network, route files, final
    RL policy), so the main table is reproducible from a fresh clone.
13. **M1 network pipeline:** OSM API `map` call (not Overpass) -> snapshot
    `data/osm/deland_downtown.osm.xml.gz` + `.meta.json` (SHA-256 of the
    uncompressed XML) -> clip to the study box in Python (`osm.clip_to_bbox`;
    netconvert's `--keep-edges.in-geo-boundary` keeps whole roads that only
    touch the box) -> netconvert with `NETCONVERT_OPTIONS` (each with a
    reason) and two type files (SUMO's osmNetconvert.typ.xml, then
    `network/config/florida_speed_defaults.typ.xml`) -> optional patches ->
    netconvert's header replaced by a fixed provenance header.
14. **Determinism is tested.** Same snapshot -> byte-identical
    `network/deland.net.xml` (committed uncompressed: gzip bytes depend on the
    zlib build). CI reruns the M1 script on Linux, Windows and macOS and runs
    `git diff --exit-code` on the network and reports (not the PNG: fonts).
    All generated text files are written with LF line endings.
15. **Speed defaults:** OSM tags `maxspeed` only on the primary roads. Untagged
    roads get 30 mph (Florida Statutes 316.183(2), read on flsenate.gov).
16. **U-turns only at dead ends** (`--no-turnarounds.except-deadend`): two OSM
    "no U-turn" relations on Woodland (9993350, 9993352) have a via-way that
    netconvert cannot import.
17. **Study area** (`omniflow.network.area.DELAND_STUDY_AREA`): lon -81.3105
    to -81.2950, lat 29.0215 to 29.0455. Plymouth Ave to Voorhis Ave on
    Woodland; Clara Ave to Amelia Ave (plus margin) on New York Ave. ISB and
    Beresford Ave left out. The owner must approve it.

## Conventions

- **Code:** small modules, type hints and Google-style docstrings everywhere
  (ruff enforces rule sets `D` and `ANN` outside `tests/`). Line length 100.
  Write docstrings and comments so a first-year student can follow them.
- **Scripts:** thin command-line wrappers around functions in `src/omniflow/`.
  Logic lives in the package so tests can import it.
- **Tests:** `tests/test_<module>.py`. Tests that start SUMO are marked
  `@pytest.mark.sumo`. Warnings are errors. Use the `toy_scenario` fixture for
  anything that needs a real simulation; it runs in well under a second.
- **Docs:** `DESIGN.md` labels facts as **[verified]**, **[planned]** or
  **[check]**. Keep that honest. `LEARNING.md` uses simple language.
- **Numbers:** no hand-typed results in `README.md` or `REPORT.md`. Tables are
  generated from `results/` by a script (mechanism to be built in M3).
- **Git:** work on the branch the session designates. Commit messages start
  with the milestone, for example `M1: build DeLand network from OSM`.
  No pull request unless the owner asks.

## Environment notes for cloud sessions

- Network access is Full since 2026-11-11 (owner's change). Verified then:
  `api.openstreetmap.org`, `nominatim.openstreetmap.org` and `www.flsenate.gov`
  work with curl (flsenate rate-limits: "Too Many Requests"; wait and retry
  once). Overpass (`overpass-api.de`, `lz4.`/`z.` mirrors,
  `overpass.kumi.systems`) fails at the TLS handshake. The WebFetch tool
  cannot resolve many hosts that curl in the container can reach: use curl.
- Before Full access (M0): OSM, `download.pytorch.org`, GitHub release
  downloads, FDOT, Volusia County and FHWA sites were blocked. Recheck before
  relying on any of them.
- On Linux, the `rl` extra is about 6 GB because PyPI's PyTorch bundles GPU
  libraries. It still runs on CPU.
- SUMO wheels exist for Windows x64, Linux x64/ARM and macOS on Apple Silicon
  (1.28.0 needs macOS 15+). There is no wheel for Intel Macs.

## Facts about the real corridor (all still to be confirmed by the owner)

From the OSM snapshot (2026-11-11), verified in data:

- 19 OSM `highway=traffic_signals` nodes in the study area become 19 SUMO
  traffic lights (no joining needed). The list is `results/m1_network/signals.csv`.
- Woodland Blvd & New York Ave: OSM relations 392814-392817 say
  `only_straight_on` from all four approaches; the network has only the 4
  straight movements there.
- OSM has a signal at Woodland Blvd & Church St that the FDOT list does not
  name. Minnesota Ave (#5) and Indiana Ave (#11) have only 3 approaches.
  Downtown Woodland is one through lane per direction plus turn pockets.
- Stetson campus (OSM relation 5986685): about lat 29.0318-29.0409.

Found by web search on 2026-11-11; the pages could not be opened directly.

- FDOT project 439881-5 lists signalized intersections on Woodland Blvd at
  Voorhis, Howry, New York (SR 44), Indiana, Rich, Wisconsin, Pennsylvania,
  Minnesota and Plymouth Avenues, and at International Speedway Blvd.
- FDOT project 437842-1 (listed as completed): an adaptive signal control
  system on US 17-92 from Monroe Road (Seminole County) to Minnesota Avenue
  (Volusia County). The field system may therefore be adaptive. Never claim
  that RL beats "what DeLand has today".
- AARoads: turns are prohibited in all directions at Woodland and New York.
- Volusia County Traffic Engineering (123 W. Indiana Ave, DeLand) reportedly
  maintains all signals in the county except Daytona Beach's: the place to ask
  for timing sheets.
- FDOT resurfacing project 445301-1 (Woodland from Wisconsin Ave northward)
  and proposed safety projects 449457-1/-2/-3: lane layouts may have changed.

## Gotchas already found

- `pytest` exits with code 5 when it collects no tests, which CI treats as a
  failure. An "empty" suite is not a passing suite.
- `traci` prints "Retrying in 1 seconds" while SUMO starts. That is normal.
- SUMO teleports a vehicle after 300 s stuck (default). Teleports hide
  gridlock. Count them; the smoke test disables teleporting.
- A vehicle that never entered the network has no record in SUMO's tripinfo
  output, and SUMO's own average time loss ignores it.
- Lane-data `waitingTime` is close to, but not exactly, the per-second count
  of halted vehicles. Pick one definition and use it for every controller.
- SUMO 1.28's default emission class is `HBEFA4/PC_petrol_Euro-4` (European).
  Use CO2 for comparisons between controllers only.
- GitHub release downloads and the PyTorch CPU index are blocked in the cloud
  session, so a custom PyTorch index cannot be locked from here.
- If `git push` is refused with "Claude doesn't have GitHub access", do not
  retry. The owner has to reconnect GitHub or install the Claude GitHub App on
  the repository. This happened on the first M0 push.
- XML comments may not contain `--`. SUMO refuses to load a file whose header
  comment lists options like `--junctions.join`.
- Python's gzip stores the original file name in the header unless
  `filename=""` is passed; equal data under two names gives different bytes.
- netconvert prints only the first few warnings of a kind, then
  `Warning: N total messages of type: ...`. `BuildReport.warning_kinds` uses N.
- sumolib `edge.getShape()` is the lane-side shape (offset per direction);
  `getRawShape()` is the street centreline. Use the raw shape for maps.
- sumolib needs `pyproj` for `convertXY2LonLat` (now a dependency).
- The pinned SUMO lives inside `.venv`, whose layout differs by OS: print its
  paths as `<SUMO_HOME>/...`, never relative to the repository.
- `pytest` treats warnings as errors: always close files (`with open(...)`).
- This cloud container has `/etc/matplotlib/matplotlibrc` (font Inter). Figures
  must not depend on it: `plot.py` draws inside `plt.style.context("default")`
  with the bundled DejaVu Sans font.
