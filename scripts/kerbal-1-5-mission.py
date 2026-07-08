#!/usr/bin/env python3
"""Complete Kerbal 1-5 mission: circularize, de-orbit, land.

Phases:
  1. Circularize at apoapsis (burn prograde to raise peri > 70km)
  2. Coast to apoapsis, de-orbit burn retrograde
  3. Re-entry, parachute landing
"""

from __future__ import annotations

import json
import math
import signal
import sys
import time

try:
    import krpc
except ImportError:
    print(json.dumps({"error": "krpc not installed"}))
    sys.exit(1)

# ---------------------------------------------------------------------------
# Globals & cleanup
# ---------------------------------------------------------------------------
_conn = None
_cleanup_done = False


def cleanup(*_) -> None:
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True
    if _conn is None:
        return
    try:
        v = _conn.space_center.active_vessel
        if v:
            v.control.throttle = 0.0
            v.auto_pilot.disengage()
            v.control.sas = False
            v.control.rcs = False
        print(json.dumps({"event": "cleanup", "message": "Throttle zero, autopilot off"}))
    except Exception:
        pass


signal.signal(signal.SIGINT, lambda *_: (cleanup(), sys.exit(1)))
signal.signal(signal.SIGTERM, lambda *_: (cleanup(), sys.exit(1)))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
G0 = 9.80665
MU_KERBIN = 3.5316e12
R_KERBIN = 600_000


class MissionAbort(Exception):
    pass


def log(event: str, **kw) -> None:
    msg = {"event": event}
    msg.update(kw)
    print(json.dumps(msg))
    sys.stdout.flush()


def get_active_vessel(conn) -> krpc.types.Vessel | None:
    try:
        return conn.space_center.active_vessel
    except ValueError:
        return None


def wait_until(cond_fn, poll_interval=0.2, timeout=300):
    """Wait until cond_fn() returns True or timeout (s)."""
    start = time.time()
    while not cond_fn():
        if time.time() - start > timeout:
            raise MissionAbort("Timeout waiting for condition")
        time.sleep(poll_interval)


# ---------------------------------------------------------------------------
# Phase 1: Circularization
# ---------------------------------------------------------------------------
def phase_circularize(v) -> None:
    """Burn prograde at apoapsis until periapsis >= 70km."""
    o = v.orbit
    apo = o.apoapsis_altitude
    peri = o.periapsis_altitude
    target_peri = 70_000

    log("phase_circularize_start",
        apo=f"{apo:.0f}", peri=f"{peri:.0f}",
        target_peri=f"{target_peri:.0f}",
        time_to_apo=f"{o.time_to_apoapsis:.1f}")

    if peri >= target_peri:
        log("circ_already_in_orbit")
        return

    # Wait for apoapsis
    wait_until(lambda: v.orbit.time_to_apoapsis < 3, poll_interval=0.2)

    # Set SAS to prograde for alignment
    v.control.sas = True
    v.control.sas_mode = v.control.sas_mode.prograde
    time.sleep(1.0)

    # Full throttle
    v.control.throttle = 1.0
    log("burn_start", throttle=1.0)

    burn_start = time.time()
    stall_count = 0
    last_peri = v.orbit.periapsis_altitude

    while v.orbit.periapsis_altitude < target_peri:
        # Check fuel
        has_fuel = any(
            p.engine and p.engine.has_fuel
            for p in v.parts.all if p.engine
        )
        if not has_fuel:
            v.control.throttle = 0.0
            raise MissionAbort("Out of fuel before circularization")

        curr_peri = v.orbit.periapsis_altitude
        if curr_peri == last_peri:
            stall_count += 1
            if stall_count > 100:
                log("peri_stalled", peri=f"{curr_peri:.0f}")
                v.control.throttle = 0.0
                raise MissionAbort("Periapsis stalled - check orientation")
        else:
            stall_count = 0
        last_peri = curr_peri

        time.sleep(0.05)

    v.control.throttle = 0.0
    burn_time = time.time() - burn_start
    o = v.orbit
    log("circularization_done",
        apo=f"{o.apoapsis_altitude:.0f}",
        peri=f"{o.periapsis_altitude:.0f}",
        burn_time=f"{burn_time:.1f}s")


