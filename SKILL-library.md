# Blender Helper — Library Reference

Structure, conventions, and decision rules for the solution library.

---

## Directory Layout

```
library/
├── INDEX.md
├── scripts/
│   └── [slug]/
│       ├── README.md
│       └── solution_4.1.py        ← version-specific; add solution_4.2.py only if logic differs
└── addons/
    └── [slug]/
        ├── README.md
        └── [addon source files]
```

---

## INDEX.md Columns

| Column | Description |
|---|---|
| Slug | `scripts/my-slug` or `addons/my-slug` — path relative to `library/` |
| Problem | One sentence: what problem does this solve? |
| Tags | Comma-separated: `rig`, `weights`, `export`, `analysis`, `topology`, `uv`, `handler`, `backup` |
| Blender Version | Application version the solution was written and tested against (e.g. `4.1`) |
| API Sensitive | `true` if uses Rigify operators, `bpy.ops.pose.*`, FBX export params, or other version-sensitive APIs |
| Status | `done` or `WIP` |

---

## README.md Frontmatter

```yaml
---
blender_version: "4.1"    # version written/tested against
tested_on: "4.1, 4.2"    # add versions as confirmed working
api_sensitive: false       # true if Rigify/FBX/NLA APIs are used
reference_version: "4.1"  # always points to most complete/up-to-date solution file
---
```

Update `tested_on` when a version runs without error (EXECUTE pattern, on success).
Update `reference_version` when a Rewrite creates a newer, more complete file.

---

## Script vs Addon

| Use a Script when... | Use an Addon when... |
|---|---|
| One-off operation | Behavior persists across sessions |
| No Blender UI panel needed | Panel/button in Blender is useful |
| No persistent handlers | Uses `save_pre`, `load_post` etc. |
| Example: rebind, export, analyse | Example: auto-backup |

---

## Version Handling

- Add a new `solution_{version}.py` only if the logic is **fundamentally different** from the reference version.
- If a minor fix works for both versions: update the existing file in-place and add the version to `tested_on`.
- If a version-specific guard can make one file work for both: use an inline version check (`import bpy; v = bpy.app.version`).
- The `reference_version` field always points to the most up-to-date implementation. Update it when a Rewrite is performed.

---

## Code Conventions

**Parametrization (enforce silently):**
All object names, bone names, path strings, and numeric thresholds go at the top of the file as named variables. Never hardcode in the body.

**USAGE block:**
Every `solution_{version}.py` has a `# USAGE` comment block directly below the parameter variables, before any function definitions. One line per variable: what it expects, valid values, when to change it.

**Comment style:**
Comments document WHY, not WHAT:
- Hidden constraints the code works around
- Alternative approaches that were ruled out and why
- Non-obvious Blender behavior being compensated for
Never write comments that just describe what the next line does.

**Entry point:**
Every script ends with `run()` (function defined above, called at file end). This makes it easy to test individual parts or skip execution during development.
