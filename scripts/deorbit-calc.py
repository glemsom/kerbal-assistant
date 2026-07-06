#!/usr/bin/env python3
"""Deorbit burn calculator — input orbit, target Pe, output dV and landing info.

Usage:
    python scripts/deorbit-calc.py --apo 100000 --peri 95000 --body Kerbin --target-pe 35000
    python scripts/deorbit-calc.py --apo 100000 --peri 95000 --body Kerbin --target-pe 35000 --burn-at-apo
    python scripts/deorbit-calc.py --vessel "Station Alpha"       (live from kRPC)
    python scripts/deorbit-calc.py --vessel "Station Alpha" --target-pe 35000 --minify

Outputs JSON to stdout. Exits non-zero on error.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any

try:
    import krpc
except ImportError:
    print(json.dumps({"error": "krpc not installed. Run: pip install krpc"}))
    sys.exit(1)

# ---------------------------------------------------------------------------
# Body database (fallback when kRPC not available)
# ---------------------------------------------------------------------------
BODY_DATA: dict[str, dict[str, float]] = {
    "Kerbin":   {"mu": 3.5316000e12, "radius": 600_000, "atmo_depth": 70_000},
    "Mun":      {"mu": 6.5138398e10, "radius": 200_000, "atmo_depth": 0},
    "Minmus":   {"mu": 1.7658000e09, "radius": 60_000,  "atmo_depth": 0},
    "Duna":     {"mu": 3.0136321e11, "radius": 320_000, "atmo_depth": 50_000},
    "Eve":      {"mu": 8.1717302e12, "radius": 700_000, "atmo_depth": 90_000},
    "Moho":     {"mu": 1.6866098e11, "radius": 250_000, "atmo_depth": 0},
    "Dres":     {"mu": 2.1484489e10, "radius": 138_000, "atmo_depth": 0},
    "Laythe":   {"mu": 1.9620000e12, "radius": 500_000, "atmo_depth": 60_000},
    "Vall":     {"mu": 2.0748000e11, "radius": 300_000, "atmo_depth": 0},
    "Tylo":     {"mu": 2.8252800e12, "radius": 600_000, "atmo_depth": 0},
    "Bop":      {"mu": 2.4148308e09, "radius": 65_000,  "atmo_depth": 0},
    "Pol":      {"mu": 7.2170208e08, "radius": 44_000,  "atmo_depth": 0},
    "Eeloo":    {"mu": 7.4141000e10, "radius": 210_000, "atmo_depth": 0},
    "Gilly":    {"mu": 8.2850000e06, "radius": 13_000,  "atmo_depth": 0},
    "Ike":      {"mu": 1.8560000e10, "radius": 130_000, "atmo_depth": 0},
}

G0 = 9.80665  # standard gravity (m/s^2)


# ---------------------------------------------------------------------------
# Orbital mechanics helpers
# ---------------------------------------------------------------------------

def orbital_speed_at_radius(mu: float, r: float, sma: float) -> float:
    """Orbital speed at distance r from center, given semi-major axis sma.
    
    Uses vis-viva: v^2 = mu * (2/r - 1/a).
    """
    if r <= 0 or sma <= 0:
        return 0.0
    return math.sqrt(mu * (2.0 / r - 1.0 / sma))


def deorbit_delta_v(
    mu: float,
    body_r: float,
    apo_alt: float,
    peri_alt: float,
    target_pe_alt: float,
    burn_at_apo: bool = True,
) -> dict[str, Any]:
    """Compute dV to lower periapsis to target_pe_alt.
    
    Assumes burn occurs at apoapsis (most efficient for lowering Pe).
    Returns dict with dV, velocities, and orbit parameters.
    """
    r_apo = body_r + apo_alt
    r_pe = body_r + peri_alt
    r_target_pe = body_r + target_pe_alt

    a_cur = (r_apo + r_pe) / 2.0  # current semi-major axis

    if burn_at_apo:
        # Speed at current apoapsis
        v_cur = orbital_speed_at_radius(mu, r_apo, a_cur)

        # After burn, new orbit has same apoapsis but lower periapsis
        a_new = (r_apo + r_target_pe) / 2.0
        v_new = orbital_speed_at_radius(mu, r_apo, a_new)

        dv = v_cur - v_new
        burn_pos = "apoapsis"
        r_burn = r_apo
    else:
        # Burn at periapsis (less efficient for lowering Pe, but sometimes needed)
        v_cur = orbital_speed_at_radius(mu, r_pe, a_cur)
        a_new = (r_pe + r_target_pe) / 2.0
        v_new = orbital_speed_at_radius(mu, r_pe, a_new)
        dv = v_cur - v_new
        burn_pos = "periapsis"
        r_burn = r_pe

    if dv < 0:
        dv = 0.0
        note = "Target Pe already below current Pe — no burn needed"
    else:
        note = None

    return {
        "body_mu": mu,
        "body_radius": body_r,
        "current_apoapsis_alt": apo_alt,
        "current_periapsis_alt": peri_alt,
        "target_periapsis_alt": target_pe_alt,
        "burn_position": burn_pos,
        "burn_altitude": r_burn - body_r,
        "delta_v_required": round(dv, 2),
        "current_speed_at_burn": round(v_cur, 2),
        "new_speed_after_burn": round(v_new, 2) if dv > 0 else round(v_cur, 2),
        "new_semi_major_axis": round((r_apo + r_target_pe) / 2.0, 1) if burn_at_apo else round((r_pe + r_target_pe) / 2.0, 1),
        "new_apoapsis_alt": round(apo_alt, 1) if burn_at_apo else round(target_pe_alt, 1),
        "new_periapsis_alt": round(target_pe_alt, 1) if burn_at_apo else round(apo_alt, 1),
        "note": note,
    }


def burn_duration_info(dv: float, isp: float, thrust_n: float, mass_kg: float) -> dict[str, Any]:
    """Estimate burn duration and fuel consumption.
    
    Uses: t = (Isp * g0 * m0 / F) * (1 - exp(-dV / (Isp * g0)))
    Fuel consumption: mf = m0 - m0 * exp(-dV / (Isp * g0))
    """
    if thrust_n <= 0 or dv <= 0 or mass_kg <= 0:
        return {"burn_duration_s": 0.0, "fuel_consumed_kg": 0.0}

    v_exhaust = isp * G0
    burn_t = (v_exhaust * mass_kg / thrust_n) * (1.0 - math.exp(-dv / v_exhaust))
    fuel_kg = mass_kg * (1.0 - math.exp(-dv / v_exhaust))

    return {
        "burn_duration_s": round(burn_t, 2),
        "fuel_consumed_kg": round(fuel_kg, 2),
        "isp_vac": isp,
        "thrust_n": thrust_n,
        "initial_mass_kg": round(mass_kg, 2),
    }


def estimate_landing_ellipse(
    body_r: float,
    mu: float,
    has_atmo: bool,
    apo_alt: float,
    target_pe_alt: float,
) -> dict[str, Any]:
    """Estimate landing zone from ballistic trajectory after deorbit.
    
    For airless bodies: simple suborbital arc.
    For atmospheric bodies: very approximate — actual landing depends on drag.
    """
    r_apo = body_r + apo_alt
    r_pe = body_r + target_pe_alt
    a_deorbit = (r_apo + r_pe) / 2.0
    e = (r_apo - r_pe) / (r_apo + r_pe)  # eccentricity

    # True anomaly at entry interface
    # For atmospheric: at atmo_depth altitude
    # For airless: at surface
    entry_r = body_r + (target_pe_alt if not has_atmo else max(target_pe_alt, 0))

    if entry_r <= r_pe:
        entry_r = r_pe + 100  # just above Pe

    # True anomaly from periapsis for a given radius on a Keplerian orbit
    # theta = arccos((a*(1-e^2) - r) / (e * r))
    try:
        cos_theta = (a_deorbit * (1.0 - e * e) - entry_r) / (e * entry_r)
        cos_theta = max(-1.0, min(1.0, cos_theta))
        theta = math.acos(cos_theta)
    except (ValueError, ZeroDivisionError):
        theta = math.pi  # falling straight down

    # Downrange angle from entry to periapsis (impact)
    # For a non-rotating body, this is the angle from entry to Pe
    downrange_angle_rad = math.pi - theta  # from entry to Pe

    # Great-circle distance
    downrange_km = body_r * downrange_angle_rad / 1000.0

    # Impact speed (at surface or entry interface)
    v_entry = orbital_speed_at_radius(mu, entry_r, a_deorbit)

    return {
        "entry_altitude": round(entry_r - body_r, 1),
        "downrange_distance_km": round(downrange_km, 1),
        "downrange_angle_deg": round(math.degrees(downrange_angle_rad), 2),
        "entry_speed_m_s": round(v_entry, 2),
        "orbit_eccentricity": round(e, 6),
        "note": "Landing ellipse is approximate (no drag model). "
                "For atmospheric bodies, actual downrange is much shorter.",
    }


# ---------------------------------------------------------------------------
# kRPC integration
# ---------------------------------------------------------------------------

def resolve_body_from_krpc(conn, body_name: str | None) -> tuple[str, float, float, bool]:
    """Get body parameters from kRPC (fallback to BODY_DATA)."""
    sc = conn.space_center
    if body_name and body_name in sc.bodies:
        body = sc.bodies[body_name]
        return (
            body.name,
            body.gravitational_parameter,
            body.equatorial_radius,
            body.has_atmosphere,
        )
    # Use active vessel's orbit body
    vessel = sc.active_vessel
    if vessel and vessel.orbit:
        body = vessel.orbit.body
        return (
            body.name,
            body.gravitational_parameter,
            body.equatorial_radius,
            body.has_atmosphere,
        )
    # Fallback to static data
    if body_name and body_name in BODY_DATA:
        d = BODY_DATA[body_name]
        return (body_name, d["mu"], d["radius"], d["atmo_depth"] > 0)
    return ("Kerbin", BODY_DATA["Kerbin"]["mu"], BODY_DATA["Kerbin"]["radius"], True)


def get_orbit_from_krpc(conn) -> dict[str, Any]:
    """Read current orbit from active vessel."""
    sc = conn.space_center
    vessel = sc.active_vessel
    if vessel is None:
        return {"error": "No active vessel"}
    orbit = vessel.orbit
    if orbit is None:
        return {"error": "Vessel is not in orbit"}
    return {
        "apoapsis_alt": orbit.apoapsis_altitude,
        "periapsis_alt": orbit.periapsis_altitude,
        "body_name": orbit.body.name,
        "inclination": orbit.inclination,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_result(args: argparse.Namespace) -> dict[str, Any]:
    """Build the full deorbit calculation result."""
    mu: float = 0.0
    r_body: float = 0.0
    has_atmo = False
    body_name = args.body or "Kerbin"

    if args.vessel:
        # Live from kRPC
        try:
            conn = krpc.connect(name="kerbal-assistant-deorbit-calc",
                                address="127.0.0.1", rpc_port=50000)
        except Exception as e:
            return {"error": f"kRPC connection failed: {e}"}

        body_name, mu, r_body, has_atmo = resolve_body_from_krpc(conn, args.body)

        if not args.apo or not args.peri:
            orbit_data = get_orbit_from_krpc(conn)
            if "error" in orbit_data:
                return orbit_data
            args.apo = orbit_data["apoapsis_alt"]
            args.peri = orbit_data["periapsis_alt"]
            body_name = orbit_data["body_name"]
    else:
        # Static mode
        if args.body not in BODY_DATA:
            return {"error": f"Unknown body: {args.body}. Known: {', '.join(sorted(BODY_DATA))}"}
        d = BODY_DATA[args.body]
        mu = d["mu"]
        r_body = d["radius"]
        has_atmo = d["atmo_depth"] > 0

    if not args.apo or not args.peri:
        return {"error": "Need --apo and --peri (or use --vessel to read live)"}

    target_pe = args.target_pe
    if target_pe is None:
        # Default: enter upper atmosphere or 10 km above surface
        if has_atmo:
            target_pe = args.atmo_entry if args.atmo_entry else 35000.0
        else:
            target_pe = 10000.0

    deorbit = deorbit_delta_v(
        mu=mu,
        body_r=r_body,
        apo_alt=args.apo,
        peri_alt=args.peri,
        target_pe_alt=target_pe,
        burn_at_apo=args.burn_at_apo,
    )

    result: dict[str, Any] = {
        "body": body_name,
        "has_atmosphere": has_atmo,
        "deorbit_burn": deorbit,
        "landing_ellipse": estimate_landing_ellipse(
            body_r=r_body,
            mu=mu,
            has_atmo=has_atmo,
            apo_alt=args.apo,
            target_pe_alt=target_pe,
        ),
    }

    # Burn duration if ISP and thrust provided
    if args.isp is not None and args.thrust is not None and args.mass is not None:
        dur = burn_duration_info(
            dv=deorbit.get("delta_v_required", 0),
            isp=args.isp,
            thrust_n=args.thrust,
            mass_kg=args.mass,
        )
        result["burn_execution"] = dur

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Deorbit burn calculator")
    parser.add_argument("--apo", type=float, help="Current apoapsis altitude (m)")
    parser.add_argument("--peri", type=float, help="Current periapsis altitude (m)")
    parser.add_argument("--body", help="Celestial body name (default: from orbit)")
    parser.add_argument("--target-pe", type=float, help="Target periapsis altitude after burn (m)")
    parser.add_argument("--atmo-entry", type=float, default=35000,
                        help="Default target Pe for atmospheric entry (m, default: 35000)")
    parser.add_argument("--burn-at-apo", action="store_true", default=True,
                        help="Burn at apoapsis (default: True)")
    parser.add_argument("--vessel", help="Read orbit from live kRPC vessel by name")
    parser.add_argument("--isp", type=float, help="Vacuum Isp (s) for burn duration calc")
    parser.add_argument("--thrust", type=float, help="Thrust (N) for burn duration calc")
    parser.add_argument("--mass", type=float, help="Vessel mass (kg) for burn duration calc")
    parser.add_argument("--minify", action="store_true", help="Minify JSON output")

    args = parser.parse_args()

    result = build_result(args)
    indent = None if args.minify else 2
    print(json.dumps(result, indent=indent))

    if "error" in result:
        sys.exit(1)


if __name__ == "__main__":
    main()
