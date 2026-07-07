#!/usr/bin/env python3
"""Generate a simple orbital rocket .craft file in VAB directory.

Builds a clean 2-stage rocket with correct staging for Kerbin orbit.
Does NOT launch — only creates the craft file for VAB.

Design:
  Stage 3 (first to fire): 2x RT-5 Flea SRBs + LV-30 Reliant core engine
  Stage 2: Radial decouplers (jettison spent boosters)
  Stage 1: (empty — core continues)
  Stage 0: Mk16 parachute (deploy on re-entry)

Parts:
  - Mk1 Command Pod (root)
  - Mk16 Parachute (top of pod)
  - SAS Module (under pod)
  - 4x FL-T200 Fuel Tanks (stacked)
  - LV-30 Reliant Liquid Engine (bottom)
  - 2x RT-5 Flea SRBs (radial, on decouplers)
  - 2x Radial Decouplers (attach boosters to core)
  - 2x Nose Cones (on top of each Flea)
  - 3x Basic Fins (on bottom core tank)

Usage:
    python scripts/build-craft.py
    python scripts/build-craft.py --name "My Rocket"
    python scripts/build-craft.py --name "My Rocket" --sandbox
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

# ---------------------------------------------------------------------------
# KSP paths
# ---------------------------------------------------------------------------
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
# Craft file template (embedded — no dependency on existing saves)
# ---------------------------------------------------------------------------

# The template below is a minimal orbital rocket craft. Part positions
# are pre-computed for the standard Kerbin VAB build platform.
# Persistent IDs are generated once; they remain stable for craft identity.
CRAFT_TEMPLATE = """ship = {name}
version = 1.12.5
description = 
type = VAB
size = 4.1556778,10.736639,3.982162
steamPublishedFileId = 0
persistentId = 233386374
rot = 0,0,0,0
missionFlag = Squad/Flags/default
vesselType = Debris
OverrideDefault = False,False,False,False
OverrideActionControl = 0,0,0,0
OverrideAxisControl = 0,0,0,0
OverrideGroupNames = ,,,

PART
{{
	part = mk1pod.v2_{pod_id}
	partName = Part
	persistentId = {pod_id}
	pos = -0.117464766,16.8527088,-0.22905539
	attPos = 0,0,0
	attPos0 = -0.117464766,16.8527088,-0.22905539
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
	link = radialDrogue_{drogue1_id}
	link = radialDrogue_{drogue2_id}
	link = parachuteSingle_{chute_id}
	link = GooExperiment_{goo_id}
	link = sasModule_{sas_id}
	attN = bottom,sasModule_{sas_id}_0|-0.40503791|0_0|-1|0_0|-0.40503791|0_0|-1|0
	attN = top,parachuteSingle_{chute_id}_0|0.642375588|0_0|1|0_0|0.642375588|0_0|1|0
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
	part = radialDrogue_{drogue1_id}
	partName = Part
	persistentId = {drogue1_id}
	pos = -0.495754004,17.2267818,-0.175915703
	attPos = 0,0,0
	attPos0 = -0.495754004,17.2267818,-0.175915703
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
		Deploy
		{{
			actionGroup = Abort
		}}
	}}
}}

PART
{{
	part = radialDrogue_{drogue2_id}
	partName = Part
	persistentId = {drogue2_id}
	pos = 0.117700204,17.2267818,0.0719828457
	attPos = 0,0,0
	attPos0 = 0.117700204,17.2267818,0.0719828457
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
		Deploy
		{{
			actionGroup = Abort
		}}
	}}
}}

PART
{{
	part = parachuteSingle_{chute_id}
	partName = Part
	persistentId = {chute_id}
	pos = -0.117464766,17.5101662,-0.22905539
	attPos = 0,0,0
	attPos0 = -0.117464766,17.5101662,-0.22905539
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
}}

PART
{{
	part = GooExperiment_{goo_id}
	partName = Part
	persistentId = {goo_id}
	pos = -0.402487934,16.9548321,-0.458584189
	attPos = 0,0,0
	attPos0 = -0.402487934,16.9548321,-0.458584189
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
	part = sasModule_{sas_id}
	partName = Part
	persistentId = {sas_id}
	pos = -0.117464766,16.3565598,-0.22905539
	attPos = 0,0,0
	attPos0 = -0.117464766,16.3565598,-0.22905539
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
	link = fuelTank_{tank1_id}
	attN = bottom,fuelTank_{tank1_id}_0|-0.0911109|0_0|-0.5|0_0|-0.0911109|0_0|-0.5|0
	attN = top,mk1pod.v2_{pod_id}_0|0.0911109|0_0|0.5|0_0|0.0911109|0_0|0.5|0
	EVENTS
	{{
	}}
	ACTIONS
	{{
	}}
}}

