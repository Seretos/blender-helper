# Combined Execution Plan: Blender Helper Skill

## Context

Eight individual plans exist but nothing has been written yet. This plan implements all of them in a single execution by distributing work across 4 parallel agents. Together they build the complete blender-helper skill: a Claude Code skill with a reusable library of Blender scripts and addons for a game development pipeline (Synty → Rigify → Unity via meshy.ai).

**Base path:** `C:\Users\arnev\.claude\skills\blender-helper\`

---

## Key Constraint

`library/INDEX.md` is created exclusively by **Agent 1**. Agents 2–4 create only their respective library files and must **not** touch INDEX.md.

---

## Agent 1 — Skill Infrastructure

**Source plan:** `blender-helper-skill.md`

Creates the 3 top-level files that define the skill itself.

### Files to create

**`SKILL.md`** — The invokable skill prompt (must be named `SKILL.md` — that is the filename Claude Code uses to find and invoke the skill). YAML frontmatter required. Hard limit: ≤ 4 000 chars **for the main file**. If the content would exceed this limit, split into companion files (e.g. `SKILL-patterns.md`, `SKILL-library.md`) and reference them from SKILL.md with a short description and relative link. SKILL.md itself must stay ≤ 4 000 chars and be self-contained enough to orient a new conversation; companion files hold the detail. Must cover:
- Purpose: Blender workflows for game development (graphics pipeline broadly; first entries cover rigging / binding / export for meshy.ai + Synty → Unity)
- Three behavioral patterns and when to use them:
  - **ANALYSE** — use `get_scene_info` / `execute_blender_code` with analysis scripts; only when needed
  - **STRATEGY** — for problems with no library entry; add WIP row to INDEX.md immediately; develop algorithm collaboratively; write files only on explicit user confirmation
  - **EXECUTE** — find match in INDEX.md; version-check (`print(bpy.app.version_string)`); run `solution_{version}.py`; on error: decide between Extend or Rewrite
- Library structure (scripts vs addons, README frontmatter, INDEX.md columns)
- Language: respond in user's language; all library files and code in English
- Scripts must always be parametrized (object/bone names as top-level variables) — enforce silently
- Always work in small `execute_blender_code` chunks during STRATEGY
- seredos-backup: check installed/enabled on every session start; auto-install if not; call `bpy.ops.wm.save_mainfile()` after every scene-modifying operation
- On MCP failure: check `setup/blender-mcp-setup.md`

Use AGENTS.md for formatting constraints (imperatives not prose, ≤ 6 sections, ≤ 2 nesting levels, ≤ 120 chars per instruction line).

**`library/INDEX.md`** — Pre-populated with all 7 initial entries, all status `done`:

| Slug | Problem | Tags | Blender Version | API Sensitive | Status |
|---|---|---|---|---|---|
| scripts/analyse-scene-overview | Report all objects, armatures, bindings, actions, items, and export readiness in current scene | analysis | 4.1 | false | done |
| scripts/analyse-rigify-setup | Check which of the 12 seredos post-processing steps have been applied to the generated rig | analysis, rig | 4.1 | true | done |
| scripts/analyse-mesh-binding | Report per-mesh armature binding state, unmapped VGs, Synty-era VGs, face constraint status | analysis, weights | 4.1 | false | done |
| scripts/rigify-generate-and-fix | Generate Rigify rig from metarig and apply all Synty-specific post-processing fixes | rig | 4.1 | true | done |
| scripts/rebind-to-rig | Rebind Synty character meshes from source armature to generated Rigify rig via position-based bone mapping | rig, weights | 4.1 | false | done |
| scripts/export-fbx-unity | Export rigged character (model, items, body/face animations) to FBX with Unity axis settings | export | 4.1 | true | done |
| addons/seredos-backup | Auto-backup blend file before every save via persistent save_pre handler | backup, handler | 4.1 | true | done |

**`setup/blender-mcp-setup.md`** — Installation and activation guide for Blender MCP. Cover:
- Installing the Blender MCP addon (blender-mcp package or manual)
- Enabling it in Blender preferences
- Connecting Claude Code (MCP server config in Claude settings)
- Verifying connection: test `get_scene_info` returns data
- Troubleshooting: common errors (port conflicts, addon not enabled, wrong Python path)

---

## Agent 2 — Analysis Scripts (written from scratch)

**Source plans:** `analysis-scene-overview.md`, `analysis-rigify-setup.md`, `analysis-mesh-binding.md`

All 3 scripts are written from scratch — no source addon files needed. All are read-only (modify nothing in the scene).

### Script 1: `library/scripts/analyse-scene-overview/`

**What it does:** Comprehensive scene report consumed by the skill before acting. Reports: scene state flags (metarig/rig/meshes/actions/items), metarig structure, generated rig structure (bone count by prefix, face/control bone presence), source armatures, per-mesh stats (armature modifier target, VG DEF-ratio, shape keys), action classification (body/face/blacklisted), SLOT-* items, and 8-item export readiness checklist with BLOCKERS list.

**Parameters:** None — reads entire active scene.

**Key bpy API:** `bpy.data.objects`, `obj.type`, `obj.data.get("rigify_target_rig")`, `obj.pose.bones`, `obj.modifiers`, `obj.vertex_groups`, `obj.data.shape_keys`, `bpy.data.actions`, `bpy.data.filepath`

**Armature classification heuristic:**
- Metarig: has `data.get("rigify_target_rig")` OR name starts with `META-` OR name == `metarig`
- Generated rig: has both `DEF-spine` and `ORG-spine` pose bones
- Source: anything else with mesh children

**Action classification:** `FACE-` prefix → face; `Armature|Take 001|BaseLayer` prefix → blacklisted; else → body

**Readiness checks (8):** metarig linked to RIG, RIG with DEF/ORG structure, all meshes rebound, face VGs present, face shape keys exist, FACE- actions present, no source armature still has meshes bound, blend file saved.

**Output format:** Plain text, `════` header, `────` section separators, `✓`/`✗` flags. See `analysis-scene-overview.md` for exact format skeleton.

**README frontmatter:** `blender_version: "4.1"`, `tested_on: "4.1"`, `api_sensitive: false`, `reference_version: "4.1"`

---

### Script 2: `library/scripts/analyse-rigify-setup/`

**What it does:** Checks which of 12 seredos post-processing steps are applied to the rig. Per-check result: `APPLIED` / `NOT_APPLIED` / `PARTIAL`. Reports metarig presence, finger rigify_type config, rig presence, all 12 fix steps. Summary line: `N/12 steps applied`.

**Parameters:** `METARIG_NAME = ""` (auto-detect), `RIG_NAME = ""` (auto-detect)

**The 12 checks** (detection methods from `analysis-rigify-setup.md`):
1. Unwanted bones removed — `ORG-Eyebrows`, `ORG-Eyes`, `ORG-eyebrow_anchor.R` absent
2. IK pole targets repositioned — `upper_arm_ik_target.L/R`, `thigh_ik_target.L/R` not at world origin
3. Eye control bones created — `eye_ctrl.L`, `eye_ctrl.R`, `eyes_ctrl` present
4. Eye control parent hierarchy — `eye_ctrl.*.parent == "eyes_ctrl"`, `eyes_ctrl.parent == "head"`
5. Eye DAMPED_TRACK constraints — `Eye_L/R` have DAMPED_TRACK → `eye_ctrl.L/R`
6. Eye control custom shapes — `pbone.custom_shape` references `WGT-*` object
7. Eyebrow control bones created — `eyebrow_ctrl.R`, `eyebrow_ctrl_center`, `eyebrow_ctrl.L` present
8. Eyebrow parent + axis lock — parent == `head`; `lock_location == (True, False, True)`
9. Eyebrow ORG constraints — `ORG-Eyebrow_L/R` have COPY_LOCATION + DAMPED_TRACK constraints
10. DEF-Eyebrow bones — `DEF-Eyebrow_L/R` present; parent == `ORG-Eyebrow_L/R`
11. Full DEF hierarchy — check all pairs from `DEF_PARENTS` dict (see plan for full dict)
12. Split DEF bones disabled — `DEF-upper_arm.*.001` etc. have `use_deform=False`

**Hardcoded data to embed in script** (from `analysis-rigify-setup.md`):
```python
DEF_PARENTS = {
    "DEF-thigh.L": "DEF-spine", "DEF-thigh.R": "DEF-spine",
    "DEF-shoulder.L": "DEF-spine.003", "DEF-shoulder.R": "DEF-spine.003",
    "DEF-upper_arm.L": "DEF-shoulder.L", "DEF-upper_arm.R": "DEF-shoulder.R",
    "DEF-RingFinger_01_L": "DEF-hand.L", "DEF-IndexFinger_01_L": "DEF-hand.L",
    "DEF-MiddleFinger_01_L": "DEF-hand.L", "DEF-PinkyFinger_01_L": "DEF-hand.L",
    "DEF-Thumb_01_L": "DEF-hand.L",
    "DEF-RingFinger_01_R": "DEF-hand.R", "DEF-IndexFinger_01_R": "DEF-hand.R",
    "DEF-MiddleFinger_01_R": "DEF-hand.R", "DEF-PinkyFinger_01_R": "DEF-hand.R",
    "DEF-Thumb_01_R": "DEF-hand.R",
    "DEF-jaw": "DEF-spine.006",
    "DEF-Eye_L": "DEF-spine.006", "DEF-Eye_R": "DEF-spine.006",
    "DEF-Eyebrow_L": "DEF-spine.006", "DEF-Eyebrow_R": "DEF-spine.006",
}
SPLIT_DEF_TO_DISABLE = [
    "DEF-upper_arm.L.001", "DEF-upper_arm.R.001",
    "DEF-forearm.L.001", "DEF-forearm.R.001",
    "DEF-thigh.L.001", "DEF-thigh.R.001",
    "DEF-shin.L.001", "DEF-shin.R.001",
]
```

**README frontmatter:** `blender_version: "4.1"`, `tested_on: "4.1"`, `api_sensitive: true`, `reference_version: "4.1"`

---

### Script 3: `library/scripts/analyse-mesh-binding/`

**What it does:** Per-mesh binding report: armature modifier target, VG count, mapped/unmapped VGs (vs rig pose bones), Synty-era VG detection, rebind state (UNBOUND/PARTIAL/FULL). Also reports face COPY_TRANSFORMS constraint status for 4 DEF/ORG pairs. Summary with counts and actionable next steps.

**Parameters:** `RIG_NAME = ""` (auto-detect: armature with both `DEF-` and `ORG-` pose bones)

**Rebind state logic:**
- `UNBOUND`: no armature modifier, OR modifier points to non-RIG armature, OR all VGs unmapped
- `PARTIAL`: modifier points to RIG, but some VGs unmapped (Synty names still present)
- `FULL`: modifier points to RIG, all VGs map to rig pose bones

**Synty-era VG detection** — embed in script:
```python
SYNTY_VG_NAMES = {"Eyes", "Eyebrows", "Eyebrow_L", "Eyebrow_R"}
SYNTY_BONE_PATTERNS = {
    "spine", "thigh", "hand", "forearm", "shoulder", "shin",
    "Thumb", "IndexFinger", "MiddleFinger", "PinkyFinger", "RingFinger",
    "Root", "Hips", "UpperArm", "LowerArm", "UpperLeg", "LowerLeg",
}
def is_synty_vg(name):
    if name.startswith("DEF-"): return False
    if name in SYNTY_VG_NAMES: return True
    return any(p in name for p in SYNTY_BONE_PATTERNS)
