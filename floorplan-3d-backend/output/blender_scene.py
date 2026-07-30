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
for mat in list(bpy.data.materials):
    bpy.data.materials.remove(mat)

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
# Room: room
verts_room_557a6a98 = [(5.2845, 2.2815, 0.0), (5.304, 1.248, 0.0), (7.683, 1.287, 0.0), (7.644, 2.301, 0.0)]
faces_room_557a6a98 = [list(range(len(verts_room_557a6a98)))]
mesh_room_557a6a98 = bpy.data.meshes.new('floor_room_557a6a98')
mesh_room_557a6a98.from_pydata(verts_room_557a6a98, [], faces_room_557a6a98)
mesh_room_557a6a98.update()
obj_room_557a6a98 = bpy.data.objects.new('Floor_room', mesh_room_557a6a98)
bpy.context.collection.objects.link(obj_room_557a6a98)
mod_room_557a6a98 = obj_room_557a6a98.modifiers.new('Solidify', 'SOLIDIFY')
mod_room_557a6a98.thickness = 0.2
mod_room_557a6a98.offset = -1.0

# Room: room
verts_room_58b1b487 = [(0.9945, 8.0145, 0.0), (0.9945, 6.357, 0.0), (2.028, 6.3375, 0.0), (2.0085, 6.1035, 0.0), (0.975, 6.1425, 0.0), (1.014, 2.4765, 0.0), (3.5685, 2.4765, 0.0), (3.627, 2.7885, 0.0), (3.7635, 2.769, 0.0), (3.783, 2.535, 0.0), (7.6635, 2.4765, 0.0), (7.6635, 9.1455, 0.0), (3.4515, 9.165, 0.0), (3.315, 7.9755, 0.0)]
faces_room_58b1b487 = [list(range(len(verts_room_58b1b487)))]
mesh_room_58b1b487 = bpy.data.meshes.new('floor_room_58b1b487')
mesh_room_58b1b487.from_pydata(verts_room_58b1b487, [], faces_room_58b1b487)
mesh_room_58b1b487.update()
obj_room_58b1b487 = bpy.data.objects.new('Floor_room', mesh_room_58b1b487)
bpy.context.collection.objects.link(obj_room_58b1b487)
mod_room_58b1b487 = obj_room_58b1b487.modifiers.new('Solidify', 'SOLIDIFY')
mod_room_58b1b487.thickness = 0.2
mod_room_58b1b487.offset = -1.0

