# Orbit Test 1

Purpose: Reach 200 km circular Kerbin orbit. First orbital test flight.

## Design Overview

2-stage liquid-fuel rocket. All stock parts. Launched from Kerbin VAB.

### Performance

| Metric | Value |
|---|---|
| Total vacuum dV | 5 116 m/s |
| Estimated dV after losses | ~3 600 m/s (adequate for 200 km) |
| Launch TWR | 1.26 |
| Payload to 200 km orbit | 1.79 t (Mk1 pod + science + chute) |
| Total wet mass | 16.17 t |
| Total dry mass | 4.17 t |
| Effective payload fraction | 7.2 % |

### Parts & Staging

#### Stage 2 (lower — fires first, ~2142 m/s)

| Part | Qty | Mass ea (wet) | Mass ea (dry) |
|---|---|---|---|
| FL-T800 Fuel Tank | 2 | 4.50 t | 0.50 t |
| LV-T45 Swivel Engine | 1 | 0.25 t | 0.25 t |
| Basic Fin | 3 | 0.01 t | 0.01 t |
| TR-18A Stack Decoupler | 1 | 0.05 t | 0.05 t |

*Stage 2 wet total:* 9.33 t  
*Stage 2 dry total:* 1.33 t  
*Thrust:* 200 kN (ASL) / 250 kN (vac)  
*Isp:* 270 (ASL) / 320 (vac)  
*Burn duration:* ~2 min

#### Stage 1 (upper — circularization, ~2974 m/s)

| Part | Qty | Mass ea (wet) | Mass ea (dry) |
|---|---|---|---|
| FL-T800 Fuel Tank | 1 | 4.50 t | 0.50 t |
| LV-909 Terrier Engine | 1 | 0.50 t | 0.50 t |
| TR-18A Stack Decoupler | 1 | 0.05 t | 0.05 t |

*Stage 1 wet total:* 5.05 t  
*Stage 1 dry total:* 1.05 t  
*Thrust:* 60 kN (vac)  
*Isp:* 345 (vac)  
*Burn duration:* ~3-4 min

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
6. FL-T800 Fuel Tank (upper)
7. TR-18A Decoupler (between stages)
8. FL-T800 Fuel Tank (lower)
9. FL-T800 Fuel Tank (lower)
10. LV-T45 Swivel Engine
11. 3× Basic Fin (radial on bottom tank, 120° spacing)

### Staging Order (in VAB)

| Stage | Action |
|---|---|
| 2 | LV-T45 Swivel ignition, launch clamps release |
| 1 | Stage 2 decouple (separator fires), LV-909 Terrier ignition |
| 0 | Mk16 Parachute deploy |

### Launch Clamps

2× TT-70 Launch Clamps (radial symmetry, base of lower tanks).

## Ascent Profile

Use `scripts/auto-ascent.py` with:

```bash
python scripts/auto-ascent.py \
  --target-apo 200000 \
  --target-peri 180000 \
  --turn-start 250 \
  --turn-end 40000 \
  --final-pitch 5 \
  --max-q 15000 \
  --heading 90
```

Or manual ascent:

1. **Liftoff** — Full throttle, SAS on, hold vertical.
2. **Pitch over** — Start gradual prograde turn at 250 m, reach ~5° pitch by 40 km.
3. **Stage to upper** — At ~60-70 km, stage separation, LV-909 ignites.
4. **Circularization** — Coast to 200 km apoapsis, burn prograde until orbit circular.
5. **Deploy** — Parachute on re-entry (optional for this test).

## dV Budget Breakdown

| Phase | dV needed |
|---|---|
| Launch & gravity turn to 80 km | ~3 100 m/s |
| Raise apoapsis from 80 km to 200 km | ~150 m/s |
| Circularization burn at 200 km | ~350 m/s |
| **Total required** | **~3 600 m/s** |
| Available (vacuum, no losses) | 5 116 m/s |
| Margin | ~1 500 m/s (covers losses + piloting) |

## Design Notes

- All stock parts — no mods required.
- Terrier upper stage provides high Isp for circularization.
- Swivel gimbaling gives control authority during ascent.
- 3× Basic Fins keep rocket aerodynamically stable.
- Science Jr enables EVA reports and crew reports for early career science.
- Heatshield absent; 200 km orbit permits safe re-entry with pod alone.
