# ====================================================================
# AUTO-GENERATED BLENDER SCRIPT
# Source: FloorPlan-3D Pipeline
# DO NOT EDIT MANUALLY — regenerate by re-running the pipeline
# ====================================================================
import bpy, math, mathutils

# ── Scene Reset ──────────────────────────────────────────────────────
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for col in list(bpy.data.collections):
    bpy.data.collections.remove(col)

# ── Units ────────────────────────────────────────────────────────────
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.length_unit = 'METERS'
bpy.context.scene.unit_settings.scale_length = 1.0

# ── Collection ───────────────────────────────────────────────────────
main_col = bpy.data.collections.new('Building')
bpy.context.scene.collection.children.link(main_col)
bpy.context.view_layer.active_layer_collection = \
    bpy.context.view_layer.layer_collection.children['Building']



# ── Floor Slabs & Base ──────────────────────────────────────────
# Generic Base Plate
base_verts = [(-2.0, -2.0, -0.2), (8.416015999999999, -2.0, -0.2), (8.416015999999999, 10.241729, -0.2), (-2.0, 10.241729, -0.2)]
base_faces = [[0, 1, 2, 3]]
base_mesh = bpy.data.meshes.new('BasePlate')
base_mesh.from_pydata(base_verts, [], base_faces)
base_mesh.update()
base_obj = bpy.data.objects.new('BasePlate', base_mesh)
bpy.context.collection.objects.link(base_obj)
base_mod = base_obj.modifiers.new('Solidify', 'SOLIDIFY')
base_mod.thickness = 0.2
base_mod.offset = -1.0


# ── Walls ───────────────────────────────────────────────
# Wall: w1  (length=1.759m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(5.410082, 0.013955, 1.5)
)
wall_obj_w1 = bpy.context.active_object
wall_obj_w1.name = 'Wall_w1'
wall_obj_w1.scale = (1.7585214977645285, 0.195312, 3.0)
wall_obj_w1.rotation_euler[2] = 0.01587195374793344
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
import bmesh
bpy.context.view_layer.objects.active = wall_obj_w1
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(wall_obj_w1.data)
bm.faces.ensure_lookup_table()
top_faces = [f for f in bm.faces if f.normal.z > 0.9]
bmesh.ops.delete(bm, geom=top_faces, context='FACES')
bmesh.update_edit_mesh(wall_obj_w1.data)
bpy.ops.object.mode_set(mode='OBJECT')

# Wall: w4  (length=3.652m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(6.416016, 2.001494, 1.5)
)
wall_obj_w4 = bpy.context.active_object
wall_obj_w4.name = 'Wall_w4'
wall_obj_w4.scale = (3.652344, 0.195312, 3.0)
wall_obj_w4.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
import bmesh
bpy.context.view_layer.objects.active = wall_obj_w4
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(wall_obj_w4.data)
bm.faces.ensure_lookup_table()
top_faces = [f for f in bm.faces if f.normal.z > 0.9]
bmesh.ops.delete(bm, geom=top_faces, context='FACES')
bmesh.update_edit_mesh(wall_obj_w4.data)
bpy.ops.object.mode_set(mode='OBJECT')

# Wall: w9  (length=3.320m, thickness=1.230m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(2.177734, 2.8901660000000002, 1.5)
)
wall_obj_w9 = bpy.context.active_object
wall_obj_w9.name = 'Wall_w9'
wall_obj_w9.scale = (3.3203120000000004, 1.230469, 3.0)
wall_obj_w9.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
import bmesh
bpy.context.view_layer.objects.active = wall_obj_w9
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(wall_obj_w9.data)
bm.faces.ensure_lookup_table()
top_faces = [f for f in bm.faces if f.normal.z > 0.9]
bmesh.ops.delete(bm, geom=top_faces, context='FACES')
bmesh.update_edit_mesh(wall_obj_w9.data)
bpy.ops.object.mode_set(mode='OBJECT')