# Generic Base Plate
base_verts = [(-1.1225, -0.8494999999999999, -0.2), (9.761, -0.8494999999999999, -0.2), (9.761, 11.282, -0.2), (-1.1225, 11.282, -0.2)]
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
# Wall: wall_joined_1a19a0a2  (length=6.786m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(4.309531654509479, 2.379, 1.5)
)
wall_obj_wall_joined_1a19a0a2 = bpy.context.active_object
wall_obj_wall_joined_1a19a0a2.name = 'Wall_wall_joined_1a19a0a2'
wall_obj_wall_joined_1a19a0a2.scale = (6.786063309018959, 0.195, 3.0)
wall_obj_wall_joined_1a19a0a2.rotation_euler[2] = 0.0
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_82f488ad  (length=7.819m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(7.761, 5.157749999999999, 1.5)
)
wall_obj_wall_joined_82f488ad = bpy.context.active_object
wall_obj_wall_joined_82f488ad.name = 'Wall_wall_joined_82f488ad'
wall_obj_wall_joined_82f488ad.scale = (7.8195, 0.195, 3.0)
wall_obj_wall_joined_82f488ad.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_8eb1e9a7  (length=5.284m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(0.8775, 5.27475, 1.5)
)
wall_obj_wall_joined_8eb1e9a7 = bpy.context.active_object
wall_obj_wall_joined_8eb1e9a7.name = 'Wall_wall_joined_8eb1e9a7'
wall_obj_wall_joined_8eb1e9a7.scale = (5.2844999999999995, 0.195, 3.0)
wall_obj_wall_joined_8eb1e9a7.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_aa3aad7e  (length=4.446m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(5.518474610063728, 9.2625, 1.5)
)
wall_obj_wall_joined_aa3aad7e = bpy.context.active_object
wall_obj_wall_joined_aa3aad7e.name = 'Wall_wall_joined_aa3aad7e'
wall_obj_wall_joined_aa3aad7e.scale = (4.446050779872545, 0.195, 3.0)
wall_obj_wall_joined_aa3aad7e.rotation_euler[2] = 0.0
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_8f4d829f  (length=3.335m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(3.6855, 4.10475, 1.5)
)
wall_obj_wall_joined_8f4d829f = bpy.context.active_object
wall_obj_wall_joined_8f4d829f.name = 'Wall_wall_joined_8f4d829f'
wall_obj_wall_joined_8f4d829f.scale = (3.3345000000000002, 0.195, 3.0)
wall_obj_wall_joined_8f4d829f.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_16a9af85  (length=2.321m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(2.05725, 8.112, 1.5)
)
wall_obj_wall_16a9af85 = bpy.context.active_object
wall_obj_wall_16a9af85.name = 'Wall_wall_16a9af85'
wall_obj_wall_16a9af85.scale = (2.3205, 0.195, 3.0)
wall_obj_wall_16a9af85.rotation_euler[2] = 0.0
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_1673e2d2  (length=2.594m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(6.44475, 1.1505, 1.5)
)
wall_obj_wall_joined_1673e2d2 = bpy.context.active_object
wall_obj_wall_joined_1673e2d2.name = 'Wall_wall_joined_1673e2d2'
wall_obj_wall_joined_1673e2d2.scale = (2.5935000000000006, 0.195, 3.0)
wall_obj_wall_joined_1673e2d2.rotation_euler[2] = 0.0
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_348d0dde  (length=2.496m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(3.276, 8.033999999999999, 1.5)
)
wall_obj_wall_joined_348d0dde = bpy.context.active_object
wall_obj_wall_joined_348d0dde.name = 'Wall_wall_joined_348d0dde'
wall_obj_wall_joined_348d0dde.scale = (2.4960000000000004, 0.195, 3.0)
wall_obj_wall_joined_348d0dde.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_a3601c5c  (length=1.287m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(2.613, 6.8055, 1.5)
)
wall_obj_wall_joined_a3601c5c = bpy.context.active_object
wall_obj_wall_joined_a3601c5c.name = 'Wall_wall_joined_a3601c5c'
wall_obj_wall_joined_a3601c5c.scale = (1.287, 0.195, 3.0)
wall_obj_wall_joined_a3601c5c.rotation_euler[2] = 0.0
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_506d0659  (length=1.482m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(2.847, 5.7525, 1.5)
)
wall_obj_wall_joined_506d0659 = bpy.context.active_object
wall_obj_wall_joined_506d0659.name = 'Wall_wall_joined_506d0659'
wall_obj_wall_joined_506d0659.scale = (1.4820000000000002, 0.195, 3.0)
wall_obj_wall_joined_506d0659.rotation_euler[2] = 0.0
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_a9f957ed  (length=1.170m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(5.187, 1.755, 1.5)
)
wall_obj_wall_joined_a9f957ed = bpy.context.active_object
wall_obj_wall_joined_a9f957ed.name = 'Wall_wall_joined_a9f957ed'
wall_obj_wall_joined_a9f957ed.scale = (1.17, 0.195, 3.0)
wall_obj_wall_joined_a9f957ed.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_7c123767  (length=0.956m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(1.41375, 6.28875, 1.5)
)
wall_obj_wall_7c123767 = bpy.context.active_object
wall_obj_wall_7c123767.name = 'Wall_wall_7c123767'
wall_obj_wall_7c123767.scale = (0.955698958877742, 0.195, 3.0)
wall_obj_wall_7c123767.rotation_euler[2] = 0.0
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_38111277  (length=1.072m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(1.95, 6.30825, 1.5)
)
wall_obj_wall_joined_38111277 = bpy.context.active_object
wall_obj_wall_joined_38111277.name = 'Wall_wall_joined_38111277'
wall_obj_wall_joined_38111277.scale = (1.0724999999999998, 0.195, 3.0)
wall_obj_wall_joined_38111277.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


# ── Openings (Doors & Windows) ───────────────────────────
# Door: door_1
bpy.ops.mesh.primitive_cube_add(size=1, location=(5.187, 1.74525, 1.125))
cut_door_1 = bpy.context.active_object
cut_door_1.name = 'Cutter_door_1'
cut_door_1.scale = (0.9, 0.39, 2.25)
cut_door_1.rotation_euler[2] = 1.5707963267948966
cut_door_1.display_type = 'WIRE'
wall_target_door_1 = bpy.data.objects.get('Wall_wall_joined_a9f957ed')
if wall_target_door_1:
    bool_mod_door_1 = wall_target_door_1.modifiers.new('Cut_door_1', 'BOOLEAN')
    bool_mod_door_1.operation = 'DIFFERENCE'
    bool_mod_door_1.object = cut_door_1
    cut_door_1.hide_render = True

