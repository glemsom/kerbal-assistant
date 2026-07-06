#!/usr/bin/env python3
"""Execute next maneuver node — orient, warp, burn, fine-tune — kRPC.

Usage:
    python scripts/execute-burn.py
    python scripts/execute-burn.py --lead-time 120 --cutoff 0.2
    python scripts/execute-burn.py --throttle 0.5 --correction

Outputs JSON telemetry events during burn.
Exits non-zero on error.
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
_native_cleanup_done = False


def cleanup(*_: Any) -> None:
    global _native_cleanup_done
    if _native_cleanup_done:
        return
    _native_cleanup_done = True
    if _conn is None:
        return
    try:
        vessel = _conn.space_center.active_vessel
        if vessel:
            vessel.control.throttle = 0.0
            vessel.auto_pilot.disengage()
            print(json.dumps({"event": "abort", "message": "Autopilot disengaged, throttle zero"}))
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
        _conn = krpc.connect(name="kerbal-assistant-execute-burn",
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


def estimate_burn_duration(vessel: Any, dv: float, isp: float, initial_mass: float) -> float:
    """Estimate burn duration using Tsiolkovsky (constant thrust assumed)."""
    thrust = vessel.available_thrust
    if thrust < 0.001 or dv < 0.001:
        return 0.0
    g0 = 9.80665
    ve = isp * g0
    return (ve * initial_mass / thrust) * (1 - math.exp(-dv / ve))


def find_next_node(vessel: Any) -> Any | None:
    """Return the next maneuver node for the active vessel, or None."""
    nodes = vessel.control.nodes
    if not nodes:
        return None
    # Nodes are sorted by UT ascending in kRPC
    return nodes[0]


# ---------------------------------------------------------------------------
# Core burn execution
# ---------------------------------------------------------------------------

def execute_burn(args: argparse.Namespace) -> None:
    """Find next node, orient, warp, burn, report."""
    conn = connect()
    sc = conn.space_center
    vessel = sc.active_vessel

    if vessel is None:
        print(json.dumps({"error": "No active vessel"}))
        sys.exit(1)

    # --- Find node ---------------------------------------------------------
    node = find_next_node(vessel)
    if node is None:
        print(json.dumps({"error": "No maneuver node found on vessel"}))
        sys.exit(1)

    log_event("node_found",
              ut=round(node.ut, 2),
              prograde=round(node.prograde, 2),
              normal=round(node.normal, 2),
              radial=round(node.radial, 2),
              total_dv=round(node.delta_v, 2))

    # --- Calcs -------------------------------------------------------------
    lead_time = args.lead_time
    cutoff_dv = args.cutoff
    burn_throttle = args.throttle

    # Estimate burn duration
    isp = vessel.specific_impulse
    if isp < 0.1:
        isp = 300.0  # sensible fallback
    burn_dur = estimate_burn_duration(vessel, node.delta_v, isp, vessel.mass)
    log_event("burn_estimate", isp=round(isp, 1),
              mass=round(vessel.mass, 1),
              thrust=round(vessel.available_thrust, 1),
              duration=round(burn_dur, 1))

    # Midpoint timing: burn at T - burn_dur/2 for even split
    burn_mid_ut = node.ut
    burn_start_ut = burn_mid_ut - burn_dur / 2.0
    warp_target_ut = burn_start_ut - lead_time

    # --- Orient vessel ----------------------------------------------------
    log_event("orient_start")
    ap = vessel.auto_pilot
    ap.reference_frame = node.orbital_reference_frame
    ap.target_direction = (0, 1, 0)  # +Y = prograde in node frame
    ap.engage()
    ap.wait()
    log_event("orient_done")

    # --- Warp to burn -----------------------------------------------------
    ut_now = sc.ut
    if warp_target_ut > ut_now:
        log_event("warp_start", target_ut=round(warp_target_ut, 2),
                  warp_duration=round(warp_target_ut - ut_now, 1))
        sc.warp_to(warp_target_ut)
        # Wait for warp to finish (warp_to is synchronous in kRPC)
        log_event("warp_done", ut=round(sc.ut, 2))
    else:
        log_event("warp_skip", reason="Already past warp target")

    # --- Pre-burn wait (drain remaining seconds) --------------------------
    while sc.ut < burn_start_ut - 0.5:
        left = burn_start_ut - sc.ut
        log_event("countdown", seconds_to_burn=round(left, 2))
        time.sleep(0.2 if left > 2 else 0.05)

    # --- Execute burn -----------------------------------------------------
    log_event("burn_start",
              ut=round(sc.ut, 2),
              node_ut=round(node.ut, 2))
    vessel.control.throttle = burn_throttle

    # Telemetry streams
    node_frame = node.orbital_reference_frame
    rem_dv_stream = conn.add_stream(getattr, node, "remaining_delta_v")
    ut_stream = conn.add_stream(getattr, sc, "ut")
    throttle = burn_throttle

    # Main burn loop: stop when remaining_dV < cutoff_dv
    last_rem = rem_dv_stream()
    throttle_reduced = False

    while rem_dv_stream() > cutoff_dv:
        ut_now = ut_stream()
        rem = rem_dv_stream()

        # Live telemetry every 0.5s
        log_event("burn_telemetry",
                  ut=round(ut_now, 2),
                  remaining_dv=round(rem, 3),
                  throttle=round(throttle, 3))

        # Coast phase detection: if we've passed node.ut and still have
        # significant dV left, we're burning the wrong side. Keep going.
        # No special action needed — autopilot maintains direction.

        # Throttle modulation near end for precision
        if rem < 5.0 and not throttle_reduced:
            throttle = min(throttle, 0.2)
            vessel.control.throttle = throttle
            throttle_reduced = True
            log_event("throttle_reduced", throttle=round(throttle, 3))

        if rem < cutoff_dv * 5 and throttle > 0.05:
            throttle = max(0.05, throttle * 0.5)
            vessel.control.throttle = throttle
            log_event("fine_tune", throttle=round(throttle, 3))

        time.sleep(0.05)

    # --- Cutoff -----------------------------------------------------------
    vessel.control.throttle = 0.0
    log_event("burn_done",
              remaining_dv=round(rem_dv_stream(), 4),
              ut=round(sc.ut, 2))

    # --- Post-burn drift check (correction burn if enabled) ---------------
    if args.correction:
        time.sleep(0.5)
        final_rem = rem_dv_stream()
        if final_rem > cutoff_dv:
            log_event("correction_start", remaining_dv=round(final_rem, 3))
            vessel.control.throttle = 0.1
            while rem_dv_stream() > cutoff_dv:
                time.sleep(0.05)
            vessel.control.throttle = 0.0
            log_event("correction_done")

    # --- Report -----------------------------------------------------------
    node.remove()
    final_orbit = vessel.orbit
    final = orbit_summary(final_orbit) if final_orbit else None

    dv_error = rem_dv_stream()  # should be ~0
    result = {
        "event": "burn_complete",
        "dv_error": round(dv_error, 4),
        "orbit_achieved": final,
        "node_removed": True,
    }
    print(json.dumps(result))

    ap.disengage()
    vessel.control.sas = True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execute the next maneuver node on the active vessel")
    parser.add_argument("--lead-time", type=float, default=30.0,
                        help="Seconds before burn start to warp to (default: 30)")
    parser.add_argument("--cutoff", type=float, default=0.3,
                        help="Residual dV threshold to cut throttle (default: 0.3 m/s)")
    parser.add_argument("--throttle", type=float, default=0.3,
                        help="Throttle setting for burn (default: 0.3)")
    parser.add_argument("--correction", action="store_true",
                        help="Perform a small correction burn if residual dV remains")
    parser.add_argument("--minify", action="store_true",
                        help="Output compact JSON")

    args = parser.parse_args()

    try:
        execute_burn(args)
    except Exception as e:
        log_event("error", message=str(e))
        cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
