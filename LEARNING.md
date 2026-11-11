# LEARNING.md — your study guide for OmniFlow Real

Each milestone adds one section to this file. A section explains, in plain
language, what was built, why it was built that way, and what was hard. It ends
with five questions an interviewer could ask you. Answer them out loud first,
then open the notes underneath.

A tip for interviews: nobody expects a first-year student to have invented
everything. They want to see that you understand *why* each choice was made
and what the alternatives were. That is what this file is for.

---

## Milestone 0: the plan, the workshop, and a first simulation

### 1. What was built

Think of M0 as setting up a workshop before building anything. There is no
DeLand traffic yet. Four things exist now:

1. **A plan** (`DESIGN.md`). What we will build, how we will measure it, how
   the comparison stays fair, and what could go wrong.
2. **A reproducible environment.** One command, `uv sync`, installs exactly
   the same version of every tool on any computer, including the traffic
   simulator SUMO.
3. **Quality gates.** A linter (`ruff`), 24 automated tests (`pytest`), and
   a continuous integration workflow (GitHub runs both on every push).
4. **A first working simulation.** One intersection with one traffic light,
   simulated by SUMO and controlled from Python.

Read the code in this order. It is short on purpose.

| File | What to look for |
|------|------------------|
| `src/omniflow/toy.py` | How a road network and its traffic are described in XML |
| `src/omniflow/smoke.py` | The loop that runs the simulation one second at a time |
| `src/omniflow/sumo_tools.py` | How the code finds the simulator |
| `tests/test_smoke.py` | The promises we make about the code |
| `pyproject.toml` | The list of dependencies and the tool settings |

### 2. Seven ideas you should be able to explain

**A microscopic traffic simulator.** SUMO moves every car individually. Time
advances in steps of one second. In each step every car picks its speed from
simple rules: do not hit the car in front, obey the signal, do not exceed your
preferred speed. "Microscopic" means each vehicle is simulated. (A
"macroscopic" model would treat traffic like water flowing in pipes.)

**The observe-act loop.** This is the heart of `smoke.py`, and of the whole
project:

```python
for each second:
    act      # tell the traffic light what to do (or leave it alone)
    step     # the simulator moves every car forward by one second
    observe  # read what happened: how many cars are waiting?
```

Every controller we build is this same loop with a different brain. A
fixed-time controller follows a clock. An actuated controller follows a simple
rule. An RL controller asks a neural network.

**Seeds.** A computer cannot roll dice. It produces "random" numbers from a
formula, and the formula starts from a number called the *seed*. The same seed
gives the same sequence of numbers, so the same cars appear at the same
moments, so the whole simulation comes out identical. A different seed gives a
different but equally believable day of traffic. Seeds give us two powers: we
can rerun any experiment exactly, and we can test two controllers on the very
same traffic.

**Virtual environment and lockfile.** A virtual environment (the `.venv`
folder) is a private set of Python packages for this project only.
`pyproject.toml` says what we *need* ("pandas, version 2.3 or newer").
`uv.lock` records what we actually *got*: the exact version of all 82 packages,
including the ones our packages need themselves. Without a lockfile, two
people who install a month apart get different versions, and you get the
classic "but it works on my machine".

**Tests.** A test is a small program that checks one promise about the code. A
*unit test* checks one function against a known answer. A *smoke test* just
switches the whole thing on to see whether it runs. Ours check the three
promises everything else will depend on:

| Promise | Why the project needs it |
|---------|--------------------------|
| Same seed gives exactly the same result | Otherwise no result can be reproduced |
| The fast and the slow way of talking to SUMO agree exactly | We train with the fast one and debug with the slow one |
| Python really controls the traffic light | Otherwise RL has nothing to control |

**Linter and formatter.** `ruff check` reads the code without running it and
reports problems: unused imports, missing docstrings, likely bugs.
`ruff format` rewrites the layout so all code looks the same. The point is
fewer silly mistakes, and code reviews about ideas instead of commas.

**Continuous integration (CI).** On every push, GitHub starts clean machines,
installs the project from the lockfile, and runs the linter and the tests. If
a change breaks something, we know within minutes. The workflow
(`.github/workflows/ci.yml`) covers Windows, macOS and Linux because SUMO
ships a different program for each. Its first run passed on all three. Until
then, "works on Windows and macOS" was only a hope, because everything had been
written and run on Linux. That gap is exactly what CI closes. A nice detail
from that first run: the smoke test printed the same vehicle counts and mean
queues on all three systems, although each one runs a different build of SUMO.

