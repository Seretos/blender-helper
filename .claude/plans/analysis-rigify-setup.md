# Plan: analyse-rigify-setup

## Context

Write a read-only analysis script from scratch that checks which of the 12 post-processing steps from `seredos_rigify` have been applied to the generated rig. Used by the skill before running `rigify-generate-and-fix` to know what's already done — and after, to verify completeness.

Directly informed by `seredos_rigify/rigify_fix.py` — every check maps to a specific step in that file.

**Target:** `library/scripts/analyse-rigify-setup/`

---

## What the Script Reports

### Pre-generation checks (metarig)
- Metarig present?
- `MiddleFinger_01_L/R`, `PinkyFinger_01_L/R` have `rigify_type == "limbs.super_finger"`?

### Post-generation check
- Generated rig present?

### 12 fix step checks (one per step in `rigify_fix.py`)

| # | Check | Detection method |
|---|---|---|
| 1 | Unwanted bones removed | `ORG-Eyebrows`, `ORG-Eyes`, `ORG-eyebrow_anchor.R` absent from `rig.data.bones` |
| 2 | IK pole targets repositioned | `upper_arm_ik_target.L/R`, `thigh_ik_target.L/R` head positions ≠ world origin |
| 3 | Eye control bones created | `eye_ctrl.L`, `eye_ctrl.R`, `eyes_ctrl` present in `rig.data.bones` |
| 4 | Eye control parent hierarchy | `eye_ctrl.*.parent.name == "eyes_ctrl"`, `eyes_ctrl.parent.name == "head"` |
| 5 | Eye DAMPED_TRACK constraints | `Eye_L/R` pose bones have DAMPED_TRACK constraint targeting `eye_ctrl.L/R` |
| 6 | Eye control custom shapes | `pbone.custom_shape` references `WGT-*_eye_ctrl.*` object |
| 7 | Eyebrow control bones created | `eyebrow_ctrl.R`, `eyebrow_ctrl_center`, `eyebrow_ctrl.L` present |
| 8 | Eyebrow parent + axis lock | Parent == `head`; `lock_location == (True, False, True)` |
| 9 | Eyebrow ORG constraints | `ORG-Eyebrow_L/R` have COPY_LOCATION from `eyebrow_ctrl_center` + DAMPED_TRACK to `eyebrow_ctrl.L/R` |
| 10 | DEF-Eyebrow bones | `DEF-Eyebrow_L/R` present; parent == `ORG-Eyebrow_L/R` |
| 11 | Full DEF hierarchy | All 30 bone pairs match expected parent (see table below) |
| 12 | Split DEF bones disabled | `DEF-upper_arm.*.001`, `DEF-forearm.*.001`, `DEF-thigh.*.001`, `DEF-shin.*.001` have `use_deform=False` |

---

## Expected DEF Parent Map (check #11)

Hardcoded in script from `rigify_fix.py` lines 197–223:

```python
DEF_PARENTS = {
    "DEF-thigh.L":           "DEF-spine",
    "DEF-thigh.R":           "DEF-spine",
    "DEF-shoulder.L":        "DEF-spine.003",
    "DEF-shoulder.R":        "DEF-spine.003",
    "DEF-upper_arm.L":       "DEF-shoulder.L",
    "DEF-upper_arm.R":       "DEF-shoulder.R",
    "DEF-RingFinger_01_L":   "DEF-hand.L",
    "DEF-IndexFinger_01_L":  "DEF-hand.L",
    "DEF-MiddleFinger_01_L": "DEF-hand.L",
    "DEF-PinkyFinger_01_L":  "DEF-hand.L",
    "DEF-Thumb_01_L":        "DEF-hand.L",
    "DEF-RingFinger_01_R":   "DEF-hand.R",
    "DEF-IndexFinger_01_R":  "DEF-hand.R",
    "DEF-MiddleFinger_01_R": "DEF-hand.R",
    "DEF-PinkyFinger_01_R":  "DEF-hand.R",
    "DEF-Thumb_01_R":        "DEF-hand.R",
    "DEF-jaw":               "DEF-spine.006",
    "DEF-Eye_L":             "DEF-spine.006",
    "DEF-Eye_R":             "DEF-spine.006",
    "DEF-Eyebrow_L":         "DEF-spine.006",
    "DEF-Eyebrow_R":         "DEF-spine.006",
}
SPLIT_DEF_TO_DISABLE = [
    "DEF-upper_arm.L.001", "DEF-upper_arm.R.001",
    "DEF-forearm.L.001",   "DEF-forearm.R.001",
    "DEF-thigh.L.001",     "DEF-thigh.R.001",
    "DEF-shin.L.001",      "DEF-shin.R.001",
]
FACE_DEF_TO_ORG = [
    ("DEF-Eye_L", "ORG-Eye_L"), ("DEF-Eye_R", "ORG-Eye_R"),
    ("DEF-Eyebrow_L", "ORG-Eyebrow_L"), ("DEF-Eyebrow_R", "ORG-Eyebrow_R"),
]
```

