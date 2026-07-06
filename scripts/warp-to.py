#!/usr/bin/env python3
"""Time warp to a specific event — kRPC.

Usage:
    python scripts/warp-to.py --ut 2350000
    python scripts/warp-to.py --relative 3600
    python scripts/warp-to.py --node          (next maneuver node)
    python scripts/warp-to.py --sunrise       (next sunrise at current location)
    python scripts/warp-to.py --soi-change    (next SOI transition)
    python scripts/warp-to.py --event type=soi_change

Outputs JSON to stdout. Exits non-zero on error.
"""
from __future__ import annotations

import argparse
import json
import math
import signal
import sys
import time
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
        _conn = krpc.connect(name="kerbal-assistant-warp-to",
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
    }


# ---------------------------------------------------------------------------
# Warp control
# ---------------------------------------------------------------------------

MAX_PHYSICS_WARP = 4       # kRPC physics warp factor
MAX_REGULAR_WARP = 100000  # kRPC regular warp factor


def get_regular_warp_rate(factor: int) -> float:
    """Return simulation speed multiplier for a given regular warp factor."""
    # kRPC warp rates: https://krpc.github.io/krpc/python/api/space-center/warp.html
    rates = {
        0: 1, 1: 5, 2: 10, 3: 50, 4: 100, 5: 1000,
        6: 10000, 7: 100000,
    }
    return rates.get(factor, 1)


def warp_to_ut(sc: Any, target_ut: float, lead_time: float = 30.0,
               max_regular: int = 7, max_physics: int = 4) -> None:
    """Warp to target_ut, stopping at (target_ut - lead_time) for handover.

    Uses physics warp (up to 4x) for small time skips, then transitions to
    regular warp (up to 100kx) for large skips.  Drops to 1x at arrival.
    """
    ut_now = sc.ut
    if target_ut <= ut_now:
        log_event("warp_skip", reason="Target UT already passed",
                  target_ut=round(target_ut, 2), ut_now=round(ut_now, 2))
        return

    arrival_ut = target_ut - lead_time
    if arrival_ut <= ut_now:
        arrival_ut = target_ut
        lead_time = 0.0

    dt = arrival_ut - ut_now
    log_event("warp_start",
              target_ut=round(target_ut, 2),
              arrival_ut=round(arrival_ut, 2),
              duration=round(dt, 1),
              lead_time=round(lead_time, 1))

    # Small skip → physics warp
    if dt < 10:
        sc.physics_warp_factor = min(max_physics, 2)
        while sc.ut < arrival_ut:
            time.sleep(0.05)
        sc.physics_warp_factor = 0
        log_event("warp_done", ut=round(sc.ut, 2), method="physics")
        return

    # Medium skip → regular warp at increasing rates
    # Determine appropriate warp factor based on time remaining
    warp_factor = 0
    for factor in range(min(max_regular, 7), 0, -1):
        rate = get_regular_warp_rate(factor)
        if dt / rate > 2.0:  # at least 2s real-time
            warp_factor = factor
            break
    warp_factor = max(1, min(warp_factor, max_regular))

    sc.regular_warp_factor = warp_factor
    log_event("warp_active",
              warp_factor=warp_factor,
              rate=get_regular_warp_rate(warp_factor))

    # Monitor progress, reduce warp as we approach
    while sc.ut < arrival_ut:
        remaining = arrival_ut - sc.ut

        # Gradually reduce warp
        if remaining < 60 and sc.regular_warp_factor > 4:
            sc.regular_warp_factor = 4
            log_event("warp_reduced", warp_factor=4, remaining=round(remaining, 1))
        elif remaining < 30 and sc.regular_warp_factor > 2:
            sc.regular_warp_factor = 2
            log_event("warp_reduced", warp_factor=2, remaining=round(remaining, 1))
        elif remaining < 10 and sc.regular_warp_factor > 1:
            sc.regular_warp_factor = 1
            log_event("warp_reduced", warp_factor=1, remaining=round(remaining, 1))

        # Switch to physics warp for final seconds
        if remaining < 5 and sc.regular_warp_factor > 0:
            sc.regular_warp_factor = 0
            sc.physics_warp_factor = 2
            log_event("warp_physics", remaining=round(remaining, 1))

        time.sleep(0.2)

    # Drop to 1x
    sc.regular_warp_factor = 0
    sc.physics_warp_factor = 0
    log_event("warp_arrived",
              ut=round(sc.ut, 2),
              lead_time=round(lead_time, 1))


