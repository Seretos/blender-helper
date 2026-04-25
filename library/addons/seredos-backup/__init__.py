bl_info = {
    "name": "Seredos Auto Backup",
    "author": "Seredos",
    "version": (1, 0, 0),
    "blender": (4, 1, 0),
    "category": "System",
    "description": "Creates a numbered backup of the .blend file before every save",
}

import bpy
from . import backup_handler


def register():
    backup_handler.register()


def unregister():
    backup_handler.unregister()
