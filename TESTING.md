# Testing — Pi agent KSP capabilities

Tests whether Pi agents (Pi coding agent) can perform Kerbal Space Program
tasks correctly — choosing the right scripts, passing correct parameters,
interpreting output, and applying skill knowledge.

**Not** testing the scripts themselves. Scripts are assumed correct.
We test the agent's orchestration and reasoning.

---

## How to run a test

### Pre-flight: verify kRPC connectivity

Before running any scenario, confirm the testing rig works:

```bash
cd ~/Documents/git/kerbal-assistant
.venv/bin/python scripts/ksp-status.py --all
```

Expected output (exit 0, JSON with `"connected": true`):

```json
{
  "connected": true,
  ...
}
```

If `"connected": false`, fix KSP/kRPC before proceeding.
Do not spawn Pi until this passes.



### Prerequisites

- **tmux** installed
- **KSP running** with kRPC server enabled
- **This repo** cloned and configured (see `setup/` and `USAGE.md`)
- **Pi** configured with OpenCode Go or equivalent provider
- **Pre-flight check** passed (see below)

### Procedure

### Guiding principle: prefer scripts over inline Python

Pi may write inline Python for connectivity checks. This is **not acceptable**
here. The repo has scripts that handle null vessel, connection errors, clean
JSON output. Scenarios must check: did Pi use the existing script, or reinvent?

| Instead of inline Python | Use existing script |
|-------------------------|-------------------|
| `krpc.connect()` + try/except | `ksp-status.py --all` |
| `sc.active_vessel` bare | `ksp-status.py` or `krpc_utils.get_active_vessel()` |
| Raw orbit calculations | `dv-calc.py`, `dv-map.py` |
| Phase angle math | `transfer-window.py --standalone` |



1. **Spawn a fresh Pi agent** in this repo's root:

   ```bash
   cd ~/Documents/git/kerbal-assistant
   tmux new-session -d -s ksp-test 'pi'
   tmux attach -t ksp-test
   ```

   Pi loads skills from `.pi/skills/` automatically because we're in the
   repo root.

2. **Wait** for the Pi prompt to appear.

3. **Type the test prompt** verbatim from the scenario.

4. **Observe** Pi's actions (tool calls, script invocations, reasoning)
   and its final response to the user.

5. **Check pass criteria** — tick each bullet in the scenario.

6. **Kill the session** when done:

   ```bash
   tmux kill-session -t ksp-test
   ```

### Clean state

Always spawn a fresh tmux session for each test. Do not reuse sessions —
context leakage between tests invalidates results. Kill after each run.

---

## Scenario: Build a simple rocket, launch to orbit

The first and most fundamental test. Exercises rocket design, TWR/dV
budgeting, vessel loading, and autonomous ascent.

### User prompt

```
I need to get a simple rocket into a 100 km circular orbit around Kerbin.
Can you help me design one and launch it?
```

### Preconditions

| Condition | Value |
|-----------|-------|
| KSP scene | Space Center (KSC) |
| Active vessel | None (at KSC) |
| Available craft | A simple rocket in VAB (any name — agent must query via `--list`. NOTE: the default craft is suborbital-only; agent must detect inadequate dV and suggest building a proper orbital rocket.) |
| Career/Sandbox | Sandbox preferred (no part unlock constraints) |
| kRPC server | Started |

### Expected Pi actions (in order)

1. **Design phase**
   - Query existing craft: `python scripts/launch-vessel.py --list`
   - If no suitable craft, describe a simple rocket design:
     - Stage 1: Swivel/Terrier, ~1.2–1.5 TWR at launch
     - Stage 2: Terrier/Spark, ~0.7–1.0 TWR in vacuum
     - Total dV ≥ 3400 m/s for Kerbin orbit
   - Optionally run `dv-calc.py` to validate TWR/dV targets
   - Ask user to build it in VAB (since Pi cannot build craft)

2. **Launch phase** (after user confirms craft exists)
   - Load craft: `python scripts/launch-vessel.py "<craft-name>"` (name from `--list` output)
   - Launch: `python scripts/auto-ascent.py --target-apo 100000`

### Expected output shape

Pi should:
- Explain the rocket design rationale (TWR, staging, dV budget)
- Give clear instructions for building in VAB (parts, staging order)
- After launch, report success (orbit achieved, final apo/peri)
- If script errors occur, explain them helpfully

### Pass criteria

- [ ] Pi checks for existing craft before asking user to build
- [ ] Pi suggests a design with dV ≥ 3400 m/s and reasonable TWR
- [ ] Pi uses `dv-calc.py` with concrete numbers (not vague estimates)
- [ ] Pi loads the craft via `launch-vessel.py`
- [ ] Pi runs `auto-ascent.py` with `--target-apo 100000`
- [ ] Pi correctly interprets orbit-achieved event from ascent output
- [ ] Pi reports final orbit parameters (apoapsis, periapsis)
- [ ] Pi does NOT hallucinate part names or KSP mechanics

### Skills that should be loaded

| Skill | Why |
|-------|-----|
| `.pi/skills/ascent-profiles.md` | Launch parameters, TWR targets |
| `.pi/skills/delta-v-planning.md` | dV budget, Tsiolkovsky equation |
| `.pi/skills/krpc-reference.md` | Script APIs, connection patterns |

---

## Scenario: Staging validation

Tests the agent's ability to manage multi-stage launches — inspecting stage
structure, detecting burnout, sequencing stage activation, and verifying
thrust/mass changes at each transition.