# Wall: w11  (length=1.154m, thickness=1.092m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(0.352963, 5.1949955, 1.5)
)
wall_obj_w11 = bpy.context.active_object
wall_obj_w11.name = 'Wall_w11'
wall_obj_w11.scale = (1.1537748927503149, 1.092442, 3.0)
wall_obj_w11.rotation_euler[2] = 1.5300023611518052
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
import bmesh
bpy.context.view_layer.objects.active = wall_obj_w11
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(wall_obj_w11.data)
bm.faces.ensure_lookup_table()
top_faces = [f for f in bm.faces if f.normal.z > 0.9]
bmesh.ops.delete(bm, geom=top_faces, context='FACES')
bmesh.update_edit_mesh(wall_obj_w11.data)
bpy.ops.object.mode_set(mode='OBJECT')

# Wall: w14  (length=1.289m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(1.943359, 6.38626, 1.5)
)
wall_obj_w14 = bpy.context.active_object
wall_obj_w14.name = 'Wall_w14'
wall_obj_w14.scale = (1.2890619999999995, 0.195312, 3.0)
wall_obj_w14.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
import bmesh
bpy.context.view_layer.objects.active = wall_obj_w14
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(wall_obj_w14.data)
bm.faces.ensure_lookup_table()
top_faces = [f for f in bm.faces if f.normal.z > 0.9]
bmesh.ops.delete(bm, geom=top_faces, context='FACES')
bmesh.update_edit_mesh(wall_obj_w14.data)
bpy.ops.object.mode_set(mode='OBJECT')

# Wall: w16  (length=5.840m, thickness=0.977m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(0.0, 4.149932, 1.5)
)
wall_obj_w16 = bpy.context.active_object
wall_obj_w16.name = 'Wall_w16'
wall_obj_w16.scale = (5.839844, 0.976562, 3.0)
wall_obj_w16.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
import bmesh
bpy.context.view_layer.objects.active = wall_obj_w16
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(wall_obj_w16.data)
bm.faces.ensure_lookup_table()
top_faces = [f for f in bm.faces if f.normal.z > 0.9]
bmesh.ops.delete(bm, geom=top_faces, context='FACES')
bmesh.update_edit_mesh(wall_obj_w16.data)
bpy.ops.object.mode_set(mode='OBJECT')

# Wall: w19  (length=0.703m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(6.416016, 7.890166499999999, 1.5)
)
wall_obj_w19 = bpy.context.active_object
wall_obj_w19.name = 'Wall_w19'
wall_obj_w19.scale = (0.7031249999999991, 0.195312, 3.0)
wall_obj_w19.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
import bmesh
bpy.context.view_layer.objects.active = wall_obj_w19
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(wall_obj_w19.data)
bm.faces.ensure_lookup_table()
top_faces = [f for f in bm.faces if f.normal.z > 0.9]
bmesh.ops.delete(bm, geom=top_faces, context='FACES')
bmesh.update_edit_mesh(wall_obj_w19.data)
bpy.ops.object.mode_set(mode='OBJECT')

# Wall: w22  (length=1.094m, thickness=0.312m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(2.03125, 7.694853999999999, 1.5)
)
wall_obj_w22 = bpy.context.active_object
wall_obj_w22.name = 'Wall_w22'
wall_obj_w22.scale = (1.0937499999999991, 0.3125, 3.0)
wall_obj_w22.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
import bmesh
bpy.context.view_layer.objects.active = wall_obj_w22
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(wall_obj_w22.data)
bm.faces.ensure_lookup_table()
top_faces = [f for f in bm.faces if f.normal.z > 0.9]
bmesh.ops.delete(bm, geom=top_faces, context='FACES')
bmesh.update_edit_mesh(wall_obj_w22.data)
bpy.ops.object.mode_set(mode='OBJECT')


# ── Openings (Doors & Windows) ───────────────────────────
# Door: d1
bpy.ops.mesh.primitive_cube_add(size=1, location=(1.011475, 1.302348, 1.125))
cut_d1 = bpy.context.active_object
cut_d1.name = 'Cutter_d1'
cut_d1.scale = (1.054688, 1.953124, 2.25)
cut_d1.rotation_euler[2] = 1.5707963267948966
cut_d1.display_type = 'WIRE'
wall_target_d1 = bpy.data.objects.get('Wall_w16')
if wall_target_d1:
    bool_mod_d1 = wall_target_d1.modifiers.new('Cut_d1', 'BOOLEAN')
    bool_mod_d1.operation = 'DIFFERENCE'
    bool_mod_d1.object = cut_d1
    cut_d1.hide_render = True

