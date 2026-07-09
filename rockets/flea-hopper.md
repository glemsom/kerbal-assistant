# Flea Hopper

**Purpose**: Complete first career contracts — FIRSTLAUNCH (launch first vessel) and SCIENCE (gather mystery goo data). Suborbital science hopper.

**Design**: Minimal single-stage solid rocket. Only `start` tech node parts.

## Parts (top→bottom)

| Part | Qty | Mass (wet) | Mass (dry) |
|---|---|---|---|
| Mk16 Parachute | 1 | 0.10 t | 0.10 t |
| Mk1 Command Pod | 1 | 0.84 t | 0.84 t |
| Mystery Goo Containment Unit | 1 | 0.05 t | 0.05 t |
| RT-5 "Flea" Solid Fuel Booster | 1 | 0.45 t | 0.045 t |
| Basic Fin | 3 | 0.01 t | 0.01 t |

**Total wet mass**: ~1.47 t
**Total dry mass**: ~1.065 t
**Launch TWR**: ~2.7 (Flea = 22.5 kN thrust)
**Burn time**: ~5.5 s
**Max altitude**: ~25-35 km

## Staging

| Stage | Action |
|---|---|
| 0 | RT-5 Flea ignition, liftoff |
| 1 | Mk16 parachute deploy (after apogee, descent) |

No decoupler — the Flea stays attached during re-entry. Parachute handles the ~1 t assembly.

## Build (VAB)

1. Place **Mk1 Command Pod** (root)
2. Attach **Mk16 Parachute** on top node
3. Attach **Mystery Goo** radially to pod side
4. Attach **RT-5 Flea** to pod bottom node
5. Attach **3× Basic Fin** radially on Flea body (120° symmetry)

## Flight Profile

1. **SAS on**, throttle 100%
2. **Stage** — Flea ignites, liftoff
3. **Pitch 10° east** at ~200 m (gentle arc toward horizon)
4. **Run Mystery Goo** experiment at >10 km altitude (right-click → "Run Test")
5. Flea burns out at ~5.5 s, coasts ballistically to ~25-35 km
6. **Deploy parachute** after apogee, below ~4 km altitude
7. Splash down or land on Kerbin
8. **Recover vessel** — contracts complete automatically

## dV / Performance

- Total dV (vacuum): ~1,100 m/s
- Aerodynamic losses: ~200-300 m/s
- Gravity losses: ~200-300 m/s
- Net effective dV: ~500-600 m/s → ~25-35 km suborbital

## Scripts

| Script | Purpose |
|---|---|
| `scripts/build-flea-hopper.py` | Generate .craft file in VAB |
| `scripts/launch-flea-hopper.py` | Auto-launch and fly (kRPC) |

## Notes

- No reaction wheel/SAS module — the pod has built-in SAS torque
- The Flea cannot be shut down once lit; plan accordingly
- Mystery Goo data is stored in the pod; recovery returns the science
- Both contracts complete on recovery or when the game detects the conditions