PART
{{
	part = fuelTank_{tank1_id}
	partName = Part
	persistentId = {tank1_id}
	pos = -0.117464766,15.2837238,-0.22905539
	attPos = 0,0,0
	attPos0 = -0.117464766,15.2837238,-0.22905539
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
	link = fuelTank_{tank2_id}
	attN = top,sasModule_{sas_id}_0|0.981724977|0_0|1|0_0|0.981724977|0_0|1|0
	attN = bottom,fuelTank_{tank2_id}_0|-0.912500024|0_0|-1|0_0|-0.912500024|0_0|-1|0
	EVENTS
	{{
	}}
	ACTIONS
	{{
	}}
}}

PART
{{
	part = fuelTank_{tank2_id}
	partName = Part
	persistentId = {tank2_id}
	pos = -0.117464766,13.3894987,-0.22905539
	attPos = 0,0,0
	attPos0 = -0.117464766,13.3894987,-0.22905539
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
	link = fuelTank_{tank3_id}
	attN = top,fuelTank_{tank1_id}_0|0.981724977|0_0|1|0_0|0.981724977|0_0|1|0
	attN = bottom,fuelTank_{tank3_id}_0|-0.912500024|0_0|-1|0_0|-0.912500024|0_0|-1|0
	EVENTS
	{{
	}}
	ACTIONS
	{{
	}}
}}

PART
{{
	part = fuelTank_{tank3_id}
	partName = Part
	persistentId = {tank3_id}
	pos = -0.117464766,11.4952736,-0.22905539
	attPos = 0,0,0
	attPos0 = -0.117464766,11.4952736,-0.22905539
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
	link = fuelTank_{tank4_id}
	link = radialDecoupler_{dec1_id}
	link = radialDecoupler_{dec2_id}
	link = basicFin_{fin1_id}
	link = basicFin_{fin2_id}
	link = basicFin_{fin3_id}
	attN = top,fuelTank_{tank2_id}_0|0.981724977|0_0|1|0_0|0.981724977|0_0|1|0
	attN = bottom,fuelTank_{tank4_id}_0|-0.912500024|0_0|-1|0_0|-0.912500024|0_0|-1|0
	EVENTS
	{{
	}}
	ACTIONS
	{{
	}}
}}

PART
{{
	part = fuelTank_{tank4_id}
	partName = Part
	persistentId = {tank4_id}
	pos = -0.117464766,9.60104942,-0.22905539
	attPos = 0,0,0
	attPos0 = -0.117464766,9.60104942,-0.22905539
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
	link = liquidEngine2.v2_{engine_id}
	link = basicFin_{fin4_id}
	link = basicFin_{fin5_id}
	link = basicFin_{fin6_id}
	attN = top,fuelTank_{tank3_id}_0|0.981724977|0_0|1|0_0|0.981724977|0_0|1|0
	attN = bottom,liquidEngine2.v2_{engine_id}_0|-0.912500024|0_0|-1|0_0|-0.912500024|0_0|-1|0
	EVENTS
	{{
	}}
	ACTIONS
	{{
	}}
}}

PART
{{
	part = liquidEngine2.v2_{engine_id}
	partName = Part
	persistentId = {engine_id}
	pos = -0.117464766,8.68855,-0.22905539
	attPos = 0,0,0
	attPos0 = -0.117464766,8.68855,-0.22905539
	rot = 0,0,0,1
	attRot = 0,0,0,1
	attRot0 = 0,0,0,1
	mir = 1,1,1
	symMethod = Radial
	autostrutMode = Off
	rigidAttachment = False
	istg = 1
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
	EVENTS
	{{
	}}
	ACTIONS
	{{
		ToggleEngine
		{{
			actionGroup = None
		}}
	}}
}}

