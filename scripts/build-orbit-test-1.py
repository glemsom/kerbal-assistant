#!/usr/bin/env python3
"""Generate orbit-test-1 .craft file (2-stage liquid, 200 km orbit).
"""
from __future__ import annotations

import argparse
import json
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
    saves_dir = KSP_DIR / "saves"
    best: tuple[float, Path] = (0, None)
    for entry in saves_dir.iterdir():
        vab_dir = entry / "Ships" / "VAB"
        if vab_dir.exists():
            mtime = os.path.getmtime(vab_dir)
            if mtime > best[0]:
                best = (mtime, vab_dir)
    return best[1]


# ── Part positions (Y coords) ──
# Root Mk1 pod at Y=16.853 (matching build-craft.py convention).
Y_POD     = 16.853
Y_CHUTE   = Y_POD + 0.710
Y_SCI     = Y_POD - 0.947
Y_DEC1    = Y_SCI - 0.592
Y_SAS     = Y_DEC1 - 0.355
Y_TANK_U  = Y_SAS - 3.078
Y_TERRIER = Y_TANK_U - 3.315
Y_DEC2    = Y_TERRIER - 0.592
Y_TANK_L1 = Y_DEC2 - 2.960
Y_TANK_L2 = Y_TANK_L1 - 5.682
Y_SWIVEL  = Y_TANK_L2 - 3.552

X0 = -0.117464766
Z0 = -0.22905539


def pid(rng: random.Random) -> int:
    return rng.randint(100000000, 999999999)


# Part node data: (part_name, top_y, top_nys, bot_y, bot_nys)
# ny_scaled = normal_y * rescaleFactor (for attN z-value)
NODES = {
    "mk1pod.v2":      (0.6423756, 1.0,  -0.4050379, -1.0),
    "science_module": (0.49,      0.1,  -0.41,      -0.1),
    "stackDecoupler": (0.0650517, 1.0,  -0.1329949, -1.0),
    "sasModule":      (0.0911109, 0.5,  -0.0911109, -0.5),
    "fuelTank_long":  (1.875,     1.0,  -1.8875,    -1.0),
    "liquidEngine3_v2": (0.0,     1.0,  -0.83,      -1.0),
    "liquidEngine2":  (0.721461,  0.1,  -0.574338,  -0.1),
    "parachuteSingle": (None,     None, -0.120649,  None),
}


def attn_str(which: str, pname: str) -> str:
    """Generate 8-value attN data: y|0_0|z|0_0|y|0_0|z|0"""
    top_y, top_nys, bot_y, bot_nys = NODES[pname]
    y, z = (top_y, top_nys) if which == "top" else (bot_y, bot_nys)
    return f"{y}|0_0|{z}|0_0|{y}|0_0|{z}|0"


def part_block(name: str, pid_v: int, y: float,
               links: list[str] | None = None,
               attn_top: str | None = None,
               attn_bottom: str | None = None,
               stage: int = -1, sidx: int = -1) -> str:
    lines = [
        "PART", "{",
        f"\tpart = {name}_{pid_v}",
        "\tpartName = Part",
        f"\tpersistentId = {pid_v}",
        f"\tpos = {X0},{y},{Z0}",
        "\tattPos = 0,0,0",
        f"\tattPos0 = {X0},{y},{Z0}",
        "\trot = 0,0,0,1",
        "\tattRot = 0,0,0,1",
        "\tattRot0 = 0,0,0,1",
        "\tmir = 1,1,1",
        "\tsymMethod = Radial",
        "\tautostrutMode = Off",
        "\trigidAttachment = False",
        f"\tistg = {stage}",
        "\tresPri = 0", "\tdstg = 0", f"\tsidx = {sidx}",
        "\tsqor = -1", "\tsepI = -1", "\tattm = 0",
        "\tsameVesselCollision = False",
        "\tmodCost = 0", "\tmodMass = 0", "\tmodSize = 0,0,0",
    ]
    if links:
        for l in links:
            lines.append(f"\tlink = {l}")
    if attn_top:
        lines.append(f"\tattN = {attn_top}")
    if attn_bottom:
        lines.append(f"\tattN = {attn_bottom}")
    lines.extend(["\tEVENTS", "\t{", "\t}", "\tACTIONS", "\t{", "\t}", "}"])
    return "\n".join(lines)


