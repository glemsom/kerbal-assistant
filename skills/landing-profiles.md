---
keywords: ["landing", "suicide burn", "deorbit", "reentry", "aerobrake", "parachute", "touchdown", "descent", "powered landing", "entry corridor", "Duna landing", "Mun landing", "Minmus landing", "Kerbin reentry"]
---

# Landing Profiles Reference

Reference for descent and landing profiles across the Kerbol system. Used with `scripts/landing.py`.

## Profile Selection

| Condition | Profile | Description |
|-----------|---------|-------------|
| No atmosphere (Mun, Minmus, etc.) | **Airless** | Suicide burn — retrograde full-throttle from calculated altitude |
| Atmosphere present (Kerbin, Laythe, Eve) | **Atmospheric** | Deorbit → aerobrake → parachute → touchdown |
| Thin atmosphere (Duna) | **Hybrid** | Aerobrake → parachute → terminal powered landing |

Detection is automatic via `CelestialBody.has_atmosphere`. Duna is special-cased to `hybrid`.

---

## Suicide Burn Math (Airless Bodies)

### Principle
A suicide burn waits until the last possible moment, then fires engines full throttle retrograde to reach zero velocity exactly at surface contact.

### Distance to stop

```
d = v² / (2 * (TWR - 1) * g)
```

Where:
- `v` = current vertical speed (m/s)
- `g` = local surface gravity (m/s²)
- `TWR` = thrust-to-weight ratio at current mass

### Derivation

1. Net deceleration from retrograde burn: `a = F/m - g = (TWR - 1) * g`
2. From kinematics: `v²_final = v² - 2 * a * d`
3. Setting `v_final = 0`: `d = v² / (2 * a)`
4. Substitute `a`: `d = v² / (2 * (TWR - 1) * g)`

### Safety margin

Real engines have spool-up time, mass changes as fuel burns, and terrain varies. Apply 5-15% margin:

```
burn_start_alt = d * (1 + safety_margin)
```

Start the burn when `surface_altitude <= burn_start_alt`.

### Practical considerations

- **TWR changes** during burn (mass decreases). The formula uses instantaneous TWR at start. Higher initial TWR = shorter burn = more efficient.
- **Horizontal velocity** is cancelled by retrograde tracking. The formula assumes vertical-only for simplicity; off-vertical burns are slightly less efficient.
- **Terrain**: Check terrain altitude below. On Mun (max terrain ~7000 m) or Minmus (max ~5000 m), adjust safety margin.

| Body | g (m/s²) | Orbit v | Typical TWR for landing | Burn start alt (from 100 m/s) |
|------|----------|---------|------------------------|-------------------------------|
| Mun | 1.63 | ~580 m/s | 2.0-5.0 | ~310 m (TWR=3) to ~1020 m (TWR=2) |
| Minmus | 0.49 | ~170 m/s | 2.0-10.0 | ~180 m (TWR=3) to ~520 m (TWR=2) |
| Tylo | 7.85 | ~950 m/s | 1.5-2.5 | ~1300 m (TWR=2) to ~2600 m (TWR=1.5) |
| Moho | 2.70 | ~780 m/s | 2.0-4.0 | ~420 m (TWR=3) to ~1300 m (TWR=2) |
| Vall | 1.86 | ~545 m/s | 2.0-4.0 | ~340 m (TWR=3) to ~1100 m (TWR=2) |
| Eeloo | 1.69 | ~570 m/s | 2.0-4.0 | ~380 m (TWR=3) to ~1200 m (TWR=2) |

### Insufficient TWR

If `TWR <= 1.0` (thrust cannot overcome gravity), the vessel cannot land via powered descent. The burn must start immediately (or not at all). This is common on:

- **Tylo** — many landers underpowered. Ensure vac TWR > 1.5 for safe landing.
- **Eve ascent** — not relevant for landing (atmosphere does the work).

---

## Deorbit Burn Planning

### Where to burn

Burn **retrograde at apoapsis** for most efficient periapsis lowering. The dV required:

```
v_apo = √(μ * (2/r_apo - 1/a_cur))
v_new = √(μ * (2/r_apo - 1/a_new))
dv = v_apo - v_new
```

Where:
- `a_cur = (r_apo + r_pe) / 2` (current SMA)
- `a_new = (r_apo + r_target_pe) / 2` (post-burn SMA)

### Target periapsis altitudes

