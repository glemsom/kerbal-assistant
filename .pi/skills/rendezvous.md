---
name: rendezvous
description: Orbital rendezvous and docking techniques — Hohmann transfer rendezvous, phasing burns, matching velocities, docking approach patterns with kRPC patterns. Use when planning or executing rendezvous and docking.
---

# Rendezvous & Docking Reference

## Orbital Rendezvous Techniques

### Hohmann Transfer Rendezvous

Standard two-burn approach for coplanar circular orbits.

| Step | Action | kRPC Pattern |
|---|---|---|
| 1 | Determine target orbit altitude | `target.orbit.apoapsis_altitude` |
| 2 | Calculate transfer orbit parameters | semi-major axis = (r1 + r2) / 2 |
| 3 | Burn prograde at periapsis to raise apoapsis to target altitude | `node = v.control.add_node(ut, 0, 0, 0)` |
| 4 | Coast to target intercept point | `time_to_apoapsis` ≈ ½ period |
| 5 | Burn prograde at apoapsis to circularise | Match target orbital speed |

### Relative Inclination

Burn normal/anti-normal at the ascending/descending node to match inclinations.

**When to correct inclination:**
- Before Hohmann transfer (plane change at node is cheaper)
- At high altitude (farther from body = cheaper plane change)
- Combined with ejection burn (vector sum is often cheaper)

### Phase Angle Method

For intercepting a target in a similar orbit (same body, similar altitude):

$$t_{wait} = \frac{\phi_{current} - \phi_{desired}}{\omega_{target} - \omega_{chaser}}$$

Where $\omega$ = angular velocity = $2\pi / period$

### Phasing Orbit Method

Used when the target is ahead or behind in the same orbit.

| Situation | Action | Result |
|---|---|---|
| Target is ahead | Lower your orbit (retrograde burn) | You catch up (shorter period) |
| Target is behind | Raise your orbit (prograde burn) | They catch up (longer period) |

#### Phasing orbit math

$$T_{phase} = \frac{2\pi \cdot a_{chaser}^{3/2}}{\sqrt{\mu}} \quad \text{(period of phase orbit)}$$

For small phase angles: $$\Delta v \approx \frac{\mu \cdot \Delta \theta}{4 \cdot r \cdot v} \quad \text{(approximate dV for phase correction)}$$

### Bi-Elliptic Transfer

For large altitude changes (ratio > 12), a bi-elliptic transfer can be more efficient than Hohmann. Use when going from LKO to Mun orbit or beyond.

Three burns:
1. Raise apoapsis far beyond target
2. At apoapsis, raise periapsis to target altitude
3. At new periapsis, circularise

## Docking Approach

### Approach Phases

| Phase | Distance | Action |
|---|---|---|
| **Far** | > 500 m | RCS translation, align velocity vectors |
| **Medium** | 100 - 500 m | Reduce relative velocity, align to docking port |
| **Close** | 10 - 100 m | Fine RCS corrections, keep docking port aligned |
| **Contact** | < 10 m | Slow approach (< 0.5 m/s), maintain alignment |

### Docking Port Alignment

```python
# Find docking ports
target_ports = target_vessel.parts.with_module('ModuleDockingNode')
my_port = vessel.parts.with_module('ModuleDockingNode')[0]

# Get port positions in world space
target_port_pos = target_ports[0].position(target_ports[0].reference_frame)
my_port_pos = my_port.position(my_port.reference_frame)

# Vector from my port to target port
approach_vector = (
    target_port_pos[0] - my_port_pos[0],
    target_port_pos[1] - my_port_pos[1],
    target_port_pos[2] - my_port_pos[2]
)

# Point docking port at target
vessel.auto_pilot.target_direction(approach_vector)
```

### RCS Translation

```python
# Set up RCS control
vessel.control.rcs = True

# Translate forward (toward target)
vessel.control.forward = 1.0  # 0.0 to 1.0
time.sleep(0.5)
vessel.control.forward = 0.0

# Translate sideways
vessel.control.right = 1.0  # positive = right, negative = left

# Translate up/down
vessel.control.up = 1.0  # positive = up
```

### Relative Velocity Management

