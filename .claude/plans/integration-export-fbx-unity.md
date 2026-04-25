# Integration Plan: export-fbx-unity

## Context

Port the core logic of `seredos_export` from an addon operator into a parametrized MCP-runnable library script. The addon is large (~1020 lines total) but well-structured: ~42% pure logic (zero changes needed), ~54% bpy-dependent helpers (kept as-is), ~14% operator boilerplate (stripped).

**Source:** `E:\development\ai-villager\Blender\addons\seredos_export\`
- `__init__.py` (62 lines) — addon registration + menu hooks
- `export_characters.py` (958 lines) — all logic

**Target:** `library/scripts/export-fbx-unity/`

---

## What the Addon Does

Exports a rigged character to FBX for Unity with four export types:

1. **Static model** — rig + all bound meshes → `characters.fbx` in `Models/Characters/`
2. **Items** — meshes under `SLOT-*` empties → individual FBXes in `Models/Items/`
3. **Body animations** — each non-blacklisted action: bake constraints via `nla.bake` → FBX in `Animations/`
4. **Face animations** — `FACE-` prefixed actions: per-frame shape key baking → FBX (no rig, shape keys only) in `Animations/Face/`

All exports use Unity-specific FBX settings:
```python
axis_forward = '-Y', axis_up = 'Z'
apply_scale_options = 'FBX_SCALE_UNITS'
add_leaf_bones = False
use_armature_deform_only = True
primary_bone_axis = 'Y', secondary_bone_axis = 'X'
```

---

## Extent of Changes

**Overall change magnitude: ~15% of lines** (boilerplate removal + entry point + variable block)

### What gets stripped (~110 lines)
- `EXPORT_OT_seredos_characters` operator class
- `EXPORT_OT_seredos_setup_face_shapekeys` operator class
- Menu registration (`FILE_MT_export.append/remove`)
- `register()` / `unregister()` functions

### What gets parametrized (new top-of-script block)

The existing module-level constants (`EXPORT_SUBPATH`, `FBX_SETTINGS`, etc.) are already isolated — just expose them as editable variables at the top:

```python
import os
import bpy

RIG_NAME   = ""  # Auto-detect active armature if empty
BLEND_FILE_PATH = bpy.data.filepath  # Usually auto

EXPORT_SUBPATH    = os.path.join("..", "Assets", "Seredos", "Character", "Models", "Characters")
ANIM_SUBPATH      = os.path.join("..", "Assets", "Seredos", "Character", "Animations")
FACE_ANIM_SUBPATH = os.path.join("..", "Assets", "Seredos", "Character", "Animations", "Face")
ITEMS_SUBPATH     = os.path.join("..", "Assets", "Seredos", "Character", "Models", "Items")
EXPORT_FILE       = "characters.fbx"

SLOT_PREFIX              = "SLOT-"
FACE_PREFIX              = "FACE-"
ANIM_BLACKLIST_PREFIXES  = {"Armature|Take 001|BaseLayer"}

