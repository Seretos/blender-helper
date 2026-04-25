# Integration Plan: rebind-to-rig

## Context

Port the core logic of `seredos_rebind` from an addon operator into a parametrized MCP-runnable library script. This is the cleanest of the four addons — zero `bpy.ops` calls in the core logic, dry-run support already built in, functions already separated from UI.

**Source:** `E:\development\ai-villager\Blender\addons\seredos_rebind\`
- `__init__.py` (69 lines) — UI panel + registration
- `rebind_character.py` (604 lines) — all core logic

**Target:** `library/scripts/rebind-to-rig/`

---

## What the Addon Does

Rebinds Synty character meshes from their original armature to a Rigify-generated rig:

1. Detects source armature (Synty skeleton), metarig, and generated RIG from scene
2. For each mesh child of source armature:
   a. Splits shared `Eyes` VG into `DEF-Eye_L` / `DEF-Eye_R` by X-axis position
   b. Builds position-based bone map: source bones → META bones (world-space proximity)
   c. Maps META bones → DEF bones via `resolve_rig_bone`
   d. Renames all vertex groups: source name → DEF name
   e. Replaces ARMATURE modifier: old rig → new rig
   f. Reparents mesh to new rig (world matrix preserved)
3. Adds COPY_TRANSFORMS constraints: `DEF-Eye_L/R` → `ORG-Eye_L/R`, `DEF-Eyebrow_L/R` → `ORG-Eyebrow_L/R`

---

## Extent of Changes

**Overall change magnitude: ~35% of lines** (boilerplate removal + entry point + parameter block)

### What gets stripped (~165 lines)
- `SEREDOS_PT_rebind` panel class (~45 lines in `__init__.py`)
- `OBJECT_OT_seredos_rebind` operator class (~100 lines)
- `bpy.types.Scene.seredos_rebind_dry_run` property registration
- `register()` / `unregister()` functions (~20 lines)

### What gets parametrized (new top-of-script block)
```python
SOURCE_ARMATURE_NAME = ""    # Auto-detect if empty
META_ARMATURE_NAME   = ""    # Auto-detect if empty
RIG_ARMATURE_NAME    = ""    # Auto-detect if empty
DRY_RUN              = False
POSITION_THRESHOLD   = 0.15  # Max bone distance for position matching (Blender units)
EYES_VG_NAME         = "Eyes"
EYEBROW_VG_L         = "Eyebrow_L"
EYEBROW_VG_R         = "Eyebrow_R"
EYEBROW_VG_COMBINED  = "Eyebrows"
```

### What stays completely unchanged (all 10 core functions)
- `resolve_rig_bone(rig_arm, meta_bone_name)` — META → DEF name mapping
- `_coerce_armature_object(candidate)` — normalize rig references
- `_looks_like_generated_rig(arm_obj)` — heuristic rig detection
- `_iter_scene_objects()` — stable object iteration
- `_get_object_by_name(name)` — name-based lookup with fallback
- `_is_animatable_ctrl_bone(bone_name)` — control bone filter
- `build_bone_mapping(source_arm, meta_arm, threshold)` — position-based mapping
- `build_control_bone_mapping(source_arm, meta_arm, rig_arm, threshold)` — 3-step mapping
- `split_by_symmetry(mesh, old_vg, new_l, new_r, dry_run)` — X-axis VG split
- `rename_vertex_groups_with_mapping(mesh, mapping, rig_arm, dry_run)` — VG rename
- `rebind_armature_modifier(mesh, source_arm, rig_arm, dry_run)` — modifier swap
- `reparent_to_rig(mesh, rig_arm, dry_run)` — reparent with matrix preservation
- `set_def_org_constraints(rig_arm, dry_run)` — face COPY_TRANSFORMS
- `get_meshes_of_armature(source_arm)` — mesh children
- `get_rig_from_meta(arm_obj)` — detect meta/rig pair

### New entry point to add (~30 lines)
```python
def run():
    source_arm = _get_object_by_name(SOURCE_ARMATURE_NAME) if SOURCE_ARMATURE_NAME else None
    if source_arm is None:
        # Auto-detect: armature that is not meta/rig and has mesh children
        for obj in _iter_scene_objects():
            if obj.type == 'ARMATURE' and not _looks_like_generated_rig(obj):
                if any(c.type == 'MESH' for c in obj.children):
                    source_arm = obj
                    break
    meta_arm, rig_arm = get_rig_from_meta(source_arm)
    meshes = get_meshes_of_armature(source_arm)
    for mesh in meshes:
        split_by_symmetry(mesh, EYES_VG_NAME, "DEF-Eye_L", "DEF-Eye_R", DRY_RUN)
        mapping = build_bone_mapping(source_arm, meta_arm, POSITION_THRESHOLD)
        rename_vertex_groups_with_mapping(mesh, mapping, rig_arm, DRY_RUN)
        rebind_armature_modifier(mesh, source_arm, rig_arm, DRY_RUN)
        reparent_to_rig(mesh, rig_arm, DRY_RUN)
    set_def_org_constraints(rig_arm, DRY_RUN)
    print(f"Rebind complete. Processed {len(meshes)} meshes. DRY_RUN={DRY_RUN}")

run()
```

---

## Algorithm (for README.md)

1. Detect or look up source armature, metarig, and generated rig
2. For each mesh child of source armature:
   - Split `Eyes` VG into `DEF-Eye_L` (x≥0) and `DEF-Eye_R` (x<0)
   - Build position-based map: source bones → META bones (within `POSITION_THRESHOLD`)
   - Resolve META → DEF via Rigify naming conventions
   - Rename all vertex groups to their DEF equivalents
   - Swap ARMATURE modifier target from source to RIG
   - Reparent mesh to RIG (world matrix unchanged)
3. On the RIG: add COPY_TRANSFORMS constraints on DEF-Eye_L/R → ORG-Eye_L/R, DEF-Eyebrow_L/R → ORG-Eyebrow_L/R

---

## API Sensitivity

`api_sensitive: false`

Uses only `bpy.data`, `mathutils.Matrix`, and direct property access. No `bpy.ops` in core logic. Version-safe handling already present via `_iter_scene_objects()` and `_get_object_by_name()`.

---

## Files to Create

```
library/scripts/rebind-to-rig/
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

**Prerequisites (README.md body):**
- Scene must contain the Synty source armature with bound meshes
- Rigify rig must already be generated (run `rigify-generate-and-fix` first)
- Metarig must still be in scene (used for position mapping)
- Blender 4.0+

---

## Verification

1. Open a Blender file with a Synty character bound to its original armature + generated Rigify rig
2. Run `analyse-mesh-binding` → confirm meshes show `UNBOUND` state
3. Run `solution_4.1.py` via `execute_blender_code` (with `DRY_RUN = True` first)
4. Inspect printed report — confirm expected VG renames and modifier swaps
5. Set `DRY_RUN = False` and run again
6. Run `analyse-mesh-binding` → confirm all meshes show `FULL` state
7. Pose the rig in Blender — meshes should deform correctly
