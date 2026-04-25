import os
import shutil

import bpy


def get_backup_path(filepath: str, backup_dir: str) -> str:
    """Return the next available backup path (e.g. backups/file_003.blend)."""
    stem = os.path.splitext(os.path.basename(filepath))[0]
    n = 1
    while True:
        candidate = os.path.join(backup_dir, f"{stem}_{n:03d}.blend")
        if not os.path.exists(candidate):
            return candidate
        n += 1


def do_backup(filepath: str) -> str | None:
    """Perform the backup. Returns the backup path, or None if no filepath is set."""
    if not filepath:
        return None
    backup_dir = os.path.join(os.path.dirname(filepath), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    dest = get_backup_path(filepath, backup_dir)
    shutil.copy2(filepath, dest)
    return dest


@bpy.app.handlers.persistent
def _on_save_pre(dummy):
    filepath = bpy.data.filepath
    print(f"[seredos_backup] save_pre fired, filepath='{filepath}'")
    if not filepath:
        print("[seredos_backup] No file path set (not yet saved), skipped")
        return
    try:
        dest = do_backup(filepath)
        if dest:
            print(f"[seredos_backup] Backup created: {dest}")
    except Exception as e:
        import traceback
        print(f"[seredos_backup] Backup error: {e}")
        traceback.print_exc()


def register():
    bpy.app.handlers.save_pre.append(_on_save_pre)


def unregister():
    bpy.app.handlers.save_pre.remove(_on_save_pre)
