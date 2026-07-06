# Kerbal Assistant — Usage Guide

How to set up, run, and integrate everything in this repo.

## Contents

1. [Quick start](#quick-start)
2. [Setup](#setup)
3. [Script reference](#script-reference)
4. [Skills reference](#skills-reference)
5. [Workflows](#workflows)
6. [Integration with Pi](#integration-with-pi)
7. [Common tasks](#common-tasks)

---

## Quick start

```bash
# 1. Install kRPC mod + Python client
bash setup/install-krpc.sh

# 2. Launch KSP, enable kRPC server (toolbar icon → Start Server)

# 3. Run a script
python scripts/live-telemetry.py
python scripts/dv-map.py --body Duna
python scripts/transfer-window.py --target Duna --standalone
```

---

## Setup

### Prerequisites

- KSP 1.12.5 installed via Steam at `~/.local/share/Steam/steamapps/common/Kerbal Space Program/`
- Python ≥ 3.10
- [OpenCode Go](https://opencode.ai) subscription (optional — needed only for Pi agent interaction)

### Step 1: Install kRPC mod

```bash
bash setup/install-krpc.sh
```

Downloads kRPC v0.5.4, installs the mod into GameData, and installs the Python `krpc` package. Uses pip, pipx, or creates a `.venv` automatically.

### Step 2: Launch KSP + enable kRPC

1. Open KSP via Steam
2. Load any save (sandbox or career)
3. Click the **kRPC** toolbar icon (top-right)
4. Click **Start Server**
5. Default ports: RPC=50000, Stream=50001

### Step 3: Verify connection

```bash
python3 -c "import krpc; conn = krpc.connect(name='test'); print(conn.space_center.active_vessel.name)"
```

Should print your active vessel name. If it fails, KSP may not be running or kRPC server not started.

### Alternative: standalone mode

Scripts marked with a ★ work **without KSP running** — they use built-in community data instead of live kRPC queries.

---

## Script reference

All scripts in `scripts/` are standalone CLIs. They output **JSON to stdout**, errors to stderr. Exit 0 on success, 1 on failure.

### `live-telemetry.py` — Vessel state snapshot

Fetch real-time vessel data from KSP.

| Flag | Description |
|------|-------------|
| `--vessel / -v <name>` | Target specific vessel (default: active vessel) |
| `--minify` | Compact JSON output (single line) |

```bash
# Default: current active vessel
python scripts/live-telemetry.py

# Specific vessel
python scripts/live-telemetry.py --vessel "Mun Lander 1"

# Compact for scripting
python scripts/live-telemetry.py --minify
```

**Output example** (abbreviated):

```json
{
  "vessel": { "name": "Mun Lander 1", "type": "Lander", "situation": "Landed", "biome": "Midlands" },
  "mass": { "total": 12.345, "dry": 4.200, "fuel_mass": 8.145 },
  "thrust": { "available": 50.0, "max": 100.0 },
  "flight": { "mean_altitude": 8200.0, "g_force": 1.0, "dynamic_pressure": 0.0 },
  "orbit": { "body": "Mun", "apoapsis_altitude": 0.0, "periapsis_altitude": 0.0 },
  "resources": { "0": { "LiquidFuel": { "amount": 800.0, "max": 1000.0 } } },
  "time": { "ut": 1234567.89 }
}
```

**Use cases:**
- Check vessel status mid-mission
- Pipe into other scripts (`dv-calc.py --json "$(python scripts/live-telemetry.py --minify)"`)
- Monitor G-force / Q during ascent

---

### `auto-ascent.py` — Autonomous surface→orbit launch ★

Fully automated launch from surface to target orbit. Handles liftoff, gravity turn, staging, coasting, and circularization.

| Flag | Default | Description |
|------|---------|-------------|
| `--target-apo` | 100000 | Target apoapsis (m) |
| `--target-peri` | apo-20000 | Target periapsis (m) |
| `--turn-start` | 250 | Start gravity turn at altitude (m) |
| `--turn-end` | 40000 | End gravity turn at altitude (m) |
| `--final-pitch` | 5 | Final pitch angle (° above horizon) |
| `--max-q` | 15000 | Max dynamic pressure (Pa) |
| `--heading` | 90 | Launch heading (0=N, 90=E) |

```bash
# Default Kerbin orbit (100 km circular)
python scripts/auto-ascent.py

# Higher orbit, aggressive turn
python scripts/auto-ascent.py --target-apo 120000 --turn-start 100 --turn-end 30000 --final-pitch 10

# Launch from Mun
python scripts/auto-ascent.py --target-apo 100000 --turn-start 500 --final-pitch 20 --heading 90
```

**Output:** Streams JSON events to stdout (`liftoff`, `stage`, `coast_start`, `orbit_achieved`, etc.).

**Abort:** Ctrl+C disengages autopilot, zeroes throttle, exits cleanly.

**Body-specific profiles** — see `skills/ascent-profiles.md`.

---

### `create-node.py` — Maneuver node planner ★

Create or simulate maneuver nodes at specific times or orbital events.

| Flag | Description |
|------|-------------|
| `--prograde <dV>` | Prograde delta-V (m/s) |
| `--normal <dV>` | Normal delta-V (m/s) |
| `--radial <dV>` | Radial delta-V (m/s) |
| `--ut <time>` | Explicit universal time |
| `--at-apoapsis` | Place node at next apoapsis |
| `--at-periapsis` | Place node at next periapsis |
| `--at-an` | Place node at next ascending node |
| `--at-dn` | Place node at next descending node |
| `--multi N` | Split dV across N nodes |
| `--spacing S` | Seconds between multi-nodes (default: 600) |
| `--no-remove` | Keep nodes (default: remove after simulation) |

```bash
# Plan a 850 m/s ejection burn at next apoapsis
python scripts/create-node.py --prograde 850 --at-apoapsis

# Plane change at ascending node
python scripts/create-node.py --prograde 150 --normal 50 --at-an

# Multi-node: split 850 m/s across 3 burns, 10 min apart
python scripts/create-node.py --multi 3 --prograde 850 --spacing 600

# Explicit UT
python scripts/create-node.py --prograde 200 --ut 2350000
```

**Output example:**

```json
{
  "vessel": "Mun Transfer Stage",
  "body": "Kerbin",
  "nodes": [
    {
      "index": 1,
      "ut": 2350000.0,
      "delta_v": { "prograde": 850.0, "normal": 0.0, "radial": 0.0, "total": 850.0 },
      "burn_vector": { "x": 0.866, "y": 0.0, "z": 0.5 }
    }
  ]
}
```

---

### `warp-to.py` — Time warp to events

Warp to a specific UT or orbital event with smooth approach.

| Flag | Default | Description |
|------|---------|-------------|
| `--ut <time>` | — | Explicit UT target |
| `--relative <s>` | — | Warp N seconds from now |
| `--node` | default | Warp to next maneuver node |
| `--sunrise` | — | Warp to next sunrise at current position |
| `--soi-change` | — | Warp to next SOI transition |
| `--lead-time` | 30 | Arrive this many seconds before target |
| `--node-lead` | — | Override lead time for maneuver nodes |
| `--max-warp` | 7 | Max warp factor (0-7) |
| `--max-physics` | 4 | Max physics warp factor (0-4) |

```bash
# Warp to next maneuver node
python scripts/warp-to.py --node

# Warp to a specific time
python scripts/warp-to.py --ut 2350000

# Warp 1 hour forward
python scripts/warp-to.py --relative 3600

# Warp to next sunrise (e.g., for solar-powered probe)
python scripts/warp-to.py --sunrise

# Warp to SOI change
python scripts/warp-to.py --soi-change

# Warp to node but arrive 60s before (for setup)
python scripts/warp-to.py --node --node-lead 60
```

**Approach sequence:**
1. High-speed warp (`sc.warp_to`) for bulk of distance
2. Physics warp for final approach
3. Drops to 1x at T-30s, physics warp off at T-5s
4. Arrives at target - lead_time

---

### `dv-calc.py` — Delta-V / stage calculator ★

Compute delta-V per stage using Tsiolkovsky rocket equation. **No KSP required.**

| Flag | Description |
|------|-------------|
| `--isp <csv>` | Vacuum Isp per stage |
| `--wet <csv>` | Wet mass per stage (kg) |
| `--dry <csv>` | Dry mass per stage (kg) |
| `--stages N` | Number of stages |
| `--payload <kg>` | Payload mass |
| `--thrust <csv>` | Thrust per stage (N) — enables TWR / burn time |
| `--body <name>` | Body name (default: Kerbin) |
| `--gravity <m/s²>` | Override surface gravity |
| `--json <str>` | JSON mass data (piped from telemetry) |

```bash
# Single stage
python scripts/dv-calc.py --isp 350 --wet 40000 --dry 5000

# Two stages with payload
python scripts/dv-calc.py --isp 320,350 --wet 10000,3000 --dry 1000,500 --stages 2 --payload 2000

# Include TWR calculation
python scripts/dv-calc.py --isp 350 --wet 40000 --dry 5000 --thrust 200000 --body Mun

# Pipe from live telemetry
python scripts/live-telemetry.py --minify | python -c "
import sys, json
data = json.load(sys.stdin)
# Extract mass data from telemetry
m = data.get('mass', {})
payload_input = json.dumps({'vessel': {'mass': m}})
" | xargs -I{} python scripts/dv-calc.py --json '{}'
```

**Output:**

```json
{
  "stages": [
    { "stage": 1, "isp_vac": 320, "wet_mass": 10000, "dry_mass": 1000, "dv": 7241.2, "twr": 1.53, "burn_duration_s": 154.2 },
    { "stage": 2, "isp_vac": 350, "wet_mass": 3000, "dry_mass": 500, "dv": 6150.7, "twr": null }
  ],
  "total_dv": 13391.9,
  "payload_mass": 2000,
  "effective_payload_fraction": 0.1333
}
```

---

### `dv-map.py` — Kerbol system dV map ★

Structured JSON with delta-V requirements for all bodies. **No KSP required.**

| Flag | Description |
|------|-------------|
| `--body <name>` | Single body only |
| `--rankings` | Difficulty rankings only |
| `--minify` | Compact JSON |

```bash
# Full map (all bodies)
python scripts/dv-map.py

# Single body
python scripts/dv-map.py --body Duna

# Just rankings (easiest→hardest)
python scripts/dv-map.py --rankings

# Compact for scripting
python scripts/dv-map.py --minify
```

**Output:**

```json
{
  "source": "KSP community delta-V map, v1.12",
  "bodies": {
    "Mun": {
      "transfer_dV_from_reference": 860,
      "capture_dV": 240,
      "landing_dV": 580,
      "ascent_dV": 580,
      "round_trip_dV": 3260,
      "difficulty_rank": 2
    }
  }
}
```

---

### `transfer-window.py` — Transfer window / phase angle ★

Compute optimal phase angle and transfer duration to any body.

| Flag | Description |
|------|-------------|
| `--target <body>` | **Required.** Target body |
| `--source <body>` | Source body (default: Kerbin) |
| `--standalone` | Use community values (no KSP) |
| `--list-bodies` | List all known bodies with data |
| `--minify` | Compact JSON |

```bash
# Community values (no KSP needed)
python scripts/transfer-window.py --target Duna --standalone

# Live kRPC data (KSP must be running)
python scripts/transfer-window.py --target Duna

# Inner planet transfer
python scripts/transfer-window.py --target Eve --standalone

# List all available bodies
python scripts/transfer-window.py --list-bodies
```

**Standalone output:**

```json
{
  "source": "Kerbin",
  "target": "Duna",
  "optimal_phase_angle_deg": 180.0,
  "ejection_dV_m_s": 1040,
  "transfer_duration_s": 1404000,
  "transfer_duration_days": 65.0
}
```

The script auto-detects kRPC availability and falls back to standalone mode. Use `--standalone` to force community values.

---

### `save-parser.py` — Career save parser ★

Parse KSP `.sfs` save files into structured JSON. **No KSP required.**

| Argument | Description |
|----------|-------------|
| `<path>` | Path to `persistent.sfs` |
| `--minify` | Compact output |
| `--pretty` | Pretty-printed (default) |
| `--raw` | Full parse tree (instead of career summary) |

```bash
# Career pulse
python scripts/save-parser.py ~/.local/share/Steam/steamapps/common/Kerbal\ Space\ Program/saves/default/persistent.sfs

# Quick currency check
python scripts/save-parser.py path/to/persistent.sfs | jq '.currency'

# Active contracts
python scripts/save-parser.py path/to/persistent.sfs | jq '.contracts.active_list'

# Unlocked tech nodes
python scripts/save-parser.py path/to/persistent.sfs | jq '.tech_nodes[].id'

# Raw parse tree
python scripts/save-parser.py path/to/persistent.sfs --raw
```

**Output example:**

```json
{
  "meta": { "version": "1.12.5", "mode": "Career" },
  "currency": { "funds": 1250000, "science": 345, "reputation": 180 },
  "tech_nodes": [{ "id": "basicRocketry", "state": "Researched" }],
  "contracts": {
    "active": 3,
    "offered": 5,
    "completed": 12,
    "active_list": [ { "guid": "...", "type": "ExploreBody", "state": "active" } ]
  },
  "vessels": { "total": 8, "list": [ { "name": "Station Alpha", "situation": "Orbiting" } ] }
}
```

---

## Skills reference

Skills in `.pi/skills/` are proper Pi skills with YAML frontmatter (`name`, `description`). Pi auto-discovers them when the project is trusted — their descriptions appear in the system prompt, and Pi reads full content on-demand when the task matches. They provide background reference, not executable code.

| Skill | File | What it covers |
|-------|------|----------------|
| **kRPC Reference** | `.pi/skills/krpc-reference.md` | Condensed kRPC API — connection, services, common patterns |
| **Vessel Operations** | `.pi/skills/vessel-operations.md` | Interpreting telemetry, when to stage/burn, biome science |
| **Ascent Profiles** | `.pi/skills/ascent-profiles.md` | Launch profiles per body, gravity turn parameters, TWR |
| **Career Strategy** | `.pi/skills/career-strategy.md` | Contract stacking, tech priorities, science farming |
| **Delta-V Planning** | `.pi/skills/delta-v-planning.md` | Rocket equation, dV map, transfer windows, TWR guidelines |

Skills pair with scripts: e.g., `.pi/skills/ascent-profiles.md` tells you the right `auto-ascent.py` parameters for each body.

---

## Workflows

### Pre-mission: Can my ship reach Duna?

```bash
# 1. Get vessel mass
python scripts/live-telemetry.py --minify > ship.json

# 2. Calculate total dV
#    (manually extract mass, then:)
python scripts/dv-calc.py --isp 350,320 --wet 40000,5000 --dry 5000,1000 --payload 2000

# 3. Check dV requirements
python scripts/dv-map.py --body Duna | jq '.transfer_dV_from_reference, .capture_dV, .landing_dV'

# 4. Check transfer window
python scripts/transfer-window.py --target Duna --standalone
```

### Autonomous launch

```bash
# Launch to 100 km circular orbit
python scripts/auto-ascent.py --target-apo 100000 --heading 90
```

Watch the JSON events stream by. The script stages automatically, throttles through max Q, and circularizes.

### Maneuver planning chain

```bash
# 1. Warp to next node
python scripts/warp-to.py --node --node-lead 60

# 2. Create ejection node
python scripts/create-node.py --prograde 850 --at-apoapsis

# 3. Execute (via Pi or manually)
#    Point to node burn vector, throttle up
```

### Career pulse + strategy

```bash
# 1. Parse save
python scripts/save-parser.py saves/default/persistent.sfs > career.json

# 2. Check what contracts are active
cat career.json | jq '.contracts.active_list[] | {type, state}'

# 3. Check budget
cat career.json | jq '.currency'
```

### Live telemetry → dV check pipe

```bash
# Get vessel mass and feed into dV calculator
TELE=$(python scripts/live-telemetry.py --minify)
MASS=$(echo "$TELE" | python -c "import sys,json; d=json.load(sys.stdin); print(f'--wet {d[\"mass\"][\"total\"]*1000} --dry {d[\"mass\"][\"dry\"]*1000}')")
python scripts/dv-calc.py --isp 350 $MASS
```

---

## Integration with Pi

When running as a Pi coding agent, these scripts are invoked via the `bash` tool. Pi reads their JSON output to inform its responses.

### Pattern: Pi reads telemetry

User: *"What's my vessel status?"*

Pi runs: `bash -c "cd ~/Documents/git/kerbal-assistant && python scripts/live-telemetry.py --minify"`

Pi reads the JSON and replies: *"Mun Lander 1 is landed in the Midlands biome. Fuel: 800/1000 LF. All systems nominal."*

### Pattern: Pi plans a transfer

User: *"Can I get to Duna?"*

Pi runs `dv-map.py --body Duna` and `dv-calc.py` (with vessel data), compares totals, advises.

### Pattern: Pi executes a launch

User: *"Launch to 120 km orbit."*

Pi runs `auto-ascent.py --target-apo 120000`, streams events back to user.

### Important: KSP must be running

Scripts that connect via kRPC fail if KSP isn't running or the kRPC server isn't started. The `--standalone` flag on `dv-map.py`, `dv-calc.py`, `transfer-window.py`, and `save-parser.py` works without KSP.

---

## Common tasks

| Task | Command |
|------|---------|
| Check vessel state | `python scripts/live-telemetry.py` |
| Launch to orbit | `python scripts/auto-ascent.py --target-apo 100000` |
| Calculate rocket dV | `python scripts/dv-calc.py --isp 350 --wet 40000 --dry 5000` |
| Look up dV to Duna | `python scripts/dv-map.py --body Duna` |
| Find transfer window | `python scripts/transfer-window.py --target Duna` |
| Warp to maneuver | `python scripts/warp-to.py --node` |
| Plan ejection burn | `python scripts/create-node.py --prograde 850 --at-apoapsis` |
| Check career finances | `python scripts/save-parser.py <persistent.sfs> \| jq '.currency'` |
| List active contracts | `python scripts/save-parser.py <persistent.sfs> \| jq '.contracts.active_list'` |
| Install dependencies | `bash setup/install-krpc.sh` |

---

## Architecture

See `docs/adr/ADR-0001-hybrid-architecture.md` for the three-layer design:

```
Pi Agent  →  Python scripts (scripts/)  →  kRPC  →  KSP 1.12.5
```

Scripts are standalone CLIs that output JSON. Pi calls them via `bash` tool. Skills provide context for Pi to interpret results.
