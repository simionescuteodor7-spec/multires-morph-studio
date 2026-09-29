import re
import bpy
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty


class MMS_OT_CreateShapeKeyFromMultires(Operator):
    """Capture current Multires sculpt deformation into a new Shape Key on the base mesh.
    Leaves the active Multires modifier, subdivision levels, and sculpt data 100% intact on the active object."""

    bl_idname = "mms.create_shape_key_from_multires"
    bl_label = "Create Shape Key from Multires"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj or obj.type != "MESH" or not obj.data:
            return False
        return any(m.type == "MULTIRES" for m in obj.modifiers)

    def execute(self, context):
        obj = context.active_object
        props = context.scene.multires_morph_studio

        multires_mod = next((m for m in obj.modifiers if m.type == "MULTIRES"), None)
        if not multires_mod:
            self.report({"ERROR"}, "No Multiresolution modifier found on active object.")
            return {"CANCELLED"}

        orig_mode = context.mode
        if orig_mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        temp_obj = None
        temp_mesh = None
        eval_obj_1 = None
        eval_obj_0 = None

        try:
            num_verts = len(obj.data.vertices)

            # 1. Duplicate mesh data and object into an in-memory temporary object
            # This ensures the original object and its active Multires sculpt are NEVER modified.
            temp_mesh = obj.data.copy()
            temp_obj = obj.copy()
            temp_obj.data = temp_mesh
            context.collection.objects.link(temp_obj)

            # 2. Reset base vertices cleanly to Basis
            if temp_mesh.shape_keys:
                temp_obj.shape_key_clear()

            # Find the Multires modifier on the temporary duplicate
            temp_m = next(mod for mod in temp_obj.modifiers if mod.type == "MULTIRES")
            levels = temp_m.total_levels
            mod_name = temp_m.name

            # Mute/disable all non-Multires modifiers on the temporary duplicate to isolate Multires
            for mod in temp_obj.modifiers:
                if mod.type != "MULTIRES":
                    mod.show_viewport = False

            # Ensure temp_m evaluates at full sculpt/total level
            temp_m.levels = levels

            context.view_layer.update()
            depsgraph = context.evaluated_depsgraph_get()

            # 3. S1: Sample sculpted Multires surface positions into flat C-level float buffer
            eval_obj_1 = temp_obj.evaluated_get(depsgraph)
            eval_mesh_1 = eval_obj_1.to_mesh()
            buf_1 = [0.0] * (len(eval_mesh_1.vertices) * 3)
            eval_mesh_1.vertices.foreach_get("co", buf_1)
            eval_obj_1.to_mesh_clear()
            eval_obj_1 = None

            # 4. S0: Sample neutral Multires limit surface (same levels, 0 displacement)
            temp_obj.modifiers.remove(temp_m)

            context.view_layer.objects.active = temp_obj
            temp_obj.select_set(True)
            new_m = temp_obj.modifiers.new(name=mod_name, type="MULTIRES")
            for _ in range(levels):
                bpy.ops.object.multires_subdivide(modifier=new_m.name)
            new_m.levels = levels

            context.view_layer.update()
            depsgraph = context.evaluated_depsgraph_get()
            eval_obj_0 = temp_obj.evaluated_get(depsgraph)
            eval_mesh_0 = eval_obj_0.to_mesh()
            buf_0 = [0.0] * (len(eval_mesh_0.vertices) * 3)
            eval_mesh_0.vertices.foreach_get("co", buf_0)
            eval_obj_0.to_mesh_clear()
            eval_obj_0 = None

            # 5. Ensure Basis exists on original object
            if not obj.data.shape_keys:
                sk_basis = obj.shape_key_add(name="Basis", from_mix=False)
            else:
                sk_basis = obj.data.shape_keys.key_blocks["Basis"]

            # 6. Determine intelligent unique name based on existing keys on mesh
            target_name = self._get_unique_name(obj, props)

            # 7. Compute exact delta: NewShapeKey = Basis + (S1 - S0)
            # High-performance flat float arithmetic (zero Python Vector allocations)
            basis_coords = [0.0] * (num_verts * 3)
            sk_basis.data.foreach_get("co", basis_coords)

            coords = [0.0] * (num_verts * 3)
            total_floats = num_verts * 3
            for j in range(total_floats):
                coords[j] = basis_coords[j] + (buf_1[j] - buf_0[j])

            new_sk = obj.shape_key_add(name=target_name, from_mix=False)
            new_sk.data.foreach_set("co", coords)
            new_sk.value = props.initial_key_value

            self.report(
                {"INFO"},
                f"Shape Key '{target_name}' created accurately. Multires sculpt preserved.",
            )

        except Exception as e:
            self.report({"ERROR"}, f"Failed to create shape key: {str(e)}")
            return {"CANCELLED"}

        finally:
            # Free any evaluated meshes if an exception interrupted execution
            if eval_obj_1 is not None:
                try:
                    eval_obj_1.to_mesh_clear()
                except Exception:
                    pass
            if eval_obj_0 is not None:
                try:
                    eval_obj_0.to_mesh_clear()
                except Exception:
                    pass

            # Guaranteed deletion of temporary duplicate object and mesh data
            if temp_obj is not None:
                try:
                    bpy.data.objects.remove(temp_obj, do_unlink=True)
                except Exception:
                    pass
            if temp_mesh is not None:
                try:
                    bpy.data.meshes.remove(temp_mesh)
                except Exception:
                    pass

            # Restore original active object selection
            try:
                context.view_layer.objects.active = obj
                obj.select_set(True)
            except Exception:
                pass

            if orig_mode != "OBJECT" and context.mode != orig_mode:
                try:
                    bpy.ops.object.mode_set(mode=orig_mode)
                except Exception:
                    pass

        return {"FINISHED"}

    @staticmethod
    def _get_unique_name(obj, props) -> str:
        raw_name = props.new_shape_key_name.strip() or "Sculpt_Morph"
        if not obj.data.shape_keys:
            match = re.search(r"^(.*?)(?:_(\d+))+$", raw_name)
            if match:
                raw_name = match.group(1)
                props.new_shape_key_name = raw_name
            return raw_name

        existing = set(obj.data.shape_keys.key_blocks.keys())

        # If name has a numbered suffix (e.g. d_03) but no matching keys exist on mesh, reset to base
        match = re.search(r"^(.*?)(?:_(\d+))+$", raw_name)
        if match:
            prefix = match.group(1)
            matching = [k for k in existing if k == prefix or k.startswith(f"{prefix}_")]
            if not matching:
                raw_name = prefix
                props.new_shape_key_name = raw_name

        if raw_name not in existing:
            return raw_name

        match = re.search(r"^(.*?)(?:_(\d+))?$", raw_name)
        prefix = match.group(1) if match else raw_name

        counter = 1
        target = f"{prefix}_{counter:02d}"
        while target in existing:
            counter += 1
            target = f"{prefix}_{counter:02d}"

        return target


