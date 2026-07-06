#!/usr/bin/env python3
"""Launch a craft from VAB or SPH to the launchpad/runway via kRPC.

Usage:
    python scripts/launch-vessel.py "Orbit 1"          # VAB → LaunchPad
    python scripts/launch-vessel.py "Orbit 1" --site Runway
    python scripts/launch-vessel.py --vab "My Rocket"
    python scripts/launch-vessel.py --sph "My Plane"
    python scripts/launch-vessel.py --list             # show available craft

Outputs JSON event on success.
Abort: Ctrl+C.
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
# Global clean-up
# ---------------------------------------------------------------------------
_conn: krpc.Client | None = None
_cleanup_done = False


def cleanup(*_: Any) -> None:
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True


signal.signal(signal.SIGINT, lambda *_: (cleanup(), sys.exit(1)))
signal.signal(signal.SIGTERM, lambda *_: (cleanup(), sys.exit(1)))


def connect() -> krpc.Client:
    global _conn
    try:
        _conn = krpc.connect(name="kerbal-assistant-launch-vessel", address="127.0.0.1", rpc_port=50000)
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


def list_vessels(sc: Any) -> dict[str, list[str]]:
    """Return dict of {facility: [craft_names]}."""
    result: dict[str, list[str]] = {}
    for facility_key, facility_label in [("VAB", "VAB"), ("SPH", "SPH")]:
        try:
            names = sorted(sc.launchable_vessels(facility_key))
            result[facility_label] = names
        except Exception:
            result[facility_label] = []
    return result


def launch_vessel(args: argparse.Namespace) -> None:
    conn = connect()
    sc = conn.space_center

    # -- List mode ---------------------------------------------------------------
    if args.list:
        vessels = list_vessels(sc)
        log_event("launchable_vessels",
                  VAB=[{"name": n} for n in vessels.get("VAB", [])],
                  SPH=[{"name": n} for n in vessels.get("SPH", [])])
        return

    # -- Determine facility and name --------------------------------------------
    name: str | None = None
    facility: str | None = None

    if args.vab:
        facility = "VAB"
        name = args.vab
    elif args.sph:
        facility = "SPH"
        name = args.sph
    elif args.name:
        # Auto-detect: try VAB first, then SPH
        vessels = list_vessels(sc)
        name = args.name
        if name in vessels.get("VAB", []):
            facility = "VAB"
        elif name in vessels.get("SPH", []):
            facility = "SPH"
        else:
            log_event("error", message=f"Craft '{name}' not found in VAB or SPH")
            sys.exit(1)

    if not name or not facility:
        log_event("error", message="No vessel name specified. Use --vab, --sph, or positional name.")
        sys.exit(1)

    # -- Launch ------------------------------------------------------------------
    recover = args.recover
    log_event("launch_start",
              vessel=name,
              facility=facility,
              site=args.site,
              recover=recover)

    launch_site = "LaunchPad" if facility == "VAB" else "Runway"
    # If --site explicitly given, override
    if args.site:
        launch_site = args.site

    try:
        sc.launch_vessel(facility, name, launch_site, recover)
    except Exception as e:
        log_event("error", message=f"Launch failed: {e}")
        sys.exit(1)

    # Wait for vessel to appear as active
    time.sleep(1.5)
    for _ in range(30):
        try:
            vessel = sc.active_vessel
            if vessel and vessel.name == name:
                sit = str(vessel.situation).split(".")[-1]
                log_event("launch_ok",
                          vessel=vessel.name,
                          situation=sit)
                return
        except Exception:
            pass
        time.sleep(0.5)

    log_event("warn", message="Vessel launched but not detected as active within timeout")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch a craft from VAB or SPH to the launchpad/runway.",
        epilog="Examples:\n"
               "  python scripts/launch-vessel.py \"Orbit 1\"\n"
               "  python scripts/launch-vessel.py --vab \"My Rocket\"\n"
               "  python scripts/launch-vessel.py --sph \"Spaceplane\" --site Runway\n"
               "  python scripts/launch-vessel.py --list",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("name", nargs="?", type=str, default=None,
                        help="Vessel name (craft file without .craft extension). Auto-detects VAB/SPH.")
    parser.add_argument("--vab", type=str, default=None,
                        help="Launch from VAB (craft name)")
    parser.add_argument("--sph", type=str, default=None,
                        help="Launch from SPH (craft name)")
    parser.add_argument("--site", "-s", type=str, default=None,
                        choices=["LaunchPad", "Runway"],
                        help="Launch site (default: LaunchPad for VAB, Runway for SPH)")
    parser.add_argument("--recover", "-r", action="store_true", default=True,
                        help="Recover existing active vessel before launch (default: True)")
    parser.add_argument("--no-recover", dest="recover", action="store_false",
                        help="Don't recover existing vessel")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List launchable vessels in VAB and SPH")

    args = parser.parse_args()

    if not args.list and not args.name and not args.vab and not args.sph:
        parser.print_help()
        sys.exit(1)

    try:
        launch_vessel(args)
    except Exception as e:
        log_event("error", message=str(e))
        cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
