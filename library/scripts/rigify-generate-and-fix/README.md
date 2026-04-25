---
blender_version: "4.1"
tested_on: "4.1"
api_sensitive: true
reference_version: "4.1"
---

# rigify-generate-and-fix

**Problem:** Generate a Rigify rig from a Synty-compatible metarig and apply all seredos post-processing fixes in a single run (IK pole targets, eye controls, eyebrow controls, DEF hierarchy).

**Algorithm:** (1) Configure finger bones (super_finger type) on the metarig; (2) generate rig via bpy.ops.pose.rigify_generate(); (3) remove unwanted ORG bones (Eyebrows, Eyes, eyebrow_anchor.R); (4) reposition IK pole targets for arms (natural bend direction) and legs (forward -Y); (5) create eye control bones (eye_ctrl.L/R, eyes_ctrl) with custom circle widgets; (6) create 3-point eyebrow control bones (eyebrow_ctrl.R, eyebrow_ctrl_center, eyebrow_ctrl.L); (7) create DEF-jaw bone for Unity Humanoid mapping; (8) create DEF-Eyebrow_L/R deform bones; (9) set full DEF parent hierarchy (~20 explicit pairs); (10) disable split DEF bones; (11) rename DEF-spine.004/006 to DEF-neck/DEF-head; (12) find best knee IK pole angles via iterative search; (13) set DAMPED_TRACK constraints on Eye_L/R; (14) assign custom widget meshes to eye/eyebrow controls; (15) set COPY_LOCATION + DAMPED_TRACK on ORG-Eyebrow bones; (16) set COPY_TRANSFORMS on DEF-Eye/Eyebrow bones.

**Prerequisites:** Rigify addon enabled; metarig with Synty-compatible bone structure including IndexFinger_01_L/R, MiddleFinger_01_L/R, PinkyFinger_01_L/R; metarig must be the active object when script runs; Blender 4.0+.

**API sensitivity:** Uses `bpy.ops.pose.rigify_generate()` (Rigify addon operator) and Rigify 4.0 bone naming conventions (ORG-/MCH-/DEF- prefixes). The `pole_vector` custom property key and `rigify_parameters` RNA path are Rigify-version-sensitive.
