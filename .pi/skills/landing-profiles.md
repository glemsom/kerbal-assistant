---
name: landing-profiles
description: Descent profiles for KSP bodies — suicide burn math for airless bodies, atmospheric entry guidance, landing site selection. Use when planning powered descents and landings.
---

# Landing Profiles — pilot reference

## Airless-body descent (Mun, Minmus, Gilly, etc.)

### Suicide burn math
For airless bodies, optimal powered descent = **suicide burn**: start engine at last moment to kill all velocity at surface.

**Key equation** (vertical descent approx):

$$t_{burn} = \frac{I_{sp} \cdot g_0}{g_{body}} \cdot \ln\left(1 + \frac{v_{vert}}{I_{sp} \cdot g_0 / (TWR - 1) \cdot g_{body}}\right)$$

Simplified: burn altitude $h_{burn} = \frac{v^2}{2 \cdot (a_{engine} - g_{body})}$

Where:
- $v$ = vertical velocity (m/s)
- $a_{engine}$ = $F / m$ = thrust acceleration (m/s²)
- $g_{body}$ = surface gravity (m/s²)

### Landing sequence
1. **De-orbit burn:** Retrograde at apoapsis to lower periapsis to ~0 m (surface grazing)
2. **Coast to periapsis:** Most of descent ballistic
3. **Suicide burn:** At calculated altitude, full throttle retrograde
4. **Final approach:** Below 50 m, throttle to < 5 m/s descent rate
5. **Touchdown:** 0.5-1.0 m/s vertical speed

### Body-specific parameters

| Body | g (m/s²) | Suicide burn start (typ.) | Landing TWR | Notes |
|---|---|---|---|---|
| **Mun** | 1.63 | 5 000-8 000 m | 2-3 | Standard target |
| **Minmus** | 0.491 | 1 000-2 000 m | 2-4 | Very low g, easy overshoot |
| **Gilly** | 0.008 | 50-100 m | 1.5-2 | Tiny! Approach < 10 m/s |
| **Moho** | 2.7 | 8 000-12 000 m | 2-4 | Hot, no atmo |
| **Dres** | 0.82 | 2 000-4 000 m | 2-3 | Cold, bumpy |
| **Eeloo** | 1.69 | 5 000-8 000 m | 2-3 | Ice world |
| **Tylo** | 7.85 | 20 000-30 000 m | 3-5 | Highest g airless — hardest |
| **Vall** | 1.68 | 5 000-8 000 m | 2-3 | Smooth ice |
| **Bop** | 0.59 | 1 000-3 000 m | 1.5-2 | Small, irregular |
| **Pol** | 0.37 | 500-1 500 m | 1.5-2 | Very small |

### Suicide burn altitude quick formula
$$h_{start} = \frac{v^2 \cdot TWR}{2 \cdot g \cdot (TWR - 1)}$$

Example: Mun (g=1.63), TWR=3, orbital speed ≈ 540 m/s
$h_{start} = \frac{540^2 \cdot 3}{2 \cdot 1.63 \cdot 2} \approx 134,000$ m

Theoretical altitude for perfect burn from full orbital speed. In practice, de-orbit burn reduces horizontal speed first → actual suicide burn starts much lower (~5-8 km).

### Precision landing with kRPC
```python
# Calculate suicide burn altitude
v = vessel.flight(vessel.orbit.body.reference_frame)
g = vessel.orbit.body.surface_gravity
twr = vessel.available_thrust / (vessel.mass * g)
vertical_speed = abs(v.vertical_speed)
burn_start_alt = (vertical_speed**2 * twr) / (2 * g * (twr - 1))

# Start burn at calculated altitude
if vessel.flight().mean_altitude <= burn_start_alt and vertical_speed > 5:
    vessel.control.throttle = 1.0
```

## Atmospheric descent

### Entry corridor