# Door: door_2
bpy.ops.mesh.primitive_cube_add(size=1, location=(6.747, 2.379, 1.125))
cut_door_2 = bpy.context.active_object
cut_door_2.name = 'Cutter_door_2'
cut_door_2.scale = (0.9, 0.39, 2.25)
cut_door_2.rotation_euler[2] = 0.0
cut_door_2.display_type = 'WIRE'
wall_target_door_2 = bpy.data.objects.get('Wall_wall_joined_1a19a0a2')
if wall_target_door_2:
    bool_mod_door_2 = wall_target_door_2.modifiers.new('Cut_door_2', 'BOOLEAN')
    bool_mod_door_2.operation = 'DIFFERENCE'
    bool_mod_door_2.object = cut_door_2
    cut_door_2.hide_render = True

# Door: door_3
bpy.ops.mesh.primitive_cube_add(size=1, location=(7.761, 5.343, 1.125))
cut_door_3 = bpy.context.active_object
cut_door_3.name = 'Cutter_door_3'
cut_door_3.scale = (0.9, 0.39, 2.25)
cut_door_3.rotation_euler[2] = 1.5707963267948966
cut_door_3.display_type = 'WIRE'
wall_target_door_3 = bpy.data.objects.get('Wall_wall_joined_82f488ad')
if wall_target_door_3:
    bool_mod_door_3 = wall_target_door_3.modifiers.new('Cut_door_3', 'BOOLEAN')
    bool_mod_door_3.operation = 'DIFFERENCE'
    bool_mod_door_3.object = cut_door_3
    cut_door_3.hide_render = True

# Door: door_4
bpy.ops.mesh.primitive_cube_add(size=1, location=(3.09075, 5.7525, 1.125))
cut_door_4 = bpy.context.active_object
cut_door_4.name = 'Cutter_door_4'
cut_door_4.scale = (0.9, 0.39, 2.25)
cut_door_4.rotation_euler[2] = 0.0
cut_door_4.display_type = 'WIRE'
wall_target_door_4 = bpy.data.objects.get('Wall_wall_joined_506d0659')
if wall_target_door_4:
    bool_mod_door_4 = wall_target_door_4.modifiers.new('Cut_door_4', 'BOOLEAN')
    bool_mod_door_4.operation = 'DIFFERENCE'
    bool_mod_door_4.object = cut_door_4
    cut_door_4.hide_render = True

# Door: door_5
bpy.ops.mesh.primitive_cube_add(size=1, location=(2.83725, 6.8055, 1.125))
cut_door_5 = bpy.context.active_object
cut_door_5.name = 'Cutter_door_5'
cut_door_5.scale = (0.9, 0.39, 2.25)
cut_door_5.rotation_euler[2] = 0.0
cut_door_5.display_type = 'WIRE'
wall_target_door_5 = bpy.data.objects.get('Wall_wall_joined_a3601c5c')
if wall_target_door_5:
    bool_mod_door_5 = wall_target_door_5.modifiers.new('Cut_door_5', 'BOOLEAN')
    bool_mod_door_5.operation = 'DIFFERENCE'
    bool_mod_door_5.object = cut_door_5
    cut_door_5.hide_render = True

# Window: window_1
bpy.ops.mesh.primitive_cube_add(size=1, location=(2.34, 2.379, 1.5))
cut_window_1 = bpy.context.active_object
cut_window_1.name = 'Cutter_window_1'
cut_window_1.scale = (1.2, 0.39, 1.2000000000000002)
cut_window_1.rotation_euler[2] = 0.0
cut_window_1.display_type = 'WIRE'
wall_target_window_1 = bpy.data.objects.get('Wall_wall_joined_1a19a0a2')
if wall_target_window_1:
    bool_mod_window_1 = wall_target_window_1.modifiers.new('Cut_window_1', 'BOOLEAN')
    bool_mod_window_1.operation = 'DIFFERENCE'
    bool_mod_window_1.object = cut_window_1
    cut_window_1.hide_render = True

