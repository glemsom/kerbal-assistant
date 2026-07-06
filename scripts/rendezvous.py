#!/usr/bin/env python3
"""Orbital rendezvous sequence — phasing burn, Hohmann intercept, coast, velocity match.

Usage:
    python scripts/rendezvous.py
    python scripts/rendezvous.py --target "Station Alpha"
    python scripts/rendezvous.py --target "Station Alpha" --approach 500   (intercept distance)
    python scripts/rendezvous.py --dry-run   (compute only, no burns)

Outputs JSON events to stdout. Abort: Ctrl+C (disengages autopilot, throttle zero).

Strategy:
  1. Calculate phase angle difference between active vessel and target
  2. Compute optimal phasing burn (prograde to raise orbit, target catches up;
     retrograde to lower orbit, you catch up)
  3. Create and execute phasing maneuver node (via add_node / burn pattern from #6)
  4. Coast (warp) to the phasing orbit's apoapsis/periapsis
  5. Execute Hohmann intercept burn at correct phase
  6. Coast to closest approach
  7. Match velocity with target (< 1 m/s relative)
  8. Report intercept distance, time, remaining propellant
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
# Global clean-up
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
        sc = _conn.space_center
        vessel = sc.active_vessel
        if vessel:
            vessel.control.throttle = 0.0
            vessel.auto_pilot.disengage()
            vessel.control.sas = False
            if vessel.control.rcs:
                vessel.control.rcs = False
            print(json.dumps({"event": "abort", "message": "Autopilot disengaged, throttle zero"}))
    except Exception:
        pass


signal.signal(signal.SIGINT, lambda *_: (cleanup(), sys.exit(1)))
signal.signal(signal.SIGTERM, lambda *_: (cleanup(), sys.exit(1)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def connect() -> krpc.Client:
    global _conn
    try:
        _conn = krpc.connect(name="kerbal-assistant-rendezvous", address="127.0.0.1", rpc_port=50000)
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


def vessel_by_name(conn: krpc.Client, name: str):
    """Find a vessel by name (partial match preferred, exact fallback)."""
    sc = conn.space_center
    # Try exact match first
    for v in sc.vessels:
        if v.name == name:
            return v
    # Partial match
    for v in sc.vessels:
        if name.lower() in v.name.lower():
            return v
    return None


def execute_node(
    conn: krpc.Client, vessel: Any, node: Any,
    throttle: float = 0.3, precision: float = 0.5
) -> None:
    """Execute a maneuver node using AutoPilot and fixed throttle.

    Pattern from krpc-reference.md / auto-ascent.py.
    """
    sc = conn.space_center
    ap = vessel.auto_pilot
    ap.engage()
    frame = node.orbital_reference_frame
    ap.target_direction(node.burn_vector(frame), frame)
    ap.wait()

    while node.remaining_delta_v > precision:
        vessel.control.throttle = throttle
        time.sleep(0.05)

    vessel.control.throttle = 0.0
    node.remove()
    log_event("burn_complete", event="burn_done")


def warp_to(conn: krpc.Client, target_ut: float, lead_time: float = 30.0) -> None:
    """Warp to target_ut, stopping lead_time seconds early.

    Uses physics warp (rails_warp_factor) for short coasts < 1 min,
    and non-physics warp_to for longer coasts.
    """
    sc = conn.space_center
    now = sc.ut
    remaining = target_ut - now
    if remaining <= 0:
        return

    warp_until = target_ut - lead_time

    if remaining < 60:
        # Use physics warp for short distances
        factor = 0
        if remaining < 5:
            factor = 0
        elif remaining < 15:
            factor = 2
        elif remaining < 60:
            factor = 4
        sc.rails_warp_factor = factor
        while sc.ut < warp_until:
            time.sleep(0.1)
        sc.rails_warp_factor = 0
    else:
        # Non-physics warp
        sc.warp_to(warp_until)

    log_event("warp_complete", target_ut=round(target_ut, 1), ut=round(sc.ut, 1))


# ---------------------------------------------------------------------------
# Orbital mechanics
# ---------------------------------------------------------------------------

def compute_phase_angle(
    vessel_pos: tuple, target_pos: tuple,
    reference_up: tuple = (0, 0, 1)
) -> float:
    """Compute signed phase angle (degrees) from vessel to target.

    Positive = target ahead in orbit. Negative = target behind.
    Uses cross product with reference_up to determine sign.
    """
    vx, vy, vz = vessel_pos
    tx, ty, tz = target_pos

    dot = vx * tx + vy * ty + vz * tz
    n1 = math.sqrt(vx * vx + vy * vy + vz * vz)
    n2 = math.sqrt(tx * tx + ty * ty + tz * tz)
    norm = n1 * n2
    if norm < 1e-12:
        return 0.0

    cos_angle = max(-1.0, min(1.0, dot / norm))
    phase_rad = math.acos(cos_angle)
    phase_deg = math.degrees(phase_rad)

    # Sign via cross product (assumes orbital plane ≈ XY with Z up)
    cross_z = vx * ty - vy * tx
    if cross_z < 0:
        phase_deg = -phase_deg

    return phase_deg


def hohmann_transfer_dv(
    mu: float, r1: float, r2: float
) -> tuple[float, float]:
    """Compute Hohmann transfer dV for burns at periapsis and apoapsis.

    Returns (dv1, dv2) where dv1 is the first burn (at r1) and dv2 is the
    circularization burn (at r2).  Assumes coplanar circular orbits.

    r1, r2 are distances from body center.
    """
    a_transfer = (r1 + r2) / 2.0
    v1_circular = math.sqrt(mu / r1)
    v2_circular = math.sqrt(mu / r2)
    v_transfer_at_r1 = math.sqrt(2 * mu / r1 - mu / a_transfer)
    v_transfer_at_r2 = math.sqrt(2 * mu / r2 - mu / a_transfer)

    dv1 = v_transfer_at_r1 - v1_circular
    dv2 = v2_circular - v_transfer_at_r2

    return dv1, dv2


def phase_angle_for_hohmann(r_vessel: float, r_target: float) -> float:
    """Optimal phase angle (degrees) for Hohmann transfer between circular orbits.

    Formula: phase = 180 * (1 - sqrt((r1/r2)^3))
    r_vessel = current orbital radius, r_target = target orbital radius.
    Positive means target needs to be ahead.
    """
    r1 = min(r_vessel, r_target)
    r2 = max(r_vessel, r_target)
    if r1 <= 0 or r2 <= 0:
        return 0.0
    phase = 180.0 * (1.0 - math.sqrt((r1 / r2) ** 3))
    # If target is in a lower orbit, we lead; if higher, they lead
    if r_target < r_vessel:
        phase = 360.0 - phase
    return phase


def compute_closest_approach_distance(
    vessel_pos: tuple, vessel_vel: tuple,
    target_pos: tuple, target_vel: tuple,
    dt: float, steps: int = 100
) -> tuple[float, float, tuple, tuple]:
    """Compute closest approach within time horizon dt (seconds).

    Returns (min_distance, time_to_closest, relative_velocity, relative_position).
    Brute-force search over steps intervals.
    """
    min_dist = float("inf")
    min_t = 0.0
    rel_vel: tuple = (0, 0, 0)
    rel_pos: tuple = (0, 0, 0)

    for i in range(steps + 1):
        t = dt * i / steps
        rv = (vessel_pos[0] + vessel_vel[0] * t,
              vessel_pos[1] + vessel_vel[1] * t,
              vessel_pos[2] + vessel_vel[2] * t)
        rt = (target_pos[0] + target_vel[0] * t,
              target_pos[1] + target_vel[1] * t,
              target_pos[2] + target_vel[2] * t)
        dx = rv[0] - rt[0]
        dy = rv[1] - rt[1]
        dz = rv[2] - rt[2]
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        if dist < min_dist:
            min_dist = dist
            min_t = t
            rel_vel = (vessel_vel[0] - target_vel[0],
                       vessel_vel[1] - target_vel[1],
                       vessel_vel[2] - target_vel[2])
            rel_pos = (dx, dy, dz)

    rel_speed = math.sqrt(rel_vel[0] ** 2 + rel_vel[1] ** 2 + rel_vel[2] ** 2)
    return min_dist, min_t, rel_vel, rel_pos


# ---------------------------------------------------------------------------
# Rendezvous phases
# ---------------------------------------------------------------------------

def phase_1_phasing_burn(
    conn: krpc.Client, vessel: Any, target: Any, dry_run: bool = False
) -> dict:
    """Calculate and execute phasing burn to match orbital periods.

    Determines whether vessel is ahead or behind target and burns
    prograde/retrograde accordingly.

    Returns phase info dict.
    """
    sc = conn.space_center
    body = vessel.orbit.body
    mu = body.gravitational_parameter

    v_orbit = vessel.orbit
    t_orbit = target.orbit

    r_v = v_orbit.apoapsis  # use apoapsis as reference radius
    r_t = t_orbit.apoapsis

    # Get positions in body-centered frame
    body_frame = body.reference_frame
    v_pos = v_orbit.position_at(sc.ut, body_frame)
    t_pos = t_orbit.position_at(sc.ut, body_frame)
    v_vel = v_orbit.velocity_at(sc.ut, body_frame)
    t_vel = t_orbit.velocity_at(sc.ut, body_frame)

    # Compute current phase angle
    phase_current = compute_phase_angle(v_pos, t_pos)
    phase_optimal = phase_angle_for_hohmann(r_v, r_t)

    # Determine direction: if vessel is ahead (phase > 0), we need to slow down
    # (retrograde burn, raise period) so target catches up.
    # If vessel is behind (phase < 0), we need to speed up
    # (prograde burn, lower period) so we catch up.
    if phase_current > 0:
        # Vessel is ahead — burn retrograde to raise orbit, increase period
        direction = "retrograde" 
        phase_error = abs(phase_current)  # how far ahead
        # dV proportional to phase error — rough estimate
        # For small corrections: dV ≈ phase_error_rad / (3π) * v_orbital
        v_orbital = math.sqrt(mu / r_v)
        burn_dv = (phase_error / 180.0 * math.pi) / (3 * math.pi) * v_orbital
        burn_dv = max(burn_dv, 2.0)  # minimum 2 m/s
        prograde = -burn_dv  # retrograde
    else:
        # Vessel is behind — burn prograde to lower orbit, decrease period
        direction = "prograde"
        phase_error = abs(phase_current)
        v_orbital = math.sqrt(mu / r_v)
        burn_dv = (phase_error / 180.0 * math.pi) / (3 * math.pi) * v_orbital
        burn_dv = max(burn_dv, 2.0)
        prograde = burn_dv

    info = {
        "phase_current_deg": round(phase_current, 2),
        "phase_optimal_deg": round(phase_optimal, 2),
        "direction": direction,
        "burn_dv": round(burn_dv, 2),
        "vessel_ahead": phase_current > 0,
    }
    log_event("phasing_info", **info)

    if dry_run:
        log_event("dry_run", message="Skipping phasing burn (dry-run)")
        return info

    if burn_dv < 1.0:
        log_event("phasing_skip", message="Phase error negligible, skipping phasing burn")
        return info

    # Create and execute node
    dt = 10.0  # burn now-ish
    node = vessel.control.add_node(sc.ut + dt, prograde=prograde)
    execute_node(conn, vessel, node)

    info["burn_executed"] = True
    info["burn_dv_actual"] = round(abs(prograde), 2)
    return info


def phase_2_coast_and_intercept(
    conn: krpc.Client, vessel: Any, target: Any,
    dry_run: bool = False
) -> dict:
    """Coast to the intercept point and execute Hohmann intercept burn.

    After phasing, we wait for the right moment and then do a Hohmann
    transfer burn to intercept the target at closest approach.
    """
    sc = conn.space_center
    body = vessel.orbit.body
    mu = body.gravitational_parameter

    v_orbit = vessel.orbit
    t_orbit = target.orbit
    body_frame = body.reference_frame

    # Get current orbital state
    v_pos = v_orbit.position_at(sc.ut, body_frame)
    t_pos = t_orbit.position_at(sc.ut, body_frame)
    v_vel = v_orbit.velocity_at(sc.ut, body_frame)
    t_vel = t_orbit.velocity_at(sc.ut, body_frame)

    # Compute intercept: we'll do a Hohmann transfer from our orbit to target's
    r_v = v_orbit.apoapsis  # or current radius
    r_t = t_orbit.apoapsis

    # If orbits are similar, do a small radial burn to close distance
    diff = abs(r_v - r_t)
    if diff < 5000:
        log_event("intercept_near", message="Orbits already close — using direct approach")
        # Just do a small prograde/retrograde burn to match position
        dv1 = 5.0
        if r_v < r_t:
            prograde = dv1
        else:
            prograde = -dv1
    else:
        dv1, dv2 = hohmann_transfer_dv(mu, r_v, r_t)
        if r_v < r_t:
            prograde = dv1
        else:
            prograde = -dv1  # we're higher, burn retrograde to intercept lower

    # Better approach: use relative velocity at closest approach
    # Compute time to closest approach over one orbital period
    period_min = min(v_orbit.period, t_orbit.period)
    min_dist, t_ca, rel_vel, rel_pos = compute_closest_approach_distance(
        v_pos, v_vel, t_pos, t_vel, dt=period_min, steps=500
    )

    log_event("closest_approach",
              distance=round(min_dist, 1),
              time_to_ca=round(t_ca, 1),
              relative_speed=round(math.sqrt(rel_vel[0]**2 + rel_vel[1]**2 + rel_vel[2]**2), 2))

    # If we're already close enough, skip intercept burn
    if min_dist < 2000:
        log_event("intercept_skip", message="Already close to target — skipping intercept burn")
        return {"intercept_distance": min_dist, "time_to_ca": t_ca}

    # Coast to near closest approach
    if t_ca > 10:
        log_event("coasting_to_intercept", duration=round(t_ca, 1))
        if not dry_run:
            warp_to(conn, sc.ut + t_ca, lead_time=30.0)

    return {"intercept_distance": min_dist, "time_to_ca": t_ca}


def phase_3_velocity_match(
    conn: krpc.Client, vessel: Any, target: Any,
    dry_run: bool = False
) -> dict:
    """Match velocity with target at closest approach.

    Uses AutoPilot to point retrograde of relative velocity and burn
    until relative speed < 1 m/s.
    """
    sc = conn.space_center

    body = vessel.orbit.body
    body_frame = body.reference_frame

    # Use the target and vessel orbital reference frames for relative velocity
    # kRPC provides target-relative velocity via flight() in target reference frame
    target_ref = target.orbital_reference_frame
    flight = vessel.flight(target_ref)

    # Target speed in target frame = relative velocity
    rel_speed = flight.speed
    rel_vel = flight.velocity  # (x, y, z) in target frame

    log_event("velocity_match_start",
              relative_speed=round(rel_speed, 2),
              relative_velocity=[round(v, 2) for v in rel_vel])

    if dry_run:
        log_event("dry_run", message="Skipping velocity match (dry-run)")
        return {"final_relative_speed": rel_speed}

    if rel_speed < 1.0:
        log_event("velocity_match_done",
                  message="Already matched within 1 m/s",
                  relative_speed=round(rel_speed, 2))
        return {"final_relative_speed": rel_speed}

    # Point retrograde of relative velocity
    ap = vessel.auto_pilot
    ap.engage()
    retro_dir = flight.retrograde  # in target_ref
    ap.target_direction(retro_dir, target_ref)
    ap.wait()

    # Burn at increasing throttle to avoid overshoot
    vessel.control.throttle = 0.1

    while rel_speed > 0.5:
        flight = vessel.flight(target_ref)
        rel_speed = flight.speed

        # Adaptive throttle: full burn far away, feather near
        if rel_speed > 50:
            vessel.control.throttle = 0.5
        elif rel_speed > 10:
            vessel.control.throttle = 0.3
        elif rel_speed > 3:
            vessel.control.throttle = 0.15
        else:
            vessel.control.throttle = 0.05

        time.sleep(0.1)

    vessel.control.throttle = 0.0
    log_event("velocity_match_done",
              relative_speed=round(rel_speed, 2))

    return {"final_relative_speed": rel_speed}


# ---------------------------------------------------------------------------
# Main rendezvous flow
# ---------------------------------------------------------------------------

def rendezvous(args: argparse.Namespace) -> None:
    conn = connect()
    sc = conn.space_center

    # Resolve target vessel
    if args.target:
        target = vessel_by_name(conn, args.target)
        if target is None:
            log_event("error", message=f"Target vessel '{args.target}' not found")
            sys.exit(1)
    else:
        target = sc.target_vessel
        if target is None:
            log_event("error", message="No target vessel set in-game. Use --target or set target in KSP.")
            sys.exit(1)

    vessel = sc.active_vessel
    if vessel is None:
        log_event("error", message="No active vessel")
        sys.exit(1)

    log_event("rendezvous_start",
              vessel=vessel.name,
              target=target.name,
              vessel_situation=str(vessel.situation).split(".")[-1],
              target_situation=str(target.situation).split(".")[-1],
              dry_run=args.dry_run)

    # Check both are in orbit
    if not vessel.orbit or not target.orbit:
        log_event("error", message="Both vessels must be in orbit for rendezvous")
        sys.exit(1)

    # Ensure we're in the same SOI
    if vessel.orbit.body.name != target.orbit.body.name:
        log_event("error",
                  message=f"Cannot rendezvous — different SOIs: "
                          f"{vessel.orbit.body.name} vs {target.orbit.body.name}")
        sys.exit(1)

    # Phase 1: Phasing burn
    log_event("phase", phase=1, name="phasing_burn")
    phasing_info = phase_1_phasing_burn(conn, vessel, target, dry_run=args.dry_run)

    # Phase 2: Coast and intercept burn
    log_event("phase", phase=2, name="coast_intercept")
    intercept_info = phase_2_coast_and_intercept(conn, vessel, target, dry_run=args.dry_run)

    # Phase 3: Velocity match
    log_event("phase", phase=3, name="velocity_match")
    match_info = phase_3_velocity_match(conn, vessel, target, dry_run=args.dry_run)

    # Final report
    fuel_mass = round(vessel.mass - vessel.dry_mass, 3)
    report = {
        "vessel": vessel.name,
        "target": target.name,
        "phasing": phasing_info,
        "intercept": intercept_info,
        "velocity_match": match_info,
        "fuel_remaining": fuel_mass,
    }
    log_event("rendezvous_complete", **report)

    # Disengage autopilot but leave SAS on
    vessel.auto_pilot.disengage()
    vessel.control.sas = True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Orbital rendezvous sequence")
    parser.add_argument("--target", "-t", help="Target vessel name (default: targeted vessel in-game)")
    parser.add_argument("--approach", type=float, default=500,
                        help="Desired intercept distance in meters (default: 500)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute only, do not execute burns")
    args = parser.parse_args()

    try:
        rendezvous(args)
    except Exception as e:
        log_event("error", message=str(e))
        cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