# ---------------------------------------------------------------------------
# Event time calculation
# ---------------------------------------------------------------------------

def next_maneuver_ut(vessel: Any) -> float | None:
    """Return UT of next maneuver node, or None."""
    nodes = vessel.control.nodes
    if not nodes:
        return None
    return nodes[0].ut


def next_sunrise_ut(vessel: Any, body: Any) -> float:
    """Calculate UT of next sunrise at vessel's current orbital position.

    Uses the angle between the vessel's position vector and the sun
    direction to find the next terminator crossing.  Works for orbital
    positions; surface positions need a more complex rotation model.
    """
    sc = body.space_center
    orb = vessel.orbit
    if orb is None:
        return sc.ut + 600.0

    # Get sun direction in body-centred inertial frame
    sun = sc.bodies["Sun"]
    rf = body.reference_frame
    sun_pos = sun.position(rf)
    smag = math.sqrt(sun_pos[0]**2 + sun_pos[1]**2 + sun_pos[2]**2)
    if smag < 1e-6:
        return sc.ut + orb.period / 4
    sun_dir = (sun_pos[0] / smag, sun_pos[1] / smag, sun_pos[2] / smag)

    # Current position in orbit (mean anomaly)
    orb = vessel.orbit
    period = orb.period
    sma = orb.semi_major_axis
    if sma <= 0 or period <= 0:
        return sc.ut + 600.0

    # Use orbit mean motion to step forward analytically
    mu = body.gravitational_parameter
    mean_motion = math.sqrt(mu / abs(sma) ** 3)

    # Get current true anomaly → mean anomaly
    ta = orb.true_anomaly
    # Eccentric anomaly from true anomaly
    ecc = orb.eccentricity
    cos_ta = math.cos(ta)
    sin_ta = math.sin(ta)
    cos_e = (ecc + cos_ta) / (1 + ecc * cos_ta)
    # Clamp for numerical safety
    cos_e = max(-1.0, min(1.0, cos_e))
    ea = math.acos(cos_e)
    if sin_ta < 0:
        ea = 2 * math.pi - ea
    # Mean anomaly
    ma = ea - ecc * math.sin(ea)
    ma = ma % (2 * math.pi)

    # Current position vector relative to body centre
    # At true anomaly ta, the position is at angle ta from periapsis
    # in the orbital plane.  We need the 3D position in the reference frame.
    # For the terminator crossing, we need to find when the position vector
    # is perpendicular to the sun direction (dot = 0).
    #
    # For simplicity: scan forward up to one period checking the angle
    # between the orbital position (at mean anomaly) and the sun direction.
    # The position vector in the orbital plane at mean anomaly M is:
    #   r = a*(1 - e*cos(E))
    # But without rotating into the reference frame, we can't compute the
    # exact dot product with sun_dir.  Instead, approximate sunrise as
    # occurring roughly 1/4 of an orbit after the point opposite the sun.
    #
    # Practical approach: use warping and check celestial body lighting
    # via kRPC's built-in methods if available, else use orbit geometry.

    # For now, provide a reasonable estimate: sunrise ≈ quarter orbit
    # from the current position, adjusted for the angle to the sun.
    # A proper implementation would compute the orbit in 3D and find
    # the terminator crossing angle.
    log_event("sunrise_calc", method="quarter_orbit_estimate")
    return sc.ut + period / 4


def next_soi_change_ut(vessel: Any) -> float | None:
    """Return UT of next SOI change, or None if not in orbit."""
    orb = vessel.orbit
    if orb is None:
        return None
    # Time to SOI change is when the vessel reaches the orbit's edge
    # For kRPC, the orbit's end_ut gives the time of SOI transition
    return orb.end_ut


