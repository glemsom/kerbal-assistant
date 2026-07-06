# ADR-0001: Hybrid Architecture (Pi Agent + Python + kRPC)

**Status:** Accepted  
**Date:** 2026-07-06  
**Deciders:** Glenn Sommer

## Context

Kerbal Assistant operates at the intersection of three systems:

1. **Pi** — the AI coding agent framework that orchestrates interactions, reads skills, invokes tools
2. **KSP (Kerbal Space Program)** — the game, running on Linux via Steam
3. **kRPC** — a mod + RPC library that exposes KSP internals over a network protocol

The key challenge: Pi cannot call KSP APIs directly, and KSP cannot call LLM APIs. We need a bridge.

## Decision

We adopt a **three-layer hybrid architecture**:

```
┌─────────────────────────────────────┐
│  Pi Agent                           │
│  (AI orchestration, skill prompts,  │
│   tool invocation)                  │
├─────────────────────────────────────┤
│  Python scripts                     │
│  (scripts/ — telemetry, autopilot,  │
│   planning, calculators)            │
├─────────────────────────────────────┤
│  kRPC                               │
│  (mod in KSP GameData + Python lib) │
├─────────────────────────────────────┤
│  KSP 1.12.5                         │
│  (simulation, physics, vessels)     │
└─────────────────────────────────────┘
```

### Responsibilities

- **Pi Agent** — natural-language interaction, skill-based reasoning, reading telemetry output, suggesting maneuvers, calling scripts as `bash` tools
- **Python scripts (`scripts/`)** — all KSP-facing logic: connect via kRPC, read vessel state, execute burns, control autopilot, compute transfers. Each script is a standalone CLI that outputs structured JSON or text.
- **kRPC** — the transport layer. kRPC mod runs inside KSP, opens a TCP port (default 50000). Python `krpc` client connects via `krpc.connect()`. Provides access to SpaceCenter, Vessel, Control, AutoPilot, Orbit, Flight, CelestialBody services.
- **KSP** — the game engine. Must be running with a vessel loaded for kRPC scripts to work.

### Data flow

```
User → Pi (prompt) → Pi calls bash tool → Python script → kRPC → KSP
KSP → kRPC → Python stdout → Pi reads tool output → Pi responds to user
```

### Why not alternatives

| Alternative | Rejected because |
|---|---|
| Direct Python console in Pi | No persistent KSP connection, no real-time control |
| Mono/.NET interop | Heavier, KSP-specific, less portable |
| KerbNet / kOS | kOS is its own language; KerbNet is read-only |
| Raw save file parsing | Works for planning but not real-time vessel control |
| Plugin modding (C#) | Requires Unity toolchain, compile steps, slower iteration |

## Consequences

### Positive

- **Separation of concerns:** Pi stays agnostic of KSP internals; scripts are testable in isolation (mock kRPC connection)
- **Fast iteration:** Python scripts can be edited and re-run without restarting KSP
- **Composability:** Scripts can be chained (e.g., telemetry → maneuver planner → node executer)
- **LLM-friendly:** Pi's `bash` tool can run scripts and read structured output; no exotic protocol handling needed

### Negative

- **KSP must be running** for any script that touches live vessel state
- **kRPC server must be enabled** in-game (check toolbar icon)
- **Latency:** each script invocation involves Python startup + kRPC handshake (~1-2s)
- **State lost between script runs** — scripts are stateless CLI processes, so active vessel tracking requires the user or Pi to pass context

### Mitigations

- Keep a `kRPC.KRPC.port` in `CONTEXT.md` for connection config
- Scripts accept `--connect` args and reconnect on each call (simple, stateless)
- For stateful workflows, a long-lived background script can be monitored via `monitor_process`

## Compliance

- ADR-0001 supersedes any earlier ad-hoc architecture notes
- All future `scripts/` and `skills/` must respect this layering
- Deviations require a new ADR
