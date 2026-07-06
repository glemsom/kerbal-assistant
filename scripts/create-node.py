#!/usr/bin/env python3
"""Create maneuver node at given time or orbit event — kRPC.

Usage:
    python scripts/create-node.py --prograde 850
    python scripts/create-node.py --prograde 200 --at-apoapsis
    python scripts/create-node.py --prograde 950 --normal 50 --radial -30 --ut 2350000
    python scripts/create-node.py --at-an --prograde 150
    python scripts/create-node.py --multi 3 --prograde 850   (split across N nodes)

Outputs JSON to stdout. Exits non-zero on error.
"""

from __future__ import annotations

import argparse
import json
import math
import signal
import sys
from typing import Any

try:
    import krpc
except ImportError:
    print(json.dumps({"error": "krpc not installed. Run: pip install krpc"}))
    sys.exit(1)


# ---------------------------------------------------------------------------
# Global cleanup
# ---------------------------------------------------------------------------
_conn: krpc.Client | None = None
_cleanup_done = False


def cleanup(*_: Any) -> None:
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True
    if _conn is None:
        return
    try:
        vessel = _conn.space_center.active_vessel
        if vessel:
            vessel.control.throttle = 0.0
            vessel.auto_pilot.disengage()
            print(json.dumps({"event": "abort", "message": "Cleanup done"}))
    except Exception:
        pass


