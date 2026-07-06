#!/usr/bin/env python3
"""Delta-V calculator per stage — rocket equation solver.

Usage:
    python scripts/dv-calc.py --isp 350 --wet 40000 --dry 5000
    python scripts/dv-calc.py --isp 320,350 --wet 10000,3000 --dry 1000,500 --stages 2
    python scripts/dv-calc.py --isp 320,350 --wet 10000,3000 --dry 1000,500 --stages 2 --payload 2000
    python scripts/dv-calc.py --json < telemetry.json   (pipe JSON with mass data)

Outputs JSON to stdout. Exits with non-zero on error.
"""

import json
import sys
import argparse
import math

# Standard gravity (m/s^2)
G0 = 9.80665


def dv_stage(isp_s: float, wet_mass: float, dry_mass: float) -> float:
    """Delta-V for a single stage using the Tsiolkovsky rocket equation."""
    if dry_mass <= 0 or wet_mass <= dry_mass:
        return 0.0
    return isp_s * G0 * math.log(wet_mass / dry_mass)


def twr_stage(thrust_n: float, wet_mass: float, body_g: float = 9.80665) -> float:
    """Thrust-to-weight ratio for a stage."""
    if wet_mass <= 0:
        return 0.0
    return thrust_n / (wet_mass * body_g)


def burn_duration(dv: float, isp_s: float, thrust_n: float, initial_mass: float) -> float:
    """Approximate burn duration (seconds) assuming constant thrust, linear mass loss.
    
    Uses: t = (Isp * g0 * m0 / F) * (1 - exp(-dV / (Isp * g0)))
    """
    if thrust_n <= 0 or dv <= 0:
        return 0.0
    exhaust_v = isp_s * G0
    return (exhaust_v * initial_mass / thrust_n) * (1 - math.exp(-dv / exhaust_v))


def parse_stage_args(args: argparse.Namespace):
    """Parse ISP, wet/dry mass arrays from CLI args."""
    isps = [float(x) for x in args.isp.split(",")]
    wets = [float(x) for x in args.wet.split(",")]
    drys = [float(x) for x in args.dry.split(",")]

    if args.stages is None:
        args.stages = max(len(isps), len(wets), len(drys))

    # Pad / truncate to args.stages
    while len(isps) < args.stages:
        isps.append(isps[-1] if isps else 0)
    while len(wets) < args.stages:
        wets.append(wets[-1] if wets else 0)
    while len(drys) < args.stages:
        drys.append(drys[-1] if drys else 0)

    isps = isps[:args.stages]
    wets = wets[:args.stages]
    drys = drys[:args.stages]

    return isps, wets, drys


def calc(args: argparse.Namespace) -> dict:
    """Run dV calculation and return result dict."""
    result = {
        "stages": [],
        "total_dv": 0.0,
        "total_wet_mass": 0.0,
        "total_dry_mass": 0.0,
        "payload_mass": args.payload,
        "effective_payload_fraction": 0.0,
        "body": args.body,
        "body_gravity": args.gravity,
    }

    if args.json:
        # Parse mass data from piped JSON (e.g., from live-telemetry.py)
        try:
            data = json.loads(args.json)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON input: {e}"}

        vessel = data.get("vessel", {})
        mass = vessel.get("mass", {})
        result["total_wet_mass"] = mass.get("total", 0.0)
        result["total_dry_mass"] = mass.get("dry", 0.0)
        result["payload_mass"] = mass.get("payload", args.payload)

        # If no CLI ISP/stages, try to infer from resources or set defaults
        if args.isp is None:
            args.isp = "350"
        if args.wet is None:
            args.wet = str(result["total_wet_mass"])
        if args.dry is None:
            args.dry = str(result["total_dry_mass"])
        if args.stages is None:
            args.stages = 1

    isps, wets, drys = parse_stage_args(args)

    running_wet = sum(wets)
    running_dry = sum(drys)
    result["total_wet_mass"] = running_wet
    result["total_dry_mass"] = running_dry

    for i in range(args.stages):
        wet = wets[i]
        dry = drys[i]
        isp = isps[i]
        dv = dv_stage(isp, wet, dry)

        thrust_n = args.thrust[i] if args.thrust and i < len(args.thrust) else 0.0
        twr = twr_stage(thrust_n, wet, args.gravity) if thrust_n > 0 else None
        burn_t = burn_duration(dv, isp, thrust_n, wet) if thrust_n > 0 else None

        stage_info = {
            "stage": i + 1,
            "isp_vac": isp,
            "wet_mass": wet,
            "dry_mass": dry,
            "propellant_mass": wet - dry,
            "mass_ratio": wet / dry if dry > 0 else None,
            "dv": round(dv, 1),
            "thrust_n": thrust_n if thrust_n > 0 else None,
            "twr": round(twr, 2) if twr is not None else None,
            "burn_duration_s": round(burn_t, 1) if burn_t is not None else None,
        }
        result["stages"].append(stage_info)

    result["total_dv"] = round(sum(s["dv"] for s in result["stages"]), 1)

    total_mass = result["total_wet_mass"] + result["payload_mass"]
    if total_mass > 0:
        result["effective_payload_fraction"] = round(
            result["payload_mass"] / total_mass, 4
        )

    return result


def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Delta-V calculator — rocket equation")
    parser.add_argument("--isp", help="Vacuum Isp per stage, comma-sep (e.g., 320,350)")
    parser.add_argument("--wet", help="Wet mass per stage in kg, comma-sep")
    parser.add_argument("--dry", help="Dry mass per stage in kg, comma-sep")
    parser.add_argument("--stages", type=int, default=None, help="Number of stages")
    parser.add_argument("--payload", type=float, default=0.0, help="Payload mass in kg")
    parser.add_argument("--thrust", help="Thrust per stage in N, comma-sep")
    parser.add_argument("--body", default="Kerbin", help="Celestial body (default: Kerbin)")
    parser.add_argument("--gravity", type=float, default=9.80665, help="Surface gravity m/s² (default: 9.80665)")
    parser.add_argument("--json", help="JSON string with vessel mass data (from telemetry)")
    parser.add_argument("--minify", action="store_true", help="Minify JSON output")
    return parser


def main():
    parser = setup_parser()
    args = parser.parse_args()

    if args.thrust:
        args.thrust = [float(x) for x in args.thrust.split(",")]
    else:
        args.thrust = []

    # Require at least some input
    if not args.isp and not args.json:
        parser.print_help()
        sys.exit(1)

    result = calc(args)
    indent = None if args.minify else 2
    print(json.dumps(result, indent=indent))


if __name__ == "__main__":
    main()