### 3. Design decisions and why

| Decision | Why | What we gave up |
|----------|-----|-----------------|
| Install SUMO with `pip`, pinned to exactly version 1.28.0 | Results depend on the simulator version. Everyone gets the same one with one command. | We cannot casually upgrade SUMO: an upgrade can change every number. |
| Never trust the `SUMO_HOME` environment variable | If you ever installed another SUMO, helper libraries would silently use that one. A silent wrong version means results nobody can reproduce or explain. | A few extra lines of code (`sumo_tools.py`) and tests for them. |
| `uv` with a lockfile instead of plain `pip` | One tool creates the environment, installs, and writes a lockfile valid for Windows, macOS and Linux. | One more tool to learn. |
| Two ways to talk to SUMO: `libsumo` by default, `traci` kept | `libsumo` runs SUMO inside Python and is much faster; RL needs millions of steps. `traci` is slower but works with the SUMO window, so you can watch. A test proves they give identical results. | Two code paths to keep working. |
| Heavy libraries (PyTorch, YOLO) are optional extras | Milestones M1 to M3 do not need them, and they are gigabytes. | One extra command later: `uv sync --extra rl`. |
| Strict from day one: docstrings and type hints required, warnings are errors | Cheap now, expensive to add later. You must explain this code in interviews, and documented code is explainable code. | The linter sometimes complains about small things. |
| A toy intersection for tests | The DeLand network will be slow to load. Slow tests do not get run. The toy runs in a few hundredths of a second. | The toy is not realistic. It only checks that the machinery works. |
| All metrics come from the simulator's own output files | A controller must not grade its own homework. One measuring instrument for everybody. | We cannot use the convenient numbers the RL library reports. |
| Three separate sets of seeds: training, validation, test | Like practice problems, a mock exam, and the final exam. If you choose your best model using the final exam, your grade is partly luck. | More simulation runs. |
| Controllers share phases, yellow times and minimum greens | A controlled experiment changes one thing. Here that one thing is *when a green ends*. | RL is not allowed some tricks, like skipping a phase. |
| Labels **[verified]**, **[planned]**, **[check]** in `DESIGN.md` | You always know what is a fact, what is an intention, and what still needs your eyes. | A little clutter in the text. |

### 4. The hardest bug: it installed fine, then it crashed

The plan uses a library called `sumo-rl`. `uv` installed it without a single
complaint. Before designing anything around it, I ran its built-in example.
It crashed:

```
TypeError: 'module' object is not callable
```

**The cause.** `sumo-rl` was last released in May 2024. It builds on another
library, PettingZoo. Since then, PettingZoo renamed a helper class from
`agent_selector` to `AgentSelector`. The old name still exists, but it now
refers to a *module* (a file) instead of a *class*. `sumo-rl` still calls the
old name as if it were a class, and Python refuses.

**Why the installer did not notice.** `sumo-rl` declares "I need PettingZoo
1.22.2 or newer". It does not say "but older than the version that renamed
things", because nobody can know the future. The installer followed the rule
and picked the newest PettingZoo. Remember this sentence: **"it installs" does
not mean "it works"**.

**The options.**

| Option | Good | Bad |
|--------|------|-----|
| Pin an old PettingZoo | No code needed | Old code next to new everything else: an untested mix that breaks again later |
| Patch the name at runtime (a "monkeypatch") | One line | We would be changing someone else's library behind its back |
| Use only the part of `sumo-rl` that works, behind our own small wrapper | Keeps a well-known library; we control the edges | We write and test the wrapper |
| Write our own environment from scratch | Full control | Most work; we lose a recognised library |

**The choice.** The third option, with the fourth as plan B. I checked first
that it can work: the core of `sumo-rl` runs with today's versions, and a
quick throwaway experiment trained a PPO agent on it from start to finish.

**Two lessons you can reuse anywhere.**

1. *Test your riskiest dependency before you design around it.* Engineers
   call such a quick experiment a "spike".
2. *Hide other people's libraries behind your own small interface.* All our
   code will talk to `omniflow.rl.env`, never to `sumo-rl` directly. If we
   replace the library, one file changes.

### 5. The hardest trap: a bad controller that looks good

In the smoke test, one run forces north-south to stay green forever, so
east-west traffic is never served. This is what the script printed on the
machine that wrote this section (run it to see yours):

