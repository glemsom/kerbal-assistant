---
name: vessel-operations
description: Reference for interpreting live telemetry from KSP vessels — orbital parameters, situation awareness, biome science, staging guidance, and burn timing. Use when reading telemetry or advising on vessel state.
---

# Vessel Operations Reference

## Reading Orbital Parameters

From telemetry orbit data:

| Parameter | What it tells you |
|---|---|
| **Apoapsis altitude** | Highest point in orbit — determines if you escape the body |
| **Periapsis altitude** | Lowest point — below ~70 km on Kerbin = re-entry |
| **Eccentricity** | 0 = circular, 0-1 = elliptical, ≥1 = escape trajectory |
| **Inclination** | Degrees from equatorial plane. 0° = equatorial, 90° = polar |
| **Semi-major axis** | Half the long axis — directly related to orbital period (Kepler's 3rd law) |
| **Period** | Time for one full orbit — useful for rendezvous timing |
| **Time to apoapsis** | When to perform certain burns (circularization at apoapsis) |
| **Time to periapsis** | When to perform landing burns or de-orbit |

### Interpreting the situation

| Situation | Meaning | What you can do |
|---|---|---|
| `pre_launch` | On launchpad/runway | Launch! |
| `landed` | On surface, not moving | Launch, EVA, deploy experiments |
| `splashed` | In water | Same as landed |
| `flying` | In atmosphere, not in space | Fly, ascend, or aerobrake |
| `sub_orbital` | Above 70 km but periapsis < 70 km | Circularize or re-enter |
| `orbiting` | Stable orbit (periapsis ≥ 70 km) | Maneuver, transfer, rendezvous |
| `escaping` | On escape trajectory (eccentricity ≥ 1) | Burn to capture or escape |
| `docked` | Docked to another vessel | Undock, transfer crew |

## Burn Timing

### When to burn

| Maneuver | When | kRPC check |
|---|---|---|
| Circularization burn | At apoapsis | `v.orbit.time_to_apoapsis < 5` |
| De-orbit burn | At apoapsis (retrograde) | `v.orbit.time_to_apoapsis < 5` |
| Ejection burn (prograde) | At periapsis of parking orbit | `v.orbit.time_to_periapsis < 5` |
| Plane change | At ascending/descending node | Compute from orbit vectors |
| Capture burn | At periapsis of incoming trajectory | `v.orbit.time_to_periapsis < 30` |

### Burn execution
See `krpc-patterns.md` Burn at a maneuver node for full code. Throttle phases:

| Phase | Action |
|---|---|
| Start | Full throttle (minimize gravity losses) |
| Mid-burn (~50%) | Check remaining dV — throttle down if ahead |
| Fine-tune (< 5 m/s) | Throttle ≤ 0.05 |
| Cutoff | Kill at remaining_dV < 0.5 m/s |

## Biome Science

Science differs per biome. Visit multiple biomes on same body to maximise.

**Kerbin:** Grasslands, Highlands, Mountains, Desert, Tundra, Ice Caps, Water, Shores
**Mun:** Highlands, Midlands, Lowlands, Craters, Polar, Canyon

**Detection:** `v.flight().biome` (KSP 1.12+) or biome map data.

## Staging

### When to stage

| Condition | Action |
|---|---|
| Current stage thrust = 0 (engine flameout) | Stage immediately |
| Current stage fuel depleted | Stage when convenient |
| TWR < 1.0 on ascent | Stage to improve TWR |
| Decoupler available after fairing jettison | Stage when aerodynamic enough |

### Staging in kRPC

```python
current_stage = v.control.current_stage
stage_parts = v.parts.in_stage(current_stage)

jettisoned = v.control.activate_next_stage()
if not jettisoned:
    print("No parts to stage!")
```

⚠️ **Gotcha:** Decoupler jettisoned parts become their own Vessel objects. `activate_next_stage()` returns **Vessel**, not Part. Use `.name` not `.title`.

### Burnout detection

```python
def stage_fuel_empty(vessel):
    stage_num = vessel.control.current_stage
    for part in vessel.parts.in_stage(stage_num):
        for resource in part.resources.all:
            if resource.amount > 0.001 and resource.density > 0:
                return False
    return True

while not stage_fuel_empty(v):
    time.sleep(0.5)
v.control.activate_next_stage()
```

### Engine state after staging

```python
for part in v.parts.all:
    if part.engine and part.engine.active:
        print(f"{part.title}: active, thrust={part.engine.thrust:.0f}N")
```

### Re-entry staging: separating re-entry vehicle

Before parachute deploy, separate the re-entry vehicle (pod + science + heat shield) from upper stage if a decoupler exists between them.

```python
# After de-orbit burn, before re-entry
# Stage to fire payload decoupler (separates pod from upper stage)
# The decoupler and parachute should be in separate VAB stages
v.control.activate_next_stage()  # fires decoupler, pod separates
time.sleep(2.0)  # wait for separation
# Continue coasting — upper stage burns up, pod descends alone

# Later, when conditions met: deploy chute
if alt < 5000 and speed < 400:
    v.control.activate_next_stage()  # deploys parachute
```

**Staging setup in VAB for pod-with-decoupler designs:**

| Stage | Action |
|-------|--------|
| 2 | Main engine ignition + launch clamps release |
| 1 | Interstage decoupler + upper stage engine ignition |
| 0 | **Payload decoupler** + parachute deploy (separate stages if chute deploy timing matters) |

**Common mistake:** Having the payload decoupler and parachute in the same stage → decoupler fires AND chute deploys simultaneously, which can cause the chute to rip off or tangle. Keep them separate.

### RCS Usage

| Action | kRPC | Notes |
|--------|------|-------|
| Enable RCS | `v.control.rcs = True` | Must have Monopropellant and RCS thrusters |
| Disable RCS | `v.control.rcs = False` | |
| Translation (fine) | `v.control.forward = 0.5` / `v.control.up = 0.0` | Range -1.0 to 1.0 |
| Rotation via RCS | SAS handles this when RCS enabled + SAS active | RCS provides extra torque if reaction wheels insufficient |

Use RCS when:
- Reaction wheels lack torque for orientation (heavy/tall craft)
- Docking/rendezvous fine translation
- Countering spin from asymmetric thrust
- SAS + RCS together give strongest attitude control

```python
v.control.rcs = True
v.control.sas = True
v.control.sas_mode = v.control.sas_mode.prograde
```
## Error Conditions

| Symptom | Likely cause | Fix |
|---|---|---|
| Thrust = 0 but fuel remaining | Stage not activated or engine not ignited | Stage or check engine type (solid vs liquid) |
| AP not changing during burn | Burning at wrong angle | Check prograde marker alignment |
| Spin during burn | Asymmetric mass or thrust | Enable RCS, reduce throttle |
| Can't orient to burn vector | Insufficient torque / RCS | Check RCS fuel, use reaction wheels |
| Node remaining_dV not decreasing | Out of fuel or wrong stage | Check resources, stage |
| Quicksave corrupt after script | Script modified save file during play | Don't use kRPC during save/load |