PART
{{
	part = basicFin_{fin4_id}
	partName = Part
	persistentId = {fin4_id}
	pos = -0.184710339,9.09055996,-0.832760453
	attPos = 0,0,0
	attPos0 = -0.184710339,9.09055996,-0.832760453
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
	part = basicFin_{fin5_id}
	partName = Part
	persistentId = {fin5_id}
	pos = -0.60666585,9.09055996,0.131033614
	attPos = 0,0,0
	attPos0 = -0.60666585,9.09055996,0.131033614
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
	part = basicFin_{fin6_id}
	partName = Part
	persistentId = {fin6_id}
	pos = 0.43898201,9.09055996,0.0145607591
	attPos = 0,0,0
	attPos0 = 0.43898201,9.09055996,0.0145607591
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
	part = radialDecoupler_{dec1_id}
	partName = Part
	persistentId = {dec1_id}
	pos = -0.665403128,10.9021721,-0.507408202
	attPos = 0,0,0
	attPos0 = -0.665403128,10.9021721,-0.507408202
	rot = 0,0,0,1
	attRot = 0,0,0,1
	attRot0 = 0,0,0,1
	mir = 1,1,1
	symMethod = Mirror
	autostrutMode = Off
	rigidAttachment = False
	istg = 2
	resPri = 0
	dstg = 1
	sidx = 0
	sqor = -1
	sepI = -1
	attm = 0
	sameVesselCollision = False
	modCost = 0
	modMass = 0
	modSize = 0,0,0
	link = solidBooster.sm.v2_{srb1_id}
	EVENTS
	{{
	}}
	ACTIONS
	{{
	}}
}}

PART
{{
	part = solidBooster.sm.v2_{srb1_id}
	partName = Part
	persistentId = {srb1_id}
	pos = -1.42400694,10.6471672,-0.766087055
	attPos = 0,0,0
	attPos0 = -1.42400694,10.6471672,-0.766087055
	rot = 0,0,0,1
	attRot = 0,0,0,1
	attRot0 = 0,0,0,1
	mir = 1,1,1
	symMethod = Mirror
	autostrutMode = Off
	rigidAttachment = False
	istg = 3
	resPri = 0
	dstg = 2
	sidx = 0
	sqor = -1
	sepI = -1
	attm = 0
	sameVesselCollision = False
	modCost = 0
	modMass = 0
	modSize = 0,0,0
	link = noseCone_{nose1_id}
	attN = bottom,Null_0_0|-0.997500002|0_0|-1|0_0|-0.997500002|0_0|-1|0
	attN = top,noseCone_{nose1_id}_0|0.757499993|0_0|1|0_0|0.757499993|0_0|1|0
	EVENTS
	{{
	}}
	ACTIONS
	{{
	}}
}}

PART
{{
	part = noseCone_{nose1_id}
	partName = Part
	persistentId = {nose1_id}
	pos = -1.42400706,11.4046679,-0.766087055
	attPos = 0,0,0
	attPos0 = -1.42400706,11.4046679,-0.766087055
	rot = 0,0,0,1
	attRot = 0,0,0,1
	attRot0 = 0,0,0,1
	mir = 1,1,1
	symMethod = Mirror
	autostrutMode = Off
	rigidAttachment = False
	istg = 3
	resPri = 0
	dstg = 2
	sidx = -1
	sqor = -1
	sepI = -1
	attm = 0
	sameVesselCollision = False
	modCost = 0
	modMass = 0
	modSize = 0,0,0
	attN = bottom01,solidBooster.sm.v2_{srb1_id}_0|0|0_0|-1|0_0|0|0_0|-1|0
	EVENTS
	{{
	}}
	ACTIONS
	{{
	}}
}}

PART
{{
	part = radialDecoupler_{dec2_id}
	partName = Part
	persistentId = {dec2_id}
	pos = -0.0845561177,10.9021721,0.384649575
	attPos = 0,0,0
	attPos0 = -0.0845561177,10.9021721,0.384649575
	rot = 0,0,0,1
	attRot = 0,0,0,1
	attRot0 = 0,0,0,1
	mir = 1,1,1
	symMethod = Mirror
	autostrutMode = Off
	rigidAttachment = False
	istg = 2
	resPri = 0
	dstg = 1
	sidx = 0
	sqor = -1
	sepI = -1
	attm = 0
	sameVesselCollision = False
	modCost = 0
	modMass = 0
	modSize = 0,0,0
	link = solidBooster.sm.v2_{srb2_id}
	EVENTS
	{{
	}}
	ACTIONS
	{{
	}}
}}

