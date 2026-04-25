# Plan: Blender Helper Skill

## Context

The user is a programmer (not an artist) developing a 3D game. The skill helps with **Blender workflows for game development broadly** — asset preparation, rigging, binding, export, and anything else in a graphics pipeline. The first use cases come from an existing addon codebase at `E:\development\ai-villager\Blender\addons\` (meshy.ai + Synty → Unity pipeline), but the skill is not limited to this pipeline.

- **seredos_rigify** – Generates Rigify rig + fixes IK targets, eye/eyebrow controls, DEF hierarchy
- **seredos_rebind** – Binds Synty character meshes to the new rig via position-based bone mapping
- **seredos_export** – FBX export to Unity with specific axis/transform settings
- **seredos_backup** – Auto-backup handler (persistent, must stay an addon)
- **seredos_item_handpose** – Item slot attachment + hand pose authoring

Goal: A Claude skill that supports Blender post-processing via MCP, building a growing solution library. The **existing addon logic** provides the first batch of library entries – the core functions are already modular and testable (no-bpy logic separated from operators). Scripts via MCP don't need the operator/panel boilerplate; just the logic.

The value of the skill lies in the library – without it, it's just a "ask Claude about Blender" wrapper.

**Key distinction:** Addons are better for persistent behaviors (handlers, UI panels). Library scripts are better for one-off operations run via MCP. `seredos_backup` stays an addon; `seredos_rigify`, `seredos_rebind`, `seredos_export` logic can be library entries.

---

## File Structure

```
C:\Users\arnev\.claude\skills\blender-helper\
├── blender-helper.md              ← the skill itself (invoked as /blender-helper)
├── setup\
│   └── blender-mcp-setup.md      ← MCP setup instructions (not a library entry)
└── library\
    ├── INDEX.md                   ← unified index of all solutions (scripts + addons)
    ├── scripts\
    │   └── [problem-slug]\
    │       ├── README.md          ← problem, algorithm, prerequisites (English) + frontmatter
    │       └── solution.py        ← parametrized one-shot Blender Python script
    └── addons\
        └── [addon-slug]\
            ├── README.md          ← what the addon does, when to use it, restart needed? + frontmatter
            └── [addon source files]
```

**README.md frontmatter** (scripts and addons):

```markdown
---
blender_version: "4.1"
tested_on: "4.1, 4.2"
api_sensitive: false   # true if Blender API calls are version-dependent
---
```

`api_sensitive: true` applies to scripts using e.g. Rigify operators, `bpy.ops.pose.*`, or other APIs known to change between minor versions.

**INDEX.md columns:**

```
| Slug | Problem | Tags | Blender Version | API Sensitive | Status |
|---|---|---|---|---|---|
| scripts/rebind-to-rig | ... | rig, weights | 4.1 | false | done |
| addons/seredos-backup | ... | backup, handler | 4.1 | true | done |
| scripts/fix-hand-weights | Fix hand deformation after rebind | rig, weights | 4.1 | false | WIP |
```

**Scripts vs. Addons – when to use which:**

| Use a Script when... | Use an Addon when... |
|---|---|
| The operation runs once and is done | The behavior needs to persist across sessions |
| No Blender UI panel needed | A panel/button in Blender is useful |
| No persistent handlers required | Uses `save_pre`, `load_post` etc. |
| Example: rebind mesh to rig, export FBX | Example: auto-backup, always-available operators |

**Addon installation via MCP (no restart in most cases):**
The skill can write addon files, call `bpy.ops.preferences.addon_install()` + `addon_enable()`, and save prefs – fully automated. Exception: addons with `@bpy.app.handlers.persistent` on `load_post` may need a Blender restart. The skill detects this from the addon source and warns the user proactively.

---

## How the Skill Works (no strict mode separation)

The skill is **context-driven**, not mode-driven. It reads the user's intent and acts accordingly. There are three behavioral patterns it shifts between:

### Pattern: ANALYSE
**When:** User asks about a problem, needs diagnosis, or a library script didn't work.  
**Not:** Automatic on every skill invocation – only when needed.

The skill uses `get_scene_info` to find object names / armature structure. It may also use `execute_blender_code` to run **information-gathering scripts from the library** (e.g., a script that reports mesh stats, bone hierarchy, or UV coverage). No automatic viewport screenshot – visual evaluation is the user's job.

### Pattern: STRATEGY
**When:** User wants to solve a problem that has no existing library entry (or WIP entry).

1. Discuss the problem using available context
2. Determine the solution slug — **immediately add a `WIP` row to `library/INDEX.md`**. Future sessions will find this entry and know a solution is in progress.
3. Develop an algorithm together with the user (step by step)
4. Implement iteratively via `execute_blender_code` in small chunks
5. When the solution looks complete: inform the user — *"Looks done. Run it to verify, then tell me to mark it as complete."* Do **not** save files or update status automatically.
6. On explicit user confirmation:
   - Write `library/scripts/[problem-slug]/README.md` – problem, algorithm, prerequisites (English) + frontmatter (auto-populate: current Blender version; `api_sensitive: false` by default, set `true` if Rigify operators, `bpy.ops.pose.*` or other version-sensitive APIs are used)
   - Write `library/scripts/[problem-slug]/solution.py` – parametrized Python script (English comments; all object/bone names as variables at top)
   - Update INDEX.md: status `WIP` → `done`

**Note:** Information-gathering scripts (for analysis) are also valid library entries, tagged `analysis`.

### Pattern: EXECUTE
**When:** User asks to run a specific library solution, or the skill finds a match for a described problem.

1. Read `library/INDEX.md` to find matching solution
2. Get minimum required context (e.g., object name via `get_scene_info`)
3. **Version check:** Query current Blender version via `execute_blender_code` (`print(bpy.app.version_string)`). Compare with `blender_version` from INDEX.md / README.md.
   - `api_sensitive: false` → brief info to user ("Entry was created for 4.1, you're on 4.2 – should be compatible"), proceed
   - `api_sensitive: true` + mismatch → see **Version Mismatch Handling** below
4. Execute `solution.py` via `execute_blender_code` with correct parameters
5. **On error:** Read and analyze the error, present findings to user, decide together whether to update the library entry or adapt parameters

### Version Mismatch Handling

When `api_sensitive: true` and Blender version differs from the recorded version:

```
Skill informs user:
  "This solution was written for Blender 4.1. You're running 4.2.
   The script uses version-sensitive APIs.
   Options:
   A) Run anyway – I'll analyze any errors and adapt on the fly
   B) Let me generate a version-adapted script first"
