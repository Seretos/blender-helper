# Plan: analyse-scene-overview

## Context

Write a read-only analysis script from scratch that outputs a structured text report of the current Blender scene. The report is consumed by the skill (language model) to build context before acting — not by a human. It must be comprehensive, LLM-parseable, and modify nothing.

Informed by all 4 addon sources: armature naming conventions from `seredos_rigify`, mesh/VG structure from `seredos_rebind`, SLOT-* items and action patterns from `seredos_export`.

**Target:** `library/scripts/analyse-scene-overview/`

---

## What the Script Reports

### 1. Scene State Flags (quick booleans at top)
- Metarig present? (and name)
- Generated rig present? (and name)
- Source armature(s) present? (count)
- Meshes: how many bound to RIG / bound to source / unbound
- Actions: body / face / blacklisted counts
- Items (SLOT-*): count

### 2. Metarig Structure
- Name, bone count
- `rigify_target_rig` property value (linked to RIG?)
- Key bone presence: finger bones, Eye_L/R, Eyebrow_L/R, jaw

### 3. Generated Rig
- Name, bone count breakdown: DEF / ORG / MCH / CTRL
- Key spine bones: `DEF-spine`, `DEF-spine.003`, `DEF-neck` (spine.004 renamed), `DEF-head` (spine.006 renamed)
- Face bones: `DEF-Eye_L/R`, `DEF-Eyebrow_L/R` — presence + COPY_TRANSFORMS constraint status
- Control bones: `eye_ctrl.L/R`, `eyes_ctrl`, `eyebrow_ctrl.*` — presence

### 4. Source Armature(s)
- Per armature: name, bone count, detection heuristic (why classified as source), meshes bound

### 5. Meshes
- Per mesh: name, parent object, armature modifier target, VG count (DEF- vs. non-DEF ratio), shape key count, is SLOT-* child?

### 6. Actions
- Body actions (no FACE- prefix, not blacklisted): name + frame range
- Face actions (FACE- prefix): name + frame range
- Blacklisted: names

### 7. Items (SLOT-*)
- Per slot: empty name, mesh children, vertex counts

### 8. Export Readiness Checklist
```
[✓/✗] Metarig present and linked to generated RIG
[✓/✗] Generated RIG present with DEF/ORG structure
[✓/✗] All meshes rebound (armature modifier → RIG, VGs are DEF-*)
[✓/✗] Face VGs present (DEF-Eye_L/R, DEF-Eyebrow_L/R)
[✓/✗] Face shape keys exist (FACE_* pattern on mesh)
[✓/✗] FACE- actions present
[✓/✗] No source armature still has meshes bound
[✓/✗] Blend file saved (required for export paths)

BLOCKERS: [list specific issues]
```

---

## Parameters

```python
# No parameters — reads entire active scene
```

---

## Algorithm

1. Collect all objects: split by type (ARMATURE, MESH, EMPTY)
2. **Classify armatures:**
   - Metarig: has `data.get("rigify_target_rig")` property, OR name starts with `META-`, OR name == `metarig`
   - Generated rig: has both `DEF-` and `ORG-` prefix pose bones (check `DEF-spine` + `ORG-spine`)
   - Source: anything else with mesh children
3. **Per mesh:** check armature modifier target, count VGs by DEF-prefix, count shape keys with `FACE_` prefix
4. **Classify actions:** `FACE-` prefix → face; `Armature|Take 001|BaseLayer` prefix → blacklisted; else → body
5. **SLOT-* empties:** find all empties starting with `SLOT-`, collect mesh children
6. **Evaluate 8 readiness checks**
7. Print report to stdout

---

## Output Format

Plain text, `────` section separators, `✓`/`✗` flags, no JSON. Example skeleton:

```
═══════════════════════════════════════════════════
  SCENE OVERVIEW — MyScene | character.blend
═══════════════════════════════════════════════════

SCENE STATE FLAGS
─────────────────
  Metarig         : ✓ META-Character
  Generated Rig   : ✓ RIG-Character
  Source Arms     : 1 (Armature)
  Meshes (RIG)    : 4 / Source: 0 / Unbound: 0
  Actions         : 12 body, 3 face, 1 blacklisted
  Items (SLOT-*)  : 2

EXPORT READINESS
─────────────────
  [✓] Metarig linked to RIG
  [✓] Generated RIG with DEF/ORG
  [✓] All meshes rebound
  ...
  BLOCKERS: none
...
```

---

## bpy API Calls

```python
bpy.data.objects                          # all objects
obj.type                                  # 'ARMATURE', 'MESH', 'EMPTY'
obj.data.get("rigify_target_rig")         # metarig property
obj.pose.bones                            # classify armature
pbone.name.startswith("DEF-")
obj.modifiers; mod.type == 'ARMATURE'; mod.object
obj.vertex_groups; vg.name.startswith("DEF-")
obj.data.shape_keys; sk.name.startswith("FACE_")
bpy.data.actions; action.name; action.frame_range
obj.name.startswith("SLOT-")
obj.children
bpy.data.filepath                         # saved check
```

---

## Files to Create

```
library/scripts/analyse-scene-overview/
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

---

## Verification

1. Open a partially-set-up Blender scene (e.g., metarig present but rig not generated)
2. Run `solution_4.1.py` via `execute_blender_code`
3. Confirm: scene flags correctly reflect state, blockers list the missing step
4. Run `rigify-generate-and-fix`, then re-run analysis → flags update correctly
5. Run on a fully-complete scene → all 8 readiness checks pass, BLOCKERS: none