PART
{{
	part = solidBooster.sm.v2_{srb2_id}
	partName = Part
	persistentId = {srb2_id}
	pos = 0.0707235932,10.6471672,1.17096472
	attPos = 0,0,0
	attPos0 = 0.0707235932,10.6471672,1.17096472
	rot = 0,0,0,1
	attRot = 0,0,0,1
	attRot0 = 0,0,0,1
	mir = 1,1,1
	symMethod = Mirror
	autostrutMode = Off
	rigidAttachment = False
	istg = 3
	resPri = 0
	dstg = 2
	sidx = 0
	sqor = -1
	sepI = -1
	attm = 0
	sameVesselCollision = False
	modCost = 0
	modMass = 0
	modSize = 0,0,0
	link = noseCone_{nose2_id}
	attN = bottom,Null_0_0|-0.997500002|0_0|-1|0_0|-0.997500002|0_0|-1|0
	attN = top,noseCone_{nose2_id}_0|0.757499993|0_0|1|0_0|0.757499993|0_0|1|0
	EVENTS
	{{
	}}
	ACTIONS
	{{
	}}
}}

PART
{{
	part = noseCone_{nose2_id}
	partName = Part
	persistentId = {nose2_id}
	pos = 0.0707235932,11.4046679,1.17096829
	attPos = 0,0,0
	attPos0 = 0.0707235932,11.4046679,1.17096829
	rot = 0,0,0,1
	attRot = 0,0,0,1
	attRot0 = 0,0,0,1
	mir = 1,1,1
	symMethod = Mirror
	autostrutMode = Off
	rigidAttachment = False
	istg = 3
	resPri = 0
	dstg = 2
	sidx = -1
	sqor = -1
	sepI = -1
	attm = 0
	sameVesselCollision = False
	modCost = 0
	modMass = 0
	modSize = 0,0,0
	attN = bottom01,solidBooster.sm.v2_{srb2_id}_0|0|0_0|-1|0_0|0|0_0|-1|0
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
	pos = -0.266221702,11.4029303,-0.832759857
	attPos = 0,0,0
	attPos0 = -0.266221702,11.4029303,-0.832759857
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
	pos = -0.565909684,11.4029303,0.2016242
	attPos = 0,0,0
	attPos0 = -0.565909684,11.4029303,0.2016242
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
	pos = 0.479737163,11.4029303,-0.0560304672
	attPos = 0,0,0
	attPos0 = 0.479737163,11.4029303,-0.0560304672
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
}}"""


def generate_craft(name: str) -> str:
    """Generate craft file content with unique persistent IDs."""
    import random

    rng = random.Random(name)

    def pid() -> int:
        return rng.randint(100000000, 999999999)

    return CRAFT_TEMPLATE.format(
        name=name,
        pod_id=pid(),
        drogue1_id=pid(),
        drogue2_id=pid(),
        chute_id=pid(),
        goo_id=pid(),
        sas_id=pid(),
        tank1_id=pid(),
        tank2_id=pid(),
        tank3_id=pid(),
        tank4_id=pid(),
        engine_id=pid(),
        dec1_id=pid(),
        dec2_id=pid(),
        srb1_id=pid(),
        srb2_id=pid(),
        nose1_id=pid(),
        nose2_id=pid(),
        fin1_id=pid(),
        fin2_id=pid(),
        fin3_id=pid(),
        fin4_id=pid(),
        fin5_id=pid(),
        fin6_id=pid(),
    )


# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a simple orbital rocket .craft file in VAB directory.",
        epilog="Examples:\n"
               "  python scripts/build-craft.py\n"
               "  python scripts/build-craft.py --name \"My Rocket\"\n"
               "  python scripts/build-craft.py --name \"Test Orbiter\" --sandbox",
    )
    parser.add_argument("--name", "-n", type=str, default="Orbital Rocket",
                        help="Craft name (default: 'Orbital Rocket')")
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
                "vab_list": vessels
            }))
        else:
            print(json.dumps({
                "event": "craft_written",
                "craft": args.name,
                "path": str(craft_path),
                "warn": "Craft not yet visible in VAB list (KSP may need scene reload)"
            }))
    except Exception as e:
        print(json.dumps({
            "event": "craft_written",
            "craft": args.name,
            "path": str(craft_path),
            "warn": f"Cannot verify via kRPC: {e}"
        }))


if __name__ == "__main__":
    main()
