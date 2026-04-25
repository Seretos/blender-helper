---
blender_version: "4.1"
tested_on: "4.1"
api_sensitive: true
reference_version: "4.1"
---

# seredos-backup

**What it does:** Automatically creates numbered `.blend` backups before every save. Hooks into `bpy.app.handlers.save_pre` with a `@persistent` handler — no manual action needed once installed.

**Backup location:** `{blend_file_dir}/backups/{filename}_NNN.blend` (e.g. `character_001.blend`, `character_002.blend`, ...). Counter increments per session; no cap.

**Configuration:** None required. Just install and enable.

**Installation via MCP:**
```python
bpy.ops.preferences.addon_install(filepath="/path/to/seredos_backup.zip")
bpy.ops.preferences.addon_enable(module="seredos_backup")
bpy.ops.wm.save_userpref()
```
No Blender restart required — the handler registers immediately on enable. First save after enabling triggers the backup.

**Skill integration:** The blender-helper skill checks whether this addon is installed and enabled on every session start, and auto-installs it if not. After every `execute_blender_code` call that modifies scene data, the skill calls `bpy.ops.wm.save_mainfile()` to trigger the backup handler. If something goes wrong, prior backups are available in the `backups/` subfolder and the skill can help locate them.

**API sensitivity:** Uses `@bpy.app.handlers.persistent` and `bpy.app.handlers.save_pre` — persistent handler registration is stable across Blender versions but handler list access is version-sensitive.
