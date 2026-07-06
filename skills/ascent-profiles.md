# Ascent Profiles Reference

Reference for launch profiles on different celestial bodies. Use with `scripts/auto-ascent.py`.

## Parameter Summary

| Parameter | Default | What it controls |
|---|---|---|
| `--turn-start` | 250 m | Altitude to begin pitch-over |
| `--turn-end` | 40 000 m | Altitude where final pitch is reached |
| `--final-pitch` | 5° | Final pitch relative to horizon (positive = above) |
| `--max-q` | 15 000 Pa | Max dynamic pressure before throttle-back |
| `--target-apo` | 100 000 m | Target apoapsis altitude |
| `--target-peri` | 80 000 m | Target periapsis altitude |
| `--heading` | 90° | Launch heading (0=North, 90=East) |

## Profile Guidelines by Body

### Kerbin (atmosphere, g=9.81 m/s²)

Standard gravity turn. Start turn early, end high, keep Q under 15 kPa.

| Turn Start | Turn End | Final Pitch | Notes |
|---|---|---|---|
| 250 m | 40 000 m | 5° | Default — good for most rockets (TWR 1.3-1.6) |
| 100 m | 30 000 m | 10° | Aggressive turn — high TWR rockets (>1.6) |
| 500 m | 50 000 m | 0° | Gentle turn — low TWR (<1.3) or heavy payloads |

**Staging tips:**
- Stage when boosters deplete (watch `available_thrust` in telemetry)
- For asparagus staging, let the fuel crossfeed drain outer tanks first
- Drop fairings above 50 km to shed mass

**Throttle management:**
- Max Q (maximum dynamic pressure) occurs ~10-15 km on Kerbin
- Keep Q < 15 000 Pa to avoid structural failure
- The script auto-throttles based on `--max-q`

### Eve (dense atmosphere, g=16.7 m/s²)

Most difficult ascent in the game — 11 000+ m/s to orbit.

| Turn Start | Turn End | Final Pitch | Notes |
|---|---|---|---|
| 20 000 m | 60 000 m | 10° | Eve's thick atmosphere delays turn start |
| 25 000 m | 70 000 m | 5° | Conservative — avoid aerobraking to death |

**Key facts:**
- Eve atmosphere depth: ~90 km vs Kerbin's ~70 km
- Surface pressure: 5 atm — insane drag
- TWR must be >1.7 at sea level to lift off
- Use clipped/fuel-rich designs — mass fraction is brutal
- Max Q altitude is ~30-40 km on Eve

### Duna (thin atmosphere, g=2.94 m/s²)

Thin atmosphere means less drag but also less lift for turn.

| Turn Start | Turn End | Final Pitch | Notes |
|---|---|---|---|
| 500 m | 10 000 m | 15° | Turn faster — thin air means little benefit from late turn |
| 1 000 m | 8 000 m | 20° | Even more aggressive — Duna air is very thin |

**Key facts:**
- Atmosphere depth: ~50 km
- Parachutes alone may not slow enough — use drogue chutes
- Duna orbit ~800-900 m/s from surface
- Aerodynamic surfaces barely work

### Laythe (atmosphere, g=7.85 m/s²)

Similar to Kerbin but slightly lower gravity. Smaller SOI means lower orbital velocity.

| Turn Start | Turn End | Final Pitch | Notes |
|---|---|---|---|
| 500 m | 35 000 m | 5° | Similar to Kerbin but start turn a bit later |
| 250 m | 30 000 m | 10° | For higher TWR rockets |

**Key facts:**
- Atmosphere depth: ~60 km
- Laythe orbital velocity ~1850 m/s (less than Kerbin's ~2300)
- Jet engines work in Laythe's oxygenated atmosphere
- Often used as refueling stop for Jool system

### Mun (airless, g=1.63 m/s²)

No atmosphere — immediate gravity turn. You can pitch over right after clearing terrain.

| Profile | Notes |
|---|---|
| Direct ascent | Start turn at 500 m, final pitch 20°, reach orbit at ~580 m/s |
| Efficient | Start turn at 1 000 m, final pitch 30° — minimizes gravity losses |

**Key facts:**
- Orbital velocity: ~580 m/s
- No drag — full throttle all the way
- Watch terrain: Mun has tall mountains, clear at least 500 m before pitching
- Suicide burn not needed for ascent (low gravity helps)

### Minmus (airless, g=0.491 m/s²)

Tiny gravity. Almost any rocket can reach orbit easily.

| Profile | Notes |
|---|---|
| Any | Start turn at 500 m, final pitch 30°, orbit at ~170 m/s |
| Minimum dV | Start turn at 1 000 m, final pitch 45° — gravity losses tiny |

**Key facts:**
- Orbital velocity: ~170 m/s
- Minmus is inclined (6°) — launching at right time saves plane change dV
- Flat terrain near equator is easiest
- Landing struts bounce on Minmus' low gravity

## General Ascent Principles

### Gravity Turn Mechanics

1. **Vertical rise** (0 to turn-start): Build vertical speed to clear terrain/atmosphere
2. **Pitch-over** (turn-start to turn-end): Gradually tilt toward horizontal — gravity naturally bends trajectory into orbit
3. **Horizontal coast** (after turn-end): Aim near horizontal, let apoapsis rise to target
4. **Circularization** (at apoapsis): Burn prograde to raise periapsis

### Dynamic Pressure (Q)

```
Q = 0.5 * ρ * v²
```
Where ρ = atmospheric density, v = velocity.

- **Kerbin**: Max Q around 10-15 km altitude, target < 15 kPa
- **Eve**: Max Q around 30-40 km, target < 20 kPa (atmosphere is brutal)
- **Duna**: Max Q very low (< 2 kPa), no throttle limit needed
- **Airless bodies**: No Q concerns, run full throttle

### TWR Guidelines

| Body | Launch TWR | Notes |
|---|---|---|
| Kerbin | 1.3 - 1.6 | Below 1.3 = gravity losses high, above 1.6 = aerodynamic stress |
| Eve | 1.7 - 2.5 | Need high TWR to fight thick atmo and high gravity |
| Duna | 1.2 - 1.5 | Lower TWR fine due to thin air and low gravity |
| Laythe | 1.3 - 1.6 | Similar to Kerbin |
| Mun | 2.0 - 5.0 | No drag, TWR mainly about gravity losses |
| Minmus | 1.5 - 10.0 | Almost anything works |

### When to Stage

| Indicator | Action |
|---|---|
| `available_thrust` drops to 0 | Stage immediately |
| TWR < 1 on ascent | Stage — you're losing velocity |
| Solid boosters depleted | Stage — they're dead weight |
| At staging altitude (e.g., 50 km on Kerbin) | Drop fairings / unnecessary mass |

### Pi Integration

The script outputs JSON events to stdout. Pi can read these to give the player updates:

```json
{"event": "liftoff", "stage": 1}
{"event": "stage", "stage": 2, "altitude": 12345.6}
{"event": "coast_start", "apoapsis": 100123.4, "altitude": 65000.0, "speed": 2100.0}
{"event": "orbit_achieved", "body": "Kerbin", "apoapsis": 100050.0, "periapsis": 80100.0, ...}
{"event": "error", "message": "..."}
```

Example Pi instruction: "Launch to 120 km orbit" → calls `auto-ascent.py --target-apo 120000`.