```

**Option A (Run anyway):**
- Execute script, catch errors
- On failure: skill analyzes API changes, adapts script, saves adapted version
- Update README.md Version History section

**Option B (Adapt first):**
- Skill reads `solution.py`, analyzes deprecated/changed API calls
- Creates adapted version, shows diff to user
- After confirmation: update `solution.py` + update README.md frontmatter and Version History

**`solution.py` is always the latest version.** No parallel version files. Archive only on explicit user request. Version history tracked in README.md:

```markdown
## Version History
- 4.1: Initial version
- 4.2: Updated `bpy.ops.object.armature_basic_human_metarig_add` → new API
```

---

## The Skill Prompt (SKILL.md)

Must cover:
- Context: Blender workflows for game development (graphics pipeline broadly; first entries cover rigging/binding/export for meshy.ai + Synty → Unity)
- Behavioral patterns and how to switch between them contextually
- Library structure so new conversations know where to look
- Language: respond in the user's language; all library files and code in English
- Scripts must always be parametrized (object names, bone names as variables) – silently enforce this
- Always work in small `execute_blender_code` chunks during strategy/implementation
- On MCP failure: check `setup/blender-mcp-setup.md` and help user resolve it

---

## Critical Design Decisions

**INDEX.md is the skill's persistent memory.** Every conversation starts fresh – INDEX.md is the only thing that carries knowledge between sessions. Format: table with slug, problem description, tags (`rig`, `topology`, `uv`, `analysis`, `weights`, etc.).

**Analysis scripts belong in the library too.** A script that reads bone hierarchy and reports useful stats is just as reusable as a fix script. Tag it `analysis`.

**Parametrization is silent.** The skill enforces it internally when writing scripts, but doesn't need to explain this to the user every time.

**Error handling is collaborative.** When execution fails, the skill analyzes the error and decides with the user: adapt parameters, update the library entry, or develop a new strategy.

**No automatic screenshot.** Visual evaluation is the user's responsibility. Screenshots only when explicitly useful and requested-adjacent.

---

## Files to Create

1. `SKILL.md` — the skill prompt (YAML frontmatter required; ≤ 4 000 chars total)
2. `library/INDEX.md` — solution index, pre-populated with entries from existing addon code; includes `Status` column (`done` | `WIP`)
3. `setup/blender-mcp-setup.md` — Blender MCP installation and activation guide

### Initial library entries (from existing addon code)

**Scripts – Analysis** (tagged `analysis`, run to understand the current scene):

| Slug | What it reports |
|---|---|
| `scripts/analyse-scene-overview` | All objects by type, armature names, mesh-to-armature bindings, active object |
| `scripts/analyse-rigify-setup` | META/RIG presence, which seredos fixes already applied (IK poles, eye/eyebrow bones, DEF hierarchy), rig readiness |
| `scripts/analyse-mesh-binding` | For each mesh: armature modifier target, vertex group names vs. rig bone names, unmapped VGs |

These are written from scratch, informed by the existing addon code (what to look for in a Rigify character scene). They output structured text that the skill reads to build context.

**Scripts – Operations** (adapted from addon operator logic, no UI boilerplate):

| Slug | Source | What it does |
|---|---|---|
| `scripts/rigify-generate-and-fix` | `seredos_rigify/rigify_fix.py` | Generate Rigify rig + fix IK poles, eye controls, eyebrow rig, DEF hierarchy |
| `scripts/rebind-to-rig` | `seredos_rebind/rebind_character.py` | Position-based bone mapping, VG rename, armature modifier swap, reparent |
| `scripts/export-fbx-unity` | `seredos_export/export_characters.py` | FBX export with correct axis/transform settings for Unity |

**Addons** (copied from existing, working addon infrastructure):

| Slug | Source | What it does | Restart? |
|---|---|---|---|
| `addons/seredos-backup` | `seredos_backup/` | Auto-backup before save via persistent handler | Yes (load_post handler) |
| `addons/seredos-item-handpose` | `seredos_item_handpose/` | Item slot + hand pose authoring panel | No |

**Addon version handling:** The skill reads `bl_info["blender"]` from the addon source and compares with the current Blender version. On mismatch: warn user. Optional: update `bl_info["blender"]` declaratively if user requests it. On post-install errors: same adapt flow as scripts. All initial addon entries get README.md frontmatter populated with current Blender version at creation time.

---

## Verification

After implementation:
1. Open Blender with a Synty or meshy.ai character, activate Blender MCP
2. Invoke `/blender-helper` and say "rebind the character to the rig" → skill reads INDEX.md, finds `rebind-to-rig`, executes it
3. Say "the hands still look wrong after rebind, any ideas?" → skill gathers info as needed, enters STRATEGY mode
4. Develop a solution, confirm it's saved to library
5. Start a new conversation, invoke `/blender-helper`, confirm INDEX.md is read and existing solutions are found
