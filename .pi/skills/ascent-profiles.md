---
name: ascent-profiles
description: Launch profile parameters for KSP bodies — gravity turn settings, TWR targets, pitch-over altitudes for use with auto-ascent.py. Use when planning or executing launches.
---

# Ascent Profiles Reference

Reference for launch profiles on different celestial bodies. Use with `scripts/auto-ascent.py`.

## Parameter Summary

| Parameter | Default | What it controls |
|---|---|---|
| `--turn-start` | 250 m | Altitude to begin pitch-over |
| `--turn-end` | 40 000 m | Altitude where final pitch is reached |
| `--final-pitch` | 5° | Final pitch above horizon |
| `--max-q` | 15 000 Pa | Max dynamic pressure during ascent |
| `--heading` | 90° | Launch heading (0=N, 90=E) |
| `--target-apo` | 100 000 m | Target apoapsis |
| `--target-peri` | apo - 20 000 m | Target periapsis |

## Physics Summary

### Atmospheric bodies

Follow a **gravity turn** — start vertical, pitch over gradually, follow prograde.

| Body | Atmosphere | Turn start | Turn end | Final pitch | Notes |
|---|---|---|---|---|---|
| Kerbin | Yes, 70 km | 250 m | 40 km | 5° | Nominal profile |
| Eve | Yes, 90 km | 500 m | 50 km | 10° | Dense atmo → slower turn, more drag |
| Duna | Yes, 50 km | 1 000 m | 25 km | 15° | Thin atmo → earlier pitch, less drag |
| Jool | Yes, 200 km | 2 000 m | 100 km | 10° | Deep atmo → careful with heating |
| Laythe | Yes, 50 km | 500 m | 30 km | 10° | Similar to Kerbin lite |
| Lathe | Yes, 35 km | 500 m | 20 km | 15° | Cold, thin atmosphere |

### Airless bodies

No atmosphere means no drag. Best ascent strategy is a **squared gravity turn**: start horizontal immediately, pitch 90° from vertical instantly.

| Body | TWR target | Turn start | Turn end | Final pitch |
|---|---|---|---|---|
| Mun | 2-3 | 0 m | 10 000 m | 45° → 0° |
| Minmus | 2-3 | 0 m | 5 000 m | 45° → 0° |
| Gilly | 1.5-2 | 0 m | 100 m | 30° → 0° |
| Dres | 2-3 | 0 m | 8 000 m | 45° → 0° |
| Eeloo | 2-3 | 0 m | 15 000 m | 45° → 0° |
| Tylo | 3-5 | 0 m | 20 000 m | 45° → 0° |
| Vall | 2-3 | 0 m | 12 000 m | 45° → 0° |
| Bop | 1.5-2 | 0 m | 3 000 m | 30° → 0° |
| Pol | 1.5-2 | 0 m | 2 000 m | 30° → 0° |
| Moho | 2-3 | 0 m | 15 000 m | 45° → 0° |

## TWR by Body

Minimum TWR for launch:

| Body | g (m/s²) | Min TWR | Recommended |
|---|---|---|---|
| Kerbin | 9.81 | 1.2 | 1.3-1.6 |
| Eve | 16.7 | 1.2 | 1.5-2.0 |
| Duna | 2.94 | 1.1 | 1.2-1.5 |
| Mun | 1.63 | 1.1 | 2.0-3.0 |
| Minmus | 0.491 | 1.1 | 2.0-3.0 |
| Tylo | 7.85 | 1.2 | 3.0-5.0 |
| Moho | 2.7 | 1.1 | 2.0-3.0 |
| Eve (ocean) | 16.7 | 1.2 | Must account for high drag |

## Max Q by Body

| Body | Max Q safe limit | Notes |
|---|---|---|
| Kerbin | 15 000 Pa | Default limit |
| Eve | 25 000 Pa | Thicker atmosphere → higher Q tolerance |
| Duna | 5 000 Pa | Thin atmosphere, low Q |
| Laythe | 12 000 Pa | Moderate Q |
| Jool | 50 000 Pa | Very thick, high Q tolerance |

## Quick Reference

### Kerbin to 100 km orbit

```bash
python scripts/auto-ascent.py \
  --target-apo 100000 \
  --turn-start 250 \
  --turn-end 40000 \
  --final-pitch 5 \
  --max-q 15000 \
  --heading 90
```

### Kerbin to 200 km orbit (high-orbit launch)

```bash
python scripts/auto-ascent.py \
  --target-apo 200000 \
  --target-peri 180000 \
  --final-pitch 5 \
  --max-q 15000 \
  --heading 90
```

Higher apoapsis needs more horizontal speed. Same turn profile as 100 km
(atmospheric phase identical); extra dV comes from circularization burn.

### GDLV3 (SRB-assisted launch to 200 km)

```bash
python scripts/auto-ascent.py \
  --target-apo 200000 \
  --target-peri 180000 \
  --turn-start 250 \
  --turn-end 40000 \
  --final-pitch 5 \
  --max-q 15000 \
  --heading 90 \
  --srb-boosters 30
```
```

### Mun to 100 km orbit

```bash
python scripts/auto-ascent.py \
  --target-apo 100000 \
  --turn-start 0 \
  --turn-end 10000 \
  --final-pitch 0 \
  --heading 90
```

### Duna to 80 km orbit

```bash
python scripts/auto-ascent.py \
  --target-apo 80000 \
  --turn-start 1000 \
  --turn-end 25000 \
  --final-pitch 15 \
  --heading 90
```

### Eve to 100 km orbit

```bash
python scripts/auto-ascent.py \
  --target-apo 100000 \
  --turn-start 500 \
  --turn-end 50000 \
  --final-pitch 10 \
  --max-q 25000 \
  --heading 90
```

## Advanced: Computing Your Own Profile

For a body not listed, compute:

1. **Turn start:** If atmosphere exists, start at ~0.5% of atmo depth. If no atmo, start at 0 m.
2. **Turn end:** ~60% of atmo depth for atmo bodies, higher for airless.
3. **Final pitch:** 5° for thick atmo, 15° for thin, 0° for airless.
4. **Max Q:** Body g × 1000 for rough estimate.

## Multi-Stage Ascent Notes

### Staging Logic (`auto-ascent.py`)

The script handles staging automatically. The `should_stage()` function activates the next stage when:
1. Vessel thrust drops to zero (engines burned out)
2. A 1-second cooldown has passed (prevents double-staging during transitions)
3. Stages remain (not at stage 0/parachutes)

This avoids the common error of premature staging through decoupler-only stages while SRBs are still burning.

### Typical Multi-Stage Profiles

| Layout | Staging order | Notes |
|---|---|---|
| SRBs + sustainer | SRBs fire → decouple SRBs → sustainer fires | SRBs should burn out before decouple |
| Asparagus | All engines → drop empty tanks sequentially | Auto-ascent stages when thrust drops |
| 2-stage (vacuum) | Lower stage → decouple → upper stage | Circularization on upper stage |

### Troubleshooting

- **Parachutes deploy during ascent:** Staging reached stage 0 prematurely. Check that SRBs/thrusters burn long enough before staging triggers. The `should_stage()` fix prevents this by only staging when thrust is zero.
- **Vessel won't lift off:** TWR < 1.0 or wrong staging. Check engine staging in VAB.
- **Decouplers fire too early:** SRBs still burning when staging fires. Either reduce `turn_start_alt` (to get SRBs burning longer at low altitude) or ensure SRBs have enough fuel to burn until staging.
