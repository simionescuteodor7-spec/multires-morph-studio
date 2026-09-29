import bpy
from bpy.props import (
    StringProperty,
    FloatProperty,
    IntProperty,
    EnumProperty,
    BoolProperty,
    PointerProperty,
)


class MMS_Properties(bpy.types.PropertyGroup):
    """Properties for Multires Morph Studio."""

    new_shape_key_name: StringProperty(
        name="Shape Key Name",
        description="Name for the newly created shape key",
        default="Sculpt_Morph",
    )

    initial_key_value: FloatProperty(
        name="Initial Value",
        description="Initial value for the newly created shape key (0.0 keeps the neutral base appearance)",
        default=0.0,
        min=0.0,
        max=1.0,
    )

    # Independent Baking Settings
    bake_resolution: EnumProperty(
        items=[
            ("1024", "1024 (1K)", "1024 x 1024 resolution"),
            ("2048", "2048 (2K)", "2048 x 2048 resolution"),
            ("4096", "4096 (4K)", "4096 x 4096 resolution"),
            ("8192", "8192 (8K)", "8192 x 8192 resolution"),
        ],
        default="2048",
        name="Resolution",
        description="Resolution for baked texture maps",
    )

    bake_margin: IntProperty(
        name="Margin (px)",
        description="Amount of bleed/margin pixels outside UV islands",
        default=16,
        min=0,
        max=128,
    )

    bake_image_name: StringProperty(
        name="Texture Name",
        description="Custom name for the baked image (leave blank for automatic naming)",
        default="",
    )

    bake_use_32bit_float: BoolProperty(
        name="32-Bit Float",
        description="Use 32-bit floating point image (recommended for Displacement maps)",
        default=True,
    )


classes = (
    MMS_Properties,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass
    if not hasattr(bpy.types.Scene, "multires_morph_studio"):
        bpy.types.Scene.multires_morph_studio = PointerProperty(type=MMS_Properties)


def unregister():
    if hasattr(bpy.types.Scene, "multires_morph_studio"):
        del bpy.types.Scene.multires_morph_studio
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
