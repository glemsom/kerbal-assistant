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
**Gravity turn** — start vertical, pitch over gradually, follow prograde.

| Body | Atmosphere | Turn start | Turn end | Final pitch | Notes |
|---|---|---|---|---|---|
| Kerbin | Yes, 70 km | 250 m | 40 km | 5° | Nominal profile |
| Eve | Yes, 90 km | 500 m | 50 km | 10° | Dense atmo → slower turn, more drag |
| Duna | Yes, 50 km | 1 000 m | 25 km | 15° | Thin atmo → earlier pitch, less drag |
| Jool | Yes, 200 km | 2 000 m | 100 km | 10° | Deep atmo → careful with heating |
| Laythe | Yes, 50 km | 500 m | 30 km | 10° | Similar to Kerbin lite |
| Lathe | Yes, 35 km | 500 m | 20 km | 15° | Cold, thin atmosphere |

### Airless bodies
No atmo = no drag. **Squared gravity turn:** start horizontal, pitch 90° from vertical instantly.

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
| Eve | 25 000 Pa | Thicker → higher Q tolerance |
| Duna | 5 000 Pa | Thin atmo, low Q |
| Laythe | 12 000 Pa | Moderate Q |
| Jool | 50 000 Pa | Very thick, high Q tolerance |

## Quick Reference

### Kerbin template
```bash
python scripts/auto-ascent.py \
  --target-apo <target> \
  --target-peri <target - 20000> \
  --turn-start 250 \
  --turn-end 40000 \
  --final-pitch 5 \
  --max-q 15000 \
  --heading 90
```

Variations:
- **75 km orbit:** `--target-apo 75000`, omit `--target-peri`
- **80 km orbit:** `--target-apo 80000 --target-peri 70000`
- **100 km orbit:** `--target-apo 100000`
- **200 km orbit:** `--target-apo 200000 --target-peri 180000`
- **GDLV3 (SRB):** add `--srb-boosters 30`

Turn profile identical across altitudes (atmo phase same); extra dV from circularization burn.
75-100 km orbits need ~3 350 m/s dV. Any rocket with >3 500 m/s post-loss dV can reach them.

### Body-specific commands
```bash
# Mun to 100 km orbit
python scripts/auto-ascent.py --target-apo 100000 --turn-start 0 --turn-end 10000 --final-pitch 0 --heading 90

# Duna to 80 km orbit
python scripts/auto-ascent.py --target-apo 80000 --turn-start 1000 --turn-end 25000 --final-pitch 15 --heading 90

# Eve to 100 km orbit
python scripts/auto-ascent.py --target-apo 100000 --turn-start 500 --turn-end 50000 --final-pitch 10 --max-q 25000 --heading 90
```

## Prerequisites

| Check | Command | Expected |
|---|---|---|
| KSP + kRPC server | `python -c "import krpc; krpc.connect()"` | No error |
| Vessel on launchpad | Check situation | `pre_launch` or `landed` |
| Staging correct | VAB staging order | Engine fires first |
| TWR > 1.0 | dv-calc or manual | ≥ 1.2 recommended |
| dV sufficient | dv-calc or dV map | ≥ 3 500 m/s for LKO |

Common failures:
- kRPC not running → start KSP, load save, check kRPC status
- Wrong active vessel → switch in KSP
- Staging reversed → verify VAB stage order

## Advanced: Computing Your Own Profile

For unlisted bodies:
1. **Turn start:** If atmosphere, ~0.5% of atmo depth. If airless, 0 m.
2. **Turn end:** ~60% atmo depth (atmo), higher for airless.
3. **Final pitch:** 5° thick atmo, 15° thin, 0° airless.
4. **Max Q:** Body g × 1000 (rough estimate).

## Multi-Stage Ascent Notes

### Staging Logic (`auto-aspect.py`)
Script auto-stages when: thrust drops to zero + 1s cooldown + stages remain. Prevents premature staging through decoupler-only stages while SRBs burn.

### Typical Profiles

| Layout | Staging | Notes |
|---|---|---|
| SRBs + sustainer | SRBs fire → decouple → sustainer fires | SRBs burn out before decouple |
| Asparagus | All engines → drop empty tanks sequentially | Stages when thrust drops |
| 2-stage (vacuum) | Lower → decouple → upper | Circularization on upper |

### Troubleshooting

- **Parachutes deploy during ascent:** Stage 0 reached prematurely. Check SRB burn time. `should_stage()` fix prevents staging when thrust > 0.
- **Won't lift off:** TWR < 1.0 or wrong staging.
- **Decouplers fire too early:** SRBs still burning. Reduce `turn_start_alt` or add SRB fuel.