| Body | Entry altitude | Entry speed | Heat shield needed |
|---|---|---|---|
| **Kerbin** | 70 km | 2 400-3 200 m/s | Recommended for Mun/Minmus return |
| **Eve** | 90 km | 4 000-5 000 m/s | Required |
| **Duna** | 50 km | 1 200-1 800 m/s | Optional (thin atmo) |
| **Laythe** | 50 km | 3 000-4 000 m/s | Required |
| **Jool** | 200 km | 7 000+ m/s | Required (extreme) |

### Parachute deployment

| Body | Safe deployment | Parachute type |
|---|---|---|
| **Kerbin** | < 5 000 m, < 300 m/s | Drogue + main |
| **Eve** | < 25 000 m (dense) | Drogue + main |
| **Duna** | < 10 000 m (thin) | Main only (or drogue for heavy) |
| **Laythe** | < 5 000 m | Drogue + main |

### Aerobraking capture

### LKO re-entry (75-100 km)
No heat shield needed. Mk1 pod thermal tolerance sufficient. Re-entry ~2 300-2 500 m/s. Mk16 chute deploys below 5 000 m.

**Deorbit burn:** Use `scripts/deorbit-calc.py`:
```bash
python scripts/deorbit-calc.py --apo 75000 --peri 75000 --body Kerbin --target-pe 35000 --burn-at-apo
python scripts/deorbit-calc.py --vessel "Orbit Test 1" --target-pe 35000 --burn-at-apo
```
Typical deorbit dV from 75 km LKO: ~35-55 m/s retrograde at apoapsis.

For interplanetary return (e.g., Duna → Kerbin): set PE to 50-60 km, multiple passes if needed, heat shield for >3 500 m/s.

### Eve descent
Thick atmo → easy descent, hard landing. 2.5m+ heat shield required. Parachutes deploy above 25 000 m (very effective). Terminal velocity ~10 m/s at sea level. Propulsive landing usually unnecessary. Reinforced/wide landing gear for 1.7g surface.

### Duna descent
Thin atmo. Minimal heating (small heat shield or none). Parachutes below 10 000 m, need many for heavy craft. Terminal velocity ~50-100 m/s → often need propulsive assist. Combine chutes with retro-burn at ~500 m.

## Landing site selection

### Recommended biomes

| Body | Recommended | Notes |
|---|---|---|
| **Mun** | Midlands, Craters (flat) | Avoid Highlands for first landing |
| **Minmus** | Greater Flats, Lesser Flats | Extremely flat |
| **Duna** | Lowlands, Craters | Avoid mountains |
| **Eve** | Lowlands (sea level) | Easier land, harder ascend |
| **Tylo** | Lowlands | Only option, all terrain rugged |

### Terrain hazards

| Hazard | Detection | Mitigation |
|---|---|---|
| Steep slope (>15°) | Terrain scanner, visual | Approach from downhill |
| Large boulders | Surface texture (dark spots) | Land in smooth terrain |
| Crater rim | Altitude map | Land 2+ km from center |
| Canyon | Biome map | Avoid |

## Powered landing procedure (kRPC)

```python
# 1. De-orbit burn
target_periapsis = 0  # surface grazing
# burn_time from node calculation
v.control.throttle = 1.0
time.sleep(burn_time)
v.control.throttle = 0.0

# 2. Coast until suicide burn altitude
while v.flight().mean_altitude > burn_start_alt:
    time.sleep(1.0)

# 3. Suicide burn
v.control.throttle = 1.0
v.auto_pilot.target_direction(tuple(-val for val in v.flight().velocity))

# 4. Final approach
while v.flight().surface_altitude > 50:
    time.sleep(0.1)

throttle = min(1.0, v.flight().vertical_speed / 10.0)
v.control.throttle = 0.05  # hover throttle

# 5. Touchdown
while v.flight().surface_altitude > 0.5:
    v.control.throttle = 0.03
    time.sleep(0.05)
v.control.throttle = 0.0
```

## Landing gear checklist
- [ ] Landing gear deployed before final approach
- [ ] Gear oriented correctly (downward)
- [ ] Gear supports vessel mass (check max load)
- [ ] Enough clearance between nozzle and ground
- [ ] Battery charged (RCS/reaction wheels during approach)
- [ ] SAS enabled
- [ ] RCS enabled
