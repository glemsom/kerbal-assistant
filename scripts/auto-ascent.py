#!/usr/bin/env python3
"""Autonomous ascent from surface to orbit via kRPC.

Usage:
    python scripts/auto-ascent.py
    python scripts/auto-ascent.py --target-apo 120000 --target-peri 100000
    python scripts/auto-ascent.py --turn-start 500 --turn-end 40000 --final-pitch 20

Abort: Ctrl+C (disengages autopilot, throttle zero).
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time
import math
from typing import Any

try:
    import krpc
except ImportError:
    print(json.dumps({"error": "krpc not installed. Run: pip install krpc"}))
    sys.exit(1)


# ---------------------------------------------------------------------------
# Global clean-up: ensure we don't leave KSP in a bad state
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
            print(json.dumps({"event": "abort", "message": "Autopilot disengaged, throttle zero"}))
    except Exception:
        pass


signal.signal(signal.SIGINT, lambda *_: (cleanup(), sys.exit(1)))
signal.signal(signal.SIGTERM, lambda *_: (cleanup(), sys.exit(1)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def connect() -> krpc.Client:
    """Connect to kRPC server at 127.0.0.1:50000.

    Exits with JSON error message on failure (ConnectionRefusedError,
    TimeoutError, or generic Exception). Stores connection in global
    _conn for cleanup().
    """
    global _conn
    try:
        _conn = krpc.connect(name="kerbal-assistant-ascent", address="127.0.0.1", rpc_port=50000)
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


_last_stage_time = 0.0
_max_thrust_seen = 0.0
_srb_boosters = 0       # number of SRB boosters (from --srb-boosters flag)
_liftoff_time = 0.0     # time of first stage (for timed SRB fallback)


def should_stage(vessel: Any) -> bool:
    """Return True if we should activate next stage.

    Stages when:
      1) Total thrust is zero (standard staging — sustainer cutoff)
      2) SRB burnout detected: thrust drops by >50% from peak AND
         SolidFuel is depleted but other fuel remains (SRB jettison)
    Also stages when --srb-boosters N is set and N seconds have
    elapsed since liftoff (timed SRB jettison fallback).
    """
    global _last_stage_time, _max_thrust_seen, _srb_boosters, _liftoff_time
    now = time.time()
    # Cooldown: wait 1s after last stage to avoid double-staging
    # during engine ignition transitions
    if now - _last_stage_time < 1.0:
        return False

    thrust = vessel.available_thrust
    _max_thrust_seen = max(_max_thrust_seen, thrust)

    # --- Condition 1: zero thrust (standard staging) ---
    if thrust < 1.0:
        if vessel.control.current_stage <= 0:
            return False
        _max_thrust_seen = 0   # reset baseline after staging
        _last_stage_time = now
        return True

    # --- Condition 2: SRB burnout (thrust drop + SolidFuel depleted) ---
    if _max_thrust_seen > 10.0:
        thrust_ratio = thrust / _max_thrust_seen
        if thrust_ratio < 0.5:
            # Check if SolidFuel is depleted while other fuel remains
            resources = vessel.resources
            solid = resources.amount("SolidFuel")
            liquid = resources.amount("LiquidFuel")
            if solid < 0.1 and liquid > 1.0:
                if vessel.control.current_stage <= 0:
                    return False
                _last_stage_time = now
                _max_thrust_seen = 0  # reset baseline after SRB jettison
                log_event("srb_jettison",
                          thrust_ratio=round(thrust_ratio, 3),
                          max_thrust=round(_max_thrust_seen, 1),
                          current_thrust=round(thrust, 1))
                return True

    # --- Condition 3: timed fallback for SRB jettison ---
    if _srb_boosters > 0 and _liftoff_time > 0:
        if now - _liftoff_time > _srb_boosters:
            if vessel.control.current_stage > 0:
                _last_stage_time = now
                _max_thrust_seen = 0  # reset baseline after timed jettison
                log_event("srb_timed_jettison",
                          elapsed=round(now - _liftoff_time, 1),
                          srb_boosters=_srb_boosters)
                return True

    # No more stages left (prevents staging into empty)
    if vessel.control.current_stage <= 0:
        return False
    return False

def log_event(event: str, **kwargs: Any) -> None:
    msg = {"event": event, **kwargs}
    print(json.dumps(msg))


# ---------------------------------------------------------------------------
# Core ascent logic
# ---------------------------------------------------------------------------

def auto_ascent(args: argparse.Namespace) -> None:
    """Execute full ascent to orbit.

    Phases:
      1. Liftoff — ignite engines, verify positive climb rate
      2. Gravity turn — interpolate pitch from vertical to --final-pitch,
         throttle back on high Q or G-force
      3. Coast — cut throttle, warp to near apoapsis
      4. Circularization — vis-viva dV calc, maneuver node, execute burn

    All phases emit JSON events via log_event(). Clean abort on Ctrl+C.
    """
    conn = connect()
    sc = conn.space_center
    vessel = sc.active_vessel

    if vessel is None:
        print(json.dumps({"error": "No active vessel"}))
        sys.exit(1)

    body = vessel.orbit.body
    has_atmo = body.has_atmosphere
    body_name = body.name

    log_event("ascent_start",
              vessel=vessel.name,
              body=body_name,
              has_atmosphere=has_atmo,
              target_apo=args.target_apo,
              target_peri=args.target_peri)

    global _srb_boosters, _liftoff_time
    _srb_boosters = args.srb_boosters

    # -- Pre-launch checks ---------------------------------------------------
    situation = str(vessel.situation).split(".")[-1]
    if situation not in ("pre_launch", "landed", "flying"):
        log_event("error", message=f"Unexpected vessel situation: {situation}")
        sys.exit(1)

    # AutoPilot setup
    ap = vessel.auto_pilot
    ap.engage()
    ap.target_pitch_and_heading(90, args.heading)  # straight up

    # -- Liftoff -------------------------------------------------------------
    vessel.control.throttle = 1.0
    time.sleep(0.5)

    # Stage once to ignite engines
    vessel.control.activate_next_stage()
    log_event("liftoff", stage=1)
    _liftoff_time = time.time()

    # Wait for positive TWR / gaining altitude
    start_time = time.time()
    while True:
        if time.time() - start_time > 10:
            log_event("error", message="Failed to lift off — check staging and TWR")
            sys.exit(1)
        flight = vessel.flight(body.reference_frame)
        if flight.mean_altitude > 1.0:
            break
        time.sleep(0.1)

    # -- Gravity turn ---------------------------------------------------------
    turn_start_alt = args.turn_start
    turn_end_alt = args.turn_end
    final_pitch = args.final_pitch  # degrees from horizontal (positive = above horizon)

    # Stream altitude for responsive control
    alt_stream = conn.add_stream(getattr, vessel.flight(body.reference_frame), "mean_altitude")
    vel_stream = conn.add_stream(getattr, vessel.flight(body.reference_frame), "speed")

    max_q = 0.0
    max_g = 0.0
    stage_num = 1

    # Main ascent loop
    ap.target_pitch_and_heading(90, args.heading)  # keep pointing up initially
    while True:
        altitude = alt_stream()
        speed = vel_stream()
        flight = vessel.flight(body.reference_frame)
        g_force = flight.g_force
        dyn_pressure = flight.dynamic_pressure

        max_g = max(max_g, g_force)
        max_q = max(max_q, dyn_pressure)

        # Check for staging
        if should_stage(vessel):
            try:
                vessel.control.activate_next_stage()
                stage_num += 1
                log_event("stage", stage=stage_num, altitude=round(altitude, 1))
                time.sleep(0.3)
            except Exception:
                # No more stages — can't stage further, abort
                log_event("error", message="Staging failed — aborting ascent")
                sys.exit(1)

        # Dynamic throttle: limit by dynamic pressure and G-force
        target_throttle = 1.0
        if has_atmo:
            if dyn_pressure > args.max_q:
                target_throttle = max(0.3, 1.0 - (dyn_pressure - args.max_q) / args.max_q * 0.5)
            if g_force > 5.0:
                target_throttle = max(0.2, target_throttle * 0.8)
                log_event("g_limit", g_force=round(g_force, 2), throttle=round(target_throttle, 3))
        vessel.control.throttle = target_throttle

        # Pitch control — interpolate between vertical and final pitch
        if altitude <= turn_start_alt:
            pitch = 90.0  # straight up
        elif altitude >= turn_end_alt:
            pitch = final_pitch
        else:
            fraction = (altitude - turn_start_alt) / (turn_end_alt - turn_start_alt)
            pitch = 90.0 + (final_pitch - 90.0) * fraction

        # Follow prograde during gravity turn
        ap.target_pitch_and_heading(pitch, args.heading)

        # Check if we've reached target apoapsis
        orbit = vessel.orbit
        apoapsis = orbit.apoapsis_altitude if orbit else 0.0

        if apoapsis >= args.target_apo * 0.98:
            log_event("coast_start",
                      apoapsis=round(apoapsis, 1),
                      altitude=round(altitude, 1),
                      speed=round(speed, 1))
            break

        # Escape from atmosphere: if no atmosphere and apoapsis high enough, cut
        if not has_atmo and apoapsis > args.target_apo * 0.95:
            log_event("vacuum_coast",
                      apoapsis=round(apoapsis, 1),
                      speed=round(speed, 1))
            break



        time.sleep(0.05)

    # -- Cut throttle, coast to apoapsis --------------------------------------
    vessel.control.throttle = 0.0
    log_event("coasting", apoapsis=round(vessel.orbit.apoapsis_altitude, 1))

    # Re-check apoapsis: atmospheric drag may have lowered it
    if has_atmo and vessel.orbit.apoapsis_altitude < args.target_apo * 0.95:
        log_event("re_engage",
                  apoapsis=round(vessel.orbit.apoapsis_altitude, 1),
                  message="Apoapsis decayed — burning to restore")
        vessel.control.throttle = 1.0
        while vessel.orbit.apoapsis_altitude < args.target_apo * 0.98:
            time.sleep(0.05)
        vessel.control.throttle = 0.0
        log_event("coast_resume",
                  apoapsis=round(vessel.orbit.apoapsis_altitude, 1))

    # Warp to apoapsis if far away
    time_to_apo = vessel.orbit.time_to_apoapsis
    if time_to_apo > 30:
        warp_start = max(time_to_apo - 30, 1)
        sc.warp_to(sc.ut + warp_start)
        log_event("warp", warp_duration=round(warp_start, 1))

    # Wait until T-30s to apoapsis
    while True:
        if vessel.orbit.time_to_apoapsis <= 30:
            break
        time.sleep(0.1)

    # -- Circularization burn -------------------------------------------------
    log_event("circ_burn_start",
              apoapsis=round(vessel.orbit.apoapsis_altitude, 1),
              periapsis=round(vessel.orbit.periapsis_altitude, 1))

    # Orient to prograde for circularization
    # NOTE: target_direction is a PROPERTY (tuple), not a method in kRPC 0.5.x
    ap.reference_frame = vessel.orbital_reference_frame
    flight = vessel.flight(vessel.orbital_reference_frame)
    ap.target_direction = flight.prograde
    ap.wait()

    # Calculate required dV for circularization
    # Use vis-viva to get actual speed at apoapsis (not current position)
    mu = body.gravitational_parameter
    r = vessel.orbit.apoapsis  # distance from body center at apoapsis
    a = vessel.orbit.semi_major_axis
    v_circular = (mu / r) ** 0.5
    v_apo = (2 * mu / r - mu / a) ** 0.5  # vis-viva: speed at apoapsis
    burn_dv = v_circular - v_apo

    if burn_dv < 0:
        # We're already going fast enough — raise periapsis
        burn_dv = 50.0  # small burn

    log_event("circ_info",
              v_circular=round(v_circular, 1),
              v_apo=round(v_apo, 1),
              burn_dv=round(burn_dv, 1))

    # Check if we have enough fuel for circularization
    # Tsiolkovsky: dV = Isp * g0 * ln(m0 / m1)
    remaining_fuel_kg = vessel.mass - vessel.dry_mass
    isp_est = 345  # vac Isp estimate
    g0 = 9.81
    max_dv = 0.0
    if remaining_fuel_kg > 0 and vessel.dry_mass > 0:
        max_dv = isp_est * g0 * math.log(vessel.mass / vessel.dry_mass)
    
    if 0 < max_dv < burn_dv * 0.8:
        log_event("warn", message="Insufficient fuel for full circularization",
                  max_dv=round(max_dv, 1), needed=round(burn_dv, 1),
                  fuel_kg=round(remaining_fuel_kg, 1))
        burn_dv = min(burn_dv, max_dv * 0.9)  # use 90% of what we have

    # Create node and execute — guard against negative time_to_apoapsis
    t_apo = vessel.orbit.time_to_apoapsis
    if t_apo < 0:
        log_event("warn", message="Past apoapsis — burning immediately")
        node = vessel.control.add_node(sc.ut + 10, prograde=burn_dv)
    else:
        node = vessel.control.add_node(sc.ut + t_apo, prograde=burn_dv)
    frame = node.orbital_reference_frame
    ap.reference_frame = frame
    ap.target_direction = node.burn_vector(frame)
    ap.wait()

    # Calculate burn time, start at full throttle, taper near end
    mass = vessel.mass
    isp = 345  # Terrier vac Isp (estimate)
    g0 = 9.81
    # F = Isp * g0 * mass_flow_rate => mass_flow = F / (Isp * g0)
    # Burn time = (1 - exp(-dV / (Isp*g0))) * initial_mass / mass_flow_rate...
    # Simpler: dv = Isp*g0*ln(m0/m1) => m1 = m0/exp(dV/(Isp*g0))
    # fuel_kg = m0 - m1
    m0 = mass
    m1 = m0 / (2.71828 ** (burn_dv / (isp * g0)))
    fuel_kg = m0 - m1
    thrust = vessel.max_thrust
    if thrust > 0:
        mass_flow = thrust / (isp * g0)
        burn_time = fuel_kg / mass_flow if mass_flow > 0 else 30
    else:
        burn_time = 30
    burn_time = min(burn_time, 120)  # cap at 2 minutes
    log_event("burn_info", burn_dv=round(burn_dv, 1), burn_time=round(burn_time, 1))

    # Execute burn: full throttle but check for fuel depletion
    vessel.control.throttle = 1.0
    burn_start_time = time.time()
    last_dv = node.remaining_delta_v
    stale_counter = 0
    while node.remaining_delta_v > 0.5:
        # Detect fuel depletion: thrust drops to near zero mid-burn
        if vessel.available_thrust < 1.0 and node.remaining_delta_v > 5:
            log_event("warn", message="Thrust lost during circularization — possible fuel depletion",
                      remaining_dv=round(node.remaining_delta_v, 1))
            break
        # Detect stall: remaining_dv not decreasing
        current_dv = node.remaining_delta_v
        if abs(current_dv - last_dv) < 0.01:
            stale_counter += 1
        else:
            stale_counter = 0
        last_dv = current_dv
        if stale_counter > 50:  # ~2.5s with no change
            log_event("warn", message="Burn stalled — no dV decrease",
                      remaining_dv=round(current_dv, 1))
            break
        # Throttle down near end for precision
        if current_dv < 10 and node.remaining_delta_v < 10:
            vessel.control.throttle = 0.2
        time.sleep(0.05)
    
    elapsed = time.time() - burn_start_time
    log_event("burn_complete", elapsed=round(elapsed, 1), final_thrust=round(vessel.available_thrust, 0))

    vessel.control.throttle = 0.0
    node.remove()

    # -- Report ---------------------------------------------------------------
    final_orbit = vessel.orbit
    log_event("orbit_achieved",
              body=final_orbit.body.name,
              apoapsis=round(final_orbit.apoapsis_altitude, 1),
              periapsis=round(final_orbit.periapsis_altitude, 1),
              inclination=round(final_orbit.inclination, 6),
              eccentricity=round(final_orbit.eccentricity, 6),
              max_g=round(max_g, 3),
              max_q=round(max_q, 1),
              stages=stage_num,
              fuel_mass=round(vessel.mass - vessel.dry_mass, 3))

    ap.disengage()
    vessel.control.sas = True  # leave SAS on for stability


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous launch from surface to orbit")
    parser.add_argument("--target-apo", type=float, default=100000,
                        help="Target apoapsis altitude in meters (default: 100000)")
    parser.add_argument("--target-peri", type=float, default=None,
                        help="Target periapsis altitude in meters (default: target_apo - 20000)")
    parser.add_argument("--turn-start", type=float, default=250,
                        help="Altitude to start gravity turn in meters (default: 250)")
    parser.add_argument("--turn-end", type=float, default=40000,
                        help="Altitude to end gravity turn in meters (default: 40000)")
    parser.add_argument("--final-pitch", type=float, default=5,
                        help="Final pitch angle at turn end in degrees from "
                             "horizontal (default: 5, positive = above horizon)")
    parser.add_argument("--max-q", type=float, default=15000,
                        help="Max dynamic pressure in Pa before throttling down (default: 15000)")
    parser.add_argument("--heading", type=float, default=90,
                        help="Launch heading in degrees (default: 90 = East)")
    parser.add_argument("--srb-boosters", type=int, default=0,
                        help="Number of SRB boosters for timed burnout staging (default: 0)")


    args = parser.parse_args()

    if args.target_peri is None:
        args.target_peri = args.target_apo - 20000

    try:
        auto_ascent(args)
    except Exception as e:
        log_event("error", message=str(e))
        cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
