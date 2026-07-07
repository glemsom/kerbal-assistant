#!/usr/bin/env python3
"""Detect and recover KSP from stuck state after failed launches.

Connects via kRPC, attempts to revert to launch, recovers/terminates
any pre_launch or flying vessels, then loads Space Center scene to
force clean state. Call before launch attempts:

    python scripts/ksp-recover.py && python scripts/launch-vessel.py "My Craft"

Output: JSON with "event": "recovered" or "event": "already_clean".
Exit code 0 on success, 1 on failure.
"""
from __future__ import annotations

import json
import sys
import time

try:
    import krpc
except ImportError:
    print(json.dumps({"error": "krpc not installed. Run: pip install krpc"}))
    sys.exit(1)


def connect() -> krpc.Client | None:
    """Try connecting to kRPC, return None on failure."""
    try:
        return krpc.connect(name="ksp-recover", address="127.0.0.1", rpc_port=50000)
    except ConnectionRefusedError:
        print(json.dumps({"error": "KSP not running or kRPC not responding (ConnectionRefusedError)"}))
        return None
    except TimeoutError:
        print(json.dumps({"error": "kRPC connection timed out — is KSP running?"}))
        return None
    except Exception as e:
        print(json.dumps({"error": f"kRPC connection failed: {e}"}))
        return None


def main() -> None:
    conn = connect()
    if conn is None:
        sys.exit(1)

    sc = conn.space_center
    recovered_any = False

    # Step 1: Try revert-to-launch (quickest recovery if available)
    try:
        if sc.can_revert_to_launch():
            sc.revert_to_launch()
            time.sleep(1.0)
            print(json.dumps({"event": "reverted_to_launch"}))
            recovered_any = True
    except Exception:
        pass

    # Step 2: List vessels and try to recover/terminate stuck ones
    for vessel in sc.vessels:
        sit = str(vessel.situation).split(".")[-1]
        if sit in ("pre_launch", "flying", "sub_orbital"):
            name = vessel.name
            try:
                vessel.control.throttle = 0.0
                # Try SpaceCenter recover_vessel if available
                try:
                    sc.recover_vessel(vessel)
                except Exception:
                    # Fallback: try vessel-level recover
                    try:
                        vessel.recover()
                    except Exception:
                        # Last resort: terminate via staging
                        try:
                            vessel.control.activate_next_stage()
                        except Exception:
                            pass
                print(json.dumps({
                    "event": "recover_vessel",
                    "vessel": name,
                    "situation": sit,
                }))
                recovered_any = True
            except Exception:
                print(json.dumps({
                    "event": "terminate_vessel",
                    "vessel": name,
                    "situation": sit,
                }))
                recovered_any = True
            time.sleep(0.2)

    # Step 3: Force-load Space Center to clear any modal dialogs / ghost state
    try:
        sc.load_space_center()
        time.sleep(1.0)
        print(json.dumps({"event": "space_center_loaded"}))
    except Exception as e:
        print(json.dumps({
            "event": "load_space_center_failed",
            "error": str(e),
        }))
        sys.exit(1)

    if recovered_any:
        print(json.dumps({"event": "recovered"}))
    else:
        print(json.dumps({"event": "already_clean"}))


if __name__ == "__main__":
    main()
