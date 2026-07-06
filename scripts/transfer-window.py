#!/usr/bin/env python3
"""Transfer window calculator using kRPC celestial body data.

Requires KSP running with kRPC server. Connects to get current UT and orbital
data for Kerbin and the target body, then computes the next optimal transfer
window using phase angle approximation.

Usage:
    python scripts/transfer-window.py --target Duna
    python scripts/transfer-window.py --target Duna --source Kerbin
    python scripts/transfer-window.py --list-bodies
    python scripts/transfer-window.py --minify
    python scripts/transfer-window.py --standalone   (no kRPC needed)

Outputs JSON to stdout. Exits with non-zero on error.
"""

import json
import sys
import argparse
import math

# Lazy import krpc — standalone mode doesn't need it
krpc = None

# Standard gravitational parameter for Kerbin (m^3/s^2)
# KSP uses simplified physics: G * M for each body
MU_KERBIN = 3.5316000e12
# 1 Kerbin day in seconds
DAY_S = 6 * 60 * 60  # 6 hours
# 1 Kerbin year in seconds
YEAR_S = 426 * DAY_S  # 426 days

# Standard transfer phase angles (degrees) from Kerbin to each body
# For Hohmann transfer: phase = 180 * (1 - sqrt((r1/r2)^3))
# These are community-verified approximate values
STANDARD_PHASE = {
    "Moho": 170.0,   # ~170° behind Kerbin (retrograde ejection)
    "Eve": 162.0,    # ~162° behind Kerbin
    "Duna": 180.0,   # ~180° — Duna and Kerbin at opposition
    "Dres": 140.0,   # ~140°
    "Jool": 96.0,    # ~96°
    "Eeloo": 100.0,  # ~100°
    "Mun": 60.0,     # Quick transfer
    "Minmus": 45.0,
}

# Standard ejection dV from 80km Kerbin orbit (m/s)
STANDARD_EJECTION_DV = {
    "Moho": 2200,
    "Eve": 1070,
    "Duna": 1040,
    "Dres": 1540,
    "Jool": 1980,
    "Eeloo": 2070,
    "Mun": 860,
    "Minmus": 930,
}

# Approximate transfer duration from Kerbin (seconds)
STANDARD_TRANSFER_TIME = {
    "Moho": 120 * DAY_S,
    "Eve": 40 * DAY_S,
    "Duna": 65 * DAY_S,
    "Dres": 155 * DAY_S,
    "Jool": 285 * DAY_S,
    "Eeloo": 360 * DAY_S,
    "Mun": 6 * DAY_S,     # Hours, not days
    "Minmus": 18 * DAY_S,
}


def get_semi_major_axis(body) -> float:
    """Get semi-major axis of a body's orbit around its parent (meters)."""
    try:
        return body.orbit.semi_major_axis
    except Exception:
        return 0.0


def compute_hohmann_phase(sma_source: float, sma_target: float) -> float:
    """Compute Hohmann transfer phase angle (degrees).
    
    For a transfer from a circular orbit at sma_source to sma_target.
    phase = 180 * (1 - sqrt((r1 / r2)^3))
    Returns angle in degrees. Positive means target is ahead.
    """
    if sma_source <= 0 or sma_target <= 0:
        return 0.0
    # Ensure outer > inner
    r1 = min(sma_source, sma_target)
    r2 = max(sma_source, sma_target)
    phase = 180.0 * (1.0 - math.sqrt((r1 / r2) ** 3))
    # If target is inner (closer to sun), we need to be ahead of target
    if sma_target < sma_source:
        phase = 360.0 - phase
    return phase


def compute_transfer_duration(sma_source: float, sma_target: float) -> float:
    """Compute Hohmann transfer half-orbit period (seconds)."""
    if sma_source <= 0 or sma_target <= 0:
        return 0.0
    sma_transfer = (sma_source + sma_target) / 2.0
    # Kepler's third law: T = 2*pi * sqrt(a^3 / mu)
    T = 2 * math.pi * math.sqrt(sma_transfer ** 3 / MU_KERBIN)
    return T / 2  # Half orbit for transfer


