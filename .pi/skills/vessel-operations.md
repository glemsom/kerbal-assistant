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
| `Landed` | On surface, not moving | Launch, EVA, deploy experiments |
| `Splashed` | In water | Same as landed |
| `Flying` | In atmosphere, not in space | Fly, ascend, or aerobrake |
| `SubOrbital` | Above 70 km but periapsis < 70 km | Circularize or re-enter |
| `Orbiting` | Stable orbit (periapsis ≥ 70 km) | Maneuver, transfer, rendezvous |
| `Escaping` | On escape trajectory (eccentricity ≥ 1) | Burn to capture or escape |
| `Docked` | Docked to another vessel | Undock, transfer crew |
| `PreLaunch` | On launchpad/runway | Launch! |

## Burn Timing

### When to burn

| Maneuver | When | kRPC check |
|---|---|---|
| Circularization burn | At apoapsis | `v.orbit.time_to_apoapsis < 5` |
| De-orbit burn | At apoapsis (retrograde) | `v.orbit.time_to_apoapsis < 5` |
| Ejection burn (prograde) | At periapsis of parking orbit | `v.orbit.time_to_periapsis < 5` |
| Plane change | At ascending/descending node | Compute from orbit vectors |
| Capture burn | At periapsis of incoming trajectory | `v.orbit.time_to_periapsis < 30` |

### Burn execution pattern

```python
# Orient to burn vector
v.auto_pilot.target_direction(node.burn_vector(v.orbital_reference_frame))
v.auto_pilot.engage()
v.auto_pilot.wait()
# Full throttle until close
v.control.throttle = 1.0
while node.remaining_delta_v > 0.5:
    time.sleep(0.05)
v.control.throttle = 0.0
```

### Throttle management during burns

| Phase | Action |
|---|---|
| Start | Full throttle immediately to minimize gravity losses |
| Mid-burn (~50%) | Check remaining dV — if ahead of schedule, throttle down to avoid overshoot |
| Fine-tune (< 5 m/s remaining) | Throttle ≤ 0.05 for precision |
| Cutoff | Kill throttle at remaining_dV < 0.5 m/s |

## Biome Science

Science experiments give different results per biome. Maximize science by visiting multiple biomes on the same body.

**Kerbin biomes:** Grasslands, Highlands, Mountains, Desert, Tundra, Ice Caps, Water, Shores, Desert, etc.

**Mun biomes:** Highlands, Midlands, Lowlands, Craters, Polar, Canyon, etc.

**Biome detection (kRPC):** `v.flight(v.orbit.body.reference_frame).surface_altitude` — use biome map data or `v.flight().biome` (KSP 1.12+ supports this).

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
# Stage and get list of jettisoned parts
jettisoned = v.control.activate_next_stage()
# Check if staging actually did something
if not jettisoned:
    print("No parts to stage!")
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
