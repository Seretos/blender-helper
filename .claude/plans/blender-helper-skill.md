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
    │       ├── README.md              ← problem, algorithm, prerequisites (English) + frontmatter
    │       ├── solution_4.1.py        ← parametrized script for Blender 4.1
    │       └── solution_4.2.py        ← version-specific variant (only if code differs from 4.1)
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
api_sensitive: false        # true if Blender API calls are version-dependent
reference_version: "4.1"   # version file considered the most complete implementation
---
```

`api_sensitive: true` applies to scripts using e.g. Rigify operators, `bpy.ops.pose.*`, or other APIs known to change between minor versions.

`reference_version` always points to the solution file with the most up-to-date logic. Updated automatically when a new version file is created or an existing one is substantially improved. Used to detect drift between version files (see Version Handling below).

**INDEX.md columns:**

```
| Slug | Problem | Tags | Blender Version | API Sensitive | Status |
|---|---|---|---|---|---|
| scripts/rebind-to-rig | ... | rig, weights | 4.1 | false | done |
| addons/seredos-backup | ... | backup, handler | 4.1 | true | done |
| scripts/fix-hand-weights | Fix hand deformation after rebind | rig, weights | 4.1 | false | WIP |
```

**Note:** `Blender Version` refers to the **Blender application version** the solution was written and tested against (e.g. `4.1`). It is not a solution/changelog version number. Multiple tested versions are listed in the README frontmatter (`tested_on`), not in INDEX.md.

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
   - Write `library/scripts/[problem-slug]/README.md` – problem, algorithm, prerequisites (English) + frontmatter (auto-populate: current Blender version; `api_sensitive: false` by default, set `true` if Rigify operators, `bpy.ops.pose.*` or other version-sensitive APIs are used; set `reference_version` to current Blender version)
   - Write `library/scripts/[problem-slug]/solution_{version}.py` – parametrized Python script (English; all object/bone names as variables at top; decision-comments inline — see Code Comments below)
   - Update INDEX.md: status `WIP` → `done`

**Note:** Information-gathering scripts (for analysis) are also valid library entries, tagged `analysis`.

### Pattern: EXECUTE
**When:** User asks to run a specific library solution, or the skill finds a match for a described problem.

1. Read `library/INDEX.md` to find matching solution
2. Get minimum required context (e.g., object name via `get_scene_info`)
3. **Version check:** Query current Blender version via `execute_blender_code` (`print(bpy.app.version_string)`). Look for `solution_{version}.py` in the solution directory.
   - Exact match found → run it directly
   - No exact match → warn user, note which version will be used instead, proceed
4. **Reference version check:** Read `reference_version` from README.md frontmatter. If running version ≠ `reference_version`: inform user that the reference version differs and improvements may not be present in the version being run.
5. **Always try first.** Execute the selected `solution_{version}.py` via `execute_blender_code` with correct parameters. There is no "adapt first" option — running gives either a working result or concrete error information to act on.
6. **On success:** Prompt user to confirm it worked. User confirmation is a signal, not a guarantee — skill re-evaluates on every run regardless.
   - No code changes needed → add version to `tested_on` in README.md frontmatter (no new file)
7. **On error:** Read and analyze error, then assess and inform user of chosen path before acting:
   - **Extend:** existing `solution_{version}.py` can be made to support both versions (version-neutral rewrite or inline version check) → update the existing file in place, update `tested_on` and frontmatter. No new file created.
   - **Rewrite:** new version requires fundamentally different logic → create `solution_{new_version}.py`. Existing files are never touched. Update `reference_version` to the new file.

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

**Only the user promotes WIP to done.** The skill never changes a library entry's status from `WIP` to `done` on its own — not after a successful run, not after saving files. It informs the user when it believes a solution is complete and waits for explicit confirmation.

**Error handling is collaborative.** When execution fails, the skill analyzes the error and decides with the user: adapt parameters, update the library entry, or develop a new strategy.

**No automatic screenshot.** Visual evaluation is the user's responsibility. Screenshots only when explicitly useful and requested-adjacent.

**Code comments capture reasoning, not mechanics.** When writing or updating a `solution_{version}.py`, the skill adds inline comments that document *why* a specific approach was chosen — non-obvious constraints, alternative approaches that were ruled out, workarounds for Blender-specific behavior. This allows future sessions (and future instances of the skill) to reconstruct the thought process without needing the original conversation. Comments describe decisions, not what the code does.

**Usage is documented in the solution file, not the README.** The README covers what the problem is, the algorithm, and prerequisites — it has no version scope. Each `solution_{version}.py` contains a `# USAGE` comment block directly below the parameter variables, explaining what each variable expects. This keeps usage docs automatically in sync with the code and handles version-specific parameter differences naturally.

---

## Files to Create

1. `SKILL.md` — the skill prompt (YAML frontmatter required; ≤ 4 000 chars total)
2. `library/INDEX.md` — solution index, pre-populated with entries from existing addon code; includes `Status` column (`done` | `WIP`)
3. `setup/blender-mcp-setup.md` — Blender MCP installation and activation guide

### How initial library entries are created

**Operation scripts** are not written from scratch. They are extracted from the existing addon source files at `E:\development\ai-villager\Blender\addons\`. The implementation step is:
1. Read the source file (e.g. `seredos_rigify/rigify_fix.py`)
2. Extract the core logic — strip all operator/panel/UI boilerplate, keep only the algorithmic functions
3. Parametrize: move all object/bone/path names to variables at the top of the script
4. Adapt to MCP context: no `bpy.ops` where avoidable, plain Python + `bpy.data` / `bpy.context` calls

**Addon entries** are copied directly from the existing addon directories. Only `README.md` and frontmatter are newly authored.

**Analysis scripts** are the one exception — they are written from scratch, informed by what the existing addon code looks for (bone names, modifier targets, etc.).

---

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

Note: `seredos_item_handpose` was never completed and is not included in the initial library.

**Addon version handling:** The skill reads `bl_info["blender"]` from the addon source and compares with the current Blender version. On mismatch: warn user. Optional: update `bl_info["blender"]` declaratively if user requests it. On post-install errors: same adapt flow as scripts. All initial addon entries get README.md frontmatter populated with current Blender version at creation time.

**seredos-backup — special skill behavior:**
- On every session start: check whether `seredos-backup` is installed and enabled. If not: install and enable it automatically (warn user that a Blender restart may be needed due to the `load_post` handler).
- After every change made via `execute_blender_code` that modifies scene data: call `bpy.ops.wm.save_mainfile()` to trigger the backup handler.
- The skill is aware that backup history exists and can be accessed if a change needs to be reverted. If something goes wrong, inform the user that prior backups are available and offer to locate them.

---

## Verification

After implementation:
1. Open Blender with a Synty or meshy.ai character, activate Blender MCP
2. Invoke `/blender-helper` and say "rebind the character to the rig" → skill reads INDEX.md, finds `rebind-to-rig`, executes it
3. Say "the hands still look wrong after rebind, any ideas?" → skill gathers info as needed, enters STRATEGY mode
4. Develop a solution, confirm it's saved to library
5. Start a new conversation, invoke `/blender-helper`, confirm INDEX.md is read and existing solutions are found