```
libsumo, seed 42                 departed= 207  arrived= 207  mean queue= 3.08 veh
libsumo, north-south held green  departed= 176  arrived= 126  mean queue=38.06 veh
```

Both runs use seed 42, so the same 207 vehicles wanted to enter. In the bad
run only 176 got in. The other 31 were stuck *outside the map*, because the
east-west entry roads were full.

Here is the trap. SUMO writes a trip report with one line per vehicle that
entered. Those 31 vehicles have no line. If you compute "average delay" from
that report, the unluckiest vehicles vanish from your average. A controller
that jams the network could score *better* than an honest one.

This mistake has a name: **survivorship bias**. You only look at the ones that
made it. The classic story is about bombers in the Second World War. The
military wanted to add armour where returning planes had bullet holes. The
statistician Abraham Wald pointed out that those planes had survived. The
armour belonged where the returning planes had *no* holes, because planes hit
there did not come back.

**Our fix** (DESIGN.md, section 8):

- Decide *before* the simulation which vehicles get measured, from the
  schedule, not from who made it through.
- Count the time a vehicle waits outside the network as delay.
- Print the share of vehicles that never entered or never finished next to
  every result.

Two tests now protect this:
`test_same_seed_means_same_vehicles_whatever_the_signal_does` and
`test_vehicles_that_never_entered_are_missing_from_sumos_trip_report`.

**The tradeoff.** Our delay numbers will not match the summary SUMO prints,
and the code is more work than reading one average from a file. That is the
price of a number you can defend.

**One of my own assumptions was wrong, too.** I assumed that two ways of
measuring queue length would give identical numbers: counting stopped cars
once per second from Python, or reading SUMO's lane-data file. I checked. They
are close, but not identical. So the design now uses one definition for every
controller. The lesson: check an assumption with a small experiment before you
build on it.

### 6. Try it yourself (about 30 minutes)

1. Run `uv run python scripts/m0_smoke_test.py` and read every line.
2. Run the `sumo-gui` command it prints at the end. In the window, set
   "Delay" to about 100 ms and press the green play button. Watch the queue
   grow on red and shrink on green.
3. Run it again with `--seed 7`. Which numbers change? Which checks still
   pass? Why should they?
4. In `src/omniflow/toy.py`, change `exp(0.10)` to `exp(0.30)` on the
   `north_south` line. That triples the north-south traffic. Run the script
   again. With seed 42 the mean queue rises from about 3 to about 10 vehicles.
   Undo the change afterwards.
5. Run `uv run pytest -v` and read the test names. They read like a list of
   promises.
6. Break something on purpose. In `src/omniflow/smoke.py`, change
   `departed += conn.simulation.getDepartedNumber()` to `departed += 1`. Run
   `uv run pytest`. Two tests fail. Read their messages, then undo the change.
   This is what tests are for.

### 7. Five interview questions

**Q1. You compare three traffic-signal controllers. How do you make sure the
comparison is fair?**

<details>
<summary>Notes for your answer</summary>

- Same road network, same simulation length, and the same seeds, so every
  controller faces exactly the same vehicles. A test checks this.
- Same rules for all: the same phases, yellow times and minimum greens. Only
  the timing decisions differ.
- One piece of code measures all of them, from the simulator's output files.
  No controller measures itself.
- Several seeds, reported as a mean with a 95% confidence interval, so one
  lucky day cannot decide the result.
- The baselines are tuned with care too, on separate validation seeds. A weak
  baseline makes any new method look good.

</details>

**Q2. What is the difference between `pyproject.toml` and `uv.lock`? Why do
you need both?**

<details>
<summary>Notes for your answer</summary>

- `pyproject.toml` is written by a human: what the project needs, usually as
  ranges ("2.3 or newer").
- `uv.lock` is written by the tool: the exact version of every package,
  including the dependencies of our dependencies.
- The first states intent and makes upgrades possible. The second makes
  installs repeatable. Without the lockfile, the same command gives different
  packages on different days.
- Extra point: SUMO is pinned exactly even in `pyproject.toml`, because a
  different simulator version can change the results.

</details>

**Q3. Describe how a terrible signal controller could get a better
average-delay score than a good one. How does your design prevent it?**

<details>
<summary>Notes for your answer</summary>

- If a controller jams the roads, new vehicles cannot enter the network.
- The simulator's trip report only lists vehicles that entered. The blocked
  ones are missing, so their huge delay is not in the average.
- This is survivorship bias.
- Prevention: the set of measured vehicles is fixed from the schedule before
  the run; waiting outside the network counts as delay; the share of vehicles
  that never entered or finished is shown next to every result.

