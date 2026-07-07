# GDLV3 — General Docking/Launch Vehicle 3

Purpose: Deliver docking-port-equipped payload to 200 km Kerbin orbit.

## Design Overview

Single-stick liquid core with 4× SRB boosters. All stock parts. Launched from Kerbin VAB.

### Performance

| Metric | Value |
|---|---|
| Total vacuum dV | ~3 800 m/s |
| Estimated dV after losses | ~2 800 m/s |
| Launch TWR | 1.57 |
| Total wet mass | 75.87 t |
| Total dry mass | 15.27 t |
| Payload | Docking port + fairing |

### Parts & Staging

#### Stage 2 (all engines fire together)
| Part | Qty | Notes |
|---|---|---|
| LV-T45 "Skipper" Liquid Engine | 1 | 650 kN vac, gimbal 2° |
| RT-10 "Hammer" SRB | 4 | Thrust limit 60 %, 251 kN max each |

#### Stage 1 (SRB jettison)
| Part | Qty | Notes |
|---|---|---|
| Radial Decoupler (TT-38K) | 4 | Jettison SRBs when empty |

#### Stage 0 (payload)
| Part | Qty | Notes |
|---|---|---|
| Size 2 Fairing | 1 | Shrouds docking port |
| TR-18A Stack Decoupler | 1 | Payload separation |
| Clamp-o-tron Docking Port Sr. | 1 | Orbital docking |

### Staging Order (in VAB)

| Stage | Action |
|---|---|
| 3 | *Empty — activate to ignite engines* |
| 2 | Skipper + 4× SRB ignition, launch clamps release |
| 1 | SRB jettison via radial decouplers |
| 0 | Fairing jettison + payload separation |

### Ascent Profile

Use `scripts/auto-ascent.py` with:

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

(`--srb-boosters 30` provides timed fallback for SRB jettison if thrust-drop detection fails.)

Or manual ascent:
1. **Liftoff** — Full throttle, SAS on, hold vertical.
2. **Gravity turn** — Start gradual prograde turn at 250 m, reach ~5° pitch by 40 km.
3. **SRB jettison** — SRBs burn out ~25-30 s, decouple via stage 1.
4. **Skipper sustainer** — Continues to 200 km apoapsis, then coast.
5. **Circularization** — Burn prograde at apoapsis until orbit circular.
6. **Payload deploy** — Separate docking port payload in orbit.

### dV Budget Breakdown

| Phase | dV needed |
|---|---|
| Launch & gravity turn | ~2 500 m/s |
| SRB losses + drag | ~300 m/s |
| Circularization at 200 km | ~350 m/s |
| **Total required** | **~3 150 m/s** |
| Available (vacuum) | ~3 800 m/s |
| Margin | ~650 m/s |

### Design Notes

- Skipper gimbal provides control during thick atmosphere.
- No upper stage — Skipper does the orbital insertion itself.
- SRBs at 60 % thrust limit to keep TWR manageable and extend burn time.
- Fairing jettison is on stage 0 (same as payload sep) — must manually jettison or accept drag penalty.
