# Plan: analyse-mesh-binding

## Context

Write a read-only analysis script from scratch that reports the binding state of all meshes in the scene. Used by the skill before running `rebind-to-rig` to understand what's already done, and after, to verify completeness.

Informed by `seredos_rebind/rebind_character.py` (VG naming conventions, bone name overrides, face DEF pairs) and `seredos_rigify/rigify_fix.py` (expected DEF bone names).

**Target:** `library/scripts/analyse-mesh-binding/`

---

## What the Script Reports

### Per-mesh table
For each MESH object in scene:
- Mesh name
- Armature modifier target (or `none`)
- Total VG count
- Mapped VGs (found in rig pose bones)
- Unmapped VGs (count + names)
- Synty-era VGs detected (pre-rebind indicators)
- Rebind state: `UNBOUND` / `PARTIAL` / `FULL`

### Unmapped VG details
Per mesh: list of VG names not found in rig pose bones.

### Face binding status
For the 4 face bone pairs (`DEF-Eye_L/R`, `DEF-Eyebrow_L/R`):
- VG exists on at least one mesh?
- COPY_TRANSFORMS constraint present on rig pose bone?

### Summary
- Counts by state (UNBOUND / PARTIAL / FULL)
- Overall status
- Actionable next steps (e.g., "run rebind-to-rig on: BodyMesh, HeadMesh")

---

## Rebind State Classification

| State | Condition |
|---|---|
| `UNBOUND` | No armature modifier, OR modifier points to non-RIG armature, OR all VGs unmapped |
| `PARTIAL` | Modifier points to RIG, but some VGs are unmapped (Synty names still present) |
| `FULL` | Modifier points to RIG, all VGs map to rig pose bones |

---

## Synty-era VG Detection

A VG is flagged as "pre-rebind / Synty" if it matches WITHOUT `DEF-` prefix:

```python
SYNTY_VG_NAMES = {"Eyes", "Eyebrows", "Eyebrow_L", "Eyebrow_R"}
SYNTY_BONE_PATTERNS = {
    "spine", "thigh", "hand", "forearm", "shoulder", "shin",
    "Thumb", "IndexFinger", "MiddleFinger", "PinkyFinger", "RingFinger",
    "Root", "Hips", "UpperArm", "LowerArm", "UpperLeg", "LowerLeg",
}

def is_synty_vg(name):
    if name.startswith("DEF-"):
        return False
    if name in SYNTY_VG_NAMES:
        return True
    return any(pattern in name for pattern in SYNTY_BONE_PATTERNS)
```

---

## Face Bone Pairs to Check

From `seredos_rebind/rebind_character.py` lines 48–53:
```python
FACE_DEF_TO_ORG = [
    ("DEF-Eye_L",      "ORG-Eye_L"),
    ("DEF-Eye_R",      "ORG-Eye_R"),
    ("DEF-Eyebrow_L",  "ORG-Eyebrow_L"),
    ("DEF-Eyebrow_R",  "ORG-Eyebrow_R"),
]
```

---

## Parameters

```python
RIG_NAME = ""   # Auto-detect if empty (RIG-* armature with DEF/ORG bones)
```

---

## Algorithm

1. Find RIG armature by `RIG_NAME` or heuristic (armature with both `DEF-` and `ORG-` pose bones)
2. Build set of rig pose bone names: `rig_bones = set(rig.pose.bones.keys())`
3. For each MESH in `bpy.data.objects`:
   - Find armature modifier (if any): `mod.type == 'ARMATURE'`
   - Count VGs: split into mapped (in `rig_bones`), unmapped, Synty-era
   - Determine rebind state
4. Check face COPY_TRANSFORMS constraints on rig (4 pairs from `FACE_DEF_TO_ORG`)
5. Print report

---

## Output Format

```
═══════════════════════════════════════════════════════════
  MESH BINDING ANALYSIS
  Rig: RIG-Character
═══════════════════════════════════════════════════════════

PER-MESH BINDING
─────────────────
  Mesh              ArmMod          VGs  Mapped  Unmapped  State
  ──────────────────────────────────────────────────────────────
  Body_Mesh         RIG-Character   28   28      0         FULL
  Head_Mesh         RIG-Character   24   22      2         PARTIAL
  Eyes_Mesh         OLD-Armature    4    0       4         UNBOUND

UNMAPPED VERTEX GROUPS
───────────────────────
  Head_Mesh (2 unmapped):
    - hand.L  [Synty-era]
    - custom_vg  [unknown]

  Eyes_Mesh (4 unmapped):
    - Eyes  [Synty-era — split into DEF-Eye_L/R first]
    - Eyebrow_L  [Synty-era]
    - Eyebrow_R  [Synty-era]
    - Eyebrows  [Synty-era — split into DEF-Eyebrow_L/R]

FACE BINDING STATUS
────────────────────
  DEF-Eye_L   : VG ✓ | COPY_TRANSFORMS→ORG-Eye_L ✓
  DEF-Eye_R   : VG ✓ | COPY_TRANSFORMS→ORG-Eye_R ✓
  DEF-Eyebrow_L: VG ✓ | COPY_TRANSFORMS→ORG-Eyebrow_L ✗
  DEF-Eyebrow_R: VG ✓ | COPY_TRANSFORMS→ORG-Eyebrow_R ✗

SUMMARY
────────
  FULL:    1 mesh
  PARTIAL: 1 mesh
  UNBOUND: 1 mesh

  Status: INCOMPLETE
  Next steps:
    1. Run rebind-to-rig on: Eyes_Mesh, Head_Mesh
    2. Fix face constraints: DEF-Eyebrow_L/R missing COPY_TRANSFORMS
```

---

## bpy API Calls

```python
bpy.data.objects
obj.type == 'MESH'
obj.vertex_groups; vg.name
obj.modifiers; mod.type == 'ARMATURE'; mod.object
rig.pose.bones.keys()
rig.pose.bones[name].constraints
c.type == 'COPY_TRANSFORMS'; c.target; c.subtarget
```

---

## Files to Create

```
library/scripts/analyse-mesh-binding/
├── README.md
└── solution_4.1.py
```

**README.md frontmatter:**
```yaml
---
blender_version: "4.1"
tested_on: "4.1"
api_sensitive: false
reference_version: "4.1"
---
```

---

## Verification

1. Open a scene with mixed binding state (some meshes rebound, some not)
2. Run `solution_4.1.py` via `execute_blender_code`
3. Confirm UNBOUND / PARTIAL / FULL counts match visual inspection
4. Run `rebind-to-rig` → run analysis again → all meshes show `FULL`
5. Confirm face constraint rows update to `✓` after rebind