# Window: window_2
bpy.ops.mesh.primitive_cube_add(size=1, location=(7.761, 6.6885, 1.5))
cut_window_2 = bpy.context.active_object
cut_window_2.name = 'Cutter_window_2'
cut_window_2.scale = (1.2, 0.39, 1.2000000000000002)
cut_window_2.rotation_euler[2] = 1.5707963267948966
cut_window_2.display_type = 'WIRE'
wall_target_window_2 = bpy.data.objects.get('Wall_wall_joined_82f488ad')
if wall_target_window_2:
    bool_mod_window_2 = wall_target_window_2.modifiers.new('Cut_window_2', 'BOOLEAN')
    bool_mod_window_2.operation = 'DIFFERENCE'
    bool_mod_window_2.object = cut_window_2
    cut_window_2.hide_render = True

# Window: window_3
bpy.ops.mesh.primitive_cube_add(size=1, location=(7.761, 8.0925, 1.5))
cut_window_3 = bpy.context.active_object
cut_window_3.name = 'Cutter_window_3'
cut_window_3.scale = (1.2, 0.39, 1.2000000000000002)
cut_window_3.rotation_euler[2] = 1.5707963267948966
cut_window_3.display_type = 'WIRE'
wall_target_window_3 = bpy.data.objects.get('Wall_wall_joined_82f488ad')
if wall_target_window_3:
    bool_mod_window_3 = wall_target_window_3.modifiers.new('Cut_window_3', 'BOOLEAN')
    bool_mod_window_3.operation = 'DIFFERENCE'
    bool_mod_window_3.object = cut_window_3
    cut_window_3.hide_render = True

# Window: window_4
bpy.ops.mesh.primitive_cube_add(size=1, location=(6.7177500000000006, 9.2625, 1.5))
cut_window_4 = bpy.context.active_object
cut_window_4.name = 'Cutter_window_4'
cut_window_4.scale = (1.2, 0.39, 1.2000000000000002)
cut_window_4.rotation_euler[2] = 0.0
cut_window_4.display_type = 'WIRE'
wall_target_window_4 = bpy.data.objects.get('Wall_wall_joined_aa3aad7e')
if wall_target_window_4:
    bool_mod_window_4 = wall_target_window_4.modifiers.new('Cut_window_4', 'BOOLEAN')
    bool_mod_window_4.operation = 'DIFFERENCE'
    bool_mod_window_4.object = cut_window_4
    cut_window_4.hide_render = True




# ── Furniture (Placeholder Cubes) ────────────────────────

# ── Materials ────────────────────────────────────────────
# Wall pattern: stacked_coils (WallMaterial)
if 'WallMaterial' in bpy.data.materials:
    bpy.data.materials.remove(bpy.data.materials['WallMaterial'])
mat = bpy.data.materials.new(name='WallMaterial')
mat.use_nodes = True
_tree = mat.node_tree
for _n in list(_tree.nodes):
    _tree.nodes.remove(_n)
nodes = _tree.nodes
links = _tree.links
wall_bsdf = nodes.new('ShaderNodeBsdfPrincipled')
wall_out = nodes.new('ShaderNodeOutputMaterial')
links.new(wall_bsdf.outputs['BSDF'], wall_out.inputs['Surface'])
wall_bsdf.location = (0, 0)
wall_out.location = (500, 0)
# 1) Pattern ridges (world-space horizontal bands, same colour via lighting)
_geo = nodes.new('ShaderNodeNewGeometry')
_hz_sep = nodes.new('ShaderNodeSeparateXYZ')
links.new(_geo.outputs['Position'], _hz_sep.inputs['Vector'])
_hz_scale = nodes.new('ShaderNodeMath')
_hz_scale.operation = 'MULTIPLY'
_hz_scale.inputs[1].default_value = 10.0
links.new(_hz_sep.outputs['Z'], _hz_scale.inputs[0])
_hz_vec = nodes.new('ShaderNodeCombineXYZ')
_hz_vec.inputs['X'].default_value = 0.0
_hz_vec.inputs['Y'].default_value = 0.0
links.new(_hz_scale.outputs['Value'], _hz_vec.inputs['Z'])
_hz_wave = nodes.new('ShaderNodeTexWave')
_hz_wave.wave_type = 'BANDS'
_hz_wave.bands_direction = 'Z'
_hz_wave.inputs['Scale'].default_value = 1.0
_hz_wave.inputs['Distortion'].default_value = 0.0
_hz_wave.inputs['Detail'].default_value = 0.0
links.new(_hz_vec.outputs['Vector'], _hz_wave.inputs['Vector'])
_ridge_ramp = nodes.new('ShaderNodeValToRGB')
_ridge_ramp.color_ramp.elements[0].position = 0.40
_ridge_ramp.color_ramp.elements.new(0.60)
_ridge_ramp.color_ramp.elements[1].position = 0.60
links.new(_hz_wave.outputs['Fac'], _ridge_ramp.inputs['Fac'])
wall_bump = nodes.new('ShaderNodeBump')
wall_bump.inputs['Strength'].default_value = 1.0
wall_bump.inputs['Distance'].default_value = 0.045
links.new(_ridge_ramp.outputs['Color'], wall_bump.inputs['Height'])
links.new(wall_bump.outputs['Normal'], wall_bsdf.inputs['Normal'])
# 2) Apply chosen wall colour
wall_bsdf.inputs['Base Color'].default_value = (0.20392156862745098, 0.28627450980392155, 0.3686274509803922, 1.0)
mat.diffuse_color = (0.20392156862745098, 0.28627450980392155, 0.3686274509803922, 1.0)
wall_bsdf.inputs['Roughness'].default_value = 0.78
wall_bsdf.inputs['Metallic'].default_value = 0.0

