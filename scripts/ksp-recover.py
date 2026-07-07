#!/usr/bin/env python3
"""Detect and recover KSP from stuck state after failed launches.

Connects via kRPC, attempts to revert to launch, recovers
recoverable vessels, then loads Space Center scene to force
clean state. Call before launch attempts:

    python scripts/ksp-recover.py && python scripts/launch-vessel.py "My Craft"

Output: single JSON line with "event": "recovered" or "event": "already_clean".
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
        print(json.dumps({"error": "kRPC connection timed out \u2014 is KSP running?"}))
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
            recovered_any = True
    except Exception:
        pass

    if recovered_any:
        # revert_to_launch already puts us at launchpad with clean state
        print(json.dumps({"event": "recovered"}))
        return

    # Step 2: Recover or skip stuck vessels
    for vessel in sc.vessels:
        sit = str(vessel.situation).split(".")[-1]
        if sit not in ("pre_launch", "flying", "sub_orbital"):
            continue

        name = vessel.name
        try:
            vessel.control.throttle = 0.0
        except Exception:
            pass

        if hasattr(vessel, "recoverable") and vessel.recoverable:
            try:
                vessel.recover()
                recovered_any = True
            except Exception:
                pass
        else:
            # Not recoverable; will be cleaned up by load_space_center
            pass

        time.sleep(0.2)

    # Step 3: Force-load Space Center to clear any modal dialogs / ghost state
    if hasattr(sc, "load_space_center"):
        try:
            sc.load_space_center()
            time.sleep(1.0)
        except Exception:
            pass

    if recovered_any:
        print(json.dumps({"event": "recovered"}))
    else:
        print(json.dumps({"event": "already_clean"}))


if __name__ == "__main__":
    main()
