# KSP .craft File Format Reference

Canonical reference for generating `.craft` files compatible with KSP 1.12.5 and kRPC. Covers format discovered during testing of automated craft builders (`build-craft.py`, `build-orbit-test-1.py`).

---

## 1. attN Format (8-value)

KSP 1.12.5 requires the **8-value** attN format:

```
attN = <node_name>,<child>_<childId>_<index>|<node_y>|0_0|<node_z>|0_0|<node_y>|0_0|<node_z>|0
```

**Do not** use the old 2-value format (`|y|0`) found in some KSP 1.0-1.3 documentation. The 8-value format defines both y and z components of the attachment normal vector, duplicated for symmetry.

### Example

```
attN = top,parachuteSingle_123456789_0|0.642375588|0_0|1|0_0|0.642375588|0_0|1|0
attN = bottom,fuelTank_987654321_0|-0.40503791|0_0|-1|0_0|-0.40503791|0_0|-1|0
```

Where:
- `node_name` = `"top"` or `"bottom"` (or `"bottom01"` for second radial attachment)
- `child_part_name_childId_index` = target part reference (`partName_persistentId_linkIndex`)
- `y` = y-component of the node normal (scaled by `rescaleFactor`)
- `z` = z-component of the node normal (scaled by `rescaleFactor`)

### Generating attN values from part config

Each part's attachment nodes are defined in its `.cfg` file:

```
node_stack_top = x, y, z, nx, ny, nz, size
node_stack_bottom = x, y, z, nx, ny, nz, size
```

For attN, use the **y** and **z** components of the *normal* vector (`ny`, `nz`), scaled by `rescaleFactor`:

- `attN's y value` = `node_ny` (the y-component of the node normal)
- `attN's z value` = `node_nz` (the z-component of the node normal)

For top attachment of a part: `ny` is typically `+1.0` (pointing up), `nz` is `0.0`.
For bottom attachment: `ny` is typically `-1.0` (pointing down), `nz` is `0.0`.

If the part uses `rescaleFactor = 1.0`, node values go directly into attN. When `rescaleFactor != 1.0`, scale the y/z values accordingly.

**Important for mod parts**: The actual attachment y values in attN come from the *child* part's node_stack_bottom position (for top-attached children). The simplest approach is to build a reference craft in the VAB and copy attN values from it.

---

## 2. Part Ordering — Root First

The **root part** (the first part placed in the VAB) **must** be the first `PART` entry in the `.craft` file. KSP crashes or misloads if another part comes first.

```
PART
{
    part = mk1pod.v2_123456789
    ...
}
PART
{
    part = sasModule_987654321
    ...
}
```

The root part is typically the command pod for crewed rockets.

---

## 3. Part Naming Convention

KSP craft files use **dot notation** for part names (e.g., `mk1pod.v2`), even when the part's `.cfg` file uses underscores internally.

| Part          | .craft name        | .cfg internal name    |
|---------------|--------------------|-----------------------|
| Mk1 Pod       | `mk1pod.v2`        | `mk1pod_v2`           |
| LV-30 Engine  | `liquidEngine2.v2` | `liquidEngine2_v2`    |
| LV-T45 Engine | `liquidEngine2`    | `liquidEngine2`       |
| Terrier       | `liquidEngine3_v2` | `liquidEngine3_v2`    |
| RT-5 Flea     | `solidBooster.sm.v2` | `solidBooster_sm_v2` |
| Mk16 Chute    | `parachuteSingle`  | `parachuteSingle`     |

Stick to the craft-file convention (dot-separated) to match what KSP expects.

**Each part instance has a unique ID suffix** appended to the part name in the `part` field:

```
part = mk1pod.v2_123456789
```

The ID is a random integer (typically 9 digits). It differentiates multiple instances of the same part type.

---

## 4. ACTIONS Block Requirements

The Mk1 command pod requires `ToggleSameVesselInteraction` and `SetSameVesselInteraction` entries inside `ACTIONS`. kRPC's `PartCrewManifest.FromConfigNode` will throw a parse error on empty ACTIONS blocks for crewable parts.

### Required (Mk1 pod)

```
ACTIONS
{
    ToggleSameVesselInteraction
    {
        actionGroup = None
        wasActiveBeforePartWasAdjusted = False
    }
    SetSameVesselInteraction
    {
        actionGroup = None
        wasActiveBeforePartWasAdjusted = False
    }
}
```

### Acceptable empty (non-crewable parts)

```
ACTIONS
{
}
```

Parts with no crew capacity (fuel tanks, decouplers, engines, SRBs) can have empty ACTIONS blocks.

---

## 5. symMethod Enum Values

The `symMethod` field uses specific enum string values:

| Value    | Description                       |
|----------|-----------------------------------|
| `Radial` | Single placement, not mirrored    |
| `Mirror` | Mirror-symmetric (paired parts)   |