### User prompt

```
We need to test your ability to use stages. Launch the current rocket,
and validate you can make use of the stages correctly.
```

### Preconditions

| Condition | Value |
|-----------|-------|
| KSP scene | LaunchPad (pre_launch) |
| Active vessel | A multi-stage rocket on launchpad, stage >= 3, with at least one SRB stage + decouplers + liquid engine |
| Craft manifest | 3x SRB (stage 3), 3x decoupler (stage 2), 1x LV-T45 (stage 1), core (stage 0) |
| Career/Sandbox | Sandbox |
| kRPC server | Started |

### Expected Pi actions (in order)

1. **Inspect stage structure**
   - Read `v.control.current_stage`
   - List parts per stage with `v.parts.in_stage(n)`
   - Identify engines, decouplers, fuel resources per stage

2. **First stage activation**
   - `activate_next_stage()` at highest stage
   - Verify SRBs ignite (thrust > 0, mass change)
   - Verify liftoff (positive climb rate)

3. **SRB burnout detection**
   - Monitor `stage_fuel_empty()` or equivalent
   - Detect when SolidFuel depleted in current stage
   - Report burnout (altitude, speed, burn duration)

4. **SRB jettison**
   - Stage to fire decouplers
   - Verify mass decreases, spent boosters separate
   - Note that `activate_next_stage()` returns Vessel objects for jettisoned stages

5. **Center engine activation**
   - Stage to ignite LV-T45
   - Verify engine state (active=true, has_fuel=true, thrust > 0)

6. **Fuel burn monitoring**
   - Track LiquidFuel/Oxidizer consumption
   - Verify thrust increases with altitude (vacuum Isp effect)

7. **Cleanup**
   - Kill throttle, disengage autopilot, enable SAS

### Expected output shape

Pi should emit JSON events per phase (via `log_event()` or similar):
- Structure map of stages before liftoff
- Each staging event with before/after metrics
- Burnout detection with timestamp and altitude
- Final summary of all stage transitions

### Pass criteria

- [ ] Pi reads `current_stage` and `parts.in_stage()` before launch
- [ ] Pi identifies all engines and fuel per stage
- [ ] Pi activates first stage -> SRBs ignite -> liftoff confirmed
- [ ] Pi detects SRB burnout via fuel depletion check
- [ ] Pi stages to jettison spent SRBs -> mass drops, thrust changes
- [ ] Pi activates center engine -> LV-T45 running, fuel consumed
- [ ] Pi monitors fuel burn over at least 3 ticks
- [ ] Pi kills throttle and disengages autopilot after test
- [ ] Pi avoids `p.title` on jettisoned parts (they're Vessel, not Part)

### Skills that should be loaded

| Skill | Why |
|-------|-----|
| `.pi/skills/krpc-reference.md` | kRPC staging API, `activate_next_stage()`, `parts.in_stage()` |
| `.pi/skills/vessel-operations.md` | When to stage, staging patterns, burnout detection |

---

## Future scenarios (outline)

### Scenario: dV feasibility check

Prompt: *"I'm in LKO. Can my current vessel reach Duna?"*

Checks: Pi reads telemetry, compares dV map requirements, shows math.

### Scenario: Transfer to Minmus

Prompt: *"Plan a Hohmann transfer to Minmus. Create the maneuver node."*

Checks: Transfer window calc, node creation, timing.

### Scenario: Career pulse

Prompt: *"How's my career going? What should I do next?"*

Checks: Save parsing, contract analysis, strategy advice from career skill.

### Scenario: Powered landing

Prompt: *"I'm in orbit around the Mun. Land at the south pole."*

Checks: Deorbit burn planning, landing profile, suicide burn guidance.

### Scenario: Orbital rendezvous

Prompt: *"I have two ships in LKO. Dock them together."*

Checks: Phasing burns, approach guidance, docking procedure.

### Scenario: Error recovery

Prompt: *"Launch to orbit."* (with no KSP running / no vessel)

Checks: Pi detects script failure, explains problem, suggests fix.

---

## Coverage matrix

| KSP domain | Scenario | Skills exercised | Scripts called |
|------------|----------|-----------------|----------------|
| Rocket design | Build + launch | ascent-profiles, delta-v-planning | dv-calc, launch-vessel |
| Autonomous ascent | Build + launch | ascent-profiles, krpc-reference | auto-ascent |
| Staging management | Staging validation | krpc-reference, vessel-operations | staging-test (or inline) |
| dV budgeting | dV feasibility, Transfer | delta-v-planning, krpc-reference | telemetry, dv-map, dv-calc |
| Transfer windows | Transfer to Minmus | delta-v-planning | transfer-window, create-node |
| Career management | Career pulse | career-strategy | save-parser |
| Landing | Powered landing | landing-profiles | landing, deorbit-calc |
| Rendezvous/docking | Orbital rendezvous | rendezvous | rendezvous, docking |
| Error handling | Error recovery | krpc-reference | ksp-status |

---

## Adding new scenarios

1. Copy the scenario template below
2. Decide the user prompt (exact text)
3. Decide expected Pi tool calls (ordered list)
4. List observable pass criteria
5. List skills Pi should read

### Scenario template

```markdown
### Scenario: <name>

**Prompt:** *"..."*

**Preconditions:**
| Condition | Value |
...

**Expected Pi actions:**
1. ...

**Pass criteria:**
- [ ] ...
```
