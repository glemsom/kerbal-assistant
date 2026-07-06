#!/usr/bin/env python3
"""Live vessel telemetry from KSP via kRPC — output structured JSON.

Usage:
    python scripts/live-telemetry.py
    python scripts/live-telemetry.py --vessel "Station Alpha"
    python scripts/live-telemetry.py --minify

Outputs JSON to stdout. Exits with non-zero on error.
"""

import json
import sys
import argparse

try:
    import krpc
except ImportError:
    print(json.dumps({"error": "krpc not installed. Run: pip install krpc"}))
    sys.exit(1)


def get_resource_groups(vessel):
    """Return resources grouped by decoupled stage."""
    stages = {}
    for part in vessel.parts.all:
        stage = part.decouple_stage
        if stage < 0:
            continue
        if stage not in stages:
            stages[stage] = {}
        for resource in part.resources.all:
            name = resource.name
            if name not in stages[stage]:
                stages[stage][name] = {"amount": 0.0, "max": 0.0}
            stages[stage][name]["amount"] += resource.amount
            stages[stage][name]["max"] += resource.max
    # Sort by stage number descending (later stages = lower numbers in KSP)
    return dict(sorted(stages.items(), reverse=True))


def get_telemetry(conn, target_name=None):
    """Fetch telemetry from the active vessel or named vessel."""
    sc = conn.space_center

    # Resolve target vessel
    if target_name:
        vessels = [v for v in sc.vessels if v.name == target_name]
        if not vessels:
            return {"error": f"Vessel '{target_name}' not found"}
        vessel = vessels[0]
    else:
        vessel = sc.active_vessel
        if vessel is None:
            return {"error": "No active vessel"}

    flight = vessel.flight(vessel.orbital_reference_frame)
    surface_flight = vessel.flight(vessel.surface_reference_frame)
    orbit = vessel.orbit
    resources = vessel.resources

    data = {
        "vessel": {
            "name": vessel.name,
            "type": str(vessel.type).split(".")[-1],
            "situation": str(vessel.situation).split(".")[-1],
            "biome": vessel.biome,
            "crew_count": len(vessel.crew),
            "crew": [{"name": m.name, "role": str(m.role).split(".")[-1], "trait": m.trait} for m in vessel.crew],
        },
        "mass": {
            "total": round(vessel.mass, 3),
            "dry": round(vessel.dry_mass, 3),
            "fuel_mass": round(vessel.mass - vessel.dry_mass, 3),
        },
        "thrust": {
            "available": round(vessel.available_thrust, 2),
            "max": round(vessel.max_thrust, 2),
            "max_vacuum": round(vessel.max_vacuum_thrust, 2),
        },
        "resources": get_resource_groups(vessel),
        "flight": {
            "mean_altitude": round(surface_flight.mean_altitude, 1),
            "surface_altitude": round(surface_flight.surface_altitude, 1),
            "speed": round(surface_flight.speed, 2),
            "orbital_speed": round(flight.speed, 2),
            "g_force": round(surface_flight.g_force, 3),
            "dynamic_pressure": round(surface_flight.dynamic_pressure, 2),
            "atmosphere_density": round(surface_flight.atmosphere_density, 6),
            "velocity": {
                "x": round(flight.velocity[0], 2),
                "y": round(flight.velocity[1], 2),
                "z": round(flight.velocity[2], 2),
            },
        },
        "position": {
            "latitude": round(surface_flight.latitude, 6),
            "longitude": round(surface_flight.longitude, 6),
        },
        "time": {
            "ut": round(sc.ut, 2),
            "warp_rate": sc.warp_rate,
            "rails_warp_factor": sc.rails_warp_factor,
        },
    }

    # Orbit data (None if not in orbit)
    if orbit:
        data["orbit"] = {
            "body": orbit.body.name,
            "apoapsis_altitude": round(orbit.apoapsis_altitude, 1),
            "periapsis_altitude": round(orbit.periapsis_altitude, 1),
            "semi_major_axis": round(orbit.semi_major_axis, 1),
            "eccentricity": round(orbit.eccentricity, 6),
            "inclination": round(orbit.inclination, 6),
            "period": round(orbit.period, 1),
            "time_to_apoapsis": round(orbit.time_to_apoapsis, 1),
            "time_to_periapsis": round(orbit.time_to_periapsis, 1),
            "speed": round(orbit.speed, 2),
            "radius": round(orbit.radius, 1),
        }
    else:
        # Landed/suborbital — provide partial info
        data["orbit"] = None
        if vessel.situation != vessel.situation.pre_launch:
            data["orbit"] = {
                "body": vessel.flight().body.name,
                "note": "Not in orbit — vessel is " + str(vessel.situation).split(".")[-1],
            }

    return data


def main():
    parser = argparse.ArgumentParser(description="Get live KSP vessel telemetry")
    parser.add_argument("--vessel", "-v", help="Target vessel name (default: active vessel)")
    parser.add_argument("--minify", action="store_true", help="Output compact JSON (no indentation)")
    args = parser.parse_args()

    try:
        conn = krpc.connect(name="kerbal-assistant-telemetry", address="127.0.0.1", rpc_port=50000)
    except ConnectionRefusedError:
        print(json.dumps({"error": "KSP not running or kRPC not responding (ConnectionRefusedError)"}))
        sys.exit(1)
    except TimeoutError:
        print(json.dumps({"error": "kRPC connection timed out — is KSP running?"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"kRPC connection failed: {e}"}))
        sys.exit(1)

    data = get_telemetry(conn, target_name=args.vessel)

    indent = None if args.minify else 2
    json.dump(data, sys.stdout, indent=indent)
    sys.stdout.write("\n")

    if "error" in data:
        sys.exit(1)


if __name__ == "__main__":
    main()