**Never use** `MirrorSymmetry` — this is not a valid value in KSP 1.12.x and will cause parse errors or silent misbehavior.

### Rules of thumb

- Root part: `symMethod = Radial`
- Stacked inline parts (tanks, engines on center axis): `symMethod = Radial`
- Radially attached mirrored pairs (SRBs, decouplers, fins): `symMethod = Mirror`
- Single radial parts (drogue chutes, science experiments): `symMethod = Radial`

---

## 6. MODULE Sections for Crew-Capable Parts

Parts with crew capability (Mk1 command pod, crew cabins) require `MODULE` blocks in their `PART` definition. Absent MODULE data causes kRPC crew manifest parsing (`PartCrewManifest.FromConfigNode`) to fail.

The Mk1 pod at minimum needs these MODULE entries:

```
MODULE
{
    name = ModuleCommand
}
MODULE
{
    name = ModuleDataTransmitter
}
MODULE
{
    name = ModuleScienceExperiment
}
MODULE
{
    name = ModuleReusable
}
MODULE
{
    name = ModuleTripLogger
}
MODULE
{
    name = ModuleKerbNetAccess
}
```

The safest approach: **export a reference craft from the VAB** and use its MODULE blocks verbatim. Different KSP installs (modded vs stock) may have different module requirements.

**Note**: The template in `build-craft.py` embeds a hardcoded Mk1 pod that works without explicit MODULE blocks because KSP fills in defaults for stock parts at load time. For generated crafts, the modules are optional if the part is stock and KSP can resolve them. However, kRPC's `PartCrewManifest.FromConfigNode` **will fail** without them — if your script parses crew data, include MODULE blocks.

---

## 7. Node Position Calculation

Part positions are in VAB-world coordinates. The Y-axis points up.

### Deriving attN values from node_stack definitions

Given a part's config:
```
node_stack_top = 0.0, 0.642376, 0.0, 0.0, 1.0, 0.0, 1
node_stack_bottom = 0.0, -0.405038, 0.0, 0.0, -1.0, 0.0, 1
```

The attN fields for a child part attached to the top node:

```
attN = top,child_part_childId_index|<node_ny>|0_0|<node_nz>|0_0|<node_ny>|0_0|<node_nz>|0
```

So `node_stack_top` with `ny=1.0, nz=0.0` → attN values `y=1.0, z=0.0`:

```
attN = top,child_1234_0|1.0|0_0|0|0_0|1.0|0_0|0|0
```

**But** the actual attN y-values in a real .craft file are the *child* part's node_stack_bottom position's y-value (the distance from the child's origin to its bottom attachment node), not the parent's top node position. For inline stacked parts, both values happen to match.

For radial attachments (SRBs on decouplers), the attN values encode the vector from parent attach point to child attach point in the parent's local frame.

### Key formula

```
child_bottom_y = -node_stack_bottom_y_of_child
attN_top_y_value = child_bottom_y
```

Where `node_stack_bottom_y` is the y-offset from the part's origin to its bottom node (negative = below origin).

**Example**: Fuel tank with `node_stack_bottom_y = -0.9125` and `node_ny = -1.0`:

```
# Bottom attN (= connecting a child below this tank)
attN = bottom,child_part_childId_index|-0.912500024|0_0|-1.0|0_0|-0.912500024|0_0|-1.0|0
```

### rescaleFactor scaling

If the part uses `rescaleFactor != 1.0`, multiply node_stack values by it:

```python
ny_scaled = node_ny * rescaleFactor
nz_scaled = node_nz * rescaleFactor
```

---

## Minimal Working Template

Below is a minimal single-part craft (Mk1 pod only). Save with `.craft` extension and place in `<KSP>/saves/<save>/Ships/VAB/`.

```
ship = Minimal Pod
version = 1.12.5
description =
type = VAB
size = 1.25,1.0,1.25
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
{
    part = mk1pod.v2_123456789
    partName = Part
    persistentId = 123456789
    pos = 0,1.5,0
    attPos = 0,0,0
    attPos0 = 0,1.5,0
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
    EVENTS
    {
    }
    ACTIONS
    {
        ToggleSameVesselInteraction
        {
            actionGroup = None
            wasActiveBeforePartWasAdjusted = False
        }
        SetSameVesselInteraction
        {
            actionGroup = None
            wasActiveBeforePartWasAdjusted = False
        }
    }
}
```

---

## Tools Reference

- **`scripts/build-craft.py`** — Generates a full orbital rocket .craft (Mk1 pod + tanks + SRBs + engine). Embeds a complete working template.
- **`scripts/build-orbit-test-1.py`** — Generates a 2-stage liquid rocket .craft for 200 km orbit.
- Both write to the active save's `Ships/VAB/` directory and verify via kRPC.
