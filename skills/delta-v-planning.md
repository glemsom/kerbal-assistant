---
keywords: ["delta-v", "delta v", "dV", "mission planning", "transfer window", "hohmann", "rocket equation", "tsiolkovsky", "mass ratio", "twr", "thrust to weight", "ejection angle"]
---

# Delta-V Planning

Reference for calculating and budgeting delta-V for transfers, landings, and returns in the Kerbol system.

## Rocket Equation (Tsiolkovsky)

```
dV = Isp * g0 * ln(m_wet / m_dry)
```

Where:
- `Isp` = specific impulse (vacuum) in seconds
- `g0` = 9.80665 m/s² (standard gravity)
- `m_wet` = wet mass (fuel + dry mass) in kg
- `m_dry` = dry mass (empty tanks + structure + payload) in kg

### Multi-stage

Calculate per stage, sum total. Each stage's dry mass includes all upper stages and payload.

### Mass Ratio

```
mass_ratio = m_wet / m_dry
```

Higher mass ratio = more dV. Typical max for KSP tanks ≈ 9 (LF+Ox).

### Useful dV per stage (vacuum Isp = 350s)

| Mass Ratio | dV (m/s) |
|---|---|
| 2 | 2380 |
| 3 | 3770 |
| 4 | 4750 |
| 5 | 5520 |
| 8 | 7290 |

## Thrust-to-Weight Ratio (TWR)

```
TWR = F_thrust / (m * g_body)
```

- **Launch from Kerbin:** ≥ 1.3 (ideal 1.5–2.0)
- **Launch from Mun/Minmus:** ≥ 2.0 (can manage with < 1.5 but inefficient)
- **Launch from Eve:** ≥ 15+ (very high gravity + thick atmosphere)
- **Landing (airless):** ≥ 1.5 for controlled descent
- **Circularization burn:** any TWR ≥ 0.1 works (longer burn = more cosine losses)

## Kerbol System dV Map

### Interplanetary Transfers (from 80km Kerbin orbit)

| Destination | Ejection dV | Capture dV | Landing | Ascent | Round Trip |
|---|---|---|---|---|---|
| Mun | 860 | 240 | 580 | 580 | 3260 |
| Minmus | 930 | 80 | 180 | 180 | 2540 |
| Duna | 1040 | 390 | ~0* | 1580 | 4050 |
| Eve | 1070 | 1330 | ~0* | 8000 | 11400 |
| Moho | 2200 | 900 | 870 | 870 | 7460 |
| Dres | 1540 | 470 | 510 | 510 | 5080 |
| Jool (system) | 1980 | 2820 | — | — | — |
| Eeloo | 2070 | 680 | 620 | 620 | 6070 |

*Atmospheric bodies can aerobrake for capture/landing, saving significant dV.

### Jool System (from Jool capture orbit)

| Moon | Transfer | Capture | Landing | Ascent |
|---|---|---|---|---|
| Laythe | 1070 | 220 | ~0* | 2900 |
| Vall | 910 | 230 | 520 | 520 |
| Tylo | 1100 | 380 | 2300 | 2300 |
| Bop | 980 | 120 | 150 | 150 |
| Pol | 1020 | 100 | 100 | 100 |

## Transfer Windows

### Hohmann Transfer Phase Angles

Optimal phase angle for transfer from Kerbin:

| Target | Phase Angle (degrees) | Transfer Duration (Kerbin days) |
|---|---|---|
| Moho | 170° behind | 120 |
| Eve | 162° behind | 40 |
| Duna | 180° (opposition) | 65 |
| Dres | 140° | 155 |
| Jool | 96° | 285 |
| Eeloo | 100° | 360 |

Phase angle formula for circular orbits:
```
phase = 180° * (1 - sqrt((r1 / r2)^3))
```

Where r1 = inner orbit SMA, r2 = outer orbit SMA.

### Ejection Angle

Burn prograde at the correct point in low Kerbin orbit to eject on the correct heading:

- **Prograde ejection** (going to outer planets: Duna, Jool): burn on the night side of Kerbin, approximately when the target body rises over the horizon
- **Retrograde ejection** (going to inner planets: Eve, Moho): burn on the day side

Use kRPC maneuver nodes or `scripts/transfer-window.py` for precise timing.

## Mission Planning Guidelines

### Check if your vessel can reach a destination

1. Get vessel mass from `scripts/live-telemetry.py` or KSP
2. Use `scripts/dv-calc.py --isp <Isp> --wet <wet> --dry <dry>` to calculate total dV
3. Compare against dV map requirements
4. Factor in: ~20% margin for piloting error and plane changes

### Staging efficiency tips

- **Asparagus staging:** best mass ratio, most complex
- **Side boosters:** good for early game, drop when empty
- **Inline staging (stacked):** simplest, slightly less efficient
- **Upper stage:** high Isp vacuum engine (Terrier, Poodle, Nerv)
- **Lower stage:** high thrust for TWR (Reliant, Mainsail, Mammoth)

### TWR by body (vacuum, launch)

| Body | Min TWR | Ideal TWR | Notes |
|---|---|---|---|
| Kerbin | 1.3 | 1.5–2.0 | Atmosphere hurts Isp |
| Mun | 1.0 | 2.0–5.0 | No atmosphere, low gravity |
| Minmus | 0.5 | 2.0–10.0 | Very low gravity — easy |
| Duna | 0.8 | 1.2–2.0 | Thin atmosphere |
| Eve | 15+ | 20–30 | Thick atmosphere, high gravity |
| Tylo | 2.0 | 3.0–5.0 | No atmosphere, high gravity |

### Transfer window planner (quick reference)

1. Is my target an inner or outer planet?
2. What's the current phase angle between Kerbin and target? (use `scripts/transfer-window.py --target <body>`)
3. Is the current phase close to optimal?
4. How much dV do I need for ejection?
5. How long will the transfer take? (use `scripts/dv-map.py --body <body>` for standard values)