</details>

**Q4. A library you planned to use turned out to be broken with current
versions. What did you do?**

<details>
<summary>Notes for your answer</summary>

- How it was found: by running its example *before* designing around it.
- Root cause: a library it depends on renamed a class; its version rule had
  no upper limit, so the installer chose the incompatible newer version.
- Options: pin old versions, patch at runtime, use only the working core
  behind our own wrapper, or rewrite from scratch.
- Choice and reason: the working core behind a wrapper. It keeps a known
  library, isolates the risk in one file, and leaves a rewrite as plan B.
- Evidence, not hope: the core was tested with current versions, and a quick
  experiment trained an agent on it end to end.

</details>

**Q5. Why do you use separate training, validation and test seeds? What goes
wrong if you pick your best model using the test seeds?**

<details>
<summary>Notes for your answer</summary>

- Training seeds: the traffic the RL agent learns on.
- Validation seeds: used to make choices (settings, which saved model to
  keep, how to tune the baselines).
- Test seeds: used once, for the numbers in the report.
- If you choose with the test seeds, you select the model that happened to
  fit those particular days. The reported score is then too optimistic, and
  it will not hold on new days. It is the same reason a teacher does not hand
  out the final exam as practice.

</details>

---

## Milestone 1: a digital twin of downtown DeLand's streets

### 1. What was built

A road network of downtown DeLand that the SUMO simulator can drive cars on,
built automatically from OpenStreetMap. One command builds everything:

```bash
uv run python scripts/m1_build_network.py
```

It produces:

| File | What it is |
|------|------------|
| `data/osm/deland_downtown.osm.xml.gz` | The map data, downloaded once and frozen |
| `data/osm/deland_downtown.osm.meta.json` | Where and when it came from, plus its fingerprint |
| `network/deland.net.xml` | The SUMO road network |
| `results/m1_network/network_map.png` | The map with every signal numbered |
| `results/m1_network/signals.csv` | One row per signalized intersection |
| `results/m1_network/summary.md` | Every number about the network, generated |
| `results/m1_network/field_checklist.md` | What to check on a walk along Woodland |

Read the code in pipeline order. Each file does one step:

| File | Step |
|------|------|
| `src/omniflow/network/area.py` | Which rectangle of the map, and why |
| `src/omniflow/network/osm.py` | Download, freeze, and clip the map data |
| `src/omniflow/network/build.py` | Run `netconvert`, with a reason for every option |
| `src/omniflow/network/inventory.py` | List the signals and their movements |
| `src/omniflow/network/plot.py` | Draw the map |
| `src/omniflow/network/report.py` | Write the summary and the checklist |

### 2. Six ideas you should be able to explain

**OpenStreetMap's data model.** OSM stores three things. A *node* is a point
(latitude, longitude). A *way* is an ordered list of nodes: a street, a
building outline. A *relation* groups other elements; a *turn restriction*
is a relation that says "from this way, via this node, to that way: not
allowed" (or "only allowed"). Everything carries *tags*, such as
`highway=primary`, `maxspeed=30 mph`, `lanes=2` or
`highway=traffic_signals`.

**From a map to a simulator network.** A map is for humans. A simulator needs
much more: lanes, which lane may turn where, who yields to whom, and a signal
program for every traffic light. `netconvert` works all of this out from the
tags, and fills gaps with defaults. That last part is where errors creep in,
so this milestone mostly checks defaults.

**Provenance and fingerprints.** The snapshot's `.meta.json` records the exact
request, the download time and a SHA-256 *fingerprint* of the data. A
fingerprint is a 64-character code computed from every byte; change one byte
and the code changes completely. A test recomputes it, so nobody can swap the
map data unnoticed, not even by accident.

**Determinism.** Building twice from the same snapshot gives a
*byte-identical* network file, on Windows, macOS and Linux. That makes `git
diff` meaningful: if the network file changes, something real changed. A test
and the CI workflow both check this.

**Defaults are decisions.** When data is missing, software picks a value for
you. Here, OSM had speed limits only on Woodland and New York Ave, and SUMO's
defaults would have put Amelia Ave at 62 mph. A default you did not choose is
still a decision in your model, so the project makes it explicitly, writes it
in a file, and cites its source (Florida Statutes 316.183(2): 30 mph in
business and residence districts).

