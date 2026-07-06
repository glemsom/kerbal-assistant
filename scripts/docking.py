#!/usr/bin/env python3
"""Fine approach and docking sequence — RCS translation to target port, magnetic capture.

Usage:
    python scripts/docking.py
    python scripts/docking.py --target-port "Clamp-o-Tron Sr."
    python scripts/docking.py --dry-run

Outputs JSON events to stdout. Abort: Ctrl+C or Abort key (reverses thrust, retreats to safe distance).

Approach phases:
  1. Orient to target — point vessel at target docking port
  2. Fast approach — translate at 10 m/s down the approach axis
  3. Slow approach — at <100m, slow to 3 m/s
  4. Fine approach — at <10m, slow to 0.5 m/s, maintain alignment
  5. Magnetic dock — reduce relative velocity to < 0.2 m/s, let magnets pull in
  6. Verify docked (undock event or vessel.merged_parts)
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
# Global
# ---------------------------------------------------------------------------
_conn: krpc.Client | None = None
_cleanup_done = False
_abort_flag = False


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
            vessel.control.rcs = False
            print(json.dumps({"event": "abort", "message": "Systems disengaged, throttle zero"}))
    except Exception:
        pass


def abort_handler(*_: Any) -> None:
    global _abort_flag
    _abort_flag = True


signal.signal(signal.SIGINT, abort_handler)
signal.signal(signal.SIGTERM, abort_handler)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def connect() -> krpc.Client:
    global _conn
    try:
        _conn = krpc.connect(name="kerbal-assistant-docking", address="127.0.0.1", rpc_port=50000)
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
    sc = conn.space_center
    for v in sc.vessels:
        if v.name == name:
            return v
    for v in sc.vessels:
        if name.lower() in v.name.lower():
            return v
    return None


def find_docking_port(vessel: Any, port_name: str | None = None):
    """Find a docking port on a vessel.

    If port_name given, find exact match. Otherwise return closest port
    to vessel's center of mass (default for docking).
    """
    ports = []
    for part in vessel.parts.all:
        if part.docking_port:
            ports.append(part)

    if not ports:
        return None

    if port_name:
        for p in ports:
            if port_name.lower() in p.name.lower():
                return p
        # Fallback: try part title
        for p in ports:
            if port_name.lower() in p.title.lower():
                return p

    # Return first port (closest to front of vessel by convention)
    return ports[0]


def check_docked(vessel: Any) -> bool:
    """Return True if vessel is docked (merged) to something.

    In kRPC, docked vessels merge into one. We can check if the
    original vessel name is gone or if parts are connected to another.
    Simple approach: vessel.situation has 'Docked' or check for
    docked parts.
    """
    # After docking, vessels merge. The active vessel might have
    # a different name. Check if any part has a connected docking port.
    try:
        for part in vessel.parts.all:
            if part.docking_port and part.docking_port.docked_part is not None:
                return True
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Docking phases
# ---------------------------------------------------------------------------

def phase_1_set_target_and_orient(
    conn: krpc.Client, vessel: Any, target_vessel: Any,
    target_port_name: str | None, dry_run: bool = False
) -> Any:
    """Set target docking port and orient vessel toward it."""
    sc = conn.space_center

    # Find target docking port
    port = find_docking_port(target_vessel, target_port_name)
    if port is None:
        log_event("error", message=f"No docking port found on '{target_vessel.name}'")
        sys.exit(1)

    log_event("target_port",
              port_name=port.name,
              port_title=port.title,
              vessel=target_vessel.name)

    # Set as target in kRPC
    sc.target = port.docking_port
    sc.target_vessel = target_vessel

    # Orient vessel toward target port
    ap = vessel.auto_pilot
    ap.engage()

    # Reference frame: use target docking port's reference frame
    port_frame = port.reference_frame
    # Point toward the port (approach vector is along port's negative Z axis in its frame)
    # In kRPC, the port's reference frame has Z+ pointing outward (away from vessel).
    # To approach, we point our vessel's -Z at the port.
    # Simpler: point vessel at target position
    ap.target_direction((0, 0, -1), port_frame)
    ap.wait()

    log_event("oriented", message="Vessel oriented toward target port")

    if not dry_run:
        vessel.control.rcs = True

    return port


def phase_2_approach(
    conn: krpc.Client, vessel: Any, target_vessel: Any,
    port: Any, dry_run: bool = False
) -> dict:
    """Translate toward target port at controlled speeds.

    Speed profile:
      - >100m: 10 m/s (fast approach)
      - 30-100m: 3 m/s (slow approach) 
      - 5-30m: 0.5 m/s (fine approach)
      - <5m: coast at <0.2 m/s for magnetic capture
    """
    sc = conn.space_center
    port_frame = port.reference_frame

    # In port reference frame, Z+ points outward from port.
    # To approach, we translate in -Z direction.
    # We'll use vessel.control.translate(x, y, z)  where
    # values are -1 to 1, and translation is in vessel's reference frame.

    # For controlled approach, we track distance to port and adjust
    # translation speed.
    target_vessel_ref = target_vessel.orbital_reference_frame

    start_time = time.time()
    phase = "fast"
    prev_distance = float("inf")

    vessel_ref_frame = vessel.reference_frame

    # We'll use vessel.control.translate which operates in the vessel's
    # local frame. We need to figure out which direction to push.

    # Streams for responsive control
    flight = conn.add_stream(vessel.flight, port_frame)

    # Main approach loop
    while not _abort_flag:
        # Get distance and relative velocity in port frame
        dp = flight()
        distance = dp.mean_altitude  # Not actual height — use position magnitude
        # Actually, use position of vessel in port frame
        v_pos = vessel.position(port_frame)
        distance = math.sqrt(v_pos[0]**2 + v_pos[1]**2 + v_pos[2]**2)

        # Relative speed in port frame
        rel_speed = dp.speed

        # Determine speed target based on distance
        if distance > 100:
            target_speed = 10.0
            new_phase = "fast"
        elif distance > 30:
            target_speed = 3.0
            new_phase = "slow"
        elif distance > 5:
            target_speed = 0.5
            new_phase = "fine"
        else:
            target_speed = 0.2
            new_phase = "capture"

        if new_phase != phase:
            log_event("phase_change",
                      phase=new_phase,
                      distance=round(distance, 2),
                      speed=round(rel_speed, 3))
            phase = new_phase

        # Check if we're getting closer
        if distance < prev_distance:
            prev_distance = distance

        # Translate toward port: -Z in port frame is toward the port
        # Map to vessel's translation: we already oriented vessel's -Z at port
        # So translate along vessel's local X axis = forward/backward approach
        # In vessel reference frame, -Z is typically forward (nose)
        # vessel.control.translate(x, y, z) where z is forward/back, x is lateral, y is vertical

        # Speed control: throttle translation based on target vs actual
        speed_error = rel_speed - target_speed

        translation_z = 0.0
        if speed_error < -0.5:
            # Too fast — reduce or reverse
            translation_z = -0.3  # reverse
        elif abs(speed_error) < 0.5 and rel_speed > 0:
            # Maintain — push at appropriate level
            translation_z = -0.2
        elif rel_speed < target_speed * 0.8:
            # Too slow — push harder
            translation_z = -0.5

        # If very close and slow, coast
        if distance < 3 and rel_speed < 0.3:
            translation_z = 0.0  # coast — magnets will pull

        # Apply translation (z is forward/back in vessel frame)
        # Clamp to -1..1
        translation_z = max(-1.0, min(1.0, translation_z))

        if not dry_run:
            vessel.control.translate = (0.0, 0.0, translation_z)
        else:
            log_event("dry_run_translate",
                      distance=round(distance, 2),
                      rel_speed=round(rel_speed, 3),
                      translation_z=round(translation_z, 3))

        # Check for docking
        if check_docked(vessel) or distance < 0.5:
            log_event("docked",
                      distance=round(distance, 3),
                      rel_speed=round(rel_speed, 3),
                      elapsed=round(time.time() - start_time, 1))
            vessel.control.translate = (0.0, 0.0, 0.0)
            vessel.control.rcs = False
            return {"docked": True, "distance": distance, "elapsed": time.time() - start_time}

        # Abort check (also handled by signal handler)
        if _abort_flag:
            log_event("abort_initiated", message="Abort requested — reversing thrust")
            # Reverse thrust to retreat
            for _ in range(50):  # 5 seconds of reverse
                if not dry_run:
                    vessel.control.translate = (0.0, 0.0, 1.0)  # reverse
                time.sleep(0.1)
                if check_docked(vessel):
                    break

            vessel.control.translate = (0.0, 0.0, 0.0)
            vessel.control.rcs = False
            vessel.auto_pilot.disengage()
            return {"docked": False, "aborted": True, "distance": distance}

        time.sleep(0.1)

    # Aborted via signal
    vessel.control.translate = (0.0, 0.0, 1.0)
    time.sleep(2.0)
    vessel.control.translate = (0.0, 0.0, 0.0)
    vessel.control.rcs = False
    return {"docked": False, "aborted": True}


# ---------------------------------------------------------------------------
# Main docking flow
# ---------------------------------------------------------------------------

def docking(args: argparse.Namespace) -> None:
    conn = connect()
    sc = conn.space_center

    vessel = sc.active_vessel
    if vessel is None:
        log_event("error", message="No active vessel")
        sys.exit(1)

    # Resolve target vessel
    target = None
    if args.target:
        target = vessel_by_name(conn, args.target)
        if target is None:
            log_event("error", message=f"Target vessel '{args.target}' not found")
            sys.exit(1)
    else:
        target = sc.target_vessel
        if target is None:
            log_event("error", message="No target vessel set. Use --target or set target in KSP.")
            sys.exit(1)

    # Check target is not ourselves
    if target.id == vessel.id:
        log_event("error", message="Target vessel is the active vessel — set a different target")
        sys.exit(1)

    log_event("docking_start",
              vessel=vessel.name,
              target=target.name,
              dry_run=args.dry_run)

    # Phase 1: Orient
    log_event("phase", phase=1, name="orient")
    port = phase_1_set_target_and_orient(conn, vessel, target, args.port, dry_run=args.dry_run)

    # Phase 2: Approach and dock
    log_event("phase", phase=2, name="approach")
    result = phase_2_approach(conn, vessel, target, port, dry_run=args.dry_run)

    # Report
    log_event("docking_complete", **result)

    # Disengage
    vessel.auto_pilot.disengage()
    vessel.control.sas = False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Fine approach and docking sequence")
    parser.add_argument("--target", "-t", help="Target vessel name (default: targeted vessel in-game)")
    parser.add_argument("--port", "-p", help="Target docking port name (default: first port found)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute only, do not execute translation")
    args = parser.parse_args()

    try:
        docking(args)
    except Exception as e:
        log_event("error", message=str(e))
        cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