def compute_phase_angle_from_krpc(conn, source_name: str, target_name: str) -> dict:
    """Compute phase angle between source and target using kRPC celestial body data."""
    try:
        source = conn.space_center.bodies[source_name]
        target = conn.space_center.bodies[target_name]
    except KeyError as e:
        return {"error": f"Unknown body: {e}"}

    # Get current universal time
    ut = conn.space_center.ut

    # Get orbital parameters
    source_sma = get_semi_major_axis(source)
    target_sma = get_semi_major_axis(target)

    if source_sma <= 0 or target_sma <= 0:
        return {"error": "Cannot compute phase angle: missing orbit data"}

    # Get current true anomaly / position
    # We'll use the orbit's mean anomaly at epoch and current time
    source_orbit = source.orbit
    target_orbit = target.orbit

    # Get current orbital positions
    source_pos = source_orbit.position_at(ut, reference_frame=conn.space_center.bodies[source.orbiting_body.name].reference_frame)
    target_pos = target_orbit.position_at(ut, reference_frame=conn.space_center.bodies[source.orbiting_body.name].reference_frame)

    # Phase angle from Kerbin's perspective: angle between Kerbin->Sun and Target->Sun vectors
    v1 = (source_pos[0], source_pos[1], source_pos[2])
    v2 = (target_pos[0], target_pos[1], target_pos[2])

    dot = v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]
    n1 = math.sqrt(v1[0]*v1[0] + v1[1]*v1[1] + v1[2]*v1[2])
    n2 = math.sqrt(v2[0]*v2[0] + v2[1]*v2[1] + v2[2]*v2[2])
    norm = n1 * n2
    if norm == 0:
        return {"error": "Cannot compute phase angle: zero position vector"}

    cos_angle = dot / norm
    cos_angle = max(-1.0, min(1.0, cos_angle))
    phase_rad = math.acos(cos_angle)
    phase_deg = math.degrees(phase_rad)

    # Determine sign (ahead/behind) using cross product z-component
    # cross_z = v1_x * v2_y - v1_y * v2_x
    cross_z = v1[0] * v2[1] - v1[1] * v2[0]
    if cross_z < 0:
        phase_deg = -phase_deg

    return {
        "source": source_name,
        "target": target_name,
        "current_phase_angle_deg": round(phase_deg, 1),
        "optimal_phase_angle_deg": round(compute_hohmann_phase(source_sma, target_sma), 1),
        "source_sma_km": round(source_sma / 1000, 1),
        "target_sma_km": round(target_sma / 1000, 1),
        "transfer_duration_s": round(compute_transfer_duration(source_sma, target_sma), 0),
        "transfer_duration_days": round(compute_transfer_duration(source_sma, target_sma) / DAY_S, 1),
        "current_ut": ut,
    }


def compute_phase_angle_standalone(source_name: str, target_name: str) -> dict:
    """Compute phase angle using standard community values (no kRPC)."""
    if target_name not in STANDARD_PHASE:
        return {
            "error": f"No standard phase angle for {target_name}. "
                     f"Available: {', '.join(sorted(STANDARD_PHASE.keys()))}"
        }

    phase = STANDARD_PHASE.get(target_name, 0)
    dv = STANDARD_EJECTION_DV.get(target_name, 0)
    duration = STANDARD_TRANSFER_TIME.get(target_name, 0)

    return {
        "source": source_name or "Kerbin",
        "target": target_name,
        "optimal_phase_angle_deg": phase,
        "ejection_dV_m_s": dv,
        "transfer_duration_s": duration,
        "transfer_duration_days": round(duration / DAY_S, 1),
        "note": "Standalone mode (no kRPC). Values are community estimates.",
    }


def list_bodies() -> dict:
    """List all known bodies with transfer data."""
    bodies = {}
    for name in STANDARD_PHASE:
        bodies[name] = {
            "phase_angle_deg": STANDARD_PHASE[name],
            "ejection_dV_m_s": STANDARD_EJECTION_DV.get(name),
            "transfer_days": round(STANDARD_TRANSFER_TIME.get(name, 0) / DAY_S, 1),
        }
    return {"bodies": bodies, "count": len(bodies)}


def main():
    parser = argparse.ArgumentParser(description="Transfer window calculator")
    parser.add_argument("--target", help="Target body (e.g., Duna)")
    parser.add_argument("--source", default="Kerbin", help="Source body (default: Kerbin)")
    parser.add_argument("--minify", action="store_true", help="Minify JSON output")
    parser.add_argument("--list-bodies", action="store_true", help="List available bodies")
    parser.add_argument("--standalone", action="store_true", help="Use community values instead of kRPC")
    args = parser.parse_args()

    indent = None if args.minify else 2

    if args.list_bodies:
        print(json.dumps(list_bodies(), indent=indent))
        return

    if not args.target:
        parser.print_help()
        sys.exit(1)

    if args.standalone:
        data = compute_phase_angle_standalone(args.source, args.target)
    else:
        # Try kRPC, fallback to standalone
        try:
            global krpc
            if krpc is None:
                import krpc as _krpc
                krpc = _krpc
            conn = krpc.connect(name="TransferWindow")
            data = compute_phase_angle_from_krpc(conn, args.source, args.target)
        except (ImportError, ConnectionError, AttributeError):
            data = compute_phase_angle_standalone(args.source, args.target)
            data["connection_error"] = "Could not connect to kRPC. Used community estimates."

    print(json.dumps(data, indent=indent))


if __name__ == "__main__":
    main()
