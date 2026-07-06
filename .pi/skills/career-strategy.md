---
name: career-strategy
description: Strategic guidance for KSP career mode — contract stacking, tech tree priorities, science farming, funds management. Use when advising on career progression or interpreting save-parser.py output.
---

# Career Strategy Reference

## Overview

Strategic guidance for KSP career mode — maximising funds, science, and reputation through smart contract management, mission stacking, and tech tree priorities.

## Reading Career State

Use `scripts/save-parser.py <path-to-persistent.sfs>` to get structured JSON of the current career state. Pipe through `jq` for targeted queries:

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

Accept multiple contracts that share objectives. This is the #1 efficiency lever in career mode.

**Example stack:** If 3 contracts all want "crew report from Mun orbit", you can complete them in one mission instead of three. This multiplies your payout while costing the same fuel and time.

**High-value stack combos:**

| Stack target | Contract types to accept |
|---|---|
| **Mun flyby** | Explore Mun + Plant flag on Mun (counts if you land) + Crew report from Mun orbit |
| **Minmus science** | Explore Minmus + Return science from Minmus + Crew report from Minmus + Temperature scan from Minmus |
| **Station building** | Build station in orbit around Kerbin + Station with 5 crew capacity + Station with power generation |
| **Satellite network** | Put satellite in orbit around Mun + Put satellite with antenna + Communications network milestone |

### What to Decline

| Contract type | Why |
|---|---|
| **Part tests on the runway** | Low payout, zero science, boring |
| **Rescue from orbit** (early game) | Your rescue ship becomes a debris problem unless you have claw/KAS |
| **Tourist contracts** (without a taxi) | Need dedicated crew cabin, often marginal payout unless stacked |
| **Survey contracts** | Hunting for specific biomes at specific altitudes is tedious and time-consuming |
| **Build new VAB building** | Costs more than it pays, delay tier-3 R&D |

### Contract Acceptance Flow

1. Open contracts tab, sort by expiry
2. Scan for shared objectives (same body, same biome, same activity)
3. Accept all compatible contracts
4. Quick maths: total advance ≥ fuel cost of mission? If yes, proceed
5. Decline single-purpose contracts that don't stack

## Tech Tree Priorities

### First priority nodes

| Node | Why unlock first |
|---|---|
| **Basic Rocketry** | Free, gives Flea booster and basic pod |
| **Engineering 101** | Unlocks T-30 "Reliant" (first good LF engine) and first science parts (mystery goo, crew report) |
| **General Rocketry** | TR-18A stack decoupler (staging!), basic fins for stability |
| **Flight Control** | SAS units (stability on ascent) |
| **Science Tech** | Science Jr. (materials bay) — essential for early science farming on launchpad |
| **Landing** | Landing legs and basic wheels — needed for surface missions |
| **Advanced Rocketry** | Terrier engine (high-efficiency vacuum engine for Mun/Minmus) |

### Tech tree milestones

| Before Mun landing | Before Duna mission |
|---|---|
| Terrier engine (vacuum) | LV-N "Nerv" (nuclear engine) |
| Solar panels (basic or OX-4L) | Docking ports (Clamp-o-tron) |
| Batteries (Z-100 or Z-400) | Large solar panels (Gigantor) |
| Basic comms (HG-5) | Advanced comms (RA-2, RA-15) |
| Heat shield (1.25 m) | Heat shield (2.5 m) |
| Parachutes (MK16 or MK2-R) | Drogue chutes |

## Science Farming

### Launchpad farming (tier-1)

Before you leave the atmosphere, collect all possible science from the launchpad:

1. Crew report (while crewed)
2. Mystery goo observation
3. Materials bay analysis (if unlocked)

Total: 15–25 science from the pad alone. Can be repeated if you recover or transmit.

### Biomes to prioritise

| Body | Biomes | Science value |
|---|---|---|
| **Mun** | Highlands, Midlands, Lowlands, Craters, Polar, Canyon | High — easy to reach multiple biomes |
| **Minmus** | Flats, Lowlands, Midlands, Highlands, Slopes, Polar | Very high — low gravity makes multi-biome easy |
| **Kerbin** | Grasslands, Highlands, Water, Deserts, Tundra, Ice Caps | Medium — mostly for early game |
| **Duna** | Highlands, Lowlands, Midlands, Polar, Craters, Canyons | Good — but high dV cost to return |

### Kerbin system biome loot

Maximise: send a single ship to Minmus with 4+ science experiments, visit 3-4 biomes, return. This can unlock most of mid-tier tech tree in one mission.

### Science transmission vs recovery

| Experiment type | Transmit efficiency | Recommendation |
|---|---|---|
| Crew report | 100% | Transmit immediately (no loss) |
| EVA report | 100% | Transmit immediately |
| Mystery goo | 25% | Recover or use mobile lab |
| Materials bay | 25% | Recover or use mobile lab |
| Surface sample | 25% | Recover |

Key insight: for low-efficiency experiments, **store and recover**. Don't transmit materials bay data. Use a scientist in a Mobile Processing Lab (late game) to process and reset experiments.

## Funds Management

### Income sources by stage

| Stage | Primary income | Secondary income |
|---|---|---|
| Early (pad→orbit) | Contract advances | World first milestones |
| Mid (Mun/Minmus) | Contract completion payouts | Science from recovery |
| Late (interplanetary) | Station/satellite contracts | Tourism |

### Expense management

| Expense | When to pay | When to defer |
|---|---|---|
| New parts | After science farming mission | Don't buy until you need it |
| Building upgrade | When you have 3× the cost in reserve | Never delay R&D building |
| New astronaut | Only when needed for a specific mission | Hire free ones from rescue contracts |
| Vessel cost | Fund from contract advance | If advance doesn't cover fuel + parts, decline contract |

## Advanced Tips

### World first milestones

These are one-time bonuses for being the first to achieve something. Prioritise:

| Milestone | Funds | Notes |
|---|---|---|
| First launch | 10,000 | Automatic |
| First orbit | 15,000 | Easy |
| First Mun flyby | 25,000 | Beginner goal |
| First Mun orbit | 35,000 | |
| First Mun landing | 50,000 | |
| First Minmus landing | 40,000 | Easier than Mun! |
| First Duna flyby | 80,000 | Late goal |
| First Duna landing | 100,000 | |

### Stock vs custom vessels

- **Stock vessels** cost 10% less to build. Use stock designs when possible.
- **Custom vessels** cost 10% more but can use advanced parts.
- Balancing: early game use stock, mid/late game switch to custom.

### Orbital station strategy

Build a station in LKO (100-120 km equatorial) as a fuel depot and science hub:

1. Launch a core module (crew cabin + docking ports + solar panels + batteries)
2. Dock a fuel tanker to fill the depot
3. Dock a science lab for processing
4. Dock a crew transfer vehicle

Station pays off through station-building contracts and enables deep-space missions.