# Door: d2
bpy.ops.mesh.primitive_cube_add(size=1, location=(6.416016, 3.827666, 1.125))
cut_d2 = bpy.context.active_object
cut_d2.name = 'Cutter_d2'
cut_d2.scale = (0.410156, 0.390624, 2.25)
cut_d2.rotation_euler[2] = 1.5707963267948966
cut_d2.display_type = 'WIRE'
wall_target_d2 = bpy.data.objects.get('Wall_w4')
if wall_target_d2:
    bool_mod_d2 = wall_target_d2.modifiers.new('Cut_d2', 'BOOLEAN')
    bool_mod_d2.operation = 'DIFFERENCE'
    bool_mod_d2.object = cut_d2
    cut_d2.hide_render = True

# Door: d11
bpy.ops.mesh.primitive_cube_add(size=1, location=(6.424435, 7.004506, 1.125))
cut_d11 = bpy.context.active_object
cut_d11.name = 'Cutter_d11'
cut_d11.scale = (1.074219, 0.390624, 2.25)
cut_d11.rotation_euler[2] = 1.5707963267948966
cut_d11.display_type = 'WIRE'
wall_target_d11 = bpy.data.objects.get('Wall_w19')
if wall_target_d11:
    bool_mod_d11 = wall_target_d11.modifiers.new('Cut_d11', 'BOOLEAN')
    bool_mod_d11.operation = 'DIFFERENCE'
    bool_mod_d11.object = cut_d11
    cut_d11.hide_render = True

# Door: d12
bpy.ops.mesh.primitive_cube_add(size=1, location=(5.355392, 8.175438, 1.125))
cut_d12 = bpy.context.active_object
cut_d12.name = 'Cutter_d12'
cut_d12.scale = (1.015625, 0.390624, 2.25)
cut_d12.rotation_euler[2] = 1.5707963267948966
cut_d12.display_type = 'WIRE'
wall_target_d12 = bpy.data.objects.get('Wall_w19')
if wall_target_d12:
    bool_mod_d12 = wall_target_d12.modifiers.new('Cut_d12', 'BOOLEAN')
    bool_mod_d12.operation = 'DIFFERENCE'
    bool_mod_d12.object = cut_d12
    cut_d12.hide_render = True

# Window: win15
bpy.ops.mesh.primitive_cube_add(size=1, location=(2.177734, 2.973386, 1.5))
cut_win15 = bpy.context.active_object
cut_win15.name = 'Cutter_win15'
cut_win15.scale = (0.410156, 2.460938, 1.2000000000000002)
cut_win15.rotation_euler[2] = 1.5707963267948966
cut_win15.display_type = 'WIRE'
wall_target_win15 = bpy.data.objects.get('Wall_w9')
if wall_target_win15:
    bool_mod_win15 = wall_target_win15.modifiers.new('Cut_win15', 'BOOLEAN')
    bool_mod_win15.operation = 'DIFFERENCE'
    bool_mod_win15.object = cut_win15
    cut_win15.hide_render = True

# Window: win17
bpy.ops.mesh.primitive_cube_add(size=1, location=(6.416016, 3.766541, 1.5))
cut_win17 = bpy.context.active_object
cut_win17.name = 'Cutter_win17'
cut_win17.scale = (0.390625, 0.390624, 1.2000000000000002)
cut_win17.rotation_euler[2] = 1.5707963267948966
cut_win17.display_type = 'WIRE'
wall_target_win17 = bpy.data.objects.get('Wall_w4')
if wall_target_win17:
    bool_mod_win17 = wall_target_win17.modifiers.new('Cut_win17', 'BOOLEAN')
    bool_mod_win17.operation = 'DIFFERENCE'
    bool_mod_win17.object = cut_win17
    cut_win17.hide_render = True