```

**Face pairs to check:**
```python
FACE_DEF_TO_ORG = [
    ("DEF-Eye_L", "ORG-Eye_L"), ("DEF-Eye_R", "ORG-Eye_R"),
    ("DEF-Eyebrow_L", "ORG-Eyebrow_L"), ("DEF-Eyebrow_R", "ORG-Eyebrow_R"),
]
```

**README frontmatter:** `blender_version: "4.1"`, `tested_on: "4.1"`, `api_sensitive: false`, `reference_version: "4.1"`

---

## Agent 3 — Integration Scripts: Rigify + Rebind

**Source plans:** `integration-rigify-generate-and-fix.md`, `integration-rebind-to-rig.md`

Both scripts are ported from existing addon source files. Agent 3 must read these files first.

### Source files to read

- `E:\development\ai-villager\Blender\addons\seredos_rigify\rigify_fix.py` (425 lines)
- `E:\development\ai-villager\Blender\addons\seredos_rebind\rebind_character.py` (604 lines)

### Script 1: `library/scripts/rigify-generate-and-fix/`

**Source:** `rigify_fix.py`

**Change magnitude: ~25% of lines.** Strip: panel class, `draw_generate_fix_button()`, `register()`/`unregister()`, `bl_info`. Keep: everything else unchanged.

**New parameter block** at top (replaces stripped boilerplate):
```python
from mathutils import Vector
METARIG_NAME     = "metarig"
RIG_NAME         = "RIG-Character"
ELBOW_DISTANCE   = 0.5
KNEE_DISTANCE    = 0.5
EYE_FORWARD_DIST = 0.35
BROW_OUTER_R  = Vector((-0.0606, -0.0149, 1.6516))
BROW_INNER_R  = Vector((-0.0281, -0.0149, 1.6671))
BROW_INNER_L  = Vector(( 0.0281, -0.0149, 1.6671))
BROW_OUTER_L  = Vector(( 0.0606, -0.0149, 1.6516))
BROW_CENTER   = Vector(( 0.0,    -0.0149, 1.6637))
```

**New `run()` entry point** to add at bottom:
```python
def run():
    metarig = bpy.data.objects.get(METARIG_NAME)
    if not metarig:
        print(f"ERROR: Metarig '{METARIG_NAME}' not found.")
        return
    bpy.context.view_layer.objects.active = metarig
    bpy.ops.object.mode_set(mode='POSE')
    configure_hand_finger_rigify(metarig)
    bpy.ops.pose.rigify_generate()
    rig = (metarig.data.get("rigify_target_rig") or bpy.data.objects.get(RIG_NAME))
    if not rig:
        print("ERROR: Generated rig not found after generate.")
        return
    apply_all_fixes(rig, ELBOW_DISTANCE, KNEE_DISTANCE, EYE_FORWARD_DIST,
                    BROW_OUTER_R, BROW_INNER_R, BROW_CENTER, BROW_INNER_L, BROW_OUTER_L)
    print(f"rigify-generate-and-fix complete. Rig: {rig.name}")

