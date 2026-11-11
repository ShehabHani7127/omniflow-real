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
| M0 Design, environment, lint, tests | **Done. Waiting for the owner's approval of `DESIGN.md`.** | 24 tests pass on Linux (Python 3.11, 3.12, 3.13); smoke test passes. CI has never run yet |
| M1 Network from OpenStreetMap | Not started | Needs approval first. OSM hosts are blocked in the cloud session (see below) |
| M2 Demand and calibration | Not started | Needs real counts from the owner; build on flagged placeholders first |
| M3 Baselines and metrics | Not started | |
| M4 Multi-agent RL | Not started | |
| M5 Stress tests | Not started | |
| M6 Vision counting | Not started | Needs the owner's videos |
| M7 Report, dashboard export, polish | Not started | Needs a sample of the dashboard's JSON |

**Next action:** wait for the owner to approve `DESIGN.md` and answer the
open decisions below. Then do M1 only.

**Before M1, check the first CI run.** The workflow in
`.github/workflows/ci.yml` (Linux, Windows, macOS) had never run when M0 was
committed, so the code is untested on Windows and macOS, and the pinned
`setup-uv` commit hash in the workflow is unconfirmed. Look at the run with
the GitHub tools and fix any failure first.

### Open decisions (DESIGN.md section 13.1), not answered yet

- D1 Which hour to model (recommended: weekday afternoon peak).
- D2 Add max-pressure as an extra baseline (recommended: yes).
- D3 Number of test seeds (recommended: 10; minimum 5).
- D4 Generated SUMO files under `network/` or a separate `scenarios/` folder.
- D5 Keep the GitHub Actions CI workflow.
- D6 The owner's laptop: OS, and for a Mac the chip and macOS version.
- D7 M1 download: allow OSM hosts in the cloud session, or the owner runs the
  download command locally.

When the owner answers, record the answers here under **Key decisions**.

## Commands

```bash
uv sync                                    # create .venv with the locked dependencies
uv run pytest                              # all tests (about 3 seconds)
uv run pytest -m "not sumo"                # skip tests that start SUMO
uv run ruff check . && uv run ruff format . # lint, then auto-format
uv run python scripts/m0_smoke_test.py     # M0: prove SUMO runs and obeys Python
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
network/       generated SUMO input files (network, later demand and signal programs)
results/       committed tables and figures; results/raw/ is gitignored
scripts/       one entry point per milestone: mN_<name>.py
src/omniflow/  network/ demand/ control/ rl/ vision/ metrics/ export/  (one stage each)
               sumo_tools.py  find the pinned SUMO, choose libsumo or traci
               toy.py         one-intersection scenario for fast tests
               smoke.py       the M0 smoke simulation
tests/         pytest; conftest.py provides the toy_scenario fixture
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
8. **Seeds** (proposed, pending D3): training >= 1000, validation 100-104,
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

- The network allow-list blocks the OpenStreetMap servers (`overpass-api.de`,
  `api.openstreetmap.org`), `download.pytorch.org`, GitHub release downloads
  (YOLO weights), and FDOT, Volusia County and FHWA websites. PyPI and npm
  work. Web search works; fetching most pages does not.
- M1 therefore needs either the hosts allowed in the environment's network
  settings, or the owner running the download locally and committing the file.
- On Linux, the `rl` extra is about 6 GB because PyPI's PyTorch bundles GPU
  libraries. It still runs on CPU.
- SUMO wheels exist for Windows x64, Linux x64/ARM and macOS on Apple Silicon
  (1.28.0 needs macOS 15+). There is no wheel for Intel Macs.

## Facts about the real corridor (all still to be confirmed by the owner)

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