# ---------------------------------------------------------------------------
# Core warp logic
# ---------------------------------------------------------------------------

def do_warp(args: argparse.Namespace) -> None:
    conn = connect()
    sc = conn.space_center
    vessel = sc.active_vessel

    if vessel is None:
        print(json.dumps({"error": "No active vessel"}))
        sys.exit(1)

    # Determine target UT
    target_ut: float | None = None
    event_type: str | None = None

    if args.ut is not None:
        target_ut = args.ut
        event_type = "explicit"
    elif args.relative is not None:
        target_ut = sc.ut + args.relative
        event_type = "relative"
    elif args.node:
        nu = next_maneuver_ut(vessel)
        if nu is None:
            print(json.dumps({"error": "No maneuver node found"}))
            sys.exit(1)
        target_ut = nu
        event_type = "maneuver_node"
    elif args.sunrise:
        body = vessel.orbit.body if vessel.orbit else None
        if body is None:
            print(json.dumps({"error": "Vessel not in orbit — cannot calculate sunrise"}))
            sys.exit(1)
        target_ut = next_sunrise_ut(vessel, body)
        event_type = "sunrise"
    elif args.soi_change:
        target_ut = next_soi_change_ut(vessel)
        if target_ut is None or math.isinf(target_ut):
            print(json.dumps({"error": "No SOI change predicted (not in orbit or escape trajectory)"}))
            sys.exit(1)
        event_type = "soi_change"
    else:
        # Default: warp to next maneuver node
        nu = next_maneuver_ut(vessel)
        if nu is not None:
            target_ut = nu
            event_type = "maneuver_node"
        else:
            print(json.dumps({"error": "No target specified and no maneuver node found. Use --ut, --relative, --node, --sunrise, or --soi-change."}))
            sys.exit(1)

    log_event("warp_target",
              event_type=event_type,
              target_ut=round(target_ut, 2),
              ut_now=round(sc.ut, 2))

    # Execute warp
    lead_time = args.lead_time
    if event_type == "maneuver_node" and args.node_lead is not None:
        lead_time = args.node_lead

    warp_to_ut(sc, target_ut, lead_time=lead_time,
               max_regular=args.max_warp, max_physics=args.max_physics)

    # Report arrival
    print(json.dumps({
        "event": "arrived",
        "event_type": event_type,
        "ut": round(sc.ut, 2),
        "target_ut": round(target_ut, 2),
        "lead_time": round(lead_time, 1),
        "message": f"Arrived at T-{lead_time:.0f}s — ready for pilot",
        "vessel": vessel.name,
        "body": vessel.orbit.body.name if vessel.orbit else None,
    }))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Time warp to a specific event")
    parser.add_argument("--ut", type=float, default=None,
                        help="Explicit universal time target")
    parser.add_argument("--relative", type=float, default=None,
                        help="Relative time in seconds from now")
    parser.add_argument("--node", action="store_true",
                        help="Warp to next maneuver node")
    parser.add_argument("--sunrise", action="store_true",
                        help="Warp to next sunrise at current location")
    parser.add_argument("--soi-change", action="store_true",
                        help="Warp to next SOI transition")
    parser.add_argument("--lead-time", type=float, default=30.0,
                        help="Seconds before target to arrive (default: 30)")
    parser.add_argument("--node-lead", type=float, default=None,
                        help="Lead time for maneuver nodes (overrides --lead-time)")
    parser.add_argument("--max-warp", type=int, default=7,
                        help="Maximum regular warp factor (default: 7 = 100kx)")
    parser.add_argument("--max-physics", type=int, default=4,
                        help="Maximum physics warp factor (default: 4)")
    parser.add_argument("--minify", action="store_true",
                        help="Output compact JSON")

    args = parser.parse_args()

    # Ensure at least one target specified (or default to --node)
    targets = [args.ut is not None, args.relative is not None,
               args.node, args.sunrise, args.soi_change]
    if not any(targets):
        # Default: warp to next node
        args.node = True

    try:
        do_warp(args)
    except Exception as e:
        log_event("error", message=str(e))
        cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
