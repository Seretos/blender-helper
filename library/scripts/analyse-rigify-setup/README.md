---
blender_version: "4.1"
tested_on: "4.1"
api_sensitive: true
reference_version: "4.1"
---

# analyse-rigify-setup

**Problem:** Check which of the 12 seredos post-processing steps have been applied to the generated Rigify rig.

**Algorithm:** (1) Find metarig and rig (auto-detect or from parameters); (2) run each of 12 checks against bpy.data / pose.bones properties; (3) track APPLIED / NOT_APPLIED / PARTIAL per check; (4) count and print hierarchical report.

**Prerequisites:** A generated Rigify rig in scene. Metarig optional but improves pre-generation checks.

**API sensitivity:** Accesses Rigify-specific properties (`rigify_type` on pose bones, `rigify_target_rig` on armature data) which are Rigify 4.0+ conventions.
