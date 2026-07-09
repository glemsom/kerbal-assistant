#!/usr/bin/env python3
"""Generate a simple 'Flea Hopper' .craft file for early career contracts.

Design: suborbital science hopper using only start-tech parts.
  Stage 0: RT-5 Flea ignites (liftoff)
  Stage-1: Mk16 parachute deploy (re-entry)

Parts (top→bottom):
  - Mk16 Parachute (on pod top)
  - Mk1 Command Pod (root)
  - Mystery Goo (radial on pod)
  - RT-5 Flea SRB (under pod)
  - 3× Basic Fin (on Flea, 120° symmetry)

Completes both active contracts:
  - FIRSTLAUNCH (launch any vessel)
  - SCIENCE (collect/recover mystery goo data)

Usage:
    .venv/bin/python scripts/build-flea-hopper.py
    .venv/bin/python scripts/build-flea-hopper.py --name "Flea Hopper" --sandbox

See docs/agents/craft-format.md for format reference.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import krpc
except ImportError:
    print(json.dumps({"error": "krpc not installed. Run: pip install krpc"}))
    sys.exit(1)

KSP_DIR = Path.home() / ".local/share/Steam/steamapps/common/Kerbal Space Program"


def find_active_save() -> Path | None:
    """Return path to the most recently modified save Ships/VAB dir."""
    saves_dir = KSP_DIR / "saves"
    if not saves_dir.exists():
        return None

    best: tuple[float, Path] = (0, None)
    for entry in saves_dir.iterdir():
        vab_dir = entry / "Ships" / "VAB"
        if vab_dir.exists():
            mtime = os.path.getmtime(vab_dir)
            if mtime > best[0]:
                best = (mtime, vab_dir)
    return best[1]


# ---------------------------------------------------------------------------
# Craft template — pre-computed positions for VAB build platform
# All rescaleFactor = 1 except GooExperiment (0.6)
#
# Node reference:
#   mk1pod.v2:      top_y =  0.642376,  bottom_y = -0.405038
#   parachuteSingle: bottom_y = -0.120649
#   solidBooster.sm.v2: top_y = 0.7575, bottom_y = -0.9975
#   GooExperiment:  radial attach (0, 0, -0.15) * 0.6
#   basicFin:       radial attach (0, 0, 0)
#
# Coordinate origin at pod center. In VAB world-space the root
# pod sits at Y = 1.5 (matching the minimal template convention).
# ---------------------------------------------------------------------------

# Pod at Y=1.5
POD_Y = 1.5
POD_TOP = POD_Y + 0.642376   # 2.142376  — chute bottom node aligns here
POD_BOTTOM = POD_Y - 0.405038  # 1.094962 — flea top node aligns here

# Parachute: chute_bottom_y = chute_center_y - 0.120649
#   chute_center_y - 0.120649 = POD_TOP
#   chute_center_y = POD_TOP + 0.120649
CHUTE_Y = POD_TOP + 0.120649  # 2.263025

# Flea: flea_top_y = flea_center_y + 0.7575
#   flea_center_y + 0.7575 = POD_BOTTOM
#   flea_center_y = POD_BOTTOM - 0.7575
FLEA_Y = POD_BOTTOM - 0.7575  # 0.337462

# Flea bottom (for fin Y positioning)
FLEA_BOTTOM = FLEA_Y - 0.9975  # -0.660038

# Mystery Goo: radial attach to pod at Y ≈ pod center
GOO_Y = POD_Y  # 1.5
GOO_RADIUS = 0.625  # ~1.25m pod radius, goo sticks to side

# Fins: radial on Flea body, ~mid-height
FIN_Y = FLEA_Y  # centered on flea

CRAFT_TEMPLATE = """ship = {name}
version = 1.12.5
description = Suborbital science hopper for early career contracts
type = VAB
size = 1.25,5.5,1.25
steamPublishedFileId = 0
persistentId = 233386374
rot = 0,0,0,0
missionFlag = Squad/Flags/default
vesselType = Ship
OverrideDefault = False,False,False,False
OverrideActionControl = 0,0,0,0
OverrideAxisControl = 0,0,0,0
OverrideGroupNames = ,,,

