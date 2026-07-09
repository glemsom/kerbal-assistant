---
name: delta-v-planning
description: Reference for calculating and budgeting delta-V using Tsiolkovsky rocket equation, dV map data, transfer windows, and TWR guidelines. Use when planning missions or interpreting dv-calc.py output.
keywords: ["delta-v", "delta v", "dV", "mission planning", "transfer window", "hohmann", "rocket equation", "tsiolkovsky", "mass ratio", "twr", "thrust to weight", "ejection angle"]
---

# Delta-V Planning

Reference for calculating and budgeting delta-V for transfers, landings, and returns in the Kerbol system.

## Rocket Equation (Tsiolkovsky)

$$\Delta v = I_{sp} \cdot g_0 \cdot \ln\left(\frac{m_{wet}}{m_{dry}}\right)$$

Where:
- $I_{sp}$ = specific impulse (s) — use vacuum Isp for in-space
- $g_0$ = 9.80665 m/s² (standard gravity constant)
- $m_{wet}$ = wet mass (kg) — full fuel
- $m_{dry}$ = dry mass (kg) — empty tanks + structure + payload

### Quick approximations

| Mass ratio (wet/dry) | dV at Isp=350 (Kerbin vac) | dV at Isp=800 (NERV) |
|---|---|---|
| 1.5 | 1 421 m/s | 3 247 m/s |
| 2.0 | 2 381 m/s | 5 441 m/s |
| 2.5 | 3 211 m/s | 7 339 m/s |
| 3.0 | 3 772 m/s | 8 622 m/s |
| 4.0 | 4 762 m/s | 10 883 m/s |

### Calculating staging

For N stages, total dV is the sum of each stage's dV. Stage 1 (bottom) fires first, then drops away.

```python
import math
g0 = 9.80665
total_dv = 0
for stage in stages:
    dv = stage.isp * g0 * math.log(stage.wet_mass / stage.dry_mass)
    total_dv += dv
```

Use `scripts/dv-calc.py` for exact calculations:

```bash
# Single stage
python scripts/dv-calc.py --isp 350 --wet 40000 --dry 5000

# Two stages with payload
python scripts/dv-calc.py --isp 320,350 --wet 10000,3000 --dry 1000,500 --stages 2 --payload 2000
```

## Delta-V Map

Kerbol system dV requirements (from LKO, 100 km). Use `scripts/dv-map.py` for full data.

| Body | Transfer dV | Capture dV | Land dV | Ascent dV | Round trip |
|---|---|---|---|---|---|
| **Mun** | 860 | 240 | 580 | 580 | 3 260 |
| **Minmus** | 930 | 160 | 450 | 450 | 3 200 |
| **Duna** | 1 040 | 250 | 1 450 (aero) | 2 000 | 6 400 |
| **Ike** | (via Duna) | 100 | 550 | 550 | 7 600 |
| **Eve** | 1 050 | 600 | 8 000 (aero!) | 11 500 | 25 000+ |
| **Moho** | 2 200 | 750 | 870 | 870 | 8 480 |
| **Dres** | 1 850 | 400 | 580 | 580 | 6 400 |
| **Jool** | 1 980 | 800 | (gas giant) | — | — |
| **Laythe** | (via Jool) | 500 | 2 900 (aero) | 4 000 | 16 000+ |
| **Vall** | (via Jool) | 500 | 870 | 870 | 13 500 |
| **Tylo** | (via Jool) | 500 | 2 300 | 2 300 | 17 500 |
| **Bop** | (via Jool) | 240 | 330 | 330 | 11 400 |
| **Pol** | (via Jool) | 210 | 350 | 350 | 11 400 |
| **Eeloo** | 2 500 | 620 | 870 | 870 | 9 580 |

### Reading the map

Duna round trip example: LKO→Duna (1 040) + capture (250) + landing (~1 450 aero) + ascent (2 000) + return (~1 040) = **~5 780 m/s total**. One-way: 1 040 + 250 + 1 450 = **~2 740 m/s**.
### Optimal order (easiest → hardest)