signal.signal(signal.SIGINT, lambda *_: (cleanup(), sys.exit(1)))
signal.signal(signal.SIGTERM, lambda *_: (cleanup(), sys.exit(1)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def connect() -> krpc.Client:
    """Connect to kRPC server."""
    global _conn
    try:
        _conn = krpc.connect(name="kerbal-assistant-create-node",
                             address="127.0.0.1", rpc_port=50000)
    except ConnectionRefusedError:
        print(json.dumps({"error": "KSP not running or kRPC not responding (ConnectionRefusedError)"}))
        sys.exit(1)
    except TimeoutError:
        print(json.dumps({"error": "kRPC connection timed out — is KSP running?"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"kRPC connection failed: {e}"}))
        sys.exit(1)
    return _conn


def log_event(event: str, **kwargs: Any) -> None:
    msg = {"event": event, **kwargs}
    print(json.dumps(msg))


def orbit_summary(orbit: Any) -> dict:
    """Return a dict of key orbit parameters."""
    if orbit is None:
        return {"body": None}
    return {
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


# ---------------------------------------------------------------------------
# Time-of-event helpers
# ---------------------------------------------------------------------------

def time_to_an(vessel: Any, body: Any) -> float:
    """Seconds until next ascending node relative to body's equator."""
    orb = vessel.orbit
    aop = orb.argument_of_periapsis
    ta_an = (2 * math.pi - aop) % (2 * math.pi)
    ta_current = orb.true_anomaly
    mu = body.gravitational_parameter
    sma = orb.semi_major_axis
    if sma <= 0:
        return float("inf")
    mean_motion = math.sqrt(mu / abs(sma) ** 3)
    dt = (ta_an - ta_current) / mean_motion
    if dt < 0:
        dt += orb.period
    return dt


def time_to_dn(vessel: Any, body: Any) -> float:
    """Seconds until next descending node."""
    orb = vessel.orbit
    aop = orb.argument_of_periapsis
    ta_dn = (2 * math.pi - aop + math.pi) % (2 * math.pi)
    ta_current = orb.true_anomaly
    mu = body.gravitational_parameter
    sma = orb.semi_major_axis
    if sma <= 0:
        return float("inf")
    mean_motion = math.sqrt(mu / abs(sma) ** 3)
    dt = (ta_dn - ta_current) / mean_motion
    if dt < 0:
        dt += orb.period
    return dt


def create_nodes(args: argparse.Namespace) -> None:
    """Create maneuver node(s) and report."""
    conn = connect()
    sc = conn.space_center
    vessel = sc.active_vessel

    if vessel is None:
        print(json.dumps({"error": "No active vessel"}))
        sys.exit(1)

    orb = vessel.orbit
    if orb is None:
        print(json.dumps({"error": "Vessel not in orbit"}))
        sys.exit(1)

    body = orb.body
    ut_now = sc.ut

    # --- Determine node UT ---------------------------------------------------
    if args.ut is not None:
        node_ut = args.ut
        log_event("node_time", mode="explicit", ut=node_ut)
    elif args.at_apoapsis:
        node_ut = ut_now + orb.time_to_apoapsis
        log_event("node_time", mode="apoapsis",
                  time_to_event=round(orb.time_to_apoapsis, 1), ut=node_ut)
    elif args.at_periapsis:
        node_ut = ut_now + orb.time_to_periapsis
        log_event("node_time", mode="periapsis",
                  time_to_event=round(orb.time_to_periapsis, 1), ut=node_ut)
    elif args.at_an:
        dt = time_to_an(vessel, body)
        node_ut = ut_now + dt
        log_event("node_time", mode="ascending_node",
                  time_to_event=round(dt, 1), ut=node_ut)
    elif args.at_dn:
        dt = time_to_dn(vessel, body)
        node_ut = ut_now + dt
        log_event("node_time", mode="descending_node",
                  time_to_event=round(dt, 1), ut=node_ut)
    else:
        # Default: current position + 10s
        node_ut = ut_now + 10.0
        log_event("node_time", mode="current", ut=node_ut)

    # --- Split dV across multiple nodes if --multi ---------------------------
    prograde = args.prograde
    normal = args.normal
    radial = args.radial
    count = args.multi if args.multi else 1

    nodes: list[dict] = []
    for i in range(count):
        pg = prograde / count
        nm = normal / count
        rd = radial / count

        # Stagger node times if multi
        t = node_ut + i * args.spacing if i > 0 else node_ut
        node = vessel.control.add_node(t, prograde=pg, normal=nm, radial=rd)

        # Burn vector in node's own reference frame
        bv = node.burn_vector(node.orbital_reference_frame)
        burn_vec = {"x": round(bv[0], 3), "y": round(bv[1], 3), "z": round(bv[2], 3)}

        node_info = {
            "index": i + 1,
            "ut": round(t, 2),
            "delta_v": {
                "prograde": round(node.prograde, 2),
                "normal": round(node.normal, 2),
                "radial": round(node.radial, 2),
                "total": round(node.delta_v, 2),
            },
            "burn_vector": burn_vec,
        }
        nodes.append(node_info)

        if args.no_remove:
            log_event("node_created", **node_info)
        else:
            node.remove()
            log_event("node_simulated", **node_info)

    # --- Output --------------------------------------------------------------
    result = {
        "vessel": vessel.name,
        "body": body.name,
        "ut_now": round(ut_now, 2),
        "orbit_before": orbit_summary(orb),
        "nodes": nodes,
        "node_count": count,
    }

    if not args.minify:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create maneuver node(s) at a time or orbit event")
    # dV components
    parser.add_argument("--prograde", type=float, default=0.0,
                        help="Prograde delta-V in m/s (default: 0)")
    parser.add_argument("--normal", type=float, default=0.0,
                        help="Normal delta-V in m/s (default: 0)")
    parser.add_argument("--radial", type=float, default=0.0,
                        help="Radial delta-V in m/s (default: 0)")

    # Time specification (mutually exclusive-ish)
    parser.add_argument("--ut", type=float, default=None,
                        help="Explicit universal time for the node")
    parser.add_argument("--at-apoapsis", action="store_true",
                        help="Create node at next apoapsis")
    parser.add_argument("--at-periapsis", action="store_true",
                        help="Create node at next periapsis")
    parser.add_argument("--at-an", action="store_true",
                        help="Create node at next ascending node")
    parser.add_argument("--at-dn", action="store_true",
                        help="Create node at next descending node")

    # Multi-node splitting
    parser.add_argument("--multi", type=int, default=None,
                        help="Split dV across this many nodes")
    parser.add_argument("--spacing", type=float, default=600.0,
                        help="Seconds between multi-node placements (default: 600)")

    # Behaviour
    parser.add_argument("--no-remove", action="store_true",
                        help="Keep nodes on the vessel (default: simulate then remove)")
    parser.add_argument("--minify", action="store_true",
                        help="Output compact JSON")

    args = parser.parse_args()

    dV_total = abs(args.prograde) + abs(args.normal) + abs(args.radial)
    if dV_total < 0.001:
        parser.error("At least one dV component must be non-zero")

    try:
        create_nodes(args)
    except Exception as e:
        log_event("error", message=str(e))
        cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
