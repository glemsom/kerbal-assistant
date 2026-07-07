# Rockets

Internal rocket designs, references, and craft data for KSP missions.

Each subdirectory or file documents a specific rocket design — part lists,
dV budgets, staging orders, ascent profiles, and .craft files when available.

## Files

| File | Description |
|---|---|
| `orbit-test-1.md` | First orbital test — 200 km Kerbin orbit, 2-stage liquid rocket |

## Purpose

- Store proven rocket designs for reuse across missions.
- Track dV budgets and performance data.
- Provide build instructions for manual VAB assembly or programmatic craft generation.

## Convention

- `.md` files for human-readable design references.
- `.craft` files for KSP VAB/SPH loading (generated via `scripts/build-craft.py`).
- `.json` files for programmatic consumption by automation scripts.