PART
{{
	part = mk1pod.v2_{pod_id}
	partName = Part
	persistentId = {pod_id}
	pos = 0,{pod_y},0
	attPos = 0,0,0
	attPos0 = 0,{pod_y},0
	rot = 0,0,0,1
	attRot = 0,0,0,1
	attRot0 = 0,0,0,1
	mir = 1,1,1
	symMethod = Radial
	autostrutMode = Off
	rigidAttachment = False
	istg = -1
	resPri = 0
	dstg = 0
	sidx = -1
	sqor = -1
	sepI = -1
	attm = 0
	sameVesselCollision = False
	modCost = 0
	modMass = 0
	modSize = 0,0,0
	link = parachuteSingle_{chute_id}
	link = GooExperiment_{goo_id}
	link = solidBooster.sm.v2_{flea_id}
	attN = top,parachuteSingle_{chute_id}_0|0.642375588|0_0|1|0_0|0.642375588|0_0|1|0
	attN = bottom,solidBooster.sm.v2_{flea_id}_0|-0.40503791|0_0|-1|0_0|-0.40503791|0_0|-1|0
	EVENTS
	{{
	}}
	ACTIONS
	{{
		ToggleSameVesselInteraction
		{{
			actionGroup = None
			wasActiveBeforePartWasAdjusted = False
		}}
		SetSameVesselInteraction
		{{
			actionGroup = None
			wasActiveBeforePartWasAdjusted = False
		}}
	}}
}}

PART
{{
	part = parachuteSingle_{chute_id}
	partName = Part
	persistentId = {chute_id}
	pos = 0,{chute_y},0
	attPos = 0,0,0
	attPos0 = 0,{chute_y},0
	rot = 0,0,0,1
	attRot = 0,0,0,1
	attRot0 = 0,0,0,1
	mir = 1,1,1
	symMethod = Radial
	autostrutMode = Off
	rigidAttachment = False
	istg = 0
	resPri = 0
	dstg = 0
	sidx = 1
	sqor = -1
	sepI = -1
	attm = 0
	sameVesselCollision = False
	modCost = 0
	modMass = 0
	modSize = 0,0,0
	EVENTS
	{{
	}}
	ACTIONS
	{{
		Deploy
		{{
			actionGroup = None
		}}
	}}
	attN = bottom,mk1pod.v2_{pod_id}_0|-0.120649|0_0|-1|0_0|-0.120649|0_0|-1|0
}}

PART
{{
	part = GooExperiment_{goo_id}
	partName = Part
	persistentId = {goo_id}
	pos = {goo_r},1.5,{goo_z}
	attPos = 0,0,0
	attPos0 = {goo_r},1.5,{goo_z}
	rot = 0,0,0,1
	attRot = 0,0,0,1
	attRot0 = 0,0,0,1
	mir = 1,1,1
	symMethod = Radial
	autostrutMode = Off
	rigidAttachment = False
	istg = -1
	resPri = 0
	dstg = 0
	sidx = -1
	sqor = -1
	sepI = -1
	attm = 1
	sameVesselCollision = False
	modCost = 0
	modMass = 0
	modSize = 0,0,0
	EVENTS
	{{
	}}
	ACTIONS
	{{
		RunTest
		{{
			actionGroup = Custom01
		}}
	}}
}}

PART
{{
	part = solidBooster.sm.v2_{flea_id}
	partName = Part
	persistentId = {flea_id}
	pos = 0,{flea_y},0
	attPos = 0,0,0
	attPos0 = 0,{flea_y},0
	rot = 0,0,0,1
	attRot = 0,0,0,1
	attRot0 = 0,0,0,1
	mir = 1,1,1
	symMethod = Radial
	autostrutMode = Off
	rigidAttachment = False
	istg = 0
	resPri = 0
	dstg = 0
	sidx = 0
	sqor = -1
	sepI = -1
	attm = 0
	sameVesselCollision = False
	modCost = 0
	modMass = 0
	modSize = 0,0,0
	link = basicFin_{fin1_id}
	link = basicFin_{fin2_id}
	link = basicFin_{fin3_id}
	attN = top,mk1pod.v2_{pod_id}_0|0.7575|0_0|1|0_0|0.7575|0_0|1|0
	EVENTS
	{{
	}}
	ACTIONS
	{{
	}}
}}

PART
{{
	part = basicFin_{fin1_id}
	partName = Part
	persistentId = {fin1_id}
	pos = {fin1_x},{fin_y},{fin1_z}
	attPos = 0,0,0
	attPos0 = {fin1_x},{fin_y},{fin1_z}
	rot = 0,0,0,1
	attRot = 0,0,0,1
	attRot0 = 0,0,0,1
	mir = 1,1,1
	symMethod = Mirror
	autostrutMode = Off
	rigidAttachment = False
	istg = -1
	resPri = 0
	dstg = 0
	sidx = -1
	sqor = -1
	sepI = -1
	attm = 1
	sameVesselCollision = False
	modCost = 0
	modMass = 0
	modSize = 0,0,0
	EVENTS
	{{
	}}
	ACTIONS
	{{
	}}
}}

PART
{{
	part = basicFin_{fin2_id}
	partName = Part
	persistentId = {fin2_id}
	pos = {fin2_x},{fin_y},{fin2_z}
	attPos = 0,0,0
	attPos0 = {fin2_x},{fin_y},{fin2_z}
	rot = 0,0,0,1
	attRot = 0,0,0,1
	attRot0 = 0,0,0,1
	mir = 1,1,1
	symMethod = Mirror
	autostrutMode = Off
	rigidAttachment = False
	istg = -1
	resPri = 0
	dstg = 0
	sidx = -1
	sqor = -1
	sepI = -1
	attm = 1
	sameVesselCollision = False
	modCost = 0
	modMass = 0
	modSize = 0,0,0
	EVENTS
	{{
	}}
	ACTIONS
	{{
	}}
}}