class MMS_OT_DeleteShapeKey(Operator):
    """Delete a Shape Key without touching the Multires sculpt."""

    bl_idname = "mms.delete_shape_key"
    bl_label = "Delete Shape Key"
    bl_options = {"REGISTER", "UNDO"}

    key_name: StringProperty(name="Shape Key Name")

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.data or not obj.data.shape_keys:
            return {"CANCELLED"}

        kb = obj.data.shape_keys.key_blocks.get(self.key_name)
        if kb:
            obj.shape_key_remove(kb)
            props = getattr(context.scene, "multires_morph_studio", None)
            if props:
                non_basis = [
                    k for k in obj.data.shape_keys.key_blocks
                    if k != obj.data.shape_keys.key_blocks[0]
                ]
                if not non_basis:
                    match = re.search(r"^(.*?)(?:_(\d+))+$", props.new_shape_key_name)
                    if match:
                        props.new_shape_key_name = match.group(1)

            self.report({"INFO"}, f"Removed Shape Key '{self.key_name}'. Multires intact.")
            return {"FINISHED"}

        self.report({"WARNING"}, f"Shape Key '{self.key_name}' not found.")
        return {"CANCELLED"}


class MMS_OT_ResetMultiresSculpt(Operator):
    """Reset the active Multires sculpt displacement to match the base mesh.
    (Confirmation required: use only when you are ready to start a fresh sculpt)."""

    bl_idname = "mms.reset_multires_sculpt"
    bl_label = "Reset Multires to Base"
    bl_description = "Reset the Multires displacement to match the neutral base mesh"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == "MESH" and any(m.type == "MULTIRES" for m in obj.modifiers)

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        obj = context.active_object
        multires_mod = next((m for m in obj.modifiers if m.type == "MULTIRES"), None)
        if not multires_mod:
            return {"CANCELLED"}

        orig_mode = context.mode
        if orig_mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        try:
            total_levels = multires_mod.total_levels
            mod_name = multires_mod.name
            obj.modifiers.remove(multires_mod)

            new_mod = obj.modifiers.new(name=mod_name, type="MULTIRES")
            context.view_layer.objects.active = obj
            for _ in range(total_levels):
                bpy.ops.object.multires_subdivide(modifier=new_mod.name)

            self.report({"INFO"}, f"Multires sculpt reset to flat base at {total_levels} levels.")
        finally:
            if orig_mode != "OBJECT":
                try:
                    bpy.ops.object.mode_set(mode=orig_mode)
                except Exception:
                    pass

        return {"FINISHED"}


