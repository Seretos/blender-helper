---
blender_version: "4.1"
tested_on: "4.1"
api_sensitive: false
reference_version: "4.1"
---

# rebind-to-rig

**Problem:** Rebind Synty character meshes from their original armature to a generated Rigify rig using position-based bone mapping.

**Algorithm:** (1) Detect source armature, metarig, and generated rig (auto-detect or from parameters); (2) build position-based bone map (source bone heads → nearest META bone heads, within POSITION_THRESHOLD); (3) for each mesh: split Eyes VG by X-axis position into DEF-Eye_L/R; split Eyebrows combined VG into DEF-Eyebrow_L/R if present; (4) rename all vertex groups to DEF equivalents via source→META→DEF resolution; (5) swap ARMATURE modifier target from source armature to RIG; (6) reparent mesh to RIG (world matrix preserved); (7) add COPY_TRANSFORMS constraints on DEF-Eye/Eyebrow bones pointing to their ORG counterparts.

**Prerequisites:** Source armature with bound meshes; generated Rigify rig (run rigify-generate-and-fix first); metarig still in scene; Blender 4.0+.

**API sensitivity:** Uses only bpy.data and mathutils — no bpy.ops in core logic. Version-safe.