---

## Parameters

```python
METARIG_NAME = ""   # Auto-detect if empty (META-* name or rigify_target_rig property)
RIG_NAME     = ""   # Auto-detect if empty (RIG-* name or armature with DEF/ORG bones)
```

---

## Algorithm

1. Find metarig and rig objects (by name or auto-detect)
2. For each of the 12 checks: query the relevant `bpy.data` / `bpy.pose.bones` properties
3. Track per-check: `APPLIED` / `NOT_APPLIED` / `PARTIAL` (partial only for checks with multiple sub-items, e.g., DEF hierarchy)
4. Count applied steps
5. Print hierarchical report

---

## Output Format

```
═══════════════════════════════════════════════════════
  RIGIFY SETUP ANALYSIS
  Metarig: META-Character | Rig: RIG-Character
═══════════════════════════════════════════════════════

SUMMARY: 12/12 steps applied — READY FOR EXPORT

PRE-GENERATION (metarig)
─────────────────────────
  Metarig present         : ✓ META-Character
  Finger config (Middle)  : ✓ super_finger
  Finger config (Pinky)   : ✓ super_finger

POST-GENERATION (rig)
──────────────────────
  Generated rig present   : ✓ RIG-Character

FIX STEPS
──────────
  [1] Unwanted bones removed      : ✓ APPLIED
  [2] IK pole targets             : ✓ APPLIED
  [3] Eye control bones           : ✓ APPLIED
  ...
  [11] DEF hierarchy (30 pairs)   : ⚠ PARTIAL (28/30 correct)
       ✗ DEF-thigh.L: expected DEF-spine, found DEF-spine.001
       ✗ DEF-shoulder.R: expected DEF-spine.003, found None
  [12] Split DEF bones disabled   : ✓ APPLIED
```

---

## bpy API Calls

```python
# Bone existence
rig.data.bones.get(name)                         # None if missing

# Parent check
rig.data.bones[name].parent.name                 # AttributeError if no parent

# Constraint check
rig.pose.bones[name].constraints
c.type == 'DAMPED_TRACK'
c.type == 'COPY_LOCATION'
c.subtarget == bone_name
c.target == rig

# Custom shape
rig.pose.bones[name].custom_shape               # None if not set
rig.pose.bones[name].custom_shape.name          # widget object name

# Lock location
rig.pose.bones[name].lock_location              # tuple of 3 bools

# Deform flag
rig.data.bones[name].use_deform                 # bool

# Metarig finger config
metarig.pose.bones[name].rigify_type            # string or ""
```

---

## Files to Create

```
library/scripts/analyse-rigify-setup/
├── README.md
└── solution_4.1.py
```

**README.md frontmatter:**
```yaml
---
blender_version: "4.1"
tested_on: "4.1"
api_sensitive: true
reference_version: "4.1"
---
```

---

## Verification

1. Run on a scene with only a metarig (no rig generated) → `0/12 steps applied`
2. Run `rigify-generate-and-fix` → run analysis again → `12/12 steps applied`
3. Manually delete one eye control bone → run analysis → `11/12`, step 3 shows `✗`
4. Re-run `rigify-generate-and-fix` → `12/12` again