| Body | Entry Pe | Rationale |
|------|----------|-----------|
| Kerbin | 35 km | Top of atmosphere at 70 km, gives shallow entry |
| Duna | 12 km | Thin atmosphere starts at ~50 km, need deeper entry for capture |
| Laythe | 30 km | Atmosphere to ~60 km |
| Eve | 60 km | Very thick atmo to ~90 km, high entry altitude |
| Mun | 1 km (or surface) | No atmosphere, just clear terrain |
| Minmus | 1 km | No atmosphere, very flat |

### Burn duration

```
t = (Isp * g0 * m0 / F) * (1 - e^(-dv / (Isp * g0)))
```

For most deorbit burns, dv is small (30-200 m/s) so burn time is short. Use low throttle (30%) for precision.

---

## Reentry Corridors (Atmospheric Bodies)

### Entry angle

Entry angle (flight path angle at entry interface) determines heating and survivability:

| Body | Safe entry angle | Shallow | Steep |
|------|-----------------|---------|-------|
| Kerbin | -1° to -3° | Bounce off atmosphere | Burn up / high G |
| Duna | -3° to -8° | May skip | Fine, thin air |
| Laythe | -1° to -3° | Bounce | Overheat |
| Eve | -5° to -10° | May not capture | Extreme heating |

### Entry interface altitude

Convention: entry starts at the visible atmosphere boundary (`atmosphere_depth` + surface).

| Body | Atmo depth | Entry interface | Notes |
|------|-----------|----------------|-------|
| Kerbin | 70 km | 70 km | Smoke effects visible |
| Duna | 50 km | 50 km | Very faint effects |
| Laythe | 60 km | 60 km | Bright effects |
| Eve | 90 km | 90 km | Purple glow |

### Heating management

- Keep **heat shield pointing retrograde** during aerobrake (SAS retrograde mode)
- **Shallow entry** (smaller angle) spreads heating over longer time → cooler but may skip
- **Steep entry** (larger angle) concentrates heating → hotter but guaranteed capture
- Max G during Kerbin reentry: typical ~3-5 G for shallow, ~6-8 G for steep

### Aerobraking pass

For capture (not direct reentry):
- Set Pe to atmosphere edge, let drag lower apoapsis over multiple passes
- Each pass reduces apoapsis by 10-30% depending on Pe depth
- Use `sc.warp_to(ut)` between passes

---

## Parachute Deployment

### Deployment conditions

Parachutes require:
1. Altitude below deployment ceiling
2. Speed below deployment threshold
3. Atmosphere density sufficient (not too thin)

### Deployment altitudes

| Body | Drogue chute | Main chute | Notes |
|------|-------------|-----------|-------|
| Kerbin | 5000 m | 500 m | Main chute at 500 m for ~10 m/s touchdown |
| Duna | 5000 m | 2500 m | Main chute higher — thin air needs earlier deploy |
| Laythe | 5000 m | 1000 m | Similar to Kerbin but atmosphere thinner higher up |
| Eve | 25000 m | 500 m | Drogue deploy high due to thick atmo, main chutes alone not enough |

### Speed thresholds

| Chute type | Deploy speed | Safe speed |
|-----------|-------------|-----------|
| Drogue | < 300 m/s | < 250 m/s |
| Main (small) | < 100 m/s | < 50 m/s |
| Main (large) | < 100 m/s | < 50 m/s |
| Radial drogue | < 300 m/s | < 250 m/s |

### Parachute-only landing speeds

| Body | Typical speed under main chutes | Does it reach < 5 m/s? |
|------|--------------------------------|------------------------|
| Kerbin | ~6-8 m/s | Almost — need slight engine tap |
| Duna | ~15-20 m/s | No — need rockets |
| Laythe | ~8-10 m/s | No — need rockets |
| Eve | ~1-2 m/s | Yes — thick atmo, but landing on Eve is the easy part |

---

## Landing Site Selection

### Criteria

| Factor | Priority | Notes |
|--------|----------|-------|
| Flat terrain | High | Slope < 5° to avoid tipping. Minmus flats are ideal |
| Altitude | High | Sea level preferred. Mountains on Mun/Eve dangerous |
| Biome science | Medium | Each biome gives unique science once |
| KSC runway | High | Kerbin target: -0.05°, -74.56° |
| Day side | Low | Solar power during landing. Check solar panel angle |
| Vessel orientation | Medium | Landing legs down, heavy side down |

