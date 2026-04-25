# Integration Plan: seredos-backup (addon)

## Context

Copy the `seredos_backup` addon into the skill's addon library with minimal changes. This addon stays as an addon (not converted to a script) because it requires a persistent save handler.

**Source:** `E:\development\ai-villager\Blender\addons\seredos_backup\`
- `__init__.py` — `bl_info`, `register()`, `unregister()`, delegation to `backup_handler`
- `backup_handler.py` — persistent `save_pre` handler + `do_backup()` logic

**Target:** `library/addons/seredos-backup/`

---

## What the Addon Does

Automatically creates numbered `.blend` backups before every save:
- Hooks into `bpy.app.handlers.save_pre` with a `@persistent` handler
- On each save: copies current `.blend` to `{blend_dir}/backups/{stem}_NNN.blend`
- Counter increments per file per session; no maximum cap
- No UI, no operators, no configuration — purely event-driven

---

## Extent of Changes

**Overall change magnitude: < 5%** — cosmetic only, no logic changes.

### Changes to make

1. **Translate German console strings to English** in `backup_handler.py`:
   - `"Backup erstellt: ..."` → `"Backup created: ..."`
   - `"FEHLER beim Backup: ..."` → `"Backup error: ..."`
   - `"Keine aktive Datei"` → `"No active file"`

2. **Update `bl_info["blender"]`** in `__init__.py`:
   - Current: `(4, 0, 0)` → update to current Blender version at creation time

3. **Author `README.md`** with frontmatter and problem/usage description

### What stays unchanged
- All backup logic in `do_backup()`
- Handler registration (`save_pre.append/remove`)
- `@bpy.app.handlers.persistent` decorator
- `register()` / `unregister()` structure
- File naming scheme (`{stem}_{NNN:03d}.blend`)
- Relative backup directory (`backups/` subfolder next to blend file)

---

## Restart Required?

**No.** The handler uses `@bpy.app.handlers.persistent` and registers immediately on `addon_enable()`. The skill installs and enables the addon via:
```python
bpy.ops.preferences.addon_install(filepath=addon_zip_path)
bpy.ops.preferences.addon_enable(module="seredos_backup")
bpy.ops.wm.save_userpref()
```
First save after enabling triggers the handler. No Blender restart needed.

---

## Special Skill Behavior (from blender-helper-skill.md)

The skill has special awareness of this addon:
- On every session start: check if `seredos_backup` is installed and enabled; install automatically if not
- After every `execute_blender_code` call that modifies scene data: call `bpy.ops.wm.save_mainfile()` to trigger backup
- If something goes wrong: inform user that backups exist in `{blend_dir}/backups/` and offer to locate them

---

## Files to Create

```
library/addons/seredos-backup/
├── README.md
├── __init__.py       (source copy + bl_info version update)
└── backup_handler.py (source copy + German → English string translation)
```

**README.md frontmatter:**
```yaml
---
blender_version: "4.1"    # Populate at creation time from current Blender version
tested_on: "4.1"
api_sensitive: true        # Uses bpy.app.handlers.persistent
reference_version: "4.1"
---
```

**README.md body should cover:**
- What it does (pre-save backup)
- Where backups go (`{blend_dir}/backups/`)
- No configuration needed
- Restart not required after install
- Integration with skill auto-save behavior

---

## Verification

1. Install addon via MCP: `bpy.ops.preferences.addon_install()` + `addon_enable()`
2. Open a test blend file; save it
3. Check that `{blend_dir}/backups/` directory was created with a numbered copy
4. Save again — verify counter increments
5. Disable addon; save — verify no backup created (handler correctly unregistered)