- **Approach speed:** Start at 5-10 m/s at 500 m, reduce to 1-2 m/s at 100 m, reduce to 0.3-0.5 m/s at 10 m
- **Target approach speed:** < 0.5 m/s at docking port
- **Alignment tolerance:** < 0.5° port angle mismatch
- **Lateral drift:** Keep < 0.2 m/s lateral velocity

## kRPC Patterns for Rendezvous

### Setting target vessel

```python
# Assuming you've identified the target vessel
target_vessel = [v for v in conn.space_center.vessels if v.name == 'Station Alpha'][0]
conn.space_center.target_vessel = target_vessel
```

### Getting relative position

```python
# Relative position in orbital frame
rel_pos = conn.space_center.transform_position(
    target_vessel.position(target_vessel.orbit.body.reference_frame),
    target_vessel.orbit.body.reference_frame,
    vessel.orbital_reference_frame
)
```

### Computing relative velocity

```python
# Difference of velocity vectors in same frame
v1 = vessel.velocity(vessel.orbit.body.reference_frame)
v2 = target_vessel.velocity(vessel.orbit.body.reference_frame)
rel_velocity = (v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2])
rel_speed = (rel_velocity[0]**2 + rel_velocity[1]**2 + rel_velocity[2]**2) ** 0.5
```

### Approximation: time to closest approach

```python
import math
distance = math.sqrt(rel_pos[0]**2 + rel_pos[1]**2 + rel_pos[2]**2)
closing_speed = rel_speed  # rough approximation
time_to_intercept = distance / closing_speed if closing_speed > 0 else float('inf')
```

## Rendezvous Burn Planning

### Intercept burn

Burn prograde/retrograde to set up intercept in N orbits.

```python
# Calculate burn to raise apoapsis to target orbit
target_alt = target_vessel.orbit.apoapsis_altitude
current_alt = vessel.orbit.apoapsis_altitude
delta_v = target_alt - current_alt  # extremely simplified; use vis-viva

# Create node at next periapsis
ut = vessel.orbit.time_to_periapsis + conn.space_center.ut
node = vessel.control.add_node(ut, prograde=delta_v * 0.5, normal=0, radial=0)
```

### Match velocity at intercept

When within 500 m of target:

```python
# Set target
conn.space_center.target_vessel = target_vessel

# Burn retrograde relative to target
while rel_speed > 1.0:
    # Burn opposite to relative velocity vector
    vessel.auto_pilot.target_direction(
        (-rel_velocity[0], -rel_velocity[1], -rel_velocity[2])
    )
    vessel.auto_pilot.engage()
    vessel.control.throttle = 0.3
    time.sleep(0.5)
    # Recalculate
    v1 = vessel.velocity(vessel.orbit.body.reference_frame)
    v2 = target_vessel.velocity(vessel.orbit.body.reference_frame)
    rel_velocity = (v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2])
    rel_speed = math.sqrt(rel_velocity[0]**2 + rel_velocity[1]**2 + rel_velocity[2]**2)

vessel.control.throttle = 0.0
```

## Common Mistakes

| Mistake | Why it happens | Fix |
|---|---|---|
| **Burn too early** | Misjudged phase angle | Wait for correct phase angle before burning |
| **Plane change after transfer** | Didn't check inclination | Check target inclination before leaving LKO |
| **Docking too fast** | Misjudged distance/speed | Keep approach speed proportional to distance |
| **RCS crossfeed** | Wrong RCS thruster layout | Balance RCS placement around center of mass |
| **Port misalignment** | Wrong reference frame | Target the docking port, not the vessel |
| **Solar panels destroyed** | Docking collision | Retract panels before docking approach |

## Quick Reference: dV Requirements for Rendezvous

| Scenario | Typical dV |
|---|---|
| LKO (100 km) → LKO (150 km), same inclination | 200-300 m/s |
| LKO → MKO (Mun orbit) | 860 m/s transfer + 240 m/s capture |
| Plane change, 5° at LKO | ~150 m/s |
| Plane change, 5° at high orbit (1 000 km) | ~50 m/s |
| Circularisation after transfer | ~200-400 m/s |