### Recommended sites

| Body | Site | Lat/Lon | Notes |
|------|------|---------|-------|
| Kerbin | KSC Runway | -0.05°, -74.56° | Good for reusable craft |
| Kerbin | Shoreline | Varies | Flat water landing |
| Mun | Midlands | 0°, 0° to 30° | Many flat spots |
| Mun | Farside Crater | Varies | Unique biome science |
| Minmus | Great Flats | -5°, 0° (approx) | Perfectly flat, sea level |
| Minmus | Lesser Flats | -25°, 50° | Also flat |
| Duna | Highlands | 0°, 0° | Lowest terrain |
| Eve | Sea level | 0°, 0° | Deadly but flat |

### Targeting with kRPC

```python
# Navigate to target coordinates during descent
# Use surface reference frame for direction calculations
target_pos = sc.space_center.target_vessel...  # target a vessel at site
# Or compute bearing and adjust trajectory during parachute descent
```

In practice, precision targeting during atmospheric descent requires aerodynamic surfaces or powered cross-range. `scripts/landing.py` uses equatorial launch sites by default.

---

## Duna Hybrid Descent Strategy

Duna's unique thin atmosphere (0.2 atm at sea level) means:

1. **Aerobrake** from orbital speed (~900 m/s) slows vessel to ~200-300 m/s
2. **Parachute deploy** at 5000 m (drogue), then main at 2500 m slows to ~15-20 m/s
3. **Terminal powered landing** below ~500 m: suicide burn to < 5 m/s

The powered landing phase on Duna uses the same suicide burn math as airless bodies, but starting from ~15-20 m/s and 500 m altitude. Typical TWR of 1.5-2.5 is sufficient.

### Duna entry checklist

1. Set Pe to 12 km in deorbit burn
2. Retrograde orientation during aerobrake
3. Deploy drogue chutes at 5000 m (speed < 300 m/s)
4. Deploy main chutes at 2500 m (speed < 100 m/s)
5. Stage away used parachutes before powered landing
6. Ignite engine at calculated suicide burn altitude
7. Modulate throttle for soft touchdown

---

## Eve — The Exception

Eve's crushing atmosphere (90 km depth, 5 atm surface pressure) means:

- **Parachutes alone can land** at ~1-2 m/s
- **No powered landing needed** (unlike Duna)
- **But ascent is the problem** — 8000+ m/s to orbit
- Script uses `atmospheric` profile but warns that parachutes may not be enough for large vessels

For Eve landers: include sufficient parachute area. Small craft land fine with 2-3 large chutes. Heavy craft may need engine assist.

---

## Abort Handling

Scripts `landing.py` and `deorbit-calc.py` support clean abort:

- **Ctrl+C** or **SIGTERM**: disengages autopilot, throttle zero, SAS on
- **Abort action group**: checked each phase, same cleanup
- Cleanup leaves vessel in safe state (drifting, stable)

---

## Pi Integration

The script outputs JSON events to stdout. Pi can read and relay updates:

```json
{"event": "landing_start", "vessel": "Duna Explorer", "body": "Duna", "has_atmo": true}
{"event": "profile_selected", "profile": "hybrid", "gravity": 2.94, "atmo_depth": 50000}
{"event": "deorbit_burn", "dv": 85.3}
{"event": "aerobrake_start", "altitude": 48000.0}
{"event": "drogue_deploy", "altitude": 5000.0, "speed": 280.0}
{"event": "main_chute_deploy", "altitude": 2500.0, "speed": 85.0}
{"event": "suicide_burn_calc", "burn_start_alt": 320.0, "twr": 2.1}
{"event": "touchdown", "body": "Duna", "profile": "hybrid", "latitude": -2.3, "longitude": 12.7, "impact_speed": 2.3, "max_g": 4.5}
{"event": "abort", "message": "Autopilot disengaged, throttle zero, SAS on"}
```

Example Pi instruction: "Land at KSC" → `python scripts/landing.py`

---

## References

- `scripts/landing.py` — full autonomous landing
- `scripts/deorbit-calc.py` — standalone deorbit calculator
- `scripts/live-telemetry.py` — telemetry for landing monitoring
- KSP wiki: [Atmosphere](https://wiki.kerbalspaceprogram.com/wiki/Atmosphere)
- kRPC docs: CelestialBody API for atmosphere detection
