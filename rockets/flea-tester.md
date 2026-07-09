# Flea Tester

Minimal suborbital hopper for PartTest contracts (RT-5 Flea on launchpad) and FIRSTLAUNCH milestone. Uses only Basic Rocketry parts — no tech needed.

## Design

| Stage | Parts | Action |
|-------|-------|--------|
| 0 | RT-5 "Flea" SRB | Ignite on pad (completes PartTest), liftoff |
| -1 | Mk16 Parachute | Deploy during descent for recovery |

| Part | Qty | Purpose |
|------|-----|---------|
| Mk1 Command Pod | 1 | Crew, control |
| Mk16 Parachute | 1 | Recovery |
| RT-5 "Flea" (solidBooster.sm.v2) | 1 | Test part, propulsion |
| Basic Fin | 3 | Stability |

## Ascent Profile

1. Launch from pad
2. Stage immediately — Flea ignites, PartTest completes
3. Coast to ~1-2 km apogee (Flea burns ~8s)
4. Deploy chute, recover
5. Collect 9.2M funds from PartTest + 10k FIRSTLAUNCH milestone

## dV Budget

| Phase | dV | Engine |
|-------|----|--------|
| Liftoff + ascent | ~300 m/s | Flea |

## Script

```bash
.venv/bin/python scripts/build-flea-tester.py
# Then load "Flea Tester" from VAB and launch
```
