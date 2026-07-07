#!/usr/bin/env python3
"""Staging validation test — exercises kRPC staging API on active vessel.

Tests:
  1. Inspect stage structure before launch
  2. Stage activation (engine ignition, decoupler firing)
  3. Detect fuel depletion per stage (stage_fuel_empty)
  4. Verify thrust changes after staging
  5. Clean up and report results

Usage:
    python scripts/staging-test.py
    python scripts/staging-test.py --launch   # auto-launch if on KSC
"""

from __future__ import annotations

import argparse
import json
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
# Globals for cleanup
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
        v = _conn.space_center.active_vessel
        v.control.throttle = 0.0
        v.auto_pilot.disengage()
        v.control.sas = False
        print(json.dumps({"event": "cleanup", "message": "Throttle zero, autopilot off"}))
    except Exception:
        pass


signal.signal(signal.SIGINT, lambda *_: (cleanup(), sys.exit(1)))
signal.signal(signal.SIGTERM, lambda *_: (cleanup(), sys.exit(1)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def stage_fuel_empty(v: Any) -> bool:
    """Return True if current stage has no fuel in any resource."""
    stage_num = v.control.current_stage
    stage_parts = v.parts.in_stage(stage_num)
    for part in stage_parts:
        for resource in part.resources.all:
            if resource.amount > 0.001 and resource.density > 0:
                return False
    return True


def inspect_stages(v: Any) -> dict:
    """Return full stage structure as dict."""
    stages = {}
    for s in range(v.control.current_stage, -1, -1):
        parts = v.parts.in_stage(s)
        engines = [p for p in parts if p.engine]
        decouplers = [
            p for p in parts
            if p.engine is None and p.title
        ]
        # Filter decouplers by title
        real_decouplers = [
            p.title for p in parts
            if 'decoupler' in (p.title or '').lower()
            or 'separator' in (p.title or '').lower()
            or 'Clamp' in (p.title or '')
        ]
        fuel = {}
        for p in parts:
            for r in p.resources.all:
                if r.density > 0 and r.amount > 0.001:
                    fuel[r.name] = fuel.get(r.name, 0) + r.amount

        stages[str(s)] = {
            "parts": len(parts),
            "engine_names": [e.title for e in engines],
            "decouplers": real_decouplers,
            "fuel": fuel,
            "total_fuel_mass_kg": sum(fuel.values()) * 0.005 * 1000 if fuel else 0,  # KSP units to kg
        }
    return stages


def log_event(event: str, **kwargs: Any) -> None:
    msg = {"event": event, **kwargs}
    print(json.dumps(msg))


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------
def run_staging_test(args: argparse.Namespace) -> None:
    global _conn
    _conn = krpc.connect(name="kerbal-assistant-staging-test", address="127.0.0.1", rpc_port=50000)
    sc = _conn.space_center

    v = sc.active_vessel
    sit = str(v.situation).split(".")[-1]
    log_event("test_start", vessel=v.name, situation=sit, stage=v.control.current_stage)

    # Phase 1: Inspect pre-launch stage structure
    log_event("phase_1_inspect", message="Inspecting stage structure")
    stages = inspect_stages(v)
    log_event("stages", stages=stages, current_stage=v.control.current_stage)
    log_event("initial_state",
              mass=v.mass,
              dry_mass=v.dry_mass,
              available_thrust=v.available_thrust,
              max_thrust=v.max_thrust,
              stage=v.control.current_stage)

    if sit != "pre_launch":
        log_event("warn", message=f"Not pre_launch, current situation: {sit}")

    # Phase 2: Stage activation test
    log_event("phase_2_stage_activation", message="Activating first stage (launch clamps + SRB ignition)")

    # Set autopilot to point up before staging
    ap = v.auto_pilot
    ap.engage()
    ap.target_pitch_and_heading(90, 90)

    # Set throttle
    v.control.throttle = 1.0
    time.sleep(0.3)

    # --- Stage 4 → 3: Ignite SRBs ---
    initial_stage = v.control.current_stage
    log_event("pre_stage", current_stage=initial_stage)

    jettisoned = v.control.activate_next_stage()
    time.sleep(0.5)

    post_stage = v.control.current_stage
    log_event("post_stage_1",
              jettisoned_count=len(jettisoned),
              jettisoned_parts=[getattr(p, 'title', str(p)) for p in jettisoned],
              new_stage=post_stage,
              available_thrust=v.available_thrust,
              max_thrust=v.max_thrust,
              mass=v.mass)

    # Wait for positive climb
    start_time = time.time()
    while True:
        if time.time() - start_time > 8:
            log_event("error", message="Failed to lift off after staging")
            sys.exit(1)
        alt = v.flight(v.orbit.body.reference_frame).mean_altitude
        if alt > 2.0:
            break
        time.sleep(0.1)

    log_event("liftoff",
              altitude=round(v.flight(v.orbit.body.reference_frame).mean_altitude, 1),
              speed=round(v.flight(v.orbit.body.reference_frame).speed, 1))

    # Phase 3: Monitor SRB burn and detect burnout
    log_event("phase_3_srb_burn", message="Monitoring SRB burn — waiting for fuel depletion in current stage")

    # Track SRB fuel
    srb_burn_start = time.time()
    srb_fuel_initial = sum(
        p.resources.amount("SolidFuel") or 0
        for p in v.parts.all
        if p.resources and p.resources.has_resource("SolidFuel")
    )
    log_event("srb_fuel_initial", solid_fuel=srb_fuel_initial)

    # Wait for SRBs to burn out (fuel empty in stage)
    while not stage_fuel_empty(v):
        time.sleep(0.5)

    srb_burn_duration = time.time() - srb_burn_start
    log_event("srb_burnout",
              burn_duration_sec=round(srb_burn_duration, 1),
              current_stage=v.control.current_stage,
              altitude=round(v.flight(v.orbit.body.reference_frame).mean_altitude, 1),
              speed=round(v.flight(v.orbit.body.reference_frame).speed, 1))

    # --- Stage 3 → 2: Jettison SRBs ---
    log_event("phase_4_jettison", message="Staging to jettison spent SRBs")
    initial_stage = v.control.current_stage
    jettisoned = v.control.activate_next_stage()
    time.sleep(0.5)
    post_stage = v.control.current_stage

    log_event("jettison",
              jettisoned_count=len(jettisoned),
              jettisoned_parts=[getattr(p, 'title', str(p)) for p in jettisoned],
              old_stage=initial_stage,
              new_stage=post_stage)

    # Check: after jettison, mass should decrease, thrust may change
    log_event("post_jettison",
              mass=v.mass,
              dry_mass=v.dry_mass,
              available_thrust=v.available_thrust,
              max_thrust=v.max_thrust,
              stage=v.control.current_stage)

    # Phase 5: Center engine activation
    log_event("phase_5_center_engine", message="Staging to activate center engine (LV-T45)")
    initial_stage = v.control.current_stage
    jettisoned = v.control.activate_next_stage()
    time.sleep(0.5)
    post_stage = v.control.current_stage

    log_event("center_engine_activation",
              jettisoned_count=len(jettisoned),
              jettisoned_parts=[getattr(p, 'title', str(p)) for p in jettisoned],
              old_stage=initial_stage,
              new_stage=post_stage,
              available_thrust=v.available_thrust,
              max_thrust=v.max_thrust,
              mass=v.mass)

    # Check engine state
    lv_t45_parts = [p for p in v.parts.all if p.engine and "Swivel" in (p.title or "")]
    if lv_t45_parts:
        eng = lv_t45_parts[0].engine
        log_event("engine_status",
                  engine_name=lv_t45_parts[0].title,
                  active=eng.active,
                  has_fuel=eng.has_fuel,
                  thrust=eng.thrust if eng.active else 0)

    # Phase 6: Monitor liquid fuel burn
    log_event("phase_6_liquid_burn", message="Monitoring liquid fuel burn")
    lf_initial = v.resources.amount("LiquidFuel") or 0
    ox_initial = v.resources.amount("Oxidizer") or 0
    log_event("fuel_resources",
              liquid_fuel=lf_initial,
              oxidizer=ox_initial)

    # Let it burn for a bit to show fuel consumption
    burn_start = time.time()
    while time.time() - burn_start < 5.0:
        lf_current = v.resources.amount("LiquidFuel") or 0
        ox_current = v.resources.amount("Oxidizer") or 0
        log_event("fuel_tick",
                  t=round(time.time() - burn_start, 1),
                  liquid_fuel=round(lf_current, 1),
                  oxidizer=round(ox_current, 1),
                  thrust=v.available_thrust,
                  alt=round(v.flight(v.orbit.body.reference_frame).mean_altitude, 1),
                  speed=round(v.flight(v.orbit.body.reference_frame).speed, 1))
        time.sleep(0.5)

    # Phase 7: Final summary
    log_event("phase_7_summary", message="Staging test summary")
    log_event("test_summary",
              stages_consumed=v.control.current_stage,
              initial_stage=initial_stage,  # from the start was 4... but variable reused
              final_stage=v.control.current_stage,
              mass=v.mass,
              dry_mass=v.dry_mass,
              altitude=round(v.flight(v.orbit.body.reference_frame).mean_altitude, 1),
              speed=round(v.flight(v.orbit.body.reference_frame).speed, 1),
              max_thrust=v.max_thrust)

    # Record the active stages structure at the end
    final_stages = inspect_stages(v)
    log_event("final_stages", stages=final_stages, current_stage=v.control.current_stage)

    # Cleanup
    v.control.throttle = 0.0
    ap.disengage()
    v.control.sas = True
    log_event("test_complete", message="Staging validation complete")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Staging validation test")
    parser.add_argument("--launch", action="store_true",
                        help="Launch vessel from VAB before testing")
    args = parser.parse_args()

    try:
        run_staging_test(args)
    except Exception as e:
        log_event("error", message=str(e))
        cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
