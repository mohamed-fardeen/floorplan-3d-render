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
base_verts = [(-2.0, -0.05974999999999997, -0.2), (11.789, -0.05974999999999997, -0.2), (11.789, 7.889, -0.2), (-2.0, 7.889, -0.2)]
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
# Wall: wall_2195e4d3  (length=9.789m, thickness=3.841m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(4.8945, 1.94025, 1.5)
)
wall_obj_wall_2195e4d3 = bpy.context.active_object
wall_obj_wall_2195e4d3.name = 'Wall_wall_2195e4d3'
wall_obj_wall_2195e4d3.scale = (9.789, 3.8415, 3.0)
wall_obj_wall_2195e4d3.rotation_euler[2] = 0.0
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_62527ee4  (length=2.769m, thickness=1.190m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(9.19425, 4.5045, 1.5)
)
wall_obj_wall_62527ee4 = bpy.context.active_object
wall_obj_wall_62527ee4.name = 'Wall_wall_62527ee4'
wall_obj_wall_62527ee4.scale = (2.769, 1.1895, 3.0)
wall_obj_wall_62527ee4.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_0aa0f0b6  (length=4.934m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(4.57275, 5.85, 1.5)
)
wall_obj_wall_0aa0f0b6 = bpy.context.active_object
wall_obj_wall_0aa0f0b6.name = 'Wall_wall_0aa0f0b6'
wall_obj_wall_0aa0f0b6.scale = (4.9335, 0.195, 3.0)
wall_obj_wall_0aa0f0b6.rotation_euler[2] = 0.0
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_ec1dc1cb  (length=0.839m, thickness=0.195m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(0.41925, 5.84025, 1.5)
)
wall_obj_wall_ec1dc1cb = bpy.context.active_object
wall_obj_wall_ec1dc1cb.name = 'Wall_wall_ec1dc1cb'
wall_obj_wall_ec1dc1cb.scale = (0.8385, 0.195, 3.0)
wall_obj_wall_ec1dc1cb.rotation_euler[2] = 0.0
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


# ── Openings (Doors & Windows) ───────────────────────────
# Window: window_1
bpy.ops.mesh.primitive_cube_add(size=1, location=(2.05725, 1.94025, 1.5))
cut_window_1 = bpy.context.active_object
cut_window_1.name = 'Cutter_window_1'
cut_window_1.scale = (1.2, 7.683, 1.2000000000000002)
cut_window_1.rotation_euler[2] = 0.0
cut_window_1.display_type = 'WIRE'
wall_target_window_1 = bpy.data.objects.get('Wall_wall_2195e4d3')
if wall_target_window_1:
    bool_mod_window_1 = wall_target_window_1.modifiers.new('Cut_window_1', 'BOOLEAN')
    bool_mod_window_1.operation = 'DIFFERENCE'
    bool_mod_window_1.object = cut_window_1
    cut_window_1.hide_render = True


# ── Ceilings ─────────────────────────────────────────────

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
bpy.ops.object.camera_add(location=(4.8945, 3.914625, 14.789))
cam_top = bpy.context.active_object
cam_top.name = 'Camera_TopDown'
cam_top.rotation_euler = (0, 0, 0)
cam_top.data.type = 'ORTHO'
cam_top.data.ortho_scale = 11.746799999999999

# Camera 2: Perspective (exterior corner view)
bpy.ops.object.camera_add(location=(15.662399999999998, -3.9331499999999995, 4.8945))
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
    filepath=r'C:/Users/Abdullah/Documents/3d/floorplan-3d-backend/output/building.glb',
    export_format='GLB',
    export_apply=True
)
print('Exported GLB ->', r'C:/Users/Abdullah/Documents/3d/floorplan-3d-backend/output/building.glb')



print('Script complete.')