def fin_block(name: str, pid_v: int, x: float, y: float, z: float) -> str:
    lines = [
        "PART", "{",
        f"\tpart = {name}_{pid_v}",
        "\tpartName = Part",
        f"\tpersistentId = {pid_v}",
        f"\tpos = {x},{y},{z}",
        "\tattPos = 0,0,0", f"\tattPos0 = {x},{y},{z}",
        "\trot = 0,0,0,1", "\tattRot = 0,0,0,1", "\tattRot0 = 0,0,0,1",
        "\tmir = 1,1,1",
        "\tsymMethod = Mirror",
        "\tautostrutMode = Off", "\trigidAttachment = False",
        "\tistg = -1", "\tresPri = 0", "\tdstg = 0", "\tsidx = -1",
        "\tsqor = -1", "\tsepI = -1", "\tattm = 1",
        "\tsameVesselCollision = False",
        "\tmodCost = 0", "\tmodMass = 0", "\tmodSize = 0,0,0",
        "\tEVENTS", "\t{", "\t}", "\tACTIONS", "\t{", "\t}", "}"
    ]
    return "\n".join(lines)


def generate_craft(name: str) -> str:
    rng = random.Random(name)
    I = {k: pid(rng) for k in [
        "chute","pod","sci","dec1","sas","tank_u",
        "terrier","dec2","tank_l1","tank_l2","swivel",
        "fin1","fin2","fin3"
    ]}

    lines = [
        f"ship = {name}",
        "version = 1.12.5",
        "description = orbit-test-1: 2-stage liquid to 200 km",
        "type = VAB", "size = 4.1556778,30.0,3.982162",
        "steamPublishedFileId = 0",
        f"persistentId = {pid(rng)}",
        "rot = 0,0,0,0", "missionFlag = Squad/Flags/default",
        "vesselType = Debris",
        "OverrideDefault = False,False,False,False",
        "OverrideActionControl = 0,0,0,0",
        "OverrideAxisControl = 0,0,0,0",
        "OverrideGroupNames = ,,,",
    ]

    # Mk1 Pod (root) — must be FIRST in craft file
    lines.append(part_block(
        "mk1pod.v2", I["pod"], Y_POD,
        links=[f"parachuteSingle_{I['chute']}", f"science_module_{I['sci']}"],
        attn_top=f"top,parachuteSingle_{I['chute']}_0|{attn_str('top','mk1pod.v2')}",
        attn_bottom=f"bottom,science_module_{I['sci']}_0|{attn_str('bottom','mk1pod.v2')}",
    ))

    # Science Jr
    lines.append(part_block(
        "science_module", I["sci"], Y_SCI,
        links=[f"stackDecoupler_{I['dec1']}"],
        attn_top=f"top,mk1pod.v2_{I['pod']}_0|{attn_str('top','science_module')}",
        attn_bottom=f"bottom,stackDecoupler_{I['dec1']}_0|{attn_str('bottom','science_module')}",
    ))

    # Decoupler 1 (payload separation)
    lines.append(part_block(
        "stackDecoupler", I["dec1"], Y_DEC1,
        links=[f"sasModule_{I['sas']}"],
        attn_top=f"top,science_module_{I['sci']}_0|{attn_str('top','stackDecoupler')}",
        attn_bottom=f"bottom,sasModule_{I['sas']}_0|{attn_str('bottom','stackDecoupler')}",
    ))

    # SAS (Inline Reaction Wheel)
    lines.append(part_block(
        "sasModule", I["sas"], Y_SAS,
        links=[f"fuelTank_long_{I['tank_u']}"],
        attn_top=f"top,stackDecoupler_{I['dec1']}_0|{attn_str('top','sasModule')}",
        attn_bottom=f"bottom,fuelTank_long_{I['tank_u']}_0|{attn_str('bottom','sasModule')}",
    ))

    # FL-T800 upper (stage 1 fuel tank)
    lines.append(part_block(
        "fuelTank_long", I["tank_u"], Y_TANK_U,
        links=[f"liquidEngine3_v2_{I['terrier']}"],
        attn_top=f"top,sasModule_{I['sas']}_0|{attn_str('top','fuelTank_long')}",
        attn_bottom=f"bottom,liquidEngine3_v2_{I['terrier']}_0|{attn_str('bottom','fuelTank_long')}",
    ))

    # Terrier (upper stage engine) — stage 1
    lines.append(part_block(
        "liquidEngine3_v2", I["terrier"], Y_TERRIER,
        links=[f"stackDecoupler_{I['dec2']}"], stage=1, sidx=1,
        attn_top=f"top,fuelTank_long_{I['tank_u']}_0|{attn_str('top','liquidEngine3_v2')}",
        attn_bottom=f"bottom,stackDecoupler_{I['dec2']}_0|{attn_str('bottom','liquidEngine3_v2')}",
    ))

    # Decoupler 2 (inter-stage separation) — stage 1, fires AFTER Terrier?
    # Actually, staging: Stage 1 activates = upper stage + decoupler?
    # In KSP, decoupler in same stage as engine means they fire together.
    # Need decoupler in separate stage above engine.
    lines.append(part_block(
        "stackDecoupler", I["dec2"], Y_DEC2,
        links=[f"fuelTank_long_{I['tank_l1']}"], stage=1, sidx=0,
        attn_top=f"top,liquidEngine3_v2_{I['terrier']}_0|{attn_str('top','stackDecoupler')}",
        attn_bottom=f"bottom,fuelTank_long_{I['tank_l1']}_0|{attn_str('bottom','stackDecoupler')}",
    ))

    # FL-T800 lower 1 (stage 2 fuel tank)
    lines.append(part_block(
        "fuelTank_long", I["tank_l1"], Y_TANK_L1,
        links=[f"fuelTank_long_{I['tank_l2']}"],
        attn_top=f"top,stackDecoupler_{I['dec2']}_0|{attn_str('top','fuelTank_long')}",
        attn_bottom=f"bottom,fuelTank_long_{I['tank_l2']}_0|{attn_str('bottom','fuelTank_long')}",
    ))

    # FL-T800 lower 2
    lines.append(part_block(
        "fuelTank_long", I["tank_l2"], Y_TANK_L2,
        links=[f"liquidEngine2_{I['swivel']}"],
        attn_top=f"top,fuelTank_long_{I['tank_l1']}_0|{attn_str('top','fuelTank_long')}",
        attn_bottom=f"bottom,liquidEngine2_{I['swivel']}_0|{attn_str('bottom','fuelTank_long')}",
    ))

    # Swivel (lower stage engine) — stage 2
    lines.append(part_block(
        "liquidEngine2", I["swivel"], Y_SWIVEL, stage=2, sidx=0,
        attn_top=f"top,fuelTank_long_{I['tank_l2']}_0|{attn_str('top','liquidEngine2')}",
    ))

    # Chute — leaf at top, must come after root
    lines.append(part_block("parachuteSingle", I["chute"], Y_CHUTE,
                             stage=0, sidx=0))

    # 3× Basic Fins (radial on lower tank)
    fin_y = Y_TANK_L2 + 1.0
    fin_pos = [
        (0.479737163, fin_y, -0.0560304672),
        (-0.369975477, fin_y, 0.308997363),
        (-0.109509721, fin_y, -0.481931955),
    ]
    for i, (fx, fy, fz) in enumerate(fin_pos, 1):
        lines.append(fin_block("basicFin", I[f"fin{i}"], fx, fy, fz))

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", "-n", type=str, default="Orbit Test 1")
    parser.add_argument("--sandbox", "-s", action="store_true")
    args = parser.parse_args()

    vab_dir = KSP_DIR / "saves/Sandbox/Ships/VAB" if args.sandbox else find_active_save()
    if vab_dir is None or not vab_dir.exists():
        print(json.dumps({"error": "No VAB directory found"}))
        sys.exit(1)

    craft_path = vab_dir / f"{args.name}.craft"
    craft_path.write_text(generate_craft(args.name), encoding="utf-8")

    if not craft_path.exists():
        print(json.dumps({"error": f"Failed to write {craft_path}"}))
        sys.exit(1)

    try:
        conn = krpc.connect(name="craft-builder", address="127.0.0.1", rpc_port=50000)
        sc = conn.space_center
        time.sleep(0.5)
        vessels = sc.launchable_vessels("VAB")
        print(json.dumps({
            "event": "craft_built" if args.name in vessels else "craft_written",
            "craft": args.name,
            "vab_list": vessels
        }))
    except Exception as e:
        print(json.dumps({"event": "craft_written", "warn": str(e)}))


if __name__ == "__main__":
    main()
