---
blender_version: "4.1"
tested_on: "4.1"
api_sensitive: false
reference_version: "4.1"
---

# analyse-mesh-binding

**Problem:** Report the binding state of all mesh objects in the scene — which are fully rebound to the Rigify rig, partially bound, or still bound to the source armature.

**Algorithm:** (1) Find RIG armature; (2) for each mesh: check armature modifier target, count mapped/unmapped/Synty VGs vs rig pose bones, determine UNBOUND/PARTIAL/FULL state; (3) check COPY_TRANSFORMS constraints for 4 face DEF→ORG pairs; (4) print report with actionable next steps.

**Prerequisites:** At least one armature in scene. Most useful after running rigify-generate-and-fix and before/after rebind-to-rig.