# ---------------------------------------------------------------------------
# Phase 2: De-orbit
# ---------------------------------------------------------------------------
def phase_deorbit(v) -> None:
    """Burn retrograde at apoapsis to lower periapsis to ~35km."""
    target_peri = 35_000

    o = v.orbit
    log("phase_deorbit_start",
        apo=f"{o.apoapsis_altitude:.0f}",
        peri=f"{o.periapsis_altitude:.0f}")

    # Wait for apoapsis
    wait_until(lambda: v.orbit.time_to_apoapsis < 3, poll_interval=0.2)

    # SAS retrograde
    v.control.sas = True
    v.control.sas_mode = v.control.sas_mode.retrograde
    time.sleep(1.0)

    # Burn until peri < target
    v.control.throttle = 1.0
    log("deorbit_burn_start")

    while v.orbit.periapsis_altitude > target_peri:
        has_fuel = any(p.engine and p.engine.has_fuel for p in v.parts.all if p.engine)
        if not has_fuel:
            v.control.throttle = 0.0
            raise MissionAbort("Out of fuel during de-orbit")
        time.sleep(0.05)

    v.control.throttle = 0.0
    o = v.orbit
    log("deorbit_done",
        apo=f"{o.apoapsis_altitude:.0f}",
        peri=f"{o.periapsis_altitude:.0f}")


# ---------------------------------------------------------------------------
# Phase 3: Re-entry & Landing
# ---------------------------------------------------------------------------
def phase_reentry_and_land(v) -> None:
    """Coast through re-entry, deploy parachute."""
    log("phase_reentry_start",
        apo=f"{v.orbit.apoapsis_altitude:.0f}",
        peri=f"{v.orbit.periapsis_altitude:.0f}")

    v.control.sas = True
    chute_deployed = False
    landed = False

    while not landed:
        try:
            f = v.flight(v.orbit.body.reference_frame)
            alt = f.mean_altitude
            speed = f.speed

            if not chute_deployed and alt < 5000 and speed < 400:
                log("deploying_chute", altitude=f"{alt:.0f}", speed=f"{speed:.1f}")
                v.control.activate_next_stage()
                chute_deployed = True
                log("chute_deployed")

            if v.situation.name == "landed":
                landed = True
                log("landed", altitude=f"{alt:.0f}")

            time.sleep(0.5)

        except Exception as e:
            log("reentry_error", error=str(e))
            time.sleep(0.5)

    log("mission_complete")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    global _conn
    try:
        _conn = krpc.connect(name="kerbal-1-5-mission", address="127.0.0.1", rpc_port=50000)
    except Exception as e:
        log("connection_error", error=str(e))
        sys.exit(1)

    v = get_active_vessel(_conn)
    if not v:
        log("no_active_vessel")
        sys.exit(1)

    log("mission_start",
         vessel=v.name,
         situation=str(v.situation),
         met=f"{v.met:.1f}")

    try:
        # Phase 1: Circularize
        phase_circularize(v)

        o = v.orbit
        log("orbit_achieved",
            apo=f"{o.apoapsis_altitude:.0f}",
            peri=f"{o.periapsis_altitude:.0f}",
            speed=f"{o.speed:.1f}")

        # Need to coast to get to apoapsis for de-orbit burn
        # If we're near apo now, we just burned -- wait until next apo
        log("coasting_to_deorbit_apo",
            time_to_apo=f"{v.orbit.time_to_apoapsis:.1f}")

        # Coast to apoapsis for efficient de-orbit
        wait_until(lambda: v.orbit.time_to_apoapsis < 5,
                   poll_interval=1.0,
                   timeout=6000)

        phase_deorbit(v)

        # Phase 3: Re-entry
        phase_reentry_and_land(v)

    except MissionAbort as e:
        log("mission_abort", reason=str(e))
        cleanup()
        sys.exit(1)
    except KeyboardInterrupt:
        log("interrupted")
        cleanup()
        sys.exit(1)
    except Exception as e:
        log("error", error=str(e))
        cleanup()
        sys.exit(1)

    cleanup()


if __name__ == "__main__":
    main()
