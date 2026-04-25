---
blender_version: "4.1"
tested_on: "4.1"
api_sensitive: true
reference_version: "4.1"
---

# export-fbx-unity

**Problem:** Export a rigged character to FBX for Unity — static model, individual items, body animations, and face animations in a single run.

**Algorithm:** (1) Find rig + validate blend file is saved; (2) calculate all output paths from blend file directory; (3) collect items (SLOT-* children) and character objects; (4) export static model FBX (`characters.fbx`); (5) export each item FBX individually; (6) for each body action: bake constraints via nla.bake, export single-action FBX; (7) for each FACE- action: bake shape key values per frame from bone positions, export mesh-only FBX (no rig).

**Prerequisites:** Blend file must be saved; active armature is the rig or set RIG_NAME; FBX I/O addon enabled (built-in, usually on by default); Unity project at `../Assets/` relative to blend file; face shape keys must be set up (run `setup_face_shape_keys()` once before first face animation export); Blender 4.0+.

**API sensitivity:** `bpy.ops.export_scene.fbx` parameters changed between Blender 3.x and 4.x; `bpy.ops.nla.bake` behavior is version-sensitive; `evaluated_get(depsgraph)` for shape key evaluation.