# Window: win21
bpy.ops.mesh.primitive_cube_add(size=1, location=(2.177734, 3.579989, 1.5))
cut_win21 = bpy.context.active_object
cut_win21.name = 'Cutter_win21'
cut_win21.scale = (1.09375, 2.460938, 1.2000000000000002)
cut_win21.rotation_euler[2] = 1.5707963267948966
cut_win21.display_type = 'WIRE'
wall_target_win21 = bpy.data.objects.get('Wall_w9')
if wall_target_win21:
    bool_mod_win21 = wall_target_win21.modifiers.new('Cut_win21', 'BOOLEAN')
    bool_mod_win21.operation = 'DIFFERENCE'
    bool_mod_win21.object = cut_win21
    cut_win21.hide_render = True

# Window: win22
bpy.ops.mesh.primitive_cube_add(size=1, location=(7.506076, 4.335334, 1.5))
cut_win22 = bpy.context.active_object
cut_win22.name = 'Cutter_win22'
cut_win22.scale = (0.175781, 0.390624, 1.2000000000000002)
cut_win22.rotation_euler[2] = 1.5707963267948966
cut_win22.display_type = 'WIRE'
wall_target_win22 = bpy.data.objects.get('Wall_w4')
if wall_target_win22:
    bool_mod_win22 = wall_target_win22.modifiers.new('Cut_win22', 'BOOLEAN')
    bool_mod_win22.operation = 'DIFFERENCE'
    bool_mod_win22.object = cut_win22
    cut_win22.hide_render = True

# Window: win23
bpy.ops.mesh.primitive_cube_add(size=1, location=(6.828566, 4.132849, 1.5))
cut_win23 = bpy.context.active_object
cut_win23.name = 'Cutter_win23'
cut_win23.scale = (0.585938, 0.390624, 1.2000000000000002)
cut_win23.rotation_euler[2] = 1.5707963267948966
cut_win23.display_type = 'WIRE'
wall_target_win23 = bpy.data.objects.get('Wall_w4')
if wall_target_win23:
    bool_mod_win23 = wall_target_win23.modifiers.new('Cut_win23', 'BOOLEAN')
    bool_mod_win23.operation = 'DIFFERENCE'
    bool_mod_win23.object = cut_win23
    cut_win23.hide_render = True

# Window: win28
bpy.ops.mesh.primitive_cube_add(size=1, location=(7.166226, 4.316798, 1.5))
cut_win28 = bpy.context.active_object
cut_win28.name = 'Cutter_win28'
cut_win28.scale = (0.839844, 0.390624, 1.2000000000000002)
cut_win28.rotation_euler[2] = 1.5707963267948966
cut_win28.display_type = 'WIRE'
wall_target_win28 = bpy.data.objects.get('Wall_w4')
if wall_target_win28:
    bool_mod_win28 = wall_target_win28.modifiers.new('Cut_win28', 'BOOLEAN')
    bool_mod_win28.operation = 'DIFFERENCE'
    bool_mod_win28.object = cut_win28
    cut_win28.hide_render = True

# Window: win32
bpy.ops.mesh.primitive_cube_add(size=1, location=(7.147996, 4.765111, 1.5))
cut_win32 = bpy.context.active_object
cut_win32.name = 'Cutter_win32'
cut_win32.scale = (0.3125, 0.390624, 1.2000000000000002)
cut_win32.rotation_euler[2] = 1.5707963267948966
cut_win32.display_type = 'WIRE'
wall_target_win32 = bpy.data.objects.get('Wall_w4')
if wall_target_win32:
    bool_mod_win32 = wall_target_win32.modifiers.new('Cut_win32', 'BOOLEAN')
    bool_mod_win32.operation = 'DIFFERENCE'
    bool_mod_win32.object = cut_win32
    cut_win32.hide_render = True

# Window: win43
bpy.ops.mesh.primitive_cube_add(size=1, location=(1.364968, 5.775696, 1.5))
cut_win43 = bpy.context.active_object
cut_win43.name = 'Cutter_win43'
cut_win43.scale = (1.347656, 0.390624, 1.2000000000000002)
cut_win43.rotation_euler[2] = 1.5707963267948966
cut_win43.display_type = 'WIRE'
wall_target_win43 = bpy.data.objects.get('Wall_w14')
if wall_target_win43:
    bool_mod_win43 = wall_target_win43.modifiers.new('Cut_win43', 'BOOLEAN')
    bool_mod_win43.operation = 'DIFFERENCE'
    bool_mod_win43.object = cut_win43
    cut_win43.hide_render = True

