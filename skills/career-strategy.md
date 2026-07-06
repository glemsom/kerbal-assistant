# Career Strategy Reference

## Overview

Strategic guidance for KSP career mode — maximising funds, science, and reputation through smart contract management, mission stacking, and tech tree priorities.

## Reading Career State

Use `scripts/save-parser.py <path-to-persistent.sfs>` to get structured JSON of the current career state. Pipe through `jq` for targeted queries:

```bash
# Quick career pulse
python scripts/save-parser.py saves/default/persistent.sfs | jq '.currency'

# Active contracts
python scripts/save-parser.py saves/default/persistent.sfs | jq '.contracts.active_list'

# Unlocked tech tree nodes
python scripts/save-parser.py saves/default/persistent.sfs | jq '.tech_nodes[].id'
```

## Contract Stacking Strategy

### Core Principle
**Stack contracts that share an objective.** One mission can complete multiple contracts simultaneously.

### Best Stacking Combinations

| Stack | Contracts | Mission Example |
|-------|-----------|-----------------|
| **Science at X** | `CollectScience` + `Explore <body>` + `SurveyContract` + `PartTest` at same body | Launch a science probe to Mun — collect surface science, crew report, test LV-909 at Mun, survey Mun lowlands |
| **Station at X** | `StationContract` + `TourismContract` (crew rotation) + `PartTest` on station parts | Build a station, deliver tourists, test docking ports |
| **Satellite at X** | `SatelliteContract` + `Explore <body>` + science contracts | Put a relay + science probe in one launch |
| **Plant flag** | `PlantFlag` + `Explore <body>` + surface science | Crewed landing on a new body covers all three |
| **Test part at X** | `PartTest` + any contract going to the same biome / altitude | Batch all part tests for nearby biomes into one flight |

### Contract Valuation

When deciding which offered contracts to accept, compute **value per unit risk**:

```
Score = (reward_funds + reward_rep * 200 + advance_fee) / (risk_estimate)
```

Where `risk_estimate` accounts for:
- 1.0 — trivial (test part on launchpad)
- 2.0 — easy (suborbital flight)
- 3.0 — moderate (orbit existing vessel)
- 5.0 — hard (new body, docking, precision landing)
- 10.0 — very hard (interplanetary, grand tour)

Rules of thumb:
- **Always accept** World Firsts / Exploration contracts — reputation multipliers scale all future rewards
- **Decline** low-reward Survey contracts on bodies you can't reach yet
- **Decline** contracts approaching deadline with insufficient remaining time
- **Accept** PartTest contracts if testing on the launchpad/runway (free money)

## Tech Tree Priorities

### Early Game (0-100 science)

| Priority | Node | Rationale |
|----------|------|-----------|
| 1 | `basicRocketry` | Fuel tanks, better engines |
| 2 | `engineering101` | Thermometer, antenna, decoupler |
| 3 | `generalRocketry` | Better solids, liquid fuel engines |
| 4 | `stability` | Nose cones, winglets (aero control) |
| 5 | `survivability` | Heat shields, parachutes, landing legs |

### Mid Game (100-500 science)

| Priority | Node | Rationale |
|----------|------|-----------|
| 1 | `flightControl` | SAS modules, reaction wheels |
| 2 | `advRocketry` | Bigger tanks, radial engines |
| 3 | `landing` | Landing struts, wheels |
| 4 | `spaceExploration` | Solar panels, batteries |
| 5 | `scienceTech` | Science Jr, materials bay (more science!) |

### Late Game (500+ science)

| Priority | Node | Rationale |
|----------|------|-----------|
| 1 | `miniaturization` | Probes, low-weight parts |
| 2 | `evatech` | EVA construction, surface samples |
| 3 | `heavierRocketry` | Large engines, asparagus staging |
| 4 | `ionPropulsion` | Efficient interplanetary |
| 5 | `nuclearPropulsion` | NERV engines for deep space |

## Science Farming

### Strategy: Per-biome Science

Each experiment yields science **once per biome per body**. Maximise by visiting multiple biomes.

### Best Science Sources

| Experiment | Science Potential | Best Biomes |
|------------|------------------|-------------|
| Materials Bay (Mystery Goo) | ~10-20 per biome | All biomes |
| Science Jr (Materials Study) | ~20-40 per biome | All biomes |
| Crew Report | ~5-10 per biome | All biomes |
| EVA Report | ~5-10 per biome | Ground + flying over each biome |
| Surface Sample | ~15-30 per biome | Landed biomes only |
| Temperature Scan | ~5-8 per biome | All biomes |
| Barometer | ~5-8 per biome | All biomes (atmosphere bodies) |
| Gravity Scan | ~8-12 per biome | Orbit + surface |
| Seismometer | ~10-20 per biome | Landed (impact or quake) |

### Efficiency Tips

- **Mobile Processing Lab**: Process data into science points. A lab on Mun/Minmus can generate 200-500 science over time with repeated crew reports and surface samples.
- **One probe, many biomes**: Design landers with enough Δv to hop between biomes (Mun: ~580 m/s, Minmus: ~180 m/s for hopping).
- **Atmospheric bodies**: Fly low over multiple biomes before landing (Kerbin, Duna, Eve, Laythe, Jool).

## Fund & Reputation Management

### Income Sources

| Source | Reliability | Notes |
|--------|------------|-------|
| Contract rewards | High | Primary income |
| World First bonuses | One-time | Big reputation + funds |
| Vessel recovery | Medium | Recover vessel value (part cost × 0.6-0.98) |
| Part testing | Low | Small payouts if on launchpad |
| Tourism contracts | Very High | Tourism + station = reliable repeat income |

### Cost Reduction

- **Recover vessels** at KSC or nearby (splashed = 98% recovery, landed at KSC = 98%)
- **Part test on launchpad** = zero propellant cost
- **Single launch for multiple contracts** = shared fuel + shared vehicle
- **Build reusable** (recoverable boosters, spaceplanes for crew rotation)

### Reputation Effects

| Rep Range | Effect |
|-----------|--------|
| 0-200 | Normal contract rewards |
| 200-400 | 5-15% bonus on reward funds |
| 400-600 | 15-30% bonus |
| 600-800 | 30-50% bonus |
| 800-1000 | 50-100% bonus |

**Pro tip**: Complete World Firsts and Exploration contracts early to build reputation, which multiplies all future income.

## Mission Planning Flow

1. **Read save** → `python scripts/save-parser.py <save>`
2. **Check active contracts** → can they stack?
3. **Check offered contracts** → accept highest-value / best-stacking offers
4. **Check tech tree** → what can you build?
5. **Check vessels** → existing assets you can reuse
6. **Design mission** → one launch, multiple objectives
7. **Execute** → launch, perform maneuvers, complete contracts
8. **Recover** → recover vessel or leave as relay/station
9. **Repeat**

## Common Career Mistakes

| Mistake | Consequence | Prevention |
|---------|-------------|------------|
| Accepting too many contracts | Cramped mission scope, deadline failures | Stack contracts; decline low-value offers |
| Ignoring World Firsts | Lost reputation multiplier early | Prioritise exploration |
| Rushing Duna before Kerbin orbit | Low science, expensive failures | Master Kerbin system first |
| No science lab on station | Wasted passive science income | Include lab on orbital stations |
| Re-entering too steep | Explosive disassembly | Shallow entry angle (< 15°), heat shield |
