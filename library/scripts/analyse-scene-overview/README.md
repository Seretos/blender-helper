---
blender_version: "4.1"
tested_on: "4.1"
api_sensitive: false
reference_version: "4.1"
---

# analyse-scene-overview

**Problem:** Report a comprehensive overview of the current Blender scene for the skill to use as context before acting.

**Algorithm:** (1) Collect all objects by type; (2) classify armatures as metarig/rig/source using name and pose bone heuristics; (3) report per-mesh stats (armature modifier target, VG counts, shape keys); (4) classify actions (body/face/blacklisted); (5) collect SLOT-* items; (6) evaluate 8 export readiness checks; (7) print structured report.

**Prerequisites:** None — reads the active scene. Run at any point to get scene state.
