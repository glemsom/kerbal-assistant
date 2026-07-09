---
name: krpc-reference
description: Condensed kRPC API reference — connection setup, core services (SpaceCenter, Vessel, Control, AutoPilot), common patterns for KSP scripting. Use when writing or understanding kRPC Python scripts.
---

> **Venv**: This repo installs kRPC in `.venv/`. Run scripts with `.venv/bin/python` or activate `source .venv/bin/activate` first.

# kRPC API Reference for Pi

Condensed reference for writing kRPC scripts. Full docs at [krpc.github.io/krpc](https://krpc.github.io/krpc/).

> **Health check:** Use `python scripts/ksp-status.py --all` to test connectivity.
> Script handles null vessel, connection errors, outputs clean JSON.
> Prefer existing scripts over inline Python for standard checks.

## Connection

```python
import krpc
conn = krpc.connect(name='kerbal-assistant', address='127.0.0.1', rpc_port=50000, stream_port=50001)
```

Default ports: RPC=50000, Stream=50001. Configure in KSP → kRPC toolbar.

## Core Services

### SpaceCenter (`conn.space_center`)

| Method / Property | Returns | Description |
|---|---|---|
| `.active_vessel` | `Vessel` | Currently controlled vessel |
| | | _⚠️ Throws ValueError when no vessel active (KSC scene). Not None. Use try/except or `krpc_utils.get_active_vessel()`._ |
| `.vessels` | `list[Vessel]` | All vessels in physics range |
| `.bodies` | `dict[str, CelestialBody]` | All celestial bodies (keyed by name) |
| `.target_body` | `CelestialBody` | Currently targeted body |
| `.target_vessel` | `Vessel` | Currently targeted vessel |
| `.waypoints` | `list[Waypoint]` | All waypoints |
| `.ui_visible` | `bool` | Toggle UI |
| `.warp_to(t)` | — | Physics warp to UT `t` |
| `.rails_warp_factor` | `int` | Set rails warp (0-7) |
| `.warp_rate` | `float` | Current warp rate (1.0 = 1x) |
| `.transform_position(p, from_ref, to_ref)` | `(x,y,z)` | Coordinate transform |
| `.launch_vessel(directory, name, site, recover, crew)` | — | Launch from VAB/SPH (⚠️ param order: craft_directory, name, launch_site, recover, crew) |
| `.launch_vessel_from_vab(name, recover=True)` | — | Launch VAB craft to LaunchPad (preferred) |
| `.launch_vessel_from_sph(name, recover=True)` | — | Launch SPH craft to Runway (preferred) |
| `.launchable_vessels(directory)` | `list[str]` | Craft names in `"VAB"` or `"SPH"` |
| `.can_revert_to_launch()` | `bool` | Check if revert to launch is available |
| `.revert_to_launch()` | — | Revert to launch without returning to KSC |

> **Gotchas:** SpaceCenter has no `game_scene` attr in v0.5.4. `.warp_rate` throws
> when not in flight scene. Always wrap `active_vessel` access.
> **No `current_scene` or `game_scene` attribute** in kRPC 0.5.x. Cannot detect scene programmatically. Use `launch_vessel_from_vab()` when you know you're in VAB, or direct user to enter VAB manually.
> **No recover vessel API** — kRPC cannot recover a landed vessel. User must do it manually via KSP Tracking Station > Recover.
> **Search caveat:** Web-searching "KSP" returns Kentucky State Police results. Always query "Kerbal Space Program" instead.


### Vessel

```python
v = conn.space_center.active_vessel
```

| Attribute / Method | Returns | Description |
|---|---|---|
| `.name` | `str` | Vessel name |
| `.type` | `VesselType` | Ship, Lander, Rover, etc. |
| `.situation` | `VesselSituation` | Landed, Orbiting, SubOrbital, etc. |
| `.control` | `Control` | Throttle, SAS, RCS, action groups |
| `.auto_pilot` | `AutoPilot` | Attitude control |
| `.flight()` | `Flight` | Flight data (altitude, velocity, Q, g-force) |
| `.orbit` | `Orbit` | Orbital parameters |
| `.available_thrust` | `float` | Current max thrust (N) |
| `.max_thrust` | `float` | Max thrust (ignoring throttle) |
| `.available_torque` | `(float,float,float)` | Available torque (pitch, yaw, roll) |
| `.mass` | `float` | Total mass (kg) |
| `.dry_mass` | `float` | Dry mass (kg) |
| `.met` | `float` | Mission elapsed time (s) |
| `.resources` | `Resources` | All resources |
| `.parts` | `list[Part]` | All parts |
| `.parts.in_stage(n)` | `list[Part]` | Parts in stage `n` (launch clamps excluded) |
| `.control.rcs` | `bool` | Toggle RCS |
| `.control.sas` | `bool` | Toggle SAS |
| `.control.sas_mode` | `SASMode` | SAS mode |
| `.control.throttle` | `float` | Set throttle (0.0-1.0) |
| `.control.activate_next_stage()` | `list[Part/Vessel]` | Stage (⚠️ jettisoned decouplers return as Vessel, not Part) |
| `.control.add_node(ut, prograde, normal, radial)` | `Node` | Create maneuver node |
| `.control.nodes` | `list[Node]` | All maneuver nodes |
| `.control.remove_nodes()` | — | Remove all nodes |

# ---------------------------------------------------------------------------
# Parts & Modules
# ---------------------------------------------------------------------------

### Part

```python
parts = v.parts.all  # list[Part]
p = parts[0]
```

|| Attribute | Returns | Description |
---|---|---|
| `.name` | `str` | KSP part name (dot notation, e.g. `mk1pod.v2`) |
| `.persistent_id` | `int` | Unique part instance ID |
| `.modules` | **`list[Module]`** | ⚠️ **Not a dict!** Iterate and check `.name` |
| `.tags` | `str` | Part tags |

### Module

```python
for mod in p.modules:
    if mod.name == 'ModuleScienceExperiment':
        if mod.has_event('Deploy'):
            mod.trigger_event('Deploy')
```

|| Property | Returns | Description |
---|---|---|
| `.name` | `str` | Module class name (e.g. `ModuleScienceExperiment`) |
| `.events` | `list[str]` | Available event names |
| `.has_event(name)` | `bool` | Check if event exists |
| `.trigger_event(name)` | — | Fire a part event |
| `.fields` | `list[Field]` | Module fields/values |

| Common modules: | |
|---|---|
| `ModuleScienceExperiment` | Science parts. Events: `Deploy`, `RunTest`, `Observe ...` (varies by experiment) |
| `ModuleParachute` | Parachutes. Event: `Deploy` |
| `ModuleCommand` | Command pods/probes. Events: `ToggleSameVesselInteraction`, `SetSameVesselInteraction` |
| `ModuleAnimateGeneric` | Animated parts (solar panels, antennas). Events: `Extend`/`Retract`/`Toggle` |
| `ModuleDecouple` | Decouplers. Event: `Decouple` |
| `ModuleDockingNode` | Docking ports. Event: `Undock`, `ToggleCrossfeed` |

> **Pattern:** Always iterate `p.modules` with a for-loop. Don't assume index or dict-like access.

### AutoPilot

```python
ap = v.auto_pilot
ap.target_pitch_and_heading(pitch, heading)  # method
ap.reference_frame = some_ref_frame          # set before target_direction
ap.target_direction = (x, y, z)              # PROPERTY, not a method!
ap.engage()
ap.disengage()
ap.wait()



| Property | Description |
|---|---|
| `.engage()` | Activate autopilot |
| `.disengage()` | Release control |
| `.wait()` | Block until target attitude reached |
| `.target_pitch_and_heading(pitch, heading)` | **Method** — set pitch (0°=horizon, 90°=zenith) and heading (0°=north, 90°=east) |
| `.target_direction` | **PROPERTY** (tuple) — direction vector `(x,y,z)`. **Assign, don't call.** |
| `.reference_frame` | Reference frame — **must set before assigning `target_direction`** |
| `.error` | `(pitch,yaw,roll)` error from target |
| `.sas` | bool — use SAS for attitude hold |

> **⚠️ Gotcha (kRPC 0.5.x):** `target_direction` is a **property** (tuple), *not a method*.
> Wrong: `ap.target_direction(dir, frame)` → `TypeError: 'tuple' object is not callable`
> Correct:
> ```python
> ap.reference_frame = frame
> ap.target_direction = dir_tuple
> ```

### Orbit

```python
o = v.orbit
```

| Property | Returns | Description |
|---|---|---|
| `.body` | `CelestialBody` | Orbiting body |
| `.apoapsis_altitude` | `float` | Apoapsis above surface (m) |
| `.periapsis_altitude` | `float` | Periapsis above surface (m) |
| `.semi_major_axis` | `float` | Semi-major axis (m) |
| `.eccentricity` | `float` | Eccentricity |
| `.inclination` | `float` | Inclination (degrees) |
| `.longitude_of_ascending_node` | `float` | LAN (degrees) |
| `.argument_of_periapsis` | `float` | Argument of periapsis (degrees) |
| `.mean_anomaly_at_epoch` | `float` | Mean anomaly at epoch |
| `.epoch` | `float` | Universal time at epoch |
| `.period` | `float` | Orbital period (s) |
| `.time_to_apoapsis` | `float` | Seconds to apoapsis |
| `.time_to_periapsis` | `float` | Seconds to periapsis |
| `.radius_at(ut)` | `float` | Orbital radius at UT |
| `.true_anomaly_at(ut)` | `float` | True anomaly at UT |
| `.orbit_patch_at(ut)` | `Orbit` | Orbit patch at time (for maneuver nodes) |

### CelestialBody

```python
body = conn.space_center.bodies['Kerbin']
```

| Property | Returns | Description |
|---|---|---|
| `.name` | `str` | Body name |
| `.mass` | `float` | Mass (kg) |
| `.gravitational_parameter` | `float` | GM (m³/s²) |
| `.surface_gravity` | `float` | g at sea level (m/s²) |
| `.equatorial_radius` | `float` | Radius (m) |
| `.atmosphere_depth` | `float` | Atmosphere height (m) |
| `.has_atmosphere` | `bool` | Has atmosphere |
| `.has_oxygen` | `bool` | Breathable? |
| `.rotation_period` | `float` | Sidereal day (s) |
| `.tidally_locked` | `bool` | Tidal locking? |
| `.orbital_velocity(ut)` | `(x,y,z)` | Velocity in Sun SOI |
| `.position(ut)` | `(x,y,z)` | Position at time |
| `.reference_frame` | `ReferenceFrame` | Body-centred frame |

### Flight

```python
f = v.flight()
```

| Property | Returns | Description |
|---|---|---|
| `.mean_altitude` | `float` | Altitude above mean sea level (m) |
| `.surface_altitude` | `float` | Altitude above terrain (m) |
| `.velocity` | `(x,y,z)` | Orbital velocity vector |
| `.speed` | `float` | Orbital speed (m/s) |
| `.horizontal_speed` | `float` | Horizontal speed (m/s) |
| `.vertical_speed` | `float` | Vertical speed (m/s) |
| `.heading` | `float` | Heading (degrees) |
| `.pitch` | `float` | Pitch (degrees) |
| `.roll` | `float` | Roll (degrees) |
| `.g_force` | `float` | Current G-force |
| `.dynamic_pressure` | `float` | Q (Pa) |
| `.equivalent_air_speed` | `float` | EAS (m/s) |
| `.mach` | `float` | Mach number |
| `.lift` | `float` | Total lift (N) |
| `.drag` | `float` | Total drag (N) |
| `.atmosphere_density` | `float` | Air density (kg/m³) |

### Resources

```python
r = v.resources
```

| Method | Returns | Description |
|---|---|---|
| `.amount(name)` | `float` | Current amount of resource |
| `.max(name)` | `float` | Max capacity |
| `.has_resource(name)` | `bool` | Has any? |
| `.names` | `set[str]` | All resource names aboard |
| `.with_resource(name)` | `list[Resource]` | Per-part resource data |

Common resources: `'LiquidFuel'`, `'Oxidizer'`, `'Monopropellant'`, `'ElectricCharge'`, `'SolidFuel'`, `'XenonGas'`, `'Ore'`, `'Ablator'`

### Maneuver Node

```python
node = v.control.add_node(ut, prograde_dv, normal_dv, radial_dv)
```

| Property | Returns | Description |
|---|---|---|
| `.prograde` | `float` | Prograde delta-V |
| `.normal` | `float` | Normal delta-V |
| `.radial` | `float` | Radial delta-V |
| `.ut` | `float` | Universal time of burn |
| `.delta_v` | `float` | Total delta-V |
| `.remaining_delta_v` | `float` | Remaining delta-V |
| `.burn_vector(reference_frame)` | `(x,y,z)` | Burn direction |
| `.remove()` | — | Delete node |

### Reference Frames

| Property | Description |
|---|---|
| `conn.space_center.ReferenceFrame` | Class for reference frames |
| `.relative_to(ref_frame)` | Frame relative to another |
| `.create_relative(position, rotation, ref_frame)` | Create custom frame |

Common frames:
- `v.surface_reference_frame`
- `v.orbital_reference_frame`
- `body.reference_frame`
- `conn.space_center.bodies['Sun'].reference_frame`

## Common Patterns

Full code examples in [`krpc-patterns.md`](krpc-patterns.md) — loaded on demand:
- Connectivity check (prefer `ksp-status.py --all`, fallback `krpc_utils.get_active_vessel()`)
- Burn at a maneuver node
- Coordinate transforms
- Streaming (real-time updates)
