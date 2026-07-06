# kRPC API Reference for Pi

Condensed reference for writing kRPC scripts. Full docs at [krpc.github.io/krpc](https://krpc.github.io/krpc/).

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
| `.vessels` | `list[Vessel]` | All loaded vessels |
| `.vessels_in_physics_range` | `list[Vessel]` | Vessels within physics range |
| `.target_vessel` | `Vessel or None` | Set/get targeted vessel |
| `.ut` | `float` | Universal time (seconds) |
| `.warp_rate` | `float` | Current time warp rate |
| `.rails_warp_factor` | `int` | Physics warp factor (0-7) |
| `.warp_to(ut)` | — | Warp to given universal time |
| `.launch_vessel_from_sph(ship_path)` | `Vessel` | Spawn vessel from SPH |
| `.launch_vessel_from_vab(ship_path)` | `Vessel` | Spawn vessel from VAB |

### Vessel

| Property | Returns | Description |
|---|---|---|
| `.name` | `str` | Vessel name |
| `.type` | `VesselType` | Enum: Station, Probe, Lander, Rover, etc. |
| `.situation` | `VesselSituation` | PreLaunch, Landed, Splashed, Flying, Orbiting, SubOrbital, Escaping |
| `.control` | `Control` | Throttle, steering, action groups |
| `.auto_pilot` | `AutoPilot` | SAS, target heading |
| `.orbit` | `Orbit or None` | Current orbit |
| `.flight()` | `Flight` | Flight data (altitude, velocity, G-force) |
| `.surface_reference_frame` | `ReferenceFrame` | Surface-relative frame |
| `.orbital_reference_frame` | `ReferenceFrame` | Orbital frame |
| `.biome` | `str` | Current biome |
| `.crew` | `list[CrewMember]` | Crew manifest |
| `.available_thrust` | `float` | Current thrust in kN |
| `.available_torque` | `(float,float,float)` | Pitch/yaw/roll torque |
| `.mass` | `float` | Total mass (tons) |
| `.dry_mass` | `float` | Mass without fuel |
| `.fuel` | `float` | Total liquid fuel |
| `.resources` | `Resources` | All resource stocks |
| `.parts` | `list[Part]` | All parts |

### Control

Access via `vessel.control`.

| Property / Method | Description |
|---|---|
| `.throttle` | `float` 0-1 |
| `.pitch`, `.yaw`, `.roll` | `float` -1 to 1 |
| `.sas` | `bool` SAS enabled |
| `.sas_mode` | `SASMode` enum (StabilityAssist, Prograde, Retrograde, Normal, AntiNormal, RadialIn, RadialOut, Target, AntiTarget, Maneuver) |
| `.rcs` | `bool` RCS enabled |
| `.gear_legs` | `bool` Landing gear |
| `.lights` | `bool` Lights |
| `.brakes` | `bool` Brakes |
| `.abort` | `bool` Abort action group |
| `.activate_next_stage()` | `list[Part]` Stage |
| `.toggle_action_group(group)` | Toggle custom action group 1-10 |

### AutoPilot

Access via `vessel.auto_pilot`.

| Property / Method | Description |
|---|---|
| `.engage()` | Take over SAS control |
| `.disengage()` | Release control |
| `.target_pitch_and_heading(pitch, heading)` | Set attitude |
| `.target_direction(direction, reference_frame)` | Set direction as vector |
| `.target_speed` | `float` m/s for velocity matching |
| `.reference_frame` | Current reference frame |
| `.error` | `float` Angular error from target |
| `.sas` | `bool` Delegate to SAS |

### Orbit

Access via `vessel.orbit` (None if not in orbit).

| Property | Returns |
|---|---|
| `.apoapsis_altitude` | `float` m |
| `.periapsis_altitude` | `float` m |
| `.semi_major_axis` | `float` m |
| `.eccentricity` | `float` |
| `.inclination` | `float` radians |
| `.period` | `float` seconds |
| `.time_to_apoapsis` | `float` seconds |
| `.time_to_periapsis` | `float` seconds |
| `.true_anomaly_at_dn(other)` | True anomaly at descending node |
| `.true_anomaly_at_an(other)` | True anomaly at ascending node |
| `.relative_inclination(other)` | `float` radians |
| `.body` | `CelestialBody` |
| `.speed` | `float` m/s current orbital speed |
| `.radius` | `float` m from body center |

### Flight

Access via `vessel.flight()` (optionally with a reference frame).

| Property | Returns |
|---|---|
| `.mean_altitude` | `float` m |
| `.surface_altitude` | `float` m |
| `.speed` | `float` m/s |
| `.velocity` | `(float,float,float)` tuple |
| `.g_force` | `float` in Gs |
| `.dynamic_pressure` | `float` Pa |
| `.static_pressure_at_msl` | `float` Pa |
| `.atmosphere_density` | `float` kg/m³ |
| `.pitch` | `float` degrees |
| `.heading` | `float` degrees |
| `.roll` | `float` degrees |
| `.retrograde` | `(float,float,float)` direction |
| `.prograde` | `(float,float,float)` direction |

### CelestialBody

Available via `conn.space_center.bodies`.

| Property | Returns |
|---|---|
| `.name` | `str` |
| `.mass` | `float` kg |
| `.gravitational_parameter` | `float` m³/s² |
| `.equatorial_radius` | `float` m |
| `.rotational_period` | `float` seconds |
| `.has_atmosphere` | `bool` |
| `.atmosphere_depth` | `float` m |
| `.atmospheric_pressure_at(alt)` | `float` Pa |
| `.surface_gravity` | `float` m/s² |
| `.reference_frame` | `ReferenceFrame` |

### ReferenceFrame

Used by many functions. Common sources:

- `vessel.orbital_reference_frame`
- `vessel.surface_reference_frame`
- `vessel.non_rotating_reference_frame`
- `body.reference_frame`
- `conn.space_center.ReferenceFrame.create_relative(...)`

### Node (Maneuver Node)

Create via `vessel.control.add_node(ut, prograde=0, normal=0, radial=0)`.

| Property / Method | Description |
|---|---|
| `.prograde` | `float` dV m/s |
| `.normal` | `float` dV m/s |
| `.radial` | `float` dV m/s |
| `.ut` | Universal time of burn |
| `.delta_v` | `float` total dV |
| `.burn_vector(ref)` | Direction of burn |
| `.remaining_delta_v` | `float` dV remaining (after partial burn) |
| `.remove()` | Delete the node |
| `.orbital_reference_frame` | Reference frame for this burn |

### Streams (for live updates)

```python
alt_stream = conn.add_stream(getattr, vessel.flight(), 'mean_altitude')
```

Call `.value` anytime to get latest value without blocking.

## Common Patterns

### Wait for condition

```python
import time
while vessel.flight(vessel.surface_reference_frame).surface_altitude > 1000:
    time.sleep(0.1)
```

### Execute a burn

```python
node = vessel.control.add_node(ut, prograde=dv)
frame = node.orbital_reference_frame
vessel.auto_pilot.engage()
vessel.auto_pilot.target_direction(node.burn_vector(frame), frame)
while node.remaining_delta_v > 0.5:
    vessel.control.throttle = 0.5
    time.sleep(0.1)
vessel.control.throttle = 0
node.remove()
```

## Error Handling

- `ConnectionError` / `socket.timeout` — KSP not running or kRPC not enabled
- `RPCError` — malformed request, missing vessel, wrong state
- Check `vessel.situation != VesselSituation.pre_launch` before staging
- Always wrap live scripts in try/except for graceful exit

## Tips

- Scripts are stateless: reconnect and re-query on each invocation
- Use `vessel.control.sas = True` before engaging AutoPilot for smoother transitions
- For time warp: `space_center.rails_warp_factor = 4` (max physics warp), then `space_center.warp_to(ut)` for non-physics warp
- Test with a sandbox save first
