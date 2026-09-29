import bpy
from bpy.types import Panel


class MMS_PT_MainPanel(Panel):
    """Main Panel for Multires Morph Studio."""

    bl_label = "Multires Morph Studio"
    bl_idname = "MMS_PT_main_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Sculpt Morph"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        scene = context.scene
        props = getattr(scene, "multires_morph_studio", None)

        if not obj or obj.type != "MESH":
            box = layout.box()
            box.label(text="Select a Mesh object to begin.", icon="OBJECT_DATA")
            return

        multires_mod = next((m for m in obj.modifiers if m.type == "MULTIRES"), None)

        # Diagnostics & Status
        box = layout.box()
        row = box.row(align=True)
        row.label(text=f"Active: {obj.name}", icon="MESH_DATA")

        if not multires_mod:
            box.alert = True
            box.label(text="No Multires Modifier Found", icon="ERROR")
            box.operator("object.modifier_add", text="Add Multires Modifier", icon="MODIFIER").type = "MULTIRES"
            return

        # Multires status details
        col = box.column(align=True)
        r = col.row(align=True)
        r.label(text=f"Total: {multires_mod.total_levels}")
        r.label(text=f"Sculpt: {multires_mod.sculpt_levels}")
        r.label(text=f"Viewport: {multires_mod.levels}")

        # Helpful topology tip for low-poly primitives (e.g. default Cube)
        base_vert_count = len(obj.data.vertices) if obj.data else 0
        if base_vert_count <= 24:
            warn_box = layout.box()
            warn_box.alert = True
            warn_box.label(text=f"Notice: Base mesh has only {base_vert_count} vertices.", icon="INFO")
            col_warn = warn_box.column(align=True)
            col_warn.label(text="Shape keys deform base vertices.")
            col_warn.label(text="For sculpted morphs, use a character")
            col_warn.label(text="or subdivided base mesh.")

        layout.separator()

        # Shape Key Creation Card
        col_create = layout.column(align=True)
        col_create.label(text="Capture Sculpt to Shape Key:", icon="SHAPEKEY_DATA")

        card = col_create.box()
        col_inputs = card.column(align=True)
        col_inputs.prop(props, "new_shape_key_name", text="Name")
        col_inputs.prop(props, "initial_key_value", text="Initial Value", slider=True)

        col_inputs.separator()
        btn_row = col_inputs.row()
        btn_row.scale_y = 1.4
        btn_row.operator(
            "mms.create_shape_key_from_multires",
            text="Create Shape Key from Multires",
            icon="ADD",
        )

        hint = card.row()
        hint.alignment = "CENTER"
        hint.label(text="Deformation saved to Shape Key & Multires preserved", icon="INFO")


class MMS_PT_ShapeKeysPanel(Panel):
    """Shape Keys Manager Panel."""

    bl_label = "Shape Keys"
    bl_idname = "MMS_PT_shape_keys_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Sculpt Morph"
    bl_parent_id = "MMS_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if not obj or not obj.data or not obj.data.shape_keys:
            box = layout.box()
            box.label(text="No shape keys on this object yet.", icon="INFO")
            return

        key_blocks = obj.data.shape_keys.key_blocks

        col = layout.column(align=True)
        for kb in key_blocks:
            row = col.row(align=True)
            if kb == key_blocks[0]:
                # Basis shape key
                row.label(text=f"{kb.name} (Rest Basis)", icon="KEYINGSET")
            else:
                # Morph shape key with live slider and delete button
                row.prop(kb, "value", text=kb.name, slider=True)
                row.prop(kb, "mute", text="", icon="HIDE_ON" if kb.mute else "HIDE_OFF")
                del_op = row.operator("mms.delete_shape_key", text="", icon="TRASH")
                del_op.key_name = kb.name

        layout.separator()

        # Optional clean reset tool
        sub_box = layout.box()
        sub_col = sub_box.column(align=True)
        sub_col.label(text="Reset Sculpt Tool (Optional):", icon="LOOP_BACK")
        reset_row = sub_col.row()
        reset_row.scale_y = 1.1
        reset_row.operator(
            "mms.reset_multires_sculpt",
            text="Reset Multires to Base",
            icon="RECOVER_LAST",
        )


class MMS_PT_BakingPanel(Panel):
    """Independent Texture Baking Panel."""

    bl_label = "Texture Baking (Independent)"
    bl_idname = "MMS_PT_baking_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Sculpt Morph"
    bl_parent_id = "MMS_PT_main_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = getattr(scene, "multires_morph_studio", None)

        col = layout.column(align=True)
        col.prop(props, "bake_resolution")
        col.prop(props, "bake_margin")
        col.prop(props, "bake_image_name")
        col.prop(props, "bake_use_32bit_float")

        layout.separator()

        row = layout.row(align=True)
        row.scale_y = 1.2
        btn_normal = row.operator(
            "mms.bake_map",
            text="Bake Normal Map",
            icon="NORMALS_VERTEX",
        )
        btn_normal.map_type = "NORMALS"

        btn_disp = row.operator(
            "mms.bake_map",
            text="Bake Displacement",
            icon="MOD_DISPLACE",
        )
        btn_disp.map_type = "DISPLACEMENT"

        note = layout.row()
        note.alignment = "CENTER"
        note.label(text="Baking is independent and does not affect shape keys.", icon="CHECKMARK")


classes = (
    MMS_PT_MainPanel,
    MMS_PT_ShapeKeysPanel,
    MMS_PT_BakingPanel,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