# Window: win47
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, 6.293602000000001, 1.5))
cut_win47 = bpy.context.active_object
cut_win47.name = 'Cutter_win47'
cut_win47.scale = (0.292969, 1.953124, 1.2000000000000002)
cut_win47.rotation_euler[2] = 1.5707963267948966
cut_win47.display_type = 'WIRE'
wall_target_win47 = bpy.data.objects.get('Wall_w16')
if wall_target_win47:
    bool_mod_win47 = wall_target_win47.modifiers.new('Cut_win47', 'BOOLEAN')
    bool_mod_win47.operation = 'DIFFERENCE'
    bool_mod_win47.object = cut_win47
    cut_win47.hide_render = True

# Window: win56
bpy.ops.mesh.primitive_cube_add(size=1, location=(1.118281, 7.011026, 1.5))
cut_win56 = bpy.context.active_object
cut_win56.name = 'Cutter_win56'
cut_win56.scale = (1.445312, 0.390624, 1.2000000000000002)
cut_win56.rotation_euler[2] = 1.5707963267948966
cut_win56.display_type = 'WIRE'
wall_target_win56 = bpy.data.objects.get('Wall_w14')
if wall_target_win56:
    bool_mod_win56 = wall_target_win56.modifiers.new('Cut_win56', 'BOOLEAN')
    bool_mod_win56.operation = 'DIFFERENCE'
    bool_mod_win56.object = cut_win56
    cut_win56.hide_render = True

# Window: win60
bpy.ops.mesh.primitive_cube_add(size=1, location=(2.03125, 7.147979, 1.5))
cut_win60 = bpy.context.active_object
cut_win60.name = 'Cutter_win60'
cut_win60.scale = (0.664062, 0.625, 1.2000000000000002)
cut_win60.rotation_euler[2] = 1.5707963267948966
cut_win60.display_type = 'WIRE'
wall_target_win60 = bpy.data.objects.get('Wall_w22')
if wall_target_win60:
    bool_mod_win60 = wall_target_win60.modifiers.new('Cut_win60', 'BOOLEAN')
    bool_mod_win60.operation = 'DIFFERENCE'
    bool_mod_win60.object = cut_win60
    cut_win60.hide_render = True

# Window: win63
bpy.ops.mesh.primitive_cube_add(size=1, location=(6.416016, 8.181228, 1.5))
cut_win63 = bpy.context.active_object
cut_win63.name = 'Cutter_win63'
cut_win63.scale = (0.507812, 0.390624, 1.2000000000000002)
cut_win63.rotation_euler[2] = 1.5707963267948966
cut_win63.display_type = 'WIRE'
wall_target_win63 = bpy.data.objects.get('Wall_w19')
if wall_target_win63:
    bool_mod_win63 = wall_target_win63.modifiers.new('Cut_win63', 'BOOLEAN')
    bool_mod_win63.operation = 'DIFFERENCE'
    bool_mod_win63.object = cut_win63
    cut_win63.hide_render = True

# Window: win65
bpy.ops.mesh.primitive_cube_add(size=1, location=(2.894768, 8.184368, 1.5))
cut_win65 = bpy.context.active_object
cut_win65.name = 'Cutter_win65'
cut_win65.scale = (1.484375, 0.625, 1.2000000000000002)
cut_win65.rotation_euler[2] = 1.5707963267948966
cut_win65.display_type = 'WIRE'
wall_target_win65 = bpy.data.objects.get('Wall_w22')
if wall_target_win65:
    bool_mod_win65 = wall_target_win65.modifiers.new('Cut_win65', 'BOOLEAN')
    bool_mod_win65.operation = 'DIFFERENCE'
    bool_mod_win65.object = cut_win65
    cut_win65.hide_render = True




# ── Furniture (Placeholder Cubes) ────────────────────────

