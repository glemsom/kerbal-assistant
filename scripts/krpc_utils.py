"""Shared kRPC utilities for Kerbal Assistant scripts.

Provides safe connect() and get_active_vessel() helpers that
all scripts should use instead of raw krpc.connect() / sc.active_vessel.

Key difference: get_active_vessel() returns None instead of throwing
ValueError when no vessel is active (e.g., at KSC scene).
"""

from __future__ import annotations

import json
import sys
from typing import Any, Optional

import krpc
from krpc.client import Client


def connect(
    name: str = "kerbal-assistant",
    address: str = "127.0.0.1",
    rpc_port: int = 50000,
    stream_port: int = 50001,
) -> Client:
    """Connect to kRPC server. Exits with JSON error on failure."""
    try:
        return krpc.connect(
            name=name,
            address=address,
            rpc_port=rpc_port,
            stream_port=stream_port,
        )
    except ConnectionRefusedError:
        _die("KSP not running or kRPC not responding (ConnectionRefusedError)")
    except TimeoutError:
        _die("kRPC connection timed out — is KSP running?")
    except Exception as e:
        _die(f"kRPC connection failed: {e}")


def get_active_vessel(conn: Client) -> Any:
    """Return active vessel or None if no vessel is active.

    sc.active_vessel throws ValueError when null — this wrapper
    returns None instead so callers can check with `if vessel:`.
    """
    try:
        return conn.space_center.active_vessel
    except ValueError:
        return None


def _die(msg: str) -> None:
    print(json.dumps({"error": msg}))
    sys.exit(1)