# Show materials in viewport (pattern is invisible in Solid shading)
for _win in bpy.context.window_manager.windows:
    for _area in _win.screen.areas:
        if _area.type == 'VIEW_3D':
            for _space in _area.spaces:
                if _space.type == 'VIEW_3D':
                    _space.shading.type = 'MATERIAL'
                    _space.shading.use_scene_lights = True

for obj in bpy.data.objects:
    if obj.name.startswith('Wall_'):
        if obj.type == 'MESH' and obj.data and hasattr(obj.data, 'materials'):
            obj.data.materials.clear()
            obj.data.materials.append(bpy.data.materials['WallMaterial'])
            obj.active_material_index = 0

if 'FloorMaterial' in bpy.data.materials:
    bpy.data.materials.remove(bpy.data.materials['FloorMaterial'])
mat = bpy.data.materials.new(name='FloorMaterial')
mat.diffuse_color = (0.6549019607843137, 0.47843137254901963, 0.3137254901960784, 1.0)
mat.use_nodes = True
_tree = mat.node_tree
for _n in list(_tree.nodes):
    _tree.nodes.remove(_n)
_bsdf = _tree.nodes.new('ShaderNodeBsdfPrincipled')
_out = _tree.nodes.new('ShaderNodeOutputMaterial')
_tree.links.new(_bsdf.outputs['BSDF'], _out.inputs['Surface'])
_bsdf.location = (0, 0)
_out.location = (300, 0)
_bsdf.inputs['Base Color'].default_value = (0.6549019607843137, 0.47843137254901963, 0.3137254901960784, 1.0)
_bsdf.inputs['Roughness'].default_value = 0.55
_bsdf.inputs['Metallic'].default_value = 0.0

for obj in bpy.data.objects:
    if obj.name.startswith('Floor_') or obj.name == 'BasePlate':
        if obj.type == 'MESH' and obj.data and hasattr(obj.data, 'materials'):
            obj.data.materials.clear()
            obj.data.materials.append(bpy.data.materials['FloorMaterial'])
            obj.active_material_index = 0

if 'CeilingMaterial' in bpy.data.materials:
    bpy.data.materials.remove(bpy.data.materials['CeilingMaterial'])
mat = bpy.data.materials.new(name='CeilingMaterial')
mat.diffuse_color = (0.93, 0.93, 0.9, 1.0)
mat.use_nodes = True
_tree = mat.node_tree
for _n in list(_tree.nodes):
    _tree.nodes.remove(_n)
_bsdf = _tree.nodes.new('ShaderNodeBsdfPrincipled')
_out = _tree.nodes.new('ShaderNodeOutputMaterial')
_tree.links.new(_bsdf.outputs['BSDF'], _out.inputs['Surface'])
_bsdf.location = (0, 0)
_out.location = (300, 0)
_bsdf.inputs['Base Color'].default_value = (0.93, 0.93, 0.9, 1.0)
_bsdf.inputs['Roughness'].default_value = 0.9
_bsdf.inputs['Metallic'].default_value = 0.0

for obj in bpy.data.objects:
    if obj.name.startswith('Ceiling_'):
        if obj.type == 'MESH' and obj.data and hasattr(obj.data, 'materials'):
            obj.data.materials.clear()
            obj.data.materials.append(bpy.data.materials['CeilingMaterial'])
            obj.active_material_index = 0


# ── Lighting ─────────────────────────────────────────────
bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))
sun = bpy.context.active_object
sun.name = 'Sun_Light'
sun.data.energy = 3.0
sun.rotation_euler = (0.7853975, 0, 0.7853975)