# ── Materials ────────────────────────────────────────────
# Material: painted_white
if 'painted_white' not in bpy.data.materials:
    mat_painted_white = bpy.data.materials.new(name='painted_white')
    mat_painted_white.use_nodes = True
    bsdf_painted_white = mat_painted_white.node_tree.nodes['Principled BSDF']
    bsdf_painted_white.inputs['Base Color'].default_value = (0.95, 0.95, 0.95, 1.0)
    bsdf_painted_white.inputs['Roughness'].default_value = 0.85

for obj in bpy.data.objects:
    if obj.name.startswith('Wall'):
        if obj.data and hasattr(obj.data, 'materials'):
            if len(obj.data.materials) == 0:
                obj.data.materials.append(bpy.data.materials['painted_white'])
            else:
                obj.data.materials[0] = bpy.data.materials['painted_white']

# Material: oak_wood
if 'oak_wood' not in bpy.data.materials:
    mat_oak_wood = bpy.data.materials.new(name='oak_wood')
    mat_oak_wood.use_nodes = True
    bsdf_oak_wood = mat_oak_wood.node_tree.nodes['Principled BSDF']
    bsdf_oak_wood.inputs['Base Color'].default_value = (0.55, 0.35, 0.18, 1.0)
    bsdf_oak_wood.inputs['Roughness'].default_value = 0.7

for obj in bpy.data.objects:
    if obj.name.startswith('Floor'):
        if obj.data and hasattr(obj.data, 'materials'):
            if len(obj.data.materials) == 0:
                obj.data.materials.append(bpy.data.materials['oak_wood'])
            else:
                obj.data.materials[0] = bpy.data.materials['oak_wood']

# Material: plaster_white
if 'plaster_white' not in bpy.data.materials:
    mat_plaster_white = bpy.data.materials.new(name='plaster_white')
    mat_plaster_white.use_nodes = True
    bsdf_plaster_white = mat_plaster_white.node_tree.nodes['Principled BSDF']
    bsdf_plaster_white.inputs['Base Color'].default_value = (0.93, 0.93, 0.9, 1.0)
    bsdf_plaster_white.inputs['Roughness'].default_value = 0.9

for obj in bpy.data.objects:
    if obj.name.startswith('Ceiling'):
        if obj.data and hasattr(obj.data, 'materials'):
            if len(obj.data.materials) == 0:
                obj.data.materials.append(bpy.data.materials['plaster_white'])
            else:
                obj.data.materials[0] = bpy.data.materials['plaster_white']


# ── Lighting ─────────────────────────────────────────────
bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))
sun = bpy.context.active_object
sun.name = 'Sun_Light'
sun.data.energy = 3.0
sun.rotation_euler = (0.7853975, 0, 0.7853975)


# ── Cameras ──────────────────────────────────────────────
# Camera 1: Top-down (plan view)
bpy.ops.object.camera_add(location=(3.208008, 4.1208645, 13.241729))
cam_top = bpy.context.active_object
cam_top.name = 'Camera_TopDown'
cam_top.rotation_euler = (0, 0, 0)
cam_top.data.type = 'ORTHO'
cam_top.data.ortho_scale = 9.890074799999999

# Camera 2: Perspective (exterior corner view)
bpy.ops.object.camera_add(location=(11.3610534, -4.9450373999999995, 4.1208645))
cam_persp = bpy.context.active_object
cam_persp.name = 'Camera_Perspective'
cam_persp.data.type = 'PERSP'
cam_persp.data.lens = 35
import mathutils
cam_persp.rotation_euler = mathutils.Euler((1.047, 0, 0.785), 'XYZ')

bpy.context.scene.camera = bpy.data.objects['Camera_TopDown']


# ── Export ───────────────────────────────────────────────
import os as _os
_os.makedirs(r'C:\Users\Abdullah\Documents\3d\floorplan-3d-backend\output', exist_ok=True)

bpy.ops.export_scene.gltf(
    filepath=r'C:/Users/Abdullah/Documents/3d/floorplan-3d-backend/output/PROJECT_VILLA.glb',
    export_format='GLB',
    export_apply=True
)
print('Exported GLB ->', r'C:/Users/Abdullah/Documents/3d/floorplan-3d-backend/output/PROJECT_VILLA.glb')



print('Script complete.')
