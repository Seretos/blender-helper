# Blender Helper — Solution Library

| Slug | Problem | Tags | Blender Version | API Sensitive | Status |
|---|---|---|---|---|---|
| scripts/analyse-scene-overview | Report all objects, armatures, bindings, actions, items, and export readiness in current scene | analysis | 4.1 | false | done |
| scripts/analyse-rigify-setup | Check which of the 12 seredos post-processing steps have been applied to the generated rig | analysis, rig | 4.1 | true | done |
| scripts/analyse-mesh-binding | Report per-mesh armature binding state, unmapped VGs, Synty-era VGs, face constraint status | analysis, weights | 4.1 | false | done |
| scripts/rigify-generate-and-fix | Generate Rigify rig from metarig and apply all Synty-specific post-processing fixes | rig | 4.1 | true | done |
| scripts/rebind-to-rig | Rebind Synty character meshes from source armature to generated Rigify rig via position-based bone mapping | rig, weights | 4.1 | false | done |
| scripts/export-fbx-unity | Export rigged character (model, items, body/face animations) to FBX with Unity axis settings | export | 4.1 | true | done |
| addons/seredos-backup | Auto-backup blend file before every save via persistent save_pre handler | backup, handler | 4.1 | true | done |
