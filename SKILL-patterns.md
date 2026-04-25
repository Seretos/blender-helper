# Blender Helper — Pattern Detail

Reference for the three behavioral patterns described in SKILL.md.

---

## ANALYSE

**When to use:**
- User asks "what's in the scene?" or "is my rig ready?"
- Before running EXECUTE if object names or scene state are unknown
- When a previous EXECUTE run failed and you need to diagnose why

**Which analysis script to run:**

| Situation | Script |
|---|---|
| Know nothing about the scene | `analyse-scene-overview` |
| Checking rig readiness / Rigify post-processing | `analyse-rigify-setup` |
| Checking mesh binding state | `analyse-mesh-binding` |

Run analysis scripts via `execute_blender_code`. Read the printed output to build context before proceeding.

---

## STRATEGY

**When to use:**
- User describes a problem not in INDEX.md (or only a WIP entry exists)
- A library script failed and the error requires a fundamentally new approach

**WIP row format:**
```
| scripts/my-slug | Short problem description | tags | 4.1 | false | WIP |
```
Add this to `library/INDEX.md` before starting implementation. This makes the in-progress work visible to future sessions.

**Algorithm development checklist:**
1. Understand what bpy API calls are involved
2. Identify if `bpy.ops` calls are needed (version-sensitive → set `api_sensitive: true`)
3. Determine parameters (all object/bone/path names must be variables)
4. Write small testable chunks — run each via `execute_blender_code` before proceeding

**Writing the solution file:**
- Parameter block at the top — all hardcoded names become variables
- `# USAGE` comment block below parameters (one line per variable: what it expects)
- `run()` function containing the logic
- `run()` call at the bottom
- Comments only where WHY is non-obvious (hidden constraints, ruled-out alternatives)

**Completion gate:** Never write files or update status until user explicitly confirms the solution is correct.

---

## EXECUTE

**Version check decision tree:**

```
exact solution_{version}.py found?
  YES → run it directly
  NO  → warn user, run nearest available version instead

reference_version ≠ running version?
  → inform user: "reference version is X.Y — improvements may not be present in X.Z"
```

**Error handling — Extend vs Rewrite:**

| Choose Extend when... | Choose Rewrite when... |
|---|---|
| Same API, minor parameter difference | API changed incompatibly between versions |
| A guard or fallback fixes it | Logic restructure required |
| Diff would be < 20% of file | Diff would be > 50% of file |

Extend: update existing `solution_{version}.py` in-place, add version to `tested_on`.
Rewrite: create `solution_{new_version}.py`, never touch old file, update `reference_version`.

Always state the chosen path to the user before editing any files.