**Coordinates.** GPS positions are angles (latitude and longitude). SUMO
needs metres, so `netconvert` projects the map onto a flat grid (UTM zone
17). `sumolib` converts back to latitude and longitude with the `pyproj`
library, which is why `pyproj` became a dependency.

### 3. Design decisions and why

| Decision | Why | What we gave up |
|----------|-----|-----------------|
| Freeze one OSM snapshot in git | OSM changes daily; a frozen copy makes every later result reproducible | Fixes made to OSM later do not reach us until we refresh on purpose (`--refresh-osm`) |
| OSM API instead of Overpass | Overpass connections fail in this cloud session; the official API works and suits small areas | The API returns everything (buildings too), so the file is bigger than needed |
| Clip the data to the box ourselves | netconvert's own cut keeps whole roads that only touch the box; the first network was 4.9 km x 6.1 km instead of 1.5 km x 2.7 km | Roads now end at their last map point inside the box, a few metres short of the edge |
| Florida 30 mph default for untagged streets | SUMO's defaults are European highway speeds | If a street is really signed 25 mph, the field walk must find it |
| U-turns only at dead ends | Two OSM "no U-turn" rules on Woodland cannot be imported; this rule covers them | Real legal U-turns at an intersection, if any, are missing |
| Replace netconvert's header with a fixed one | It contains the build time and absolute paths (on Windows, your user name) | We must make sure our header is valid XML (see the bug below) |
| Store the network uncompressed | Compressed bytes depend on the zlib build, which differs between operating systems | A 1.7 MB file instead of about 0.23 MB |
| Number signals north to south, name them "Woodland Blvd & ..." | Stable, readable labels for the map, the checklist and later tables | The SUMO IDs (OSM node numbers) are still needed to talk to SUMO; both are in the CSV |
| Compare automatically with FDOT's list | An outside source catches mapping errors; doing it in code means it is redone on every rebuild | The FDOT list itself is unverified (found by web search) |

### 4. The hardest bug: a test that passed by luck

The test "the same download gives a byte-identical file" failed:

```
At index 10 diff: b'a' != b'b'
```

The two files had the same data but different names, `a.osm.xml.gz` and
`b.osm.xml.gz`. Byte 10 of a gzip file is where gzip stores the original file
name. Python writes it there unless you pass `filename=""`.

Why did the real network test pass? Because the rebuilt file was given the
same name as the committed one. The test was correct only by luck: it would
have broken the day someone renamed a file. The lesson is to **test the
property you mean**. "Equal data gives equal files" must hold for any name,
so the test should use different names on purpose.

The same detective work found three more traps:

- **`--` inside an XML comment is illegal.** The first fixed header listed
  options like `--junctions.join`. SUMO then refused to load the network. The
  load check caught it at once, which is exactly why the build ends with a
  load check.
- **A path that looks fine on Linux.** SUMO lives inside `.venv`, so its path
  printed as `.venv/lib/python3.12/...`, which on Windows is `.venv/Lib/...`.
  The header would have differed on your laptop. Now it prints `<SUMO_HOME>/...`.
- **Line endings.** Python's `write_text` writes `\r\n` on Windows, and the
  `csv` module writes `\r\n` everywhere. Every generated text file is now
  written with `\n`, so a rerun on your laptop changes nothing.
- **A computer-specific chart style.** This cloud computer has a system-wide
  matplotlib configuration that switches the font. The map would have looked
  different on your laptop. The plotting code now starts from matplotlib's own
  defaults and a font that ships with matplotlib.

### 5. The hardest tradeoff: how much to trust the map

OSM is made by volunteers. For this area it is good: all nine signals that
FDOT lists on Woodland Blvd are there, and OSM's turn restrictions at Woodland
and New York Ave agree with an independent report. But the build summary
still lists 49 warnings, and every one was read. What they mean:

| Warning kind | Meaning | Matters? |
|--------------|---------|----------|
| Restriction relation ignored / no way found | A turn rule points at a road that is outside the box or is a driveway. Two "no U-turn" rules on Woodland are the exception; the U-turn decision above covers them | Checked one by one |
| Discarding unknown compound / unusable type | Old railway tags on some roads | No |
| PT line with no stops | Bus routes; buses are not simulated | No |
| Sharp turn / roundabout replaced | The roundabout on Amelia Ave near campus, redrawn | No |
| Cannot apply turn sign information | Turn-lane arrows in OSM that do not match the lane count, on two edges | Field check |

The rule: **do not silence warnings, explain them.** A long list of ignored
warnings is how real errors hide. The summary counts them by kind, and this
table explains each kind.