run()
```
(If the source has no single `apply_all_fixes` wrapper, call the individual fix functions in order matching the 12 steps in the plan. Adapt the entry point to match actual function names in the source.)

**Critical:** `bpy.ops.pose.rigify_generate()` requires active object + POSE mode — keep this call as-is. Do not attempt to replace it.

**README frontmatter:** `blender_version: "4.1"`, `tested_on: "4.1"`, `api_sensitive: true`, `reference_version: "4.1"`

**Prerequisites (README body):** Rigify addon enabled; metarig with Synty-compatible bone structure including `IndexFinger_01_L/R`, `MiddleFinger_01_L/R`, `PinkyFinger_01_L/R`; Blender 4.0+.

---

### Script 2: `library/scripts/rebind-to-rig/`

**Source:** `rebind_character.py`

**Change magnitude: ~35% of lines.** Strip: `SEREDOS_PT_rebind` panel (~45 lines in `__init__.py`, but the core logic is in `rebind_character.py`), `OBJECT_OT_seredos_rebind` operator (~100 lines), scene property registration, `register()`/`unregister()`. Keep: all 15 core functions unchanged.

**New parameter block** at top:
```python
SOURCE_ARMATURE_NAME = ""
META_ARMATURE_NAME   = ""
RIG_ARMATURE_NAME    = ""
DRY_RUN              = False
POSITION_THRESHOLD   = 0.15
EYES_VG_NAME         = "Eyes"
EYEBROW_VG_L         = "Eyebrow_L"
EYEBROW_VG_R         = "Eyebrow_R"
EYEBROW_VG_COMBINED  = "Eyebrows"
```

**New `run()` entry point** to add at bottom (see `integration-rebind-to-rig.md` for full body — wire up auto-detect logic then call the 15 core functions in sequence).

**README frontmatter:** `blender_version: "4.1"`, `tested_on: "4.1"`, `api_sensitive: false`, `reference_version: "4.1"`

**Prerequisites (README body):** Source armature with bound meshes; generated Rigify rig (run `rigify-generate-and-fix` first); metarig still in scene; Blender 4.0+.

---

## Agent 4 — Export Script + Backup Addon

**Source plans:** `integration-export-fbx-unity.md`, `integration-seredos-backup.md`

### Source files to read

- `E:\development\ai-villager\Blender\addons\seredos_export\export_characters.py` (958 lines)
- `E:\development\ai-villager\Blender\addons\seredos_backup\__init__.py`
- `E:\development\ai-villager\Blender\addons\seredos_backup\backup_handler.py`

### Script: `library/scripts/export-fbx-unity/`

**Source:** `export_characters.py`

**Change magnitude: ~15% of lines.** Strip: `EXPORT_OT_seredos_characters` operator, `EXPORT_OT_seredos_setup_face_shapekeys` operator, `FILE_MT_export.append/remove`, `register()`/`unregister()`. Keep: all pure logic functions and bpy-dependent helpers unchanged (~850 lines).

**New parameter block** at top (replaces stripped boilerplate — existing module-level constants become these top variables):
```python
import os, bpy
RIG_NAME          = ""
BLEND_FILE_PATH   = bpy.data.filepath
EXPORT_SUBPATH    = os.path.join("..", "Assets", "Seredos", "Character", "Models", "Characters")
ANIM_SUBPATH      = os.path.join("..", "Assets", "Seredos", "Character", "Animations")
FACE_ANIM_SUBPATH = os.path.join("..", "Assets", "Seredos", "Character", "Animations", "Face")
ITEMS_SUBPATH     = os.path.join("..", "Assets", "Seredos", "Character", "Models", "Items")
EXPORT_FILE       = "characters.fbx"
SLOT_PREFIX              = "SLOT-"
FACE_PREFIX              = "FACE-"
ANIM_BLACKLIST_PREFIXES  = {"Armature|Take 001|BaseLayer"}
FBX_SETTINGS = dict(
    axis_forward='−Y', axis_up='Z',
    apply_scale_options='FBX_SCALE_UNITS', apply_unit_scale=True,
    bake_space_transform=True, add_leaf_bones=False,
    primary_bone_axis='Y', secondary_bone_axis='X',
    use_armature_deform_only=True, mesh_smooth_type='FACE',
    use_mesh_modifiers=True, path_mode='RELATIVE',
)
```

**New `run()` entry point** at bottom (see `integration-export-fbx-unity.md` for full ~20-line body).

**README frontmatter:** `blender_version: "4.1"`, `tested_on: "4.1"`, `api_sensitive: true`, `reference_version: "4.1"`

**Prerequisites (README body):** Blend file saved; active armature is rig or set `RIG_NAME`; FBX I/O addon enabled; Unity project at `../Assets/` relative to blend file; Blender 4.0+.

---

### Addon: `library/addons/seredos-backup/`

**Source:** `seredos_backup/__init__.py` + `backup_handler.py`

**Change magnitude: < 5%** — cosmetic only.

**`__init__.py`:** Copy source verbatim. Update `bl_info["blender"]` to `(4, 1, 0)`.

**`backup_handler.py`:** Copy source verbatim. Translate German strings to English:
- `"Backup erstellt: ..."` → `"Backup created: ..."`
- `"FEHLER beim Backup: ..."` → `"Backup error: ..."`
- `"Keine aktive Datei"` → `"No active file"`

**`README.md`:** Author from scratch. Cover: pre-save backup behavior, backup location (`{blend_dir}/backups/{stem}_NNN.blend`), no configuration needed, restart not required after install, skill auto-save integration (skill calls `bpy.ops.wm.save_mainfile()` after every scene-modifying operation).

**README frontmatter:** `blender_version: "4.1"`, `tested_on: "4.1"`, `api_sensitive: true`, `reference_version: "4.1"`

---

## Execution Order

Agents 1–4 run **in parallel** (single message, 4 simultaneous agent tool calls). After all complete, Agent 5 runs as a **sequential review pass**.

No agent touches `library/INDEX.md` — that belongs to Agent 1 only.

---

## Agent 5 — Post-Implementation Review (runs after Agents 1–4 complete)

A dedicated review agent reads every created file and checks it against the plan. It does **not** re-implement anything — it reports what is correct, what is missing, and what deviates from the plan. It then fixes any issues it finds.

### Checks to perform

**Structural checks:**
- `SKILL.md` exists at `C:\Users\arnev\.claude\skills\blender-helper\SKILL.md`
- `SKILL.md` char count ≤ 4 000 (count via `wc -m` or read and check length); if companion files exist, check they are properly linked from SKILL.md
- `SKILL.md` has YAML frontmatter
- `library/INDEX.md` exists and has exactly 7 data rows, all `done`
- `setup/blender-mcp-setup.md` exists
- All 6 script directories exist with both `README.md` and `solution_4.1.py`
- Addon directory `library/addons/seredos-backup/` has `README.md`, `__init__.py`, `backup_handler.py`

**Content checks:**
- Each `README.md` has the 4-field YAML frontmatter (`blender_version`, `tested_on`, `api_sensitive`, `reference_version`) with correct values as specified in the plan
- `api_sensitive` is `true` for: `analyse-rigify-setup`, `rigify-generate-and-fix`, `export-fbx-unity`, `seredos-backup`; `false` for the other 3
- Each `solution_4.1.py` has a parameter block at the top (object/bone/path names as variables)
- Each `solution_4.1.py` ends with a `run()` call
- `backup_handler.py` contains no German strings (no `"Backup erstellt"`, `"FEHLER"`, `"Keine aktive Datei"`)
- `SKILL.md` mentions all 3 behavioral patterns (ANALYSE, STRATEGY, EXECUTE)
- `SKILL.md` mentions `seredos-backup` session-start check and auto-save behavior
- `SKILL.md` references `setup/blender-mcp-setup.md` for MCP failure

**Fix any issues found.** Report a summary: what passed, what was fixed, what (if anything) still needs manual attention.

---

## Verification (manual, after Agent 5 completes)

1. Invoke `/blender-helper` in a new conversation with Blender open; say "run rebind-to-rig" → skill should find the entry in INDEX.md and execute
2. Run all 3 analysis scripts via `execute_blender_code` on a test scene and verify output format matches expected
3. Confirm `SKILL.md` appears as an available skill in Claude Code