Mun (3 260) → Minmus (3 200) → Duna (6 400) → Dres (6 400) → Eeloo (9 580) → Moho (8 480) → Eve (25 000+, hard ascent) → Jool moons (11 400-17 500, need gravity assists)
## Transfer Windows

### Phase angles

| Origin → Target | Phase angle | Transfer time | dV |
|---|---|---|---|
| Kerbin → Duna | ~44° ahead | ~156 days | 1 040 m/s |
| Kerbin → Eve | ~74° ahead | ~114 days | 1 050 m/s |
| Kerbin → Moho | ~100° (varies) | ~74 days | 2 200 m/s |
| Kerbin → Dres | ~100° (varies) | ~240 days | 1 850 m/s |
| Kerbin → Jool | ~97° ahead | ~280 days | 1 980 m/s |
| Kerbin → Eeloo | ~160° (varies) | ~400 days | 2 500 m/s |

Use `scripts/transfer-window.py` to compute exact values for your current game time:

```bash
python scripts/transfer-window.py --target Duna --standalone
```

### Ejection angles

Prograde ejection from LKO (counter-clockwise orbit, north view):

| Target | Ejection angle from prograde |
|---|---|
| Duna | ~0° (~44° ahead of Kerbin) |
| Eve | ~0° (~74° behind Kerbin) |
| Moho | ~(-30°) retrograde + plane change |
| Dres | ~15° above/below plane |
| Jool | ~0° (prograde) |
### Ejection burn calculation

Desired hyperbolic excess velocity ($v_\infty$):

$$v_\infty = \sqrt{v_{esc}^2 + v_{trans}^2} - \sqrt{v_{esc}^2 + v_{circ}^2}$$

Where:
- $v_{esc}$ = escape velocity at parking orbit altitude = $\sqrt{2\mu / r}$
- $v_{circ}$ = circular orbital velocity = $\sqrt{\mu / r}$
- $v_{trans}$ = transfer orbit velocity at Kerbin SOI boundary

Approximate for Kerbin LKO (100 km): add ~350 m/s to the transfer dV for the ejection burn.

## TWR Guidelines

| Phase | Minimum TWR | Recommended TWR |
|---|---|---|
| Kerbin launch | 1.2 | 1.3 - 1.6 |
| Eve launch | 1.2 | 1.5 - 2.0 |
| Duna launch | 1.1 | 1.2 - 1.5 |
| Airless body launch | 1.1 | 2.0 - 3.0 |
| Maneuver burn | 0.1 (impulsive approximation) | 0.2 - 0.5 |
| Landing burn (airless) | 1.0 (must be > 1.0 to slow down) | 2.0 - 4.0 |

### Burn time estimate

$$t_{burn} = \frac{I_{sp} \cdot g_0 \cdot m_{wet}}{F} \cdot \left(1 - e^{-\Delta v / (I_{sp} \cdot g_0)}\right)$$

For most burns under 1 000 m/s, approximate: $t_{burn} \approx \frac{m_{wet} \cdot \Delta v}{F}$

Where $F$ = thrust in N.

## Aerobraking

| Body | Aerobrake altitude | Notes |
|---|---|---|
| Kerbin | 50-60 km | Can capture from Mun return |
| Duna | 15-20 km | Thin atmo, may need multiple passes |
| Eve | 60-70 km | Very thick, can capture from any speed |
| Jool | 120-140 km | Deep atmo, dangerous heating |
| Laythe | 30-40 km | Moderate |
| Lathe | 5-10 km | Very thin, barely effective |

**Tips:** Set PE to aerobrake altitude before SOI entry. Use multiple passes if needed. Heat shields required. Duna aero weak — may need engine assist. Eve aero aggressive — set high PE to avoid lithobraking.
## Mission Planning Workflow

1. **Determine mission target** and use dV map for rough budget
2. **Check transfer window** with `transfer-window.py`
3. **Get vessel mass** with `live-telemetry.py`
4. **Calculate available dV** with `dv-calc.py`
5. **Compare** available dV vs required dV (include 20-30% margin)
6. **If insufficient**, redesign vessel or choose different target
7. **Execute** launch, transfer, landing, return
