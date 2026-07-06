#!/usr/bin/env python3
"""Check KSP/kRPC connection status and report game/vessel state.

Usage:
    python scripts/ksp-status.py
    python scripts/ksp-status.py --vessels     # include vessel list
    python scripts/ksp-status.py --launchable  # include launchable craft
    python scripts/ksp-status.py --all         # everything

Outputs JSON to stdout.
Exits 0 on success, 1 on connection failure.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

try:
    import krpc
except ImportError:
    print(json.dumps({"connected": False, "error": "krpc not installed. Run: pip install krpc"}))
    sys.exit(1)


def get_status(include_vessels: bool = False,
               include_launchable: bool = False) -> dict:
    """Query KSP/kRPC and return status dict."""
    conn = krpc.connect(name="kerbal-assistant-status", address="127.0.0.1",
                        rpc_port=50000, stream_port=50001)
    sc = conn.space_center

    status: dict = {
        "connected": True,
        "time": {"ut": sc.ut},
        "game_mode": str(sc.game_mode).split(".")[-1],
    }

    # -- Active vessel ---------------------------------------------------------
    try:
        vessel = sc.active_vessel
        if vessel:
            flight = vessel.flight(vessel.orbit.body.reference_frame)
            orbit = vessel.orbit
            status["active_vessel"] = {
                "name": vessel.name,
                "type": str(vessel.type).split(".")[-1],
                "situation": str(vessel.situation).split(".")[-1],
                "body": orbit.body.name if orbit else None,
                "mass": {
                    "total": round(vessel.mass, 3),
                    "dry": round(vessel.dry_mass, 3),
                },
                "altitude": {
                    "mean": round(flight.mean_altitude, 1),
                    "surface": round(flight.surface_altitude, 1),
                },
                "speed": round(flight.speed, 2),
                "g_force": round(flight.g_force, 3),
                "staging": {
                    "current_stage": vessel.control.current_stage,
                },
            }
            if orbit:
                status["active_vessel"]["orbit"] = {
                    "apoapsis": round(orbit.apoapsis_altitude, 1),
                    "periapsis": round(orbit.periapsis_altitude, 1),
                    "eccentricity": round(orbit.eccentricity, 6),
                    "inclination": round(orbit.inclination, 4),
                    "period": round(orbit.period, 1),
                }
    except Exception as e:
        status["active_vessel"] = {"error": str(e)}

    # -- All vessels in physics range ------------------------------------------
    if include_vessels:
        try:
            vessels = []
            for v in sc.vessels:
                vessels.append({
                    "name": v.name,
                    "type": str(v.type).split(".")[-1],
                    "situation": str(v.situation).split(".")[-1],
                })
            status["vessels"] = vessels
        except Exception as e:
            status["vessels"] = {"error": str(e)}

    # -- Launchable craft ------------------------------------------------------
    if include_launchable:
        status["launchable"] = {}
        for facility in ("VAB", "SPH"):
            try:
                names = sorted(sc.launchable_vessels(facility))
                status["launchable"][facility] = names
            except Exception as e:
                status["launchable"][facility] = {"error": str(e)}

    return status


def main() -> None:
    parser = argparse.ArgumentParser(description="Check KSP/kRPC connection status")
    parser.add_argument("--vessels", action="store_true",
                        help="Include vessels in physics range")
    parser.add_argument("--launchable", action="store_true",
                        help="Include launchable craft in VAB/SPH")
    parser.add_argument("--all", "-a", action="store_true",
                        help="Include all optional info")
    parser.add_argument("--minify", action="store_true",
                        help="Compact JSON (single line)")

    args = parser.parse_args()

    try:
        status = get_status(
            include_vessels=args.vessels or args.all,
            include_launchable=args.launchable or args.all,
        )
        indent = None if args.minify else 2
        print(json.dumps(status, indent=indent))
    except ConnectionRefusedError:
        print(json.dumps({"connected": False,
                          "error": "KSP not running or kRPC not responding"}))
        sys.exit(1)
    except TimeoutError:
        print(json.dumps({"connected": False,
                          "error": "kRPC connection timed out"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"connected": False,
                          "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
