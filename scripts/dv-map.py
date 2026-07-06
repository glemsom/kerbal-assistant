#!/usr/bin/env python3
"""Kerbol system delta-V map — requirements as structured data.

Outputs JSON to stdout with transfer dV, landing/ascent dV, and body rankings.

Usage:
    python scripts/dv-map.py
    python scripts/dv-map.py --body Duna
    python scripts/dv-map.py --minify
    python scripts/dv-map.py --rankings   (just difficulty rankings)
"""

import json
import sys
import argparse

# ---------------------------------------------------------------------------
# Kerbol system delta-V requirements (m/s)
# Sources: KSP community dV map (v1.12), KSP wiki, community consensus
#
# Values are approximate — actual dV depends on phase angles, eccentricity,
# inclination, and piloting skill. These are conservative planning figures.
# ---------------------------------------------------------------------------

# Transfer dV from Kerbin (low orbit, ~80km) to other bodies
# Format: {body: {"transfer": dV_in, "capture": dV_out, "landing": dV_land, "ascent": dV_ascent}}
BODIES = {
    "Moho": {
        "transfer": 2200,
        "capture": 900,
        "landing": 870,
        "ascent": 870,
        "gravity": 2.70,
        "atmosphere": False,
        "difficulty": 9,
    },
    "Eve": {
        "transfer": 1070,
        "capture": 1330,
        "landing": 0,       # Aerobrake — thick atmosphere
        "ascent": 8000,     # Very high — thick atmosphere, high gravity
        "gravity": 16.7,
        "atmosphere": True,
        "difficulty": 10,
    },
    "Gilly": {
        "transfer": 70,     # From Eve orbit
        "capture": 50,
        "landing": 30,
        "ascent": 30,
        "gravity": 0.049,
        "atmosphere": False,
        "difficulty": 3,
    },
    "Duna": {
        "transfer": 1040,
        "capture": 390,
        "landing": 0,       # Aerobrake possible (thin atmosphere)
        "ascent": 1580,
        "gravity": 2.94,
        "atmosphere": True,
        "difficulty": 5,
    },
    "Ike": {
        "transfer": 150,    # From Duna orbit
        "capture": 100,
        "landing": 270,
        "ascent": 270,
        "gravity": 1.10,
        "atmosphere": False,
        "difficulty": 3,
    },
    "Dres": {
        "transfer": 1540,
        "capture": 470,
        "landing": 510,
        "ascent": 510,
        "gravity": 0.33,
        "atmosphere": False,
        "difficulty": 7,
    },
    "Jool": {
        "transfer": 1980,
        "capture": 2820,    # Aerobrake possible at Jool (dangerous)
        "landing": None,    # No surface — gas giant
        "ascent": None,
        "gravity": 7.85,
        "atmosphere": True,
        "difficulty": 8,
    },
    "Laythe": {
        "transfer": 1070,   # From Jool orbit
        "capture": 220,
        "landing": 0,       # Aerobrake (oxygen atmosphere, no intakes needed for jets)
        "ascent": 2900,
        "gravity": 7.85,
        "atmosphere": True,
        "difficulty": 8,
    },
    "Vall": {
        "transfer": 910,    # From Jool orbit
        "capture": 230,
        "landing": 520,
        "ascent": 520,
        "gravity": 1.86,
        "atmosphere": False,
        "difficulty": 6,
    },
    "Tylo": {
        "transfer": 1100,   # From Jool orbit
        "capture": 380,
        "landing": 2300,    # No atmosphere — all dV required
        "ascent": 2300,
        "gravity": 7.85,
        "atmosphere": False,
        "difficulty": 9,
    },
    "Bop": {
        "transfer": 980,    # From Jool orbit
        "capture": 120,
        "landing": 150,
        "ascent": 150,
        "gravity": 0.062,
        "atmosphere": False,
        "difficulty": 4,
    },
    "Pol": {
        "transfer": 1020,   # From Jool orbit
        "capture": 100,
        "landing": 100,
        "ascent": 100,
        "gravity": 0.037,
        "atmosphere": False,
        "difficulty": 3,
    },
    "Eeloo": {
        "transfer": 2070,
        "capture": 680,
        "landing": 620,
        "ascent": 620,
        "gravity": 1.69,
        "atmosphere": False,
        "difficulty": 8,
    },
    "Mun": {
        "transfer": 860,       # From Kerbin LKO (~80km)
        "capture": 240,
        "landing": 580,
        "ascent": 580,
        "gravity": 1.63,
        "atmosphere": False,
        "difficulty": 2,
    },
    "Minmus": {
        "transfer": 930,       # From Kerbin LKO (~80km) — higher plane change
        "capture": 80,
        "landing": 180,
        "ascent": 180,
        "gravity": 0.49,
        "atmosphere": False,
        "difficulty": 1,
    },
}

# Order by difficulty
DIFFICULTY_RANKING = sorted(BODIES.keys(), key=lambda b: BODIES[b]["difficulty"])


def build_map() -> dict:
    """Build the full dV map."""
    return {
        "source": "KSP community delta-V map, v1.12",
        "reference_orbit": "Kerbin low orbit (80km) for interplanetary; body low orbit for moons",
        "note": "Values are approximate planning figures. Actual dV varies with phase angle, piloting, and vessel efficiency.",
        "bodies": {},
        "difficulty_rankings": DIFFICULTY_RANKING,
    }


def body_info(name: str) -> dict:
    """Return dV data for a single body."""
    b = BODIES.get(name)
    if not b:
        return {"error": f"Unknown body: {name}"}
    return {
        "name": name,
        "transfer_dV_from_Kerbin": b["transfer"],
        "capture_dV": b["capture"],
        "landing_dV": b["landing"],
        "ascent_dV": b["ascent"],
        "surface_gravity_m_s2": b["gravity"],
        "has_atmosphere": b["atmosphere"],
        "difficulty_rank": b["difficulty"],
        "round_trip_dV": (
            b["transfer"] + b["capture"] + (b["landing"] or 0) + (b["ascent"] or 0) + b["transfer"]
            if b["landing"] is not None and b["ascent"] is not None
            else None
        ),
    }


def build_full_map() -> dict:
    """Build the complete response map."""
    result = build_map()
    for name in BODIES:
        result["bodies"][name] = body_info(name)
    return result


def main():
    parser = argparse.ArgumentParser(description="Kerbol system delta-V map")
    parser.add_argument("--body", help="Show dV for a single body only")
    parser.add_argument("--minify", action="store_true", help="Minify JSON output")
    parser.add_argument("--rankings", action="store_true", help="Show difficulty rankings only")
    args = parser.parse_args()

    indent = None if args.minify else 2

    if args.body:
        data = body_info(args.body)
    elif args.rankings:
        data = {
            "rankings": DIFFICULTY_RANKING,
            "details": {b: BODIES[b]["difficulty"] for b in DIFFICULTY_RANKING},
        }
    else:
        data = build_full_map()

    print(json.dumps(data, indent=indent))


if __name__ == "__main__":
    main()
