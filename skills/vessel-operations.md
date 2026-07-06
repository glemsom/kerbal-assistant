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
| `PreLaunch` | On launchpad/runway, engines off | Stage to start, throttle up |
| `Landed` | Touched down on a surface | Launch, deploy experiments, EVA |
| `Splashed` | In water (ocean) | Same as landed, but buoyant |
| `Flying` | In atmosphere, not in orbit | Continue ascent or aerobrake |
| `SubOrbital` | Above atmosphere but not at orbital speed | Circularize at apoapsis (need ~2300 m/s for Kerbin orbit) |
| `Orbiting` | Stable orbit | Maneuver, transfer, or de-orbit |
| `Escaping` | On escape trajectory from body's SOI | Execute course correction or capture burn |

### Biome Science Value

Each biome on a body yields different science. Collect science once per biome per experiment.

- **Kerbin:** Grasslands, Highlands, Desert, Tundra, Shores, Oceans, etc.
- **Mun:** Highlands, Midlands, Lowlands, Craters, Poles
- **Minmus:** Lowlands, Midlands, Highlands, Flats, Slopes, Poles

Check `vessel.biome` from telemetry to see where you are. Use the Mobile Processing Lab (lab) to process data into science points.

## Control Guidance

### When to Stage

Stage when current stage thrust is insufficient to maintain positive acceleration.

Telemetry indicators:
- **Thrust-to-weight ratio (TWR) < 1** on ascent — you're losing velocity, stage immediately
- **Available thrust = 0** — current stage depleted, stage automatically or manually
- **Fuel in current stage = 0** for all resources — stage

Formula for TWR: `available_thrust / (mass * 9.81 * g_force)`

### When to Burn

| Maneuver | Best time | Notes |
|---|---|---|
| **Circularize** | At apoapsis (suborbital → orbit) | Burn prograde until periapsis rises above atmosphere |
| **De-orbit** | Opposite to velocity, at appropriate point | Aim for periapsis ≈ 25 km for Kerbin re-entry |
| **Transfer burn** | At ejection angle for target body | Use phase angle / transfer window calculator |
| **Plane change** | At ascending/descending node | Most efficient at apoapsis |
| **Phasing (rendezvous)** | Based on phase angle difference | Burn prograde to increase period (target catches up) or retrograde to decrease period (you catch up) |

### RCS Translation vs Rotation

| Goal | Method | kRPC Control |
|---|---|---|
| Rotate (point somewhere) | AutoPilot or SAS | `vessel.auto_pilot.target_pitch_and_heading(pitch, heading)` |
| Translate (move sideways) | RCS translation | `vessel.control.translate(x, y, z)` |
| Fine approach (docking) | RCS translate + AutoPilot target direction | Set target port as target, translate toward it |

## Common Telemetry Queries

| Question | Telemetry field(s) |
|---|---|
| "How much fuel left?" | `resources[stage].LiquidFuel.amount / .max` — check current stage |
| "Going fast enough for orbit?" | `orbit.speed` vs. orbital velocity (~2300 m/s at 70 km Kerbin) |
| "Am I stable?" | `orbit.eccentricity` close to 0 and `periapsis_altitude` > atmosphere depth |
| "Can I land?" | `vessel.situation` == Landed or surface altitude data |
| "How's my TWR?" | `available_thrust / (mass * body.surface_gravity)` |
| "Which biome am I over?" | `vessel.biome` |

## Error Conditions

| Telemetry Signal | Problem | Action |
|---|---|---|
| `g_force > 5` on ascent | Too fast through atmosphere | Reduce throttle, wait for thinner air |
| `dynamic_pressure > 15000` Pa | Aerodynamic stress risk | Throttle down to avoid structural failure |
| `atmosphere_density` increasing while descending | Heat risk | Slow down, shallower entry angle |
| `available_thrust = 0` and not staged | Fuel empty or engines off | Stage or activate engines |
| Situation = `Flying` and altitude dropping | Uncontrolled descent | Deploy parachutes or relight engines |