class MMS_OT_BakeMap(Operator):
    """Independently bake Normal or Displacement map directly from the Multiresolution modifier."""

    bl_idname = "mms.bake_map"
    bl_label = "Bake Multires Texture"
    bl_options = {"REGISTER"}

    map_type: EnumProperty(
        items=[
            ("NORMALS", "Normal Map", "Tangent space normal map"),
            ("DISPLACEMENT", "Displacement Map", "Height / displacement map"),
        ],
        default="NORMALS",
        name="Map Type",
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == "MESH" and any(m.type == "MULTIRES" for m in obj.modifiers)

    def execute(self, context):
        obj = context.active_object
        scene = context.scene
        props = scene.multires_morph_studio

        if not obj.data.uv_layers:
            self.report(
                {"ERROR"},
                "Object has no UV map. Please UV unwrap the mesh before baking.",
            )
            return {"CANCELLED"}

        orig_mode = context.mode
        if orig_mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        prev_engine = scene.render.engine
        bake_node = None
        mat = None

        try:
            res = int(props.bake_resolution)
            is_float = props.bake_use_32bit_float if self.map_type == "DISPLACEMENT" else False

            type_suffix = "Normal" if self.map_type == "NORMALS" else "Displacement"
            if props.bake_image_name.strip():
                img_name = props.bake_image_name.strip()
            else:
                img_name = f"{obj.name}_Multires_{type_suffix}_{res}"

            img = bpy.data.images.get(img_name)
            if not img or img.size[0] != res or img.size[1] != res:
                img = bpy.data.images.new(
                    name=img_name,
                    width=res,
                    height=res,
                    float_buffer=is_float,
                )

            # Normal and Displacement maps must be stored as raw mathematical data (Non-Color)
            try:
                img.colorspace_settings.name = "Non-Color"
            except Exception:
                pass

            mat = obj.active_material or (obj.data.materials[0] if obj.data.materials else None)
            if not mat:
                mat = bpy.data.materials.new(name=f"{obj.name}_Material")
                obj.data.materials.append(mat)

            if hasattr(mat, "use_nodes"):
                mat.use_nodes = True

            nodes = mat.node_tree.nodes
            bake_node = nodes.new("ShaderNodeTexImage")
            bake_node.name = "__MMS_TEMP_BAKE_NODE__"
            bake_node.image = img
            nodes.active = bake_node

            scene.render.engine = "CYCLES"
            scene.render.bake.use_multires = True
            scene.render.bake.type = self.map_type
            scene.render.bake.margin = props.bake_margin

            self.report({"INFO"}, f"Baking Multires {type_suffix} map at {res}x{res}...")
            if hasattr(bpy.ops.object, "bake_image"):
                bpy.ops.object.bake_image()
            else:
                bpy.ops.object.bake(type=self.map_type)
            self.report({"INFO"}, f"Successfully baked {type_suffix} map into image '{img.name}'.")

        except Exception as e:
            self.report({"ERROR"}, f"Bake failed: {str(e)}")
            return {"CANCELLED"}

        finally:
            if mat and getattr(mat, "node_tree", None) and bake_node:
                try:
                    if bake_node.name in mat.node_tree.nodes:
                        mat.node_tree.nodes.remove(bake_node)
                except Exception:
                    pass

            scene.render.engine = prev_engine
            if orig_mode != "OBJECT" and context.mode != orig_mode:
                try:
                    bpy.ops.object.mode_set(mode=orig_mode)
                except Exception:
                    pass

        return {"FINISHED"}


classes = (
    MMS_OT_CreateShapeKeyFromMultires,
    MMS_OT_DeleteShapeKey,
    MMS_OT_ResetMultiresSculpt,
    MMS_OT_BakeMap,
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
