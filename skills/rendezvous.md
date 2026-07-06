# Rendezvous & Docking Reference

## Orbital Rendezvous Techniques

### Hohmann Transfer Rendezvous

Standard two-burn approach for coplanar circular orbits.

| Step | Action | kRPC Pattern |
|------|--------|-------------|
| 1 | Compute phase angle | `compute_phase_angle(vessel_pos, target_pos)` |
| 2 | Phasing burn — prograde to lower orbit (you catch up) or retrograde to raise (target catches up) | `vessel.control.add_node(ut, prograde=dv)` |
| 3 | Coast to intercept (warp) | `sc.warp_to(target_ut)` |
| 4 | Velocity match burn — retrograde of relative velocity | `ap.target_direction(flight.retrograde, target_ref)` |

```
Phase angle formula (degrees):
  phase = 180 * (1 - sqrt((r1 / r2)^3))
  r1 = min(r_vessel, r_target)
  r2 = max(r_vessel, r_target)
```

Sign convention: positive = target ahead in orbit, negative = behind.

### Fast Transfer

More aggressive phasing burn for shorter rendezvous time. Higher dV cost.
If phase error > 180°, burn the other way (go the long way around).

### Co-elliptic Rendezvous

1. Match orbital planes (inclination, LAN)
2. Phasing burn to adjust semi-major axis
3. Match velocities when at closest approach

Use when there's significant inclination difference:
```
lan_diff = abs(vessel_orbit.longitude_of_ascending_node - target_orbit.longitude_of_ascending_node)
inc_diff = abs(vessel_orbit.inclination - target_orbit.inclination)
```
Plane change most efficient at apoapsis (lower orbital speed).

## Phase Angle Calculation

```python
def compute_phase_angle(v_pos, t_pos):
    dot = v_pos[0]*t_pos[0] + v_pos[1]*t_pos[1] + v_pos[2]*t_pos[2]
    n1 = sqrt(v_pos[0]**2 + v_pos[1]**2 + v_pos[2]**2)
    n2 = sqrt(t_pos[0]**2 + t_pos[1]**2 + t_pos[2]**2)
    cos_a = max(-1, min(1, dot / (n1 * n2)))
    angle = degrees(acos(cos_a))
    # sign via cross product
    if v_pos[0] * t_pos[1] - v_pos[1] * t_pos[0] < 0:
        angle = -angle
    return angle
```

Use `orbit.position_at(ut, body.reference_frame)` for both vessels in the same SOI.

### Ahead / Behind Logic

| Condition | Meaning | Burn Direction |
|-----------|---------|---------------|
| Phase > 0 | Target ahead | Retrograde (raise orbit, increase period) |
| Phase < 0 | Target behind | Prograde (lower orbit, decrease period) |

Higher orbit = longer period. Raising your orbit makes the target catch up from behind.
Lowering your orbit makes you catch up to the target ahead.

### dV Estimate for Phasing

```
dV ≈ (phase_error_rad / (3π)) * v_orbital
```

Minimum correction: 2 m/s (avoid tiny useless burns).

## Docking Approach Speeds

| Distance | Max Speed | Phase | Notes |
|----------|-----------|-------|-------|
| >100 m | 10 m/s | Fast approach | Coarse translation, align to port axis |
| 30–100 m | 3 m/s | Slow approach | Start fine alignment, check lateral offset |
| 5–30 m | 0.5 m/s | Fine approach | Precise RCS translation, maintain on-axis |
| <5 m | <0.2 m/s | Capture | Coast, let magnets engage |

### Safety Margins

- Keep lateral velocity < 0.3 m/s during fine approach.
- Maximum closing speed at contact: 0.3 m/s (magnets can pull from ~2 m).
- If drift exceeds 1 m/s laterally, abort and reset.
- Keep RCS fuel reserve: minimum 5% for abort.

## RCS Translation vs Rotation

kRPC `vessel.control.translate(x, y, z)`

- `x`: left-right (lateral)
- `y`: up-down (vertical)
- `z`: forward-back (approach axis)

| Action | kRPC |
|--------|------|
| Translate forward (toward port) | `vessel.control.translate = (0.0, 0.0, -0.5)` |
| Translate backward (retreat) | `vessel.control.translate = (0.0, 0.0, 1.0)` |
| Translate up | `vessel.control.translate = (0.0, 0.5, 0.0)` |
| Translate right | `vessel.control.translate = (0.5, 0.0, 0.0)` |
| Rotate to target | `vessel.auto_pilot.target_direction(dir, ref)` |

Values are -1 to 1 (proportional RCS thrust).

### Alignment

After orienting vessel toward target port:
- Use `flight(port_frame).velocity` to get relative speed in port coordinates.
- Point vessel's approach axis (typically -Z) at port using AutoPilot.
- Maintain alignment by checking angular error (`ap.error`).

## Abort Procedure

1. Set throttle to 0, RCS translate to (0,0,1) (reverse)
2. Wait 2–5 seconds to reach safe distance (>50 m)
3. Disable RCS, disengage AutoPilot
4. Set SAS to stability assist

In code:
```python
vessel.control.translate = (0.0, 0.0, 1.0)
time.sleep(3.0)
vessel.control.translate = (0.0, 0.0, 0.0)
vessel.control.rcs = False
vessel.auto_pilot.disengage()
vessel.control.sas = True
```

## kRPC API Summary

| Property | Type | Description |
|----------|------|-------------|
| `vessel.control.translate` | `(float,float,float)` | RCS translation -1..1 |
| `vessel.control.rcs` | `bool` | Enable RCS |
| `vessel.auto_pilot.target_direction(v, ref)` | — | Point vessel at vector |
| `vessel.flight(ref).velocity` | `(float,float,float)` | Velocity in given frame |
| `vessel.flight(ref).speed` | `float` | Speed in given frame |
| `vessel.flight(ref).retrograde` | `(float,float,float)` | Retrograde direction |
| `vessel.orbit.position_at(ut, ref)` | `(float,float,float)` | Orbital position |
| `vessel.orbit.velocity_at(ut, ref)` | `(float,float,float)` | Orbital velocity |
| `part.docking_port` | `DockingPort or None` | Docking port component |
| `port.docked_part` | `Part or None` | What's docked (if docked) |

## Scripts

- `scripts/rendezvous.py` — phasing burn, intercept, velocity match
- `scripts/docking.py` — fine approach with RCS, magnetic dock, abort

### Orchestration: "Go rendezvous with Station Alpha and dock"

```bash
python scripts/rendezvous.py --target "Station Alpha"
# ... drift to within ~200 m of target ...
python scripts/docking.py --target "Station Alpha"
```
