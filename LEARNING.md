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
   a continuous integration workflow (GitHub will run both on every push).
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
ships a different program for each. One honest caveat: when this section was
written, the workflow had not run yet, because it starts on the first push. So
far everything has only been run on Linux. Until you see the first green check
mark on GitHub, treat "works on Windows and macOS" as a hope, not a fact.

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
