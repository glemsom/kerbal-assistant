#!/usr/bin/env python3
"""Generate a minimal craft to test RT-5 Flea on launchpad (PartTest contract).

Active contract: PartTest solidBooster.sm.v2 @ PRELAUNCH (Kerbin).
Design: Mk1 Pod + Mk16 Chute + Flea + 3x Basic Fin.
No Mystery Goo — user hasn't researched Engineering 101 yet.

Usage:
    .venv/bin/python scripts/build-flea-tester.py
    .venv/bin/python scripts/build-flea-tester.py --name "Flea Tester" --sandbox
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
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
    """Return path to the most recently modified save Ships/VAB dir.

    Prefers "default" over sandbox/training/scenarios.
    """
    saves_dir = KSP_DIR / "saves"
    if not saves_dir.exists():
        return None

    # Prefer "default" if it has a VAB
    default_vab = saves_dir / "default" / "Ships" / "VAB"
    if default_vab.exists():
        return default_vab

    best: tuple[float, Path] = (0, None)
    skip = {"sandbox", "Sandbox", "scenarios", "training", "steam_autocloud.vdf"}
    for entry in saves_dir.iterdir():
        if entry.name in skip:
            continue
        vab_dir = entry / "Ships" / "VAB"
        if vab_dir.exists():
            mtime = os.path.getmtime(vab_dir)
            if mtime > best[0]:
                best = (mtime, vab_dir)
    return best[1]


# --- Coordinate constants (same VAB origin as flea-hopper) ---
POD_Y = 1.5
POD_TOP = POD_Y + 0.642376
POD_BOTTOM = POD_Y - 0.405038
CHUTE_Y = POD_TOP + 0.120649
FLEA_Y = POD_BOTTOM - 0.7575
FIN_Y = FLEA_Y
FIN_RADIUS = 0.625
FIN_ANGLES = [90, 210, 330]

fin_positions = []
for angle in FIN_ANGLES:
    rad = math.radians(angle)
    fin_positions.append((FIN_RADIUS * math.cos(rad), FIN_RADIUS * math.sin(rad)))

CRAFT_TEMPLATE = """ship = {name}
version = 1.12.5
description = Flea booster test for PartTest contract
type = VAB
size = 1.25,4.0,1.25
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
    rng = random.Random(name)

    def pid() -> int:
        return rng.randint(100000000, 999999999)

    return CRAFT_TEMPLATE.format(
        name=name,
        pod_id=pid(),
        pod_y=POD_Y,
        chute_id=pid(),
        chute_y=CHUTE_Y,
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Flea Tester .craft file for PartTest contract.",
    )
    parser.add_argument("--name", "-n", type=str, default="Flea Tester",
                        help="Craft name (default: 'Flea Tester')")
    parser.add_argument("--sandbox", "-s", action="store_true",
                        help="Write to Sandbox save instead of most recent")

    args = parser.parse_args()

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

    try:
        conn = krpc.connect(name="craft-builder", address="127.0.0.1", rpc_port=50000)
        sc = conn.space_center
        time.sleep(0.5)
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