PART
{{
	part = basicFin_{fin3_id}
	partName = Part
	persistentId = {fin3_id}
	pos = {fin3_x},{fin_y},{fin3_z}
	attPos = 0,0,0
	attPos0 = {fin3_x},{fin_y},{fin3_z}
	rot = 0,0,0,1
	attRot = 0,0,0,1
	attRot0 = 0,0,0,1
	mir = 1,1,1
	symMethod = Mirror
	autostrutMode = Off
	rigidAttachment = False
	istg = -1
	resPri = 0
	dstg = 0
	sidx = -1
	sqor = -1
	sepI = -1
	attm = 1
	sameVesselCollision = False
	modCost = 0
	modMass = 0
	modSize = 0,0,0
	EVENTS
	{{
	}}
	ACTIONS
	{{
	}}
}}
"""


def generate_craft(name: str) -> str:
    """Generate craft file content with unique persistent IDs."""
    import random
    import math

    rng = random.Random(name)

    def pid() -> int:
        return rng.randint(100000000, 999999999)

    # Fin positions: 3 fins at 120° spacing around the Flea body
    # Flea radius ≈ 0.625m (size 1)
    fin_radius = 0.625
    fin_angles = [90, 210, 330]  # Start at 90° for VAB coordinates

    fin_positions = []
    for angle in fin_angles:
        rad = math.radians(angle)
        fx = fin_radius * math.cos(rad)
        fz = fin_radius * math.sin(rad)
        fin_positions.append((fx, fz))

    # Goo position: single radial attach on pod, +Z side
    goo_radius = 0.625 + 0.09  # pod radius + goo half-thickness

    return CRAFT_TEMPLATE.format(
        name=name,
        pod_id=pid(),
        pod_y=POD_Y,
        chute_id=pid(),
        chute_y=CHUTE_Y,
        goo_id=pid(),
        goo_r=0.0,
        goo_z=goo_radius,
        flea_id=pid(),
        flea_y=FLEA_Y,
        fin1_id=pid(),
        fin2_id=pid(),
        fin3_id=pid(),
        fin_y=FIN_Y,
        fin1_x=fin_positions[0][0],
        fin1_z=fin_positions[0][1],
        fin2_x=fin_positions[1][0],
        fin2_z=fin_positions[1][1],
        fin3_x=fin_positions[2][0],
        fin3_z=fin_positions[2][1],
    )


# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Flea Hopper .craft file for early contracts.",
        epilog="Examples:\n"
               "  python scripts/build-flea-hopper.py\n"
               "  python scripts/build-flea-hopper.py --name \"Flea Hopper\"\n"
               "  python scripts/build-flea-hopper.py --sandbox",
    )
    parser.add_argument("--name", "-n", type=str, default="Flea Hopper",
                        help="Craft name (default: 'Flea Hopper')")
    parser.add_argument("--sandbox", "-s", action="store_true",
                        help="Write to Sandbox save instead of most recent")

    args = parser.parse_args()

    # Determine target VAB directory
    if args.sandbox:
        vab_dir = KSP_DIR / "saves/Sandbox/Ships/VAB"
    else:
        vab_dir = find_active_save()

    if vab_dir is None or not vab_dir.exists():
        print(json.dumps({"error": "No KSP save with Ships/VAB directory found"}))
        sys.exit(1)

    craft_path = vab_dir / f"{args.name}.craft"

    content = generate_craft(args.name)
    craft_path.write_text(content, encoding="utf-8")

    if not craft_path.exists():
        print(json.dumps({"error": f"Failed to write {craft_path}"}))
        sys.exit(1)

    # Verify via kRPC
    try:
        conn = krpc.connect(name="craft-builder", address="127.0.0.1", rpc_port=50000)
        sc = conn.space_center
        time.sleep(0.5)  # let KSP pick up new file

        vessels = sc.launchable_vessels("VAB")
        if args.name in vessels:
            print(json.dumps({
                "event": "craft_built",
                "craft": args.name,
                "path": str(craft_path),
                "vab_list": vessels,
            }))
        else:
            print(json.dumps({
                "event": "craft_written",
                "craft": args.name,
                "path": str(craft_path),
                "warn": "Craft not yet visible in VAB list (KSP may need scene reload)",
            }))
    except Exception as e:
        print(json.dumps({
            "event": "craft_written",
            "craft": args.name,
            "path": str(craft_path),
            "warn": f"Cannot verify via kRPC: {e}",
        }))


if __name__ == "__main__":
    main()