FBX_SETTINGS = dict(
    axis_forward             = '-Y',
    axis_up                  = 'Z',
    apply_scale_options      = 'FBX_SCALE_UNITS',
    apply_unit_scale         = True,
    bake_space_transform     = True,
    add_leaf_bones           = False,
    primary_bone_axis        = 'Y',
    secondary_bone_axis      = 'X',
    use_armature_deform_only = True,
    mesh_smooth_type         = 'FACE',
    use_mesh_modifiers       = True,
    path_mode                = 'RELATIVE',
)
```

### What stays completely unchanged (~850 lines)

**Pure logic functions:**
- `get_export_paths(blend_filepath)` → (model_dir, anim_dir, face_anim_dir, fbx_path)
- `get_item_export_path(blend_filepath)` → items_dir
- `find_exportable_items(rig)` → list of SLOT-* child meshes
- `collect_character_objects(rig, items)` → all rig descendants minus items
- `sanitize_filename(name)` → Windows-safe filename
- `should_export_action(action_name, blacklist_prefixes)` → bool
- `_parse_face_sk_name(sk_name)` → (bone_name, suffix, idx, direction) or None

**bpy-dependent helpers (no structural changes needed):**
- `collect_hierarchy(root_obj)`
- `switch_to_object_mode()` / `restore_mode(prev_mode)`
- `export_model(fbx_path, objects)` — `bpy.ops.export_scene.fbx`
- `export_single_item(items_dir, item_obj)` / `export_items(items_dir, items)`
- `bake_action(rig, action)` — `bpy.ops.nla.bake`
- `export_animations(anim_dir, face_anim_dir, rig)`
- `get_ctrl_bones_from_action(action)` / `find_def_bones_for_ctrl(rig, ctrl_bone_name)`
- `get_face_meshes_for_action(rig, action)`
- `setup_face_shape_keys(rig)` — complex 152-line function; unchanged
- `bake_shape_key_animation(face_meshes, action, rig)`
- `cleanup_shape_key_keyframes(face_meshes, baked)`
- `export_face_animation(face_anim_dir, rig, face_meshes, action)`

### New entry point to add (~20 lines)
```python
def run():
    rig = bpy.data.objects.get(RIG_NAME) if RIG_NAME else bpy.context.active_object
    if not rig or rig.type != 'ARMATURE':
        print("ERROR: No rig found. Set RIG_NAME or select armature.")
        return
    blend_path = BLEND_FILE_PATH or bpy.data.filepath
    if not blend_path:
        print("ERROR: Blend file not saved. Save the file first.")
        return
    model_dir, anim_dir, face_anim_dir, fbx_path = get_export_paths(blend_path)
    items_dir = get_item_export_path(blend_path)
    items = find_exportable_items(rig)
    objects = collect_character_objects(rig, items)
    prev_mode = switch_to_object_mode()
    try:
        export_model(fbx_path, objects)
        export_items(items_dir, items)
        export_animations(anim_dir, face_anim_dir, rig)
    finally:
        restore_mode(prev_mode)
    print(f"Export complete → {fbx_path}")

run()
```

---

## Algorithm (for README.md)

1. Find rig from `RIG_NAME` or active object; validate blend file is saved
2. Calculate all export paths from blend file directory
3. Collect items (meshes under `SLOT-*` empties) and character objects (all rig descendants minus items + their children)
4. Switch to OBJECT mode; save previous mode for restore
5. Export static model FBX (`characters.fbx`)
6. Export each item FBX individually (preserving parent transform from `transforms` empty)
7. For each action (filtered by `should_export_action`):
   - If name starts with `FACE-`: find affected meshes, bake shape key values per frame, export FBX (shape keys only, rig excluded)
   - Otherwise: bake constraints to keyframes via `nla.bake`, export single-action FBX (rig + meshes)
8. Restore previous mode

---

## API Sensitivity

`api_sensitive: true`

Reasons:
- `bpy.ops.export_scene.fbx` — FBX export API parameters changed between Blender 3.x and 4.x
- `bpy.ops.nla.bake` — `visual_keying=True` and `bake_types={'POSE'}` are version-sensitive
- `evaluated_get(depsgraph)` for shape key evaluation — introduced in 2.92, behavior may vary

---

## Files to Create

```
library/scripts/export-fbx-unity/
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
- Blend file must be saved (export paths derived from blend file location)
- Scene must contain a rigged character with the rig as the active armature (or set `RIG_NAME`)
- FBX I/O addon must be enabled (built into Blender, usually on by default)
- Unity project must be at `../Assets/` relative to the blend file (or update `*_SUBPATH` variables)
- Blender 4.0+

---

## Verification

1. Open a Blender file with a fully rigged and rebound Synty character, saved to disk
2. Confirm the Unity project exists at the expected relative path
3. Run `solution_4.1.py` via `execute_blender_code`
4. Check Unity project: `Models/Characters/characters.fbx` should exist
5. Check `Animations/` directory: one FBX per body action
6. Check `Animations/Face/` directory: one FBX per `FACE-` action
7. Import `characters.fbx` into Unity and verify rig deforms correctly
