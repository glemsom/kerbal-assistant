# Kerbal Assistant

KSP reference — skills, knowledge bases, and configs for AI-assisted Kerbal Space Program gameplay. KSP installed via Steam on Linux.

## Paths

All absolute paths. A new agent must read this section first.

### KSP installation

| What | Path |
|---|---|
| KSP root | `~/.local/share/Steam/steamapps/common/Kerbal Space Program/` |
| GameData | `.../Kerbal Space Program/GameData/` |

### LLM provider

| What | Path |
|---|---|
| Pi auth file (API keys) | `~/.pi/agent/auth.json` |
| OpenCode Go key in auth.json | `.opencode-go.key` |
| Pi settings (default model) | `~/.pi/agent/settings.json` |
| OpenCode Go API base URL | `https://opencode.ai/zen/go` |

### This repository

| What | Path |
|---|---|
| Repo root | `~/Documents/git/kerbal-assistant/` |
| Domain glossary | `CONTEXT.md` (this file) |
| Agent skills config | `AGENTS.md` |
| Agent docs | `docs/agents/` |
| Architecture decisions | `docs/adr/` |
| Custom skills | `skills/` |
| Vessel operations skill | `skills/vessel-operations.md` |
| Automation scripts | `scripts/` |
| Live telemetry script | `scripts/live-telemetry.py` |
| Install tools | `setup/` |

## Language

**Skill**:
A Markdown knowledge base (SKILL.md with YAML frontmatter) that an in-game AI assistant loads at startup and injects as context when matched by keyword. Skills are the primary artifact produced by this repo.
_Avoid_: "prompt", "guide", "knowledge base"

**OpenCode Go**:
LLM provider subscription ($10/month). OpenAI-compatible API at `https://opencode.ai/zen/go`. Provides DeepSeek V4 Pro, MiniMax M3, GLM-5.1, and other models.
_Avoid_: "OpenCode", "the provider"

**KSP**:
Kerbal Space Program, version 1.12.5. The game being assisted.
_Avoid_: "the game"

**Career**:
KSP's career mode — managing funds, reputation, science, contracts, and mission progression.

**Vessel**:
A spacecraft built and flown in KSP.

**kRPC**:
A mod and RPC library that exposes KSP's internal state over a network protocol. The Python client (`pip install krpc`) connects to the kRPC server running inside KSP. Provides services: SpaceCenter, Vessel, Control, AutoPilot, Orbit, Flight, CelestialBody. Default ports: RPC=50000, Stream=50001.
_Avoid_: "the mod", "kRPC server" (ambiguous)

**Live Telemetry**:
Real-time vessel state data streamed from KSP via kRPC — altitude, speed, orbit parameters, resources, G-force. Output as structured JSON for Pi consumption.
_Avoid_: "live data"

**Autopilot**:
kRPC's AutoPilot service that can control vessel attitude (pitch, heading, prograde/retrograde target) and execute burns. Also KSP's SAS system. Scripts use AutoPilot for automated maneuvers.
_Avoid_: "auto-pilot" (hyphen)

**Maneuver Node**:
A planned orbit change in KSP defined by prograde, normal, and radial delta-V components at a specific universal time. kRPC can create, read, execute, and remove nodes.

**Vessel Operations**:
Interpreting live telemetry data — orbital parameters, vessel situation, biome, staging guidance, and burn timing. Skill: `skills/vessel-operations.md`.

## Skill domains

**Mission Guidance**:
Step-by-step advice for completing specific KSP contracts and objectives — what rocket to build, what trajectory to fly, what to watch out for.

**Rocket Design**:
Principles and checklists for building stable, efficient rockets — staging, delta-V budgets, thrust-to-weight ratios, aerodynamic stability.

**Delta-V Planning**:
Calculating and budgeting delta-V for transfers, landings, and returns using the Kerbol system's delta-V map.

**Contract Strategy**:
Which contracts to accept, how to stack objectives, and how to maximize career progression efficiency.

**Vessel Operations**:
Interpreting vessel telemetry — orbital parameters, situation awareness, biome science, when to stage/burn, and error conditions. Reference: `skills/vessel-operations.md`.
