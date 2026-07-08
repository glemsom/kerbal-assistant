# Kerbal 1-5

Purpose: Reach 80 km Kerbin orbit and return. Suborbital science + orbital test flight.

## Design Overview

2-stage liquid-fuel rocket. All stock parts. Launched from Kerbin VAB.

### Performance

| Metric | Value |
|---|---|
| Total vacuum dV | ~3 900 m/s |
| Estimated dV after losses | ~2 800 m/s (adequate for 80 km orbit + de-orbit) |
| Launch TWR | 1.35 |
| Payload to 80 km LKO | 1.79 t (Mk1 pod + science + chute) |
| Total wet mass | 13.27 t |

### Parts & Staging

#### Stage 2 (lower — fires first, ~1 600 m/s)

| Part | Qty | Mass ea (wet) | Mass ea (dry) |
|---|---|---|---|
| FL-T800 Fuel Tank | 1 | 4.50 t | 0.50 t |
| LV-T30 Reliant Engine | 1 | 0.25 t | 0.25 t |
| Basic Fin | 3 | 0.01 t | 0.01 t |
| TR-18A Stack Decoupler | 1 | 0.05 t | 0.05 t |

*Stage 2 wet total:* 4.83 t
*Stage 2 dry total:* 0.83 t
*Thrust:* 215 kN (ASL) / 240 kN (vac)
*Isp:* 265 (ASL) / 310 (vac)
*Burn duration:* ~1.5 min

#### Stage 1 (upper — circularization + de-orbit, ~2 300 m/s)

| Part | Qty | Mass ea (wet) | Mass ea (dry) |
|---|---|---|---|
| FL-T400 Fuel Tank | 1 | 2.25 t | 0.25 t |
| LV-909 Terrier Engine | 1 | 0.50 t | 0.50 t |
| TR-18A Stack Decoupler | 1 | 0.05 t | 0.05 t |

*Stage 1 wet total:* 2.80 t
*Stage 1 dry total:* 0.80 t
*Thrust:* 60 kN (vac)
*Isp:* 345 (vac)
*Burn duration:* ~3 min

#### Payload (stage 0)

| Part | Qty | Mass |
|---|---|---|
| Mk1 Command Pod | 1 | 0.84 t |
| Mk16 Parachute | 1 | 0.10 t |
| Science Jr (Materials Bay) | 1 | 0.80 t |
| SAS Module (Advanced Inline Stabilizer) | 1 | 0.05 t |

*Payload total:* 1.79 t

### Stacking Order (top → bottom)

1. Mk16 Parachute (on pod top node)
2. Mk1 Command Pod (root)
3. Science Jr (on pod bottom)
4. TR-18A Decoupler
5. Advanced Inline Stabilizer (SAS)
6. FL-T400 Fuel Tank (upper)
7. TR-18A Decoupler (between stages)
8. FL-T800 Fuel Tank (lower)
9. LV-T30 Reliant Engine
10. 3× Basic Fin (radial on bottom tank, 120° spacing)

### Staging Order (in VAB)

| Stage | Action |
|---|---|
| 2 | LV-T30 Reliant ignition, launch clamps release |
| 1 | Stage 2 decouple (separator fires), LV-909 Terrier ignition |
| 0 | Mk16 Parachute deploy |

### Launch Clamps

2× TT-70 Launch Clamps (radial symmetry, base of lower tank).

## Ascent Profile

Use `scripts/auto-ascent.py` with:

```bash
.venv/bin/python scripts/auto-ascent.py \
  --target-apo 80000 \
  --target-peri 70000 \
  --turn-start 250 \
  --turn-end 40000 \
  --final-pitch 5 \
  --max-q 15000 \
  --heading 90
```

Or manual ascent:
1. **Liftoff** — Full throttle, SAS on, hold vertical.
2. **Pitch over** — Start gradual prograde turn at 250 m, reach ~5° pitch by 40 km.
3. **Stage to upper** — At ~50-60 km, LV-T30 burnout, stage separation, LV-909 Terrier ignites.
4. **Circularization** — Coast to 80 km apoapsis, burn prograde until orbit circular (peri ≥ 70 km).
5. **De-orbit** — Coast to apoapsis, burn retrograde until peri ~35 km.
6. **Re-entry** — Pod separates from upper stage, parachute deploys below 5 km.
7. **Land** — Splashdown or ground landing.

### Automated mission script

Use `scripts/kerbal-1-5-mission.py` after ascent to handle circularization, de-orbit, and landing:

```bash
.venv/bin/python scripts/auto-ascent.py \
  --target-apo 80000 \
  --target-peri 70000

.venv/bin/python scripts/kerbal-1-5-mission.py
```

## dV Budget Breakdown

| Phase | dV needed |
|---|---|
| Launch & gravity turn to 80 km apoapsis | ~2 600 m/s |
| Circularization burn (raise peri from ~40 km to 70 km) | ~40-60 m/s |
| De-orbit burn (retrograde at apoapsis) | ~50 m/s |
| **Total required** | **~2 700 m/s** |
| Available (vacuum, no losses) | 3 900 m/s |
| Margin | ~1 200 m/s (covers losses + piloting) |

## Design Notes

- All stock parts — no mods required.
- LV-T30 Reliant (no gimbal) → rocket relies on fins + SAS for stability during ascent.
- Terrier upper stage provides high Isp for circularization and de-orbit burns.
- 3× Basic Fins keep rocket aerodynamically stable.
- Science Jr enables early career science.
- No heat shield needed — Mk1 pod handles LKO re-entry safely.
- RCS optional — SAS + reaction wheel sufficient for attitude control.
