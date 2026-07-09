---
name: krpc-patterns
description: Code examples for kRPC patterns — connectivity check, maneuver node burns, coordinate transforms, streaming. Loaded on demand from krpc-reference.md.
---

# Common kRPC Patterns

Loaded on demand from `krpc-reference.md` when code examples needed.

## Connectivity check

Prefer `scripts/ksp-status.py --all` over inline Python. Handles null vessel, connection refused, timeout. JSON output. Exit 0 = connected, exit 1 = failure.

If inline needed, use `krpc_utils.get_active_vessel()`:

```python
import krpc
import sys
from scripts.krpc_utils import connect, get_active_vessel

conn = connect()  # exits with JSON error on failure
vessel = get_active_vessel(conn)  # None instead of ValueError

if vessel:
    print(f"Vessel: {vessel.name}")
else:
    print("No active vessel (KSC scene)")
```

## Burn at a maneuver node

```python
import time
node = v.control.add_node(ut, 850.0, 0.0, 0.0)
# Orient to burn direction
v.auto_pilot.target_direction(node.burn_vector(v.orbital_reference_frame))
v.auto_pilot.engage()
v.auto_pilot.wait()
# Execute burn
burn_time = node.delta_v / (v.available_thrust / v.mass)
v.control.throttle = 1.0
time.sleep(burn_time * 0.5)  # crude midpoint
# Fine-tune
while node.remaining_delta_v > 0.5:
    time.sleep(0.1)
v.control.throttle = 0.0
node.remove()
```

## Coordinate transforms

```python
# World position → orbital frame
orbital_pos = conn.space_center.transform_position(
    world_pos, 
    conn.space_center.bodies['Kerbin'].reference_frame,
    v.orbital_reference_frame
)
```

## Streaming (real-time updates)

```python
import krpc
import sys
from scripts.krpc_utils import get_active_vessel

conn = krpc.connect(name="stream-test")
vessel = get_active_vessel(conn)
if not vessel:
    print("No active vessel", file=sys.stderr)
    sys.exit(1)

# Create a stream for vessel altitude
flight = vessel.flight(vessel.orbit.body.reference_frame)
alt_stream = conn.add_stream(getattr, flight, "mean_altitude")
# Read it
alt_stream()  # returns current altitude
# Remove when done
conn.remove_stream(alt_stream)
```