What the data cannot tell us goes on the field checklist, generated from the
network so nothing is forgotten:

- Woodland & New York: really no turns at all?
- Minnesota Ave (#5) and Indiana Ave (#11): really only three approaches?
- Woodland & Church St (#7): a signal in OSM but not in FDOT's list.
- Downtown Woodland: one lane each way plus turn pockets?

### 6. Try it yourself (about 30 minutes)

1. Run `uv run python scripts/m1_build_network.py`. Then run `git status`.
   The network and every text report must be unchanged: that is determinism.
   Only `network_map.png` may show as changed on your laptop, because an
   image can differ in tiny pixel details between operating systems. (The
   plotting code already uses a font that ships with matplotlib, so the
   computer's own fonts and settings do not matter.)
2. Open the network: `uv run sumo-gui -n network/deland.net.xml`. Zoom into
   Woodland & New York Ave and look at the arrows at the end of each lane:
   they show the allowed movements. (I could not test the SUMO window in the
   cloud session, which has no screen: tell me if anything looks wrong.)
3. Open `network/deland.net.xml` in a text editor and read the header comment.
   Find one `<tlLogic>` element: that is a signal program, with phases written
   as strings of `G` (green), `y` (yellow) and `r` (red), one letter per
   movement.
4. In `network/config/florida_speed_defaults.typ.xml`, change one `13.41` to
   `27.78` (62 mph). Rebuild, then run `git diff --stat`. Which files changed?
   Look at the speed table in `results/m1_network/summary.md`. Undo with
   `git checkout -- network results`.
5. Print `results/m1_network/field_checklist.md` and take it on a walk from
   Plymouth Ave to New York Ave.

### 7. Five interview questions

**Q1. How did you turn OpenStreetMap data into a simulation network, and how
do you know the result is right?**

<details>
<summary>Notes for your answer</summary>

- Download once through the OSM API, freeze it with a fingerprint, clip it to
  the study box, convert with `netconvert` using options that each have a
  written reason.
- "Right" has several checks: SUMO loads it with no errors; every signal on
  FDOT's list for Woodland is present; turn rules at the key intersection
  match an independent source; every warning was read and explained.
- What code cannot check goes to a field checklist. Corrections become
  patch files with evidence, never hand edits.

</details>

**Q2. What does "reproducible" mean for this network, and how did you enforce
it?**

<details>
<summary>Notes for your answer</summary>

- Same input snapshot, byte-identical network, on Windows, macOS and Linux.
- Things that broke it: a build timestamp and absolute paths in netconvert's
  header; gzip storing a time and a file name; zlib differences between
  systems; `\r\n` line endings.
- Enforced by a test that rebuilds and compares, and by CI rerunning the
  build on three operating systems with `git diff --exit-code`.

</details>

**Q3. Your simulator has default values for missing data. Give an example
where a default would have been wrong, and how you handled it.**

<details>
<summary>Notes for your answer</summary>

- OSM had speed limits only on two roads. SUMO's defaults would have given
  62 mph on Amelia Ave downtown.
- Faster roads change travel times, routes, and how much signals matter, so
  every later result would be distorted.
- Fix: an explicit 30 mph default in a small file, citing Florida Statutes
  316.183(2); tagged roads keep their tagged value. The summary prints the
  speed table so anyone can check it.

</details>

**Q4. Why did you clip the map data yourself instead of using netconvert's
boundary option?**

<details>
<summary>Notes for your answer</summary>

- The API returns every road that touches the box complete. Some streets run
  far past the box without crossing another street, so they arrive as one long
  piece.
- netconvert's option keeps any road that is partly inside, so the network
  came out about 4.9 km x 6.1 km instead of 1.5 km x 2.7 km.
- Clipping keeps only points inside the box. It is tested on a hand-made map,
  including a road that leaves the box and comes back.
- Lesson: check what a tool's option actually does, here by measuring the
  network size, before trusting its name.

</details>

**Q5. A tool printed 49 warnings. What did you do with them?**

<details>
<summary>Notes for your answer</summary>

- Grouped them by kind (numbers and IDs removed), using the true totals
  netconvert reports for repeated warnings.
- Explained each kind. Most are harmless (railway tags, bus routes, roads
  outside the box). Two "no U-turn" rules could not be imported, which led to
  the U-turn decision.
- Warnings went into the generated summary instead of being silenced, so a
  new warning after a change stands out.

</details>
