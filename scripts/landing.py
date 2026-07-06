#!/usr/bin/env python3
"""Full landing sequence — deorbit burn, powered descent, touchdown.

Detects atmosphere, selects descent profile, executes autonomously.

Usage:
    python scripts/landing.py                              (active vessel, current body)
    python scripts/landing.py --lat -0.05 --lon -74.56     (target lat/lon near KSC)
    python scripts/landing.py --body Mun                   (land on Mun)
    python scripts/landing.py --body Duna --hybrid          (force hybrid Duna profile)

Profiles:
    - Airless: suicide burn to zero velocity at surface
    - Atmospheric: deorbit burn → aerobrake → parachute → soft touchdown
    - Hybrid (Duna): aerobrake → parachute → terminal powered landing

Abort: Ctrl+C (disengages autopilot, throttle zero, SAS stays).
Outputs JSON events to stdout. Pi can read and relay updates.
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
# Constants
# ---------------------------------------------------------------------------
G0 = 9.80665  # standard gravity (m/s^2)
KSC_LAT = -0.05
KSC_LON = -74.56

# Parachute deployment altitudes per body (meters above surface)
PARACHUTE_ALT: dict[str, dict[str, float]] = {
    "Kerbin": {"drogue": 5000, "main": 500},
    "Duna": {"drogue": 5000, "main": 2500},
    "Laythe": {"drogue": 5000, "main": 1000},
    "Eve": {"drogue": 25000, "main": 500},  # Eve needs rockets primarily
}

# Atmospheric entry Pe targets
ENTRY_PE: dict[str, float] = {
    "Kerbin": 35000,
    "Duna": 12000,
    "Laythe": 30000,
    "Eve": 60000,
}

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
            # Keep SAS on for passive stability
            vessel.control.sas = True
            print(json.dumps({"event": "abort",
                              "message": "Autopilot disengaged, throttle zero, SAS on"}))
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
        _conn = krpc.connect(name="kerbal-assistant-landing",
                             address="127.0.0.1", rpc_port=50000)
    except ConnectionRefusedError:
        print(json.dumps({"error": "KSP not running or kRPC not responding"}))
        sys.exit(1)
    except TimeoutError:
        print(json.dumps({"error": "kRPC connection timed out"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"kRPC connection failed: {e}"}))
        sys.exit(1)
    return _conn


def log_event(event: str, **kwargs: Any) -> None:
    msg: dict[str, Any] = {"event": event}
    msg.update(kwargs)
    print(json.dumps(msg))


def twr_at_body(thrust_n: float, mass_kg: float, g_local: float) -> float:
    """Thrust-to-weight ratio."""
    if mass_kg <= 0:
        return 0.0
    return thrust_n / (mass_kg * g_local)


def suicide_burn_altitude(
    speed: float,
    g_local: float,
    max_thrust_n: float,
    mass_kg: float,
    safety_margin: float = 0.05,
) -> float:
    """Altitude to start suicide burn for airless landing.
    
    Uses: d = v^2 / (2 * (TWR - 1) * g) + margin
    Where TWR = thrust / (mass * g_local).
    Assumes retrograde burn (thrust opposite velocity).
    """
    if max_thrust_n <= 0 or g_local <= 0:
        return 1e6  # can't compute, start early
    twr = twr_at_body(max_thrust_n, mass_kg, g_local)
    if twr <= 1.0:
        # Insufficient TWR to land — start immediately
        return 1e6
    decel = (twr - 1.0) * g_local  # net deceleration from retro burn + gravity
    alt = (speed * speed) / (2.0 * decel)
    return alt * (1.0 + safety_margin)


# ---------------------------------------------------------------------------
# Profile dispatcher
# ---------------------------------------------------------------------------

def select_profile(body: Any) -> str:
    """Select descent profile based on body atmosphere and surface gravity.
    
    Returns 'airless', 'atmospheric', or 'hybrid'.
    """
    if body.has_atmosphere:
        depth = body.atmosphere_depth
        g = body.surface_gravity
        # Duna has thin atmosphere — hybrid (parachute + powered final)
        if body.name == "Duna":
            return "hybrid"
        # Eve has crushing atmosphere — pure atmospheric but fully parachute not enough
        if body.name == "Eve":
            return "atmospheric"
        # Kerbin, Laythe — full atmospheric
        return "atmospheric"
    return "airless"


# ---------------------------------------------------------------------------
# Airless landing (suicide burn)
# ---------------------------------------------------------------------------

def land_airless(
    conn: krpc.Client,
    vessel: Any,
    body: Any,
    target_lat: float,
    target_lon: float,
    args: argparse.Namespace,
) -> None:
    """Execute suicide burn landing on airless body (Mun, Minmus, etc.).
    
    Phase:
    1. Deorbit burn to bring Pe close to surface (if in orbit)
    2. Orient retrograde
    3. Suicide burn at calculated altitude
    4. Touchdown < 5 m/s
    """
    sc = conn.space_center
    ap = vessel.auto_pilot
    ctrl = vessel.control
    srf_frame = vessel.surface_reference_frame
    orbit = vessel.orbit
    g_local = body.surface_gravity
    mu = body.gravitational_parameter
    body_r = body.equatorial_radius

    has_orbit = orbit is not None

    # -- Deorbit if in orbit ------------------------------------------------
    if has_orbit:
        log_event("deorbit_start", body=body.name,
                  apo=round(orbit.apoapsis_altitude, 1),
                  pe=round(orbit.periapsis_altitude, 1))

        # Burn retrograde at apoapsis to lower Pe
        ap.engage()
        # Wait until near apoapsis
        t_apo = orbit.time_to_apoapsis
        if t_apo > 60:
            log_event("warp_to_apo", time_to_apo=round(t_apo, 1))
            sc.warp_to(sc.ut + t_apo - 30)
            time.sleep(0.5)

        # Orient retrograde
        flight = vessel.flight(vessel.orbital_reference_frame)
        ap.target_direction(flight.retrograde, vessel.orbital_reference_frame)
        ap.wait()

        # Calculate small deorbit dV (just enough to graze surface/Pe~0)
        r_apo = orbit.apoapsis
        r_pe = orbit.periapsis
        a_cur = (r_apo + r_pe) / 2.0
        v_apo = math.sqrt(mu * (2.0 / r_apo - 1.0 / a_cur))
        pe_target = max(1000.0, body_r + 1000)  # just above surface
        a_new = (r_apo + pe_target) / 2.0
        v_new = math.sqrt(mu * (2.0 / r_apo - 1.0 / a_new))
        dv = v_apo - v_new

        if dv > 0:
            log_event("deorbit_burn", dv=round(dv, 2))
            ctrl.throttle = 0.3
            # Wait until we have a suborbital trajectory
            while True:
                if vessel.orbit is None:
                    break
                if vessel.orbit.periapsis_altitude < 5000:
                    break
                time.sleep(0.1)
            ctrl.throttle = 0.0
            log_event("deorbit_done")

    # -- Suicide burn phase ------------------------------------------------
    log_event("descent_start", profile="airless",
              body=body.name, g=round(g_local, 3))

    # Orient retrograde for descent
    ap.engage()
    ap.target_direction(vessel.flight(srf_frame).retrograde, srf_frame)
    ap.wait()

    # Stream key values
    alt_stream = conn.add_stream(
        getattr, vessel.flight(srf_frame), "surface_altitude")
    vel_stream = conn.add_stream(
        getattr, vessel.flight(srf_frame), "speed")
    max_g = 0.0

    # Compute suicide burn start altitude
    max_thrust = vessel.max_thrust * 1000.0  # kN -> N
    mass_kg = vessel.mass * 1000.0  # t -> kg

    burn_start_alt = suicide_burn_altitude(
        speed=vel_stream(),
        g_local=g_local,
        max_thrust_n=max_thrust,
        mass_kg=mass_kg,
        safety_margin=0.1,
    )
    log_event("suicide_burn_calc",
              burn_start_alt=round(burn_start_alt, 1),
              max_thrust_n=round(max_thrust, 1),
              mass_kg=round(mass_kg, 1),
              twr=round(twr_at_body(max_thrust, mass_kg, g_local), 3))

    # Coast until suicide burn altitude
    while alt_stream() > burn_start_alt:
        g_f = vessel.flight(srf_frame).g_force
        max_g = max(max_g, g_f)
        time.sleep(0.1)

    # Suicide burn: full throttle retrograde
    log_event("suicide_burn_ignition",
              altitude=round(alt_stream(), 1),
              speed=round(vel_stream(), 1))

    ctrl.throttle = 1.0
    prev_speed = vel_stream()
    landing_speed = 0.0

    while True:
        altitude = alt_stream()
        speed = vel_stream()
        g_f = vessel.flight(srf_frame).g_force
        max_g = max(max_g, g_f)

        # Update retrograde direction continuously
        ap.target_direction(vessel.flight(srf_frame).retrograde, srf_frame)

        if altitude <= 0.5:
            # Contact!
            landing_speed = speed
            break

        if altitude < 5.0 and speed < 5.0:
            # Close enough — cut throttle
            landing_speed = speed
            ctrl.throttle = 0.0
            break

        # Throttle modulation: taper as we approach to prevent overshoot
        if speed < 20.0 and altitude < 50.0:
            target_speed = max(1.0, speed * 0.8)
            ctrl.throttle = min(1.0, speed / 10.0)

        time.sleep(0.05)

    ctrl.throttle = 0.0
    ap.disengage()
    ctrl.sas = True

    # Report
    pos = vessel.flight(body.reference_frame)
    log_event("touchdown",
              body=body.name,
              profile="airless",
              latitude=round(pos.latitude, 6),
              longitude=round(pos.longitude, 6),
              impact_speed=round(landing_speed, 2),
              max_g=round(max_g, 3),
              fuel_remaining_kg=round((vessel.mass - vessel.dry_mass) * 1000, 2))


# ---------------------------------------------------------------------------
# Atmospheric landing (deorbit → aerobrake → parachute)
# ---------------------------------------------------------------------------

def land_atmospheric(
    conn: krpc.Client,
    vessel: Any,
    body: Any,
    target_lat: float,
    target_lon: float,
    args: argparse.Namespace,
) -> None:
    """Execute atmospheric descent: deorbit → aerobrake → parachute → splash.
    
    Used for Kerbin, Laythe. Eve has special handling (rocket-assisted).
    """
    sc = conn.space_center
    ap = vessel.auto_pilot
    ctrl = vessel.control
    srf_frame = vessel.surface_reference_frame
    orbit = vessel.orbit
    body_name = body.name
    atmo_depth = body.atmosphere_depth
    entry_pe = ENTRY_PE.get(body_name, atmo_depth * 0.5)

    chute_alts = PARACHUTE_ALT.get(body_name, {"drogue": 5000, "main": 500})
    g_local = body.surface_gravity

    # -- Deorbit burn --------------------------------------------------------
    log_event("deorbit_start", body=body_name,
              apo=round(orbit.apoapsis_altitude, 1) if orbit else 0,
              pe=round(orbit.periapsis_altitude, 1) if orbit else 0,
              target_pe=entry_pe)

    ap.engage()

    # Warp to near apoapsis if needed
    t_apo = orbit.time_to_apoapsis
    if t_apo > 60:
        sc.warp_to(sc.ut + t_apo - 30)
        time.sleep(0.5)

    # Orient retrograde and burn to lower Pe to entry altitude
    flight_orb = vessel.flight(vessel.orbital_reference_frame)
    ap.target_direction(flight_orb.retrograde, vessel.orbital_reference_frame)
    ap.wait()

    mu = body.gravitational_parameter
    r_apo = orbit.apoapsis
    a_cur = (r_apo + orbit.periapsis) / 2.0
    v_apo = math.sqrt(mu * (2.0 / r_apo - 1.0 / a_cur))
    r_target_pe = body.equatorial_radius + entry_pe
    a_new = (r_apo + r_target_pe) / 2.0
    v_new = math.sqrt(mu * (2.0 / r_apo - 1.0 / a_new))
    dv = v_apo - v_new

    if dv > 0:
        log_event("deorbit_burn", dv=round(dv, 2))
        ctrl.throttle = args.burn_throttle
        # Burn until periapsis reaches target
        while vessel.orbit.periapsis_altitude > entry_pe * 1.1:
            time.sleep(0.1)
        ctrl.throttle = 0.0
        log_event("deorbit_done",
                  pe=round(vessel.orbit.periapsis_altitude, 1))
    else:
        log_event("deorbit_skip",
                  message="Periapsis already low enough")

    # -- Aerobraking phase ---------------------------------------------------
    log_event("aerobrake_start",
              altitude=round(vessel.flight(srf_frame).mean_altitude, 1))

    ap.disengage()
    ctrl.sas = True
    ctrl.sas_mode = ctrl.sas_mode.retrograde  # keep heat shield forward

    max_q = 0.0
    max_g = 0.0

    # Stream altitude
    alt_stream = conn.add_stream(
        getattr, vessel.flight(srf_frame), "mean_altitude")
    vel_stream = conn.add_stream(
        getattr, vessel.flight(srf_frame), "speed")

    # Wait for atmosphere to slow us down
    # While high above surface, just wait
    # At lower altitude, deploy parachutes
    chutes_deployed = False
    parachute_alt = chute_alts["main"]

    while True:
        altitude = alt_stream()
        speed = vel_stream()
        flight = vessel.flight(srf_frame)
        q = flight.dynamic_pressure
        g_f = flight.g_force
        max_q = max(max_q, q)
        max_g = max(max_g, g_f)

        # Check for parachute deployment
        if not chutes_deployed and altitude < chute_alts["drogue"] and speed < 250:
            ctrl.activate_next_stage()  # deploy drogues
            log_event("drogue_deploy",
                      altitude=round(altitude, 1),
                      speed=round(speed, 1))
            chutes_deployed = True

        if chutes_deployed and altitude < parachute_alt and speed < 50:
            ctrl.activate_next_stage()  # deploy main chutes
            log_event("main_chute_deploy",
                      altitude=round(altitude, 1),
                      speed=round(speed, 1))
            break

        if altitude <= 0.5:
            # Parachutes may not have deployed — stage them
            if not chutes_deployed:
                ctrl.activate_next_stage()
            break

        # Follow retrograde (some vessels flip without fins)
        if q < 10000:
            ctrl.sas_mode = ctrl.sas_mode.retrograde

        time.sleep(0.1)

    # -- Parachute descent / Touchdown ---------------------------------------
    log_event("parachute_descent",
              altitude=round(alt_stream(), 1),
              speed=round(vel_stream(), 1))

    # Wait for touchdown
    while True:
        altitude = alt_stream()
        speed = vel_stream()
        if altitude <= 0.5:
            break
        if speed < 0.5 and altitude < 2.0:
            break
        time.sleep(0.2)

    pos = vessel.flight(body.reference_frame)
    log_event("touchdown",
              body=body_name,
              profile="atmospheric",
              latitude=round(pos.latitude, 6),
              longitude=round(pos.longitude, 6),
              impact_speed=round(vel_stream(), 2),
              max_q=round(max_q, 1),
              max_g=round(max_g, 3))


# ---------------------------------------------------------------------------
# Hybrid landing (Duna: aerobrake → parachute → powered landing)
# ---------------------------------------------------------------------------

def land_hybrid(
    conn: krpc.Client,
    vessel: Any,
    body: Any,
    target_lat: float,
    target_lon: float,
    args: argparse.Namespace,
) -> None:
    """Execute hybrid Duna descent: aerobrake → parachute → powered terminal.
    
    Duna's thin atmosphere slows the vessel but parachutes alone
    don't provide < 5 m/s touchdown. We use rocket power for final stage.
    """
    sc = conn.space_center
    ap = vessel.auto_pilot
    ctrl = vessel.control
    srf_frame = vessel.surface_reference_frame
    orbit = vessel.orbit
    body_name = body.name
    g_local = body.surface_gravity
    atmo_depth = body.atmosphere_depth

    entry_pe = ENTRY_PE.get(body_name, 12000)
    chute_alts = PARACHUTE_ALT.get(body_name,
                                   {"drogue": 5000, "main": 2500})

    # -- Deorbit burn --------------------------------------------------------
    log_event("deorbit_start", body=body_name,
              apo=round(orbit.apoapsis_altitude, 1) if orbit else 0,
              pe=round(orbit.periapsis_altitude, 1) if orbit else 0,
              target_pe=entry_pe)

    ap.engage()
    t_apo = orbit.time_to_apoapsis
    if t_apo > 60:
        sc.warp_to(sc.ut + t_apo - 30)
        time.sleep(0.5)

    flight_orb = vessel.flight(vessel.orbital_reference_frame)
    ap.target_direction(flight_orb.retrograde, vessel.orbital_reference_frame)
    ap.wait()

    mu = body.gravitational_parameter
    r_apo = orbit.apoapsis
    a_cur = (r_apo + orbit.periapsis) / 2.0
    v_apo = math.sqrt(mu * (2.0 / r_apo - 1.0 / a_cur))
    r_target_pe = body.equatorial_radius + entry_pe
    a_new = (r_apo + r_target_pe) / 2.0
    v_new = math.sqrt(mu * (2.0 / r_apo - 1.0 / a_new))
    dv = v_apo - v_new

    if dv > 0:
        log_event("deorbit_burn", dv=round(dv, 2))
        ctrl.throttle = args.burn_throttle
        while vessel.orbit.periapsis_altitude > entry_pe * 1.1:
            time.sleep(0.1)
        ctrl.throttle = 0.0
        log_event("deorbit_done",
                  pe=round(vessel.orbit.periapsis_altitude, 1))

    # -- Aerobrake + parachute phase -----------------------------------------
    log_event("aerobrake_start")

    ap.disengage()
    ctrl.sas = True
    ctrl.sas_mode = ctrl.sas_mode.retrograde

    alt_stream = conn.add_stream(
        getattr, vessel.flight(srf_frame), "surface_altitude")
    vel_stream = conn.add_stream(
        getattr, vessel.flight(srf_frame), "speed")

    max_q = 0.0
    max_g = 0.0
    chutes_deployed = False
    powered_phase = False

    while True:
        altitude = alt_stream()
        speed = vel_stream()
        flight = vessel.flight(srf_frame)
        q = flight.dynamic_pressure
        g_f = flight.g_force
        max_q = max(max_q, q)
        max_g = max(max_g, g_f)

        # Deploy drogue chutes when slow enough
        if not chutes_deployed and altitude < chute_alts["drogue"] and speed < 300:
            ctrl.activate_next_stage()
            log_event("drogue_deploy",
                      altitude=round(altitude, 1),
                      speed=round(speed, 1))
            chutes_deployed = True

        # Deploy main chutes
        if chutes_deployed and not powered_phase and altitude < chute_alts["main"] and speed < 100:
            ctrl.activate_next_stage()
            log_event("main_chute_deploy",
                      altitude=round(altitude, 1),
                      speed=round(speed, 1))

        # When close to ground, begin powered landing
        if altitude < 500 and speed > 5.0:
            powered_phase = True
            log_event("powered_phase_start",
                      altitude=round(altitude, 1),
                      speed=round(speed, 1))
            break

        if altitude <= 0.5:
            break

        time.sleep(0.1)

    # -- Powered landing phase -----------------------------------------------
    if powered_phase:
        ap.engage()
        ap.target_direction(flight.retrograde, srf_frame)
        ap.wait()

        # Suicide burn calculation for final stage
        # Duna gravity ~2.94 m/s^2, thin air (negligible drag at low alt)
        max_thrust = vessel.max_thrust * 1000.0
        mass_kg = vessel.mass * 1000.0

        burn_alt = suicide_burn_altitude(
            speed=vel_stream(),
            g_local=g_local,
            max_thrust_n=max_thrust,
            mass_kg=mass_kg,
            safety_margin=0.15,
        )
        log_event("suicide_burn_calc",
                  burn_start_alt=round(burn_alt, 1),
                  twr=round(twr_at_body(max_thrust, mass_kg, g_local), 3))

        # Wait for burn altitude
        while alt_stream() > burn_alt:
            time.sleep(0.1)

        log_event("engine_ignition",
                  altitude=round(alt_stream(), 1),
                  speed=round(vel_stream(), 1))

        ctrl.throttle = 1.0
        while True:
            altitude = alt_stream()
            speed = vel_stream()
            g_f = vessel.flight(srf_frame).g_force
            max_g = max(max_g, g_f)

            ap.target_direction(vessel.flight(srf_frame).retrograde, srf_frame)

            if altitude <= 0.5:
                break

            if altitude < 5.0 and speed < 5.0:
                ctrl.throttle = 0.0
                break

            # Throttle modulation
            if speed < 15.0 and altitude < 30.0:
                ctrl.throttle = min(1.0, speed / 10.0)

            time.sleep(0.05)

        ctrl.throttle = 0.0
        ap.disengage()
        ctrl.sas = True

    pos = vessel.flight(body.reference_frame)
    log_event("touchdown",
              body=body_name,
              profile="hybrid",
              latitude=round(pos.latitude, 6),
              longitude=round(pos.longitude, 6),
              impact_speed=round(vel_stream(), 2),
              max_q=round(max_q, 1),
              max_g=round(max_g, 3),
              fuel_remaining_kg=round((vessel.mass - vessel.dry_mass) * 1000, 2))


# ---------------------------------------------------------------------------
# Mission planner: compute deorbit burn for any profile
# ---------------------------------------------------------------------------

def plan_deorbit(
    conn: krpc.Client,
    vessel: Any,
    body: Any,
    target_pe: float,
) -> dict[str, Any]:
    """Compute deorbit burn parameters without executing."""
    orbit = vessel.orbit
    if orbit is None:
        return {"error": "Not in orbit"}

    mu = body.gravitational_parameter
    r_body = body.equatorial_radius
    r_apo = orbit.apoapsis
    a_cur = (r_apo + orbit.periapsis) / 2.0
    v_apo = math.sqrt(mu * (2.0 / r_apo - 1.0 / a_cur))
    r_target = r_body + target_pe
    a_new = (r_apo + r_target) / 2.0
    v_new = math.sqrt(mu * (2.0 / r_apo - 1.0 / a_new))
    dv = v_apo - v_new

    return {
        "apoapsis_alt": orbit.apoapsis_altitude,
        "periapsis_alt": orbit.periapsis_altitude,
        "target_pe_alt": target_pe,
        "delta_v": round(dv, 2),
        "current_speed": round(v_apo, 2),
        "target_speed": round(v_new, 2),
    }


# ---------------------------------------------------------------------------
# Main landing orchestrator
# ---------------------------------------------------------------------------

def landing_sequence(args: argparse.Namespace) -> None:
    conn = connect()
    sc = conn.space_center
    vessel = sc.active_vessel

    if vessel is None:
        log_event("error", message="No active vessel")
        sys.exit(1)

    # Resolve target body
    if args.body and args.body in sc.bodies:
        body = sc.bodies[args.body]
    else:
        if vessel.orbit:
            body = vessel.orbit.body
        else:
            body = vessel.flight().body

    body_name = body.name
    target_lat = args.lat if args.lat is not None else KSC_LAT
    target_lon = args.lon if args.lon is not None else KSC_LON

    log_event("landing_start",
              vessel=vessel.name,
              body=body_name,
              target_lat=target_lat,
              target_lon=target_lon,
              has_atmo=body.has_atmosphere)

    # Check situation
    sit = str(vessel.situation).split(".")[-1]
    if sit not in ("Orbiting", "SubOrbital", "Flying"):
        log_event("error", message=f"Unexpected situation: {sit}")
        sys.exit(1)

    # Select profile
    if args.profile:
        profile = args.profile
    else:
        profile = select_profile(body)

    log_event("profile_selected", profile=profile,
              gravity=round(body.surface_gravity, 3),
              atmo_depth=round(body.atmosphere_depth, 1))

    # Check abort after each phase
    def check_abort() -> bool:
        if vessel.control.abort:
            log_event("abort", message="Abort action group triggered")
            cleanup()
            return True
        return False

    # Execute based on profile
    if profile == "airless":
        land_airless(conn, vessel, body, target_lat, target_lon, args)
    elif profile == "atmospheric":
        if body.name == "Eve":
            log_event("eve_warning",
                      message="Eve landing: parachutes alone insufficient. "
                              "Engine power required for final descent.")
        land_atmospheric(conn, vessel, body, target_lat, target_lon, args)
    elif profile == "hybrid":
        land_hybrid(conn, vessel, body, target_lat, target_lon, args)
    else:
        log_event("error", message=f"Unknown profile: {profile}")
        sys.exit(1)

    if check_abort():
        return

    # Final status
    resources = vessel.resources
    fuel_amount = resources.amount("LiquidFuel") + resources.amount("Oxidizer") \
        if resources.has_resource("LiquidFuel") else 0
    log_event("landing_complete",
              biome=vessel.biome,
              fuel_remaining=round(fuel_amount, 2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autonomous landing sequence — deorbit, descent, touchdown")
    parser.add_argument("--lat", type=float, default=None,
                        help="Target latitude (default: KSC)")
    parser.add_argument("--lon", type=float, default=None,
                        help="Target longitude (default: KSC)")
    parser.add_argument("--body", default=None,
                        help="Target body (default: current body)")
    parser.add_argument("--profile", choices=["airless", "atmospheric", "hybrid"],
                        help="Force descent profile (default: auto-detect)")
    parser.add_argument("--burn-throttle", type=float, default=0.3,
                        help="Throttle for deorbit burn (0-1, default: 0.3)")
    parser.add_argument("--plan-only", action="store_true",
                        help="Only compute deorbit burn, don't execute")

    args = parser.parse_args()

    try:
        landing_sequence(args)
    except Exception as e:
        log_event("error", message=str(e))
        cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