# ── Cameras ──────────────────────────────────────────────
# Camera 1: Top-down (plan view)
bpy.ops.object.camera_add(location=(4.31925, 5.2162500000000005, 13.131499999999999))
cam_top = bpy.context.active_object
cam_top.name = 'Camera_TopDown'
cam_top.rotation_euler = (0, 0, 0)
cam_top.data.type = 'ORTHO'
cam_top.data.ortho_scale = 9.757799999999998

# Camera 2: Perspective (exterior corner view)
bpy.ops.object.camera_add(location=(9.198149999999998, 0.3373500000000016, 4.0657499999999995))
cam_persp = bpy.context.active_object
cam_persp.name = 'Camera_Perspective'
cam_persp.data.type = 'PERSP'
cam_persp.data.lens = 35
import mathutils
cam_persp.rotation_euler = mathutils.Euler((1.047, 0, 0.785), 'XYZ')

# Camera 3: Walkthrough (first-person, inside first room)
bpy.ops.object.camera_add(location=(6.475182651622004, 1.7786071932299015, 1.6))
cam_walk = bpy.context.active_object
cam_walk.name = 'Camera_Walkthrough'
cam_walk.data.type = 'PERSP'
cam_walk.data.lens = 24

bpy.context.scene.camera = bpy.data.objects['Camera_TopDown']


# ── Export ───────────────────────────────────────────────
import os as _os
_os.makedirs(r'C:\Users\Abdullah\Documents\3d\floorplan-3d-backend\output', exist_ok=True)

bpy.ops.export_scene.gltf(
    filepath=r'C:/Users/Abdullah/Documents/3d/floorplan-3d-backend/output/building.glb',
    export_format='GLB',
    export_apply=True,
    export_materials='EXPORT',
)
print('Exported GLB ->', r'C:/Users/Abdullah/Documents/3d/floorplan-3d-backend/output/building.glb')

bpy.ops.wm.save_as_mainfile(filepath=r'C:/Users/Abdullah/Documents/3d/floorplan-3d-backend/output/building.blend')
print('Saved .blend ->', r'C:/Users/Abdullah/Documents/3d/floorplan-3d-backend/output/building.blend')




# ── Origin Centring ─────────────────────────────────────────────────
# Bake every geometry object's scale into its mesh, then recompute the bbox
# in world space and translate the entire scene so the base centre sits at
# the world origin. This makes the result robust to any base-plate padding
# or scale changes upstream.
for _obj in bpy.data.objects:
    if _obj.type == 'CAMERA' or _obj.type == 'LIGHT':
        continue
    if _obj.data and hasattr(_obj.data, 'vertices'):
        try:
            bpy.context.view_layer.objects.active = _obj
            _obj.select_set(True)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        except Exception:
            pass
        _obj.select_set(False)

_min_x, _min_y, _min_z = 1e30, 1e30, 1e30
_max_x, _max_y, _max_z = -1e30, -1e30, -1e30
for _obj in bpy.data.objects:
    if _obj.type == 'CAMERA' or _obj.type == 'LIGHT':
        continue
    if not _obj.data or not hasattr(_obj.data, 'vertices'):
        continue
    for _v in _obj.data.vertices:
        _w = _obj.matrix_world @ _v.co
        if _w.x < _min_x: _min_x = _w.x
        if _w.y < _min_y: _min_y = _w.y
        if _w.z < _min_z: _min_z = _w.z
        if _w.x > _max_x: _max_x = _w.x
        if _w.y > _max_y: _max_y = _w.y
        if _w.z > _max_z: _max_z = _w.z
if _min_x <= _max_x:
    _cx = (_min_x + _max_x) / 2.0
    _cy = (_min_y + _max_y) / 2.0
    _cz = _min_z
    _span = max(_max_x - _min_x, _max_y - _min_y, 1.0)
    for _obj in bpy.data.objects:
        if _obj.type == 'CAMERA' or _obj.type == 'LIGHT':
            continue
        _obj.location.x -= _cx
        _obj.location.y -= _cy
        _obj.location.z -= _cz
    for _obj in bpy.data.objects:
        if _obj.type == 'CAMERA':
            _obj.location.x -= _cx
            _obj.location.y -= _cy
            if _obj.data and _obj.data.type == 'ORTHO' and 'TopDown' in _obj.name:
                _obj.data.ortho_scale = _span * 1.2



print('Script complete.')
