# Integration Plan: rigify-generate-and-fix

## Context

Port the core logic of `seredos_rigify` from an addon operator into a parametrized MCP-runnable library script. The script generates a Rigify rig from a metarig and applies all Synty-specific post-processing fixes in a single run.

**Source:** `E:\development\ai-villager\Blender\addons\seredos_rigify\`
- `__init__.py` (42 lines) — addon boilerplate only
- `rigify_fix.py` (425 lines) — all logic lives here

**Target:** `library/scripts/rigify-generate-and-fix/`

---

## What the Addon Does

1. Configures finger bones with `rigify_type = "limbs.super_finger"` (pre-generation)
2. Calls `bpy.ops.pose.rigify_generate()` — the actual Rigify rig generation
3. Removes unwanted ORG bones: `ORG-Eyebrows`, `ORG-Eyes`, `ORG-eyebrow_anchor.R`
4. Repositions IK pole targets for arms (`natural_pole_dir` + `ELBOW_DISTANCE`)
5. Finds optimal knee pole angles via grid search (`find_best_pole_angle`)
6. Repositions leg IK poles (`KNEE_DISTANCE`)
7. Creates eye control bones (`eye_ctrl.L/R`, `eyes_ctrl`) with custom widget meshes
8. Creates eyebrow control bones (3-point: `.R`, `_center`, `.L`) parented to head
9. Sets up full DEF bone hierarchy (~30 parent chain pairs)
10. Adds DAMPED_TRACK / COPY_LOCATION constraints on eye and eyebrow bones

---

## Extent of Changes

**Overall change magnitude: ~25% of lines** (boilerplate removal + parametrization)

### What gets stripped (~45 lines)
- `SEREDOS_PT_rigify` panel class
- `draw_generate_fix_button()` function
- `register()` / `unregister()` functions
- `bl_info` dict

### What gets parametrized (new top-of-script block)
```python
from mathutils import Vector

METARIG_NAME     = "metarig"       # Name of metarig object in scene
RIG_NAME         = "RIG-Character" # Expected generated rig name (fallback lookup)
ELBOW_DISTANCE   = 0.5             # IK pole offset for arms (Blender units)
KNEE_DISTANCE    = 0.5             # IK pole offset for legs (Blender units)
EYE_FORWARD_DIST = 0.35            # Eye control forward offset

BROW_OUTER_R  = Vector((-0.0606, -0.0149, 1.6516))
BROW_INNER_R  = Vector((-0.0281, -0.0149, 1.6671))
BROW_INNER_L  = Vector(( 0.0281, -0.0149, 1.6671))
BROW_OUTER_L  = Vector(( 0.0606, -0.0149, 1.6516))
BROW_CENTER   = Vector(( 0.0,    -0.0149, 1.6637))
```

### What stays unchanged
- `natural_pole_dir()` — pure math
- `configure_hand_finger_rigify()` — works in MCP context as-is
- All bone creation, renaming, constraint logic — no problematic ops
- Widget geometry constants (`_EYE_VERTS`, `_EYE_EDGES`, etc.)
- `find_best_pole_angle()` nested function

### Critical note: `bpy.ops.pose.rigify_generate()`
No direct Python API replacement exists. The script must:
1. Set metarig as active object: `bpy.context.view_layer.objects.active = metarig`
2. Switch to POSE mode: `bpy.ops.object.mode_set(mode='POSE')`
3. Call: `bpy.ops.pose.rigify_generate()`

This works via `execute_blender_code` since MCP runs in a full Blender context.

---

## Algorithm (for README.md)

1. Find metarig by `METARIG_NAME`; set as active object
2. Configure finger bones: `MiddleFinger_01_L/R`, `PinkyFinger_01_L/R` → `rigify_type = "limbs.super_finger"`, copy params from `IndexFinger_01_L/R`
3. Enter POSE mode → call `bpy.ops.pose.rigify_generate()`
4. Find generated rig (via `metarig.data.rigify_target_rig` or fallback to `RIG_NAME`)
5. Enter EDIT mode on rig → remove `ORG-Eyebrows`, `ORG-Eyes`, `ORG-eyebrow_anchor.R`
6. Reposition arm IK poles: `upper_arm_ik_target.L/R` using `natural_pole_dir` × `ELBOW_DISTANCE`
7. Set pole angle on `MCH-shin_ik.L/R` via `find_best_pole_angle` grid search
8. Reposition leg IK poles: `thigh_ik_target.L/R` offset `(0, -1, 0)` × `KNEE_DISTANCE`
9. Create `eye_ctrl.L/R` and `eyes_ctrl` bones; parent chain: `eye_ctrl.* → eyes_ctrl → head`
10. Add DAMPED_TRACK on `Eye_L/R` → `eye_ctrl.L/R`; hide `Eye_L/R`
11. Create eyebrow control bones at `BROW_*` positions; parent to `head`; lock X/Z
12. Add COPY_LOCATION + DAMPED_TRACK constraints on `ORG-Eyebrow_L/R`
13. Create `DEF-jaw`, `DEF-Eyebrow_L/R` bones
14. Set all DEF parent chain (~30 pairs) — see `rigify_fix.py` lines 197–223
15. Disable deform on split bones: `DEF-*.*.001` variants
16. Create eye/eyebrow widget meshes in WGTS collection; assign as `custom_shape`

---

## API Sensitivity

`api_sensitive: true`

Reasons:
- `bpy.ops.pose.rigify_generate()` — Rigify addon operator, behavior varies by Rigify version
- `bone.rigify_type`, `bone.rigify_parameters` — Rigify 4.0+ custom properties
- Hardcoded Rigify output bone names (`ORG-`, `MCH-`, `DEF-` prefixes) — Rigify 4.0 convention
- `bpy.context.view_layer.update()` — used in pole angle optimization

---

## Files to Create

```
library/scripts/rigify-generate-and-fix/
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

**Prerequisites (README.md body):**
- Rigify addon must be enabled
- Scene must contain a metarig named `METARIG_NAME` with Synty-compatible bone structure
- Finger bones: `IndexFinger_01_L/R`, `MiddleFinger_01_L/R`, `PinkyFinger_01_L/R` must be present in metarig
- Blender 4.0+

---

## Verification

1. Open a Blender file with a Synty metarig
2. Run `analyse-rigify-setup` → confirm 0/12 steps applied
3. Run `solution_4.1.py` via `execute_blender_code`
4. Run `analyse-rigify-setup` again → confirm 12/12 steps applied
5. Inspect rig in viewport: eye controls, eyebrow controls, DEF hierarchy visible
