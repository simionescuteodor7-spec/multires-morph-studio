bl_info = {
    "name": "Multires Morph Studio",
    "author": "LowPolyPotato",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Sculpt Morph Tab",
    "description": "Non-destructively capture Multires sculpts into Shape Keys and manage independent texture baking.",
    "category": "Sculpting",
}

if "bpy" in locals():
    import importlib
    if "properties" in locals():
        importlib.reload(properties)
    if "operators" in locals():
        importlib.reload(operators)
    if "ui" in locals():
        importlib.reload(ui)

import bpy
from . import properties
from . import operators
from . import ui

modules = (
    properties,
    operators,
    ui,
)


def register():
    for mod in modules:
        mod.register()


def unregister():
    for mod in reversed(modules):
        mod.unregister()


if __name__ == "__main__":
    register()
