---
name: career-strategy
description: Strategic guidance for KSP career mode — contract stacking, tech tree priorities, science farming, funds management. Use when advising on career progression or interpreting save-parser.py output.
---

# Career Strategy Reference

## Reading Career State

Use `scripts/save-parser.py <path-to-persistent.sfs>` → structured JSON. Pipe through `jq`:

```bash
# Quick financial pulse
python scripts/save-parser.py /path/to/persistent.sfs | jq '.currency'

# Active contracts overview
python scripts/save-parser.py /path/to/persistent.sfs | jq '.contracts.active_list[] | {type, state, deadline}'

# Researched tech nodes
python scripts/save-parser.py /path/to/persistent.sfs | jq '.tech_nodes[] | select(.state == "Researched") | .id'
```

## Contract Strategy

### Contract Stacking
Accept contracts sharing objectives — #1 efficiency lever. Stack 3 "crew report from Mun orbit" contracts in 1 mission instead of 3.

**High-value combos:**

| Stack target | Contract types to accept |
|---|---|
| **Mun flyby** | Explore Mun + Plant flag (counts if land) + Crew report from Mun orbit |
| **Minmus science** | Explore Minmus + Return science + Crew report + Temperature scan |
| **Station building** | Build station in Kerbin orbit + 5 crew capacity + power generation |
| **Satellite network** | Put satellite in Mun orbit + with antenna + Comms milestone |

### What to Decline

| Type | Why |
|---|---|
| **Runway part tests** | Low payout, zero science |
| **Rescue from orbit** (early) | Rescue ship becomes debris without claw/KAS |
| **Tourist contracts** (no taxi) | Need crew cabin, marginal |
| **Survey contracts** | Tedious biome hunting |
| **Build new VAB** | Costs more than pays |

### Acceptance Flow
1. Open contracts, sort by expiry
2. Scan for shared objectives (same body/biome/activity)
3. Accept all compatible contracts
4. Quick maths: total advance ≥ fuel cost? Proceed.
5. Decline single-purpose contracts that don't stack

## Tech Tree Priorities

### First priority nodes

| Node | Why |
|---|---|
| **Basic Rocketry** | Free — Flea booster + basic pod |
| **Engineering 101** | T-30 Reliant + mystery goo + crew report |
| **General Rocketry** | TR-18A decoupler + fins |
| **Flight Control** | SAS units |
| **Science Tech** | Science Jr. (materials bay) — essential |
| **Landing** | Landing legs + wheels |
| **Advanced Rocketry** | Terrier (vacuum, Mun/Minmus) |

### Milestones

| Before Mun landing | Before Duna mission |
|---|---|
| Terrier engine | LV-N Nerv (nuclear) |
| Solar panels (basic/OX-4L) | Docking ports |
| Batteries (Z-100/400) | Gigantor solar panels |
| Basic comms (HG-5) | Advanced comms (RA-2, RA-15) |
| 1.25m heat shield | 2.5m heat shield |
| Parachutes (MK16/MK2-R) | Drogue chutes |

## Science Farming

### Launchpad (tier-1)
Before leaving atmosphere: crew report + mystery goo + materials bay (if unlocked) = 15-25 science. Recover or transmit to repeat.

### Biomes to prioritise

| Body | Science value |
|---|---|
| **Mun** | High — easy multi-biome |
| **Minmus** | Very high — low gravity = easy multi-biome |
| **Kerbin** | Medium — mostly early game |
| **Duna** | Good — high dV cost to return |

### Kerbin system biome loot
One ship to Minmus with 4+ experiments, visit 3-4 biomes, return. Unlocks most mid-tier tech tree in 1 mission.

### Transmit vs Recover

| Experiment | Transmit efficiency | Recommended |
|---|---|---|
| Crew report | 100% | Transmit |
| EVA report | 100% | Transmit |
| Mystery goo | 25% | Recover or mobile lab |
| Materials bay | 25% | Recover or mobile lab |
| Surface sample | 25% | Recover |

Key: low-efficiency experiments → **store and recover**. Don't transmit materials bay. Use scientist + Mobile Processing Lab (late game) to process + reset.

## Funds Management

### Income by stage

| Stage | Primary | Secondary |
|---|---|---|
| Early (pad→orbit) | Contract advances | World first milestones |
| Mid (Mun/Minmus) | Contract payouts | Science from recovery |
| Late (interplanetary) | Station/satellite contracts | Tourism |

### Expense management

| Expense | When to pay | When to defer |
|---|---|---|
| New parts | After science farming | Don't buy until needed |
| Building upgrade | When 3× cost in reserve | Never delay R&D |
| New astronaut | Only for specific mission | Hire free from rescue contracts |
| Vessel cost | Fund from contract advance | Decline if advance < fuel+parts |

## Early Game — First Contracts

Kerbin World-Firsts Record-Keeping Society. Available from mission start. Raw `save-parser.py` output shows these as `ExplorationContract` with `PARAM.targetType`:

| targetType | Contract | Objective | dV needed |
|---|---|---|---|
| `FIRSTLAUNCH` | Launch first vessel | Any rocket ~1 km altitude | ~100 m/s |
| `SCIENCE` | Gather science data | Collect + recover experiment | same flight |
| `REACHASPACE` | Reach space | >70 km | ~1,200 m/s |
| `REACHORBIT` | Reach orbit | Stable orbit | ~3,400 m/s |
| `FLYBYMUN` | Fly by Mun | Mun flyby + return | ~4,600 m/s |
| `LANDONMUN` | Land on Mun | Mun landing | ~5,700 m/s |
| `SPLASHKERBIN` | Splash down | Land in water | same flight |

FIRSTLAUNCH + SCIENCE appear immediately, completable in **one flight**.

### Canonical first mission: Flea Hopper

**Rocket:** Mk1 Pod + Mk16 Chute + Mystery Goo + RT-5 Flea + 3× Basic Fin

**Result:** Suborbital hop ~25-35 km. Run Mystery Goo in flight. Chute down. Recover.
Completes: `FIRSTLAUNCH` + `SCIENCE`. Pays ~151k advance + rep.
See `rockets/flea-hopper.md` and `scripts/build-flea-hopper.py`.

```bash
# Generate craft file in save's VAB:
.venv/bin/python scripts/build-flea-hopper.py
# Auto-launch (kRPC, from VAB):
.venv/bin/python scripts/launch-flea-hopper.py
```

## Advanced Tips

### World first milestones
One-time bonuses:

| Milestone | Funds |
|---|---|
| First launch | 10,000 |
| First orbit | 15,000 |
| First Mun flyby | 25,000 |
| First Mun orbit | 35,000 |
| First Mun landing | 50,000 |
| First Minmus landing | 40,000 |
| First Duna flyby | 80,000 |
| First Duna landing | 100,000 |

### Orbital station strategy
Build LKO station (100-120 km equatorial) as fuel depot + science hub:
1. Core module (crew cabin + docking ports + solar panels + batteries)
2. Dock fuel tanker
3. Dock science lab
4. Dock crew transfer vehicle

Station pays off via building contracts + enables deep-space missions.
