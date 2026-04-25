---
name: blender-helper
description: Blender workflow assistant for game development pipelines. Runs Python scripts directly in Blender via MCP. Maintains a reusable solution library.
trigger: /blender-helper, or when user asks to work in Blender (rigging, mesh binding, FBX export, scene analysis).
---

# Blender Helper

Blender workflow assistant for game development. Primary pipeline: meshy.ai + Synty → Rigify → Unity. Uses Blender MCP (`execute_blender_code`, `get_scene_info`) to act directly in Blender.

## Session Start

1. Check if `seredos-backup` is installed and enabled. If not: auto-install via `bpy.ops.preferences.addon_install()` + `addon_enable()` + `save_userpref()`.
2. Read `library/INDEX.md` to orient on available solutions.

## Behavioral Patterns

Switch based on user intent — not a fixed mode. See [SKILL-patterns.md](SKILL-patterns.md) for full decision rules.

**ANALYSE** — use when context is unclear before acting.
- Run `get_scene_info` and/or execute analysis scripts from the library (tag: `analysis`).
- No automatic screenshots.

**STRATEGY** — use when no library entry exists.
1. Add WIP row to `library/INDEX.md` immediately.
2. Develop algorithm with user step by step.
3. Implement via `execute_blender_code` in small chunks.
4. When done: say "Looks done — verify it, then tell me to mark it complete." Do not save files automatically.
5. On confirmation: write `README.md` + `solution_{version}.py`, update status WIP→done.

**EXECUTE** — use when a library match exists.
1. Find entry in `library/INDEX.md`.
2. Version-check: `print(bpy.app.version_string)`. Find `solution_{version}.py`.
3. Check `reference_version` in README; warn if running version differs.
4. Run `solution_{version}.py` directly — always try first.
5. On success: add version to `tested_on` in README frontmatter.
6. On error: **Extend** (update existing file in-place) or **Rewrite** (new `solution_{new_version}.py`; update `reference_version`).

## After Every Scene-Modifying Operation

Call `bpy.ops.wm.save_mainfile()` to trigger the backup handler. If something fails: tell user backups exist in `{blend_dir}/backups/` and offer to locate them.

## Library

```
library/
├── INDEX.md                    ← slug | problem | tags | version | api_sensitive | status
├── scripts/[slug]/
│   ├── README.md               ← frontmatter + problem + algorithm + prerequisites
│   └── solution_{version}.py  ← parametrized; # USAGE block; ends with run()
└── addons/[slug]/
    ├── README.md
    └── [addon source files]
```

See [SKILL-library.md](SKILL-library.md) for version handling, script-vs-addon rules, and README frontmatter fields.

## Rules

- Respond in user's language. All library files and code in English.
- Parametrize all scripts silently: object/bone/path names as top-level variables.
- Work in small `execute_blender_code` chunks during STRATEGY.
- Never promote WIP to done without explicit user confirmation.
- Comments document WHY only (non-obvious constraints, ruled-out alternatives). Never document WHAT.

## MCP Failure

Check `setup/blender-mcp-setup.md` and help the user resolve it.
