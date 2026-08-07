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



# ── Floors (per-room) ─────────────────────────────────────
# Floor: room
floor_verts_room_b6b18900 = [(5.2845, 2.2815, -0.2), (5.304, 1.248, -0.2), (7.683, 1.287, -0.2), (7.644, 2.301, -0.2)]
floor_faces_room_b6b18900 = [[0, 1, 2], [0, 2, 3]]
floor_mesh_room_b6b18900 = bpy.data.meshes.new('Floor_room_b6b18900')
floor_mesh_room_b6b18900.from_pydata(floor_verts_room_b6b18900, [], floor_faces_room_b6b18900)
floor_mesh_room_b6b18900.update()
floor_obj_room_b6b18900 = bpy.data.objects.new('Floor_room_b6b18900', floor_mesh_room_b6b18900)
bpy.context.collection.objects.link(floor_obj_room_b6b18900)
floor_mod_room_b6b18900 = floor_obj_room_b6b18900.modifiers.new('Solidify', 'SOLIDIFY')
floor_mod_room_b6b18900.thickness = 0.2
floor_mod_room_b6b18900.offset = -1.0

# Floor: room
floor_verts_room_55494881 = [(0.9945, 8.0145, -0.2), (0.9945, 6.357, -0.2), (2.028, 6.3375, -0.2), (2.0085, 6.1035, -0.2), (0.975, 6.1425, -0.2), (1.014, 2.4765, -0.2), (3.5685, 2.4765, -0.2), (3.627, 2.7885, -0.2), (3.7635, 2.769, -0.2), (3.783, 2.535, -0.2), (7.6635, 2.4765, -0.2), (7.6635, 9.1455, -0.2), (3.4515, 9.165, -0.2), (3.315, 7.9755, -0.2)]
floor_faces_room_55494881 = [[0, 4, 5], [0, 5, 6], [0, 6, 10], [0, 10, 11], [0, 11, 12]]
floor_mesh_room_55494881 = bpy.data.meshes.new('Floor_room_55494881')
floor_mesh_room_55494881.from_pydata(floor_verts_room_55494881, [], floor_faces_room_55494881)
floor_mesh_room_55494881.update()
floor_obj_room_55494881 = bpy.data.objects.new('Floor_room_55494881', floor_mesh_room_55494881)
bpy.context.collection.objects.link(floor_obj_room_55494881)
floor_mod_room_55494881 = floor_obj_room_55494881.modifiers.new('Solidify', 'SOLIDIFY')
floor_mod_room_55494881.thickness = 0.2
floor_mod_room_55494881.offset = -1.0


# ── Walls ───────────────────────────────────────────────
# 10 corner posts at wall junctions (flush with wall)
# Wall: wall_joined_418cd61b  (length=6.817m ocr=6.817m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(4.3184455, 2.436604, 1.5)
)
wall_obj_wall_joined_418cd61b = bpy.context.active_object
wall_obj_wall_joined_418cd61b.name = 'Wall_wall_joined_418cd61b'
wall_obj_wall_joined_418cd61b.scale = (7.011891, 0.195, 3.0)
wall_obj_wall_joined_418cd61b.rotation_euler[2] = 0.0
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_e722bb35  (length=7.849m ocr=7.849m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(7.743945500000001, 5.143125, 1.5)
)
wall_obj_wall_joined_e722bb35 = bpy.context.active_object
wall_obj_wall_joined_e722bb35.name = 'Wall_wall_joined_e722bb35'
wall_obj_wall_joined_e722bb35.scale = (8.043750000000001, 0.195, 3.0)
wall_obj_wall_joined_e722bb35.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_952a6cd6  (length=5.545m ocr=5.545m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(0.88725, 5.2421665, 1.5)
)
wall_obj_wall_joined_952a6cd6 = bpy.context.active_object
wall_obj_wall_joined_952a6cd6.name = 'Wall_wall_joined_952a6cd6'
wall_obj_wall_joined_952a6cd6.scale = (5.739667000000001, 0.195, 3.0)
wall_obj_wall_joined_952a6cd6.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_56653c97  (length=4.381m ocr=4.381m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(5.5639915, 9.264937499999998, 1.5)
)
wall_obj_wall_joined_56653c97 = bpy.context.active_object
wall_obj_wall_joined_56653c97.name = 'Wall_wall_joined_56653c97'
wall_obj_wall_joined_56653c97.scale = (4.576017, 0.195, 3.0)
wall_obj_wall_joined_56653c97.rotation_euler[2] = 0.0
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_e40e0808  (length=3.362m ocr=3.362m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(3.6586875, 4.0844375, 1.5)
)
wall_obj_wall_joined_e40e0808 = bpy.context.active_object
wall_obj_wall_joined_e40e0808.name = 'Wall_wall_joined_e40e0808'
wall_obj_wall_joined_e40e0808.scale = (3.557125, 0.195, 3.0)
wall_obj_wall_joined_e40e0808.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_b4bd96ae  (length=2.370m ocr=2.370m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(2.071875, 8.0510625, 1.5)
)
wall_obj_wall_b4bd96ae = bpy.context.active_object
wall_obj_wall_b4bd96ae.name = 'Wall_wall_b4bd96ae'
wall_obj_wall_b4bd96ae.scale = (2.565378203604859, 0.195, 3.0)
wall_obj_wall_b4bd96ae.rotation_euler[2] = 0.030854402730525775
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_eb8c1742  (length=2.574m ocr=2.574m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(6.4545, 1.1895, 1.5)
)
wall_obj_wall_joined_eb8c1742 = bpy.context.active_object
wall_obj_wall_joined_eb8c1742.name = 'Wall_wall_joined_eb8c1742'
wall_obj_wall_joined_eb8c1742.scale = (2.7689999999999997, 0.195, 3.0)
wall_obj_wall_joined_eb8c1742.rotation_euler[2] = 0.0
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_b9003765  (length=2.473m ocr=2.473m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(3.3149914999999996, 8.042125, 1.5)
)
wall_obj_wall_joined_b9003765 = bpy.context.active_object
wall_obj_wall_joined_b9003765.name = 'Wall_wall_joined_b9003765'
wall_obj_wall_joined_b9003765.scale = (2.66825, 0.195, 3.0)
wall_obj_wall_joined_b9003765.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_76dbe59a  (length=1.297m ocr=1.297m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(2.6081250000000002, 6.815250000000001, 1.5)
)
wall_obj_wall_joined_76dbe59a = bpy.context.active_object
wall_obj_wall_joined_76dbe59a.name = 'Wall_wall_joined_76dbe59a'
wall_obj_wall_joined_76dbe59a.scale = (1.49175, 0.195, 3.0)
wall_obj_wall_joined_76dbe59a.rotation_euler[2] = 0.0
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_d8fde741  (length=1.614m ocr=1.614m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(2.8396875, 5.7611705, 1.5)
)
wall_obj_wall_joined_d8fde741 = bpy.context.active_object
wall_obj_wall_joined_d8fde741.name = 'Wall_wall_joined_d8fde741'
wall_obj_wall_joined_d8fde741.scale = (1.808625, 0.195, 3.0)
wall_obj_wall_joined_d8fde741.rotation_euler[2] = 0.0
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_ec62e23c  (length=1.212m ocr=1.212m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(5.2585, 1.766375, 1.5)
)
wall_obj_wall_joined_ec62e23c = bpy.context.active_object
wall_obj_wall_joined_ec62e23c.name = 'Wall_wall_joined_ec62e23c'
wall_obj_wall_joined_ec62e23c.scale = (1.4072500000000001, 0.195, 3.0)
wall_obj_wall_joined_ec62e23c.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_e24cdb68  (length=1.048m ocr=1.048m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(1.418625, 6.23422, 1.5)
)
wall_obj_wall_e24cdb68 = bpy.context.active_object
wall_obj_wall_e24cdb68.name = 'Wall_wall_e24cdb68'
wall_obj_wall_e24cdb68.scale = (1.2426775570069257, 0.195, 3.0)
wall_obj_wall_e24cdb68.rotation_euler[2] = 0.1823043723279953
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Wall: wall_joined_4c62a868  (length=1.065m ocr=1.065m)
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(1.9467665, 6.2925455, 1.5)
)
wall_obj_wall_joined_4c62a868 = bpy.context.active_object
wall_obj_wall_joined_4c62a868.name = 'Wall_wall_joined_4c62a868'
wall_obj_wall_joined_4c62a868.scale = (1.2599090000000002, 0.195, 3.0)
wall_obj_wall_joined_4c62a868.rotation_euler[2] = 1.5707963267948966
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Corner post at (0.937, 2.461) — 2 wall(s), 1 room vertex
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(0.9371, 2.4610, 1.5)
)
post_obj_p1 = bpy.context.active_object
post_obj_p1.name = 'WallPost_p1'
post_obj_p1.scale = (0.19666666666666668, 0.19666666666666668, 3.05)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Corner post at (7.723, 1.232) — 2 wall(s), 1 room vertex
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(7.7228, 1.2317, 1.5)
)
post_obj_p2 = bpy.context.active_object
post_obj_p2.name = 'WallPost_p2'
post_obj_p2.scale = (0.19666666666666668, 0.19666666666666668, 3.05)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Corner post at (7.721, 9.159) — 2 wall(s), 1 room vertex
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(7.7206, 9.1593, 1.5)
)
post_obj_p3 = bpy.context.active_object
post_obj_p3.name = 'WallPost_p3'
post_obj_p3.scale = (0.19666666666666668, 0.19666666666666668, 3.05)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Corner post at (0.923, 8.014) — 2 wall(s), 1 room vertex
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(0.9230, 8.0145, 1.5)
)
post_obj_p4 = bpy.context.active_object
post_obj_p4.name = 'WallPost_p4'
post_obj_p4.scale = (0.19666666666666668, 0.19666666666666668, 3.05)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Corner post at (3.380, 9.236) — 2 wall(s), 1 room vertex
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(3.3800, 9.2362, 1.5)
)
post_obj_p5 = bpy.context.active_object
post_obj_p5.name = 'WallPost_p5'
post_obj_p5.scale = (0.19666666666666668, 0.19666666666666668, 3.05)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Corner post at (3.653, 5.763) — 2 wall(s), 0 room vertex
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(3.6526, 5.7633, 1.5)
)
post_obj_p6 = bpy.context.active_object
post_obj_p6.name = 'WallPost_p6'
post_obj_p6.scale = (0.195, 0.195, 3.05)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Corner post at (5.243, 1.199) — 2 wall(s), 1 room vertex
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(5.2433, 1.1993, 1.5)
)
post_obj_p7 = bpy.context.active_object
post_obj_p7.name = 'WallPost_p7'
post_obj_p7.scale = (0.19666666666666668, 0.19666666666666668, 3.05)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Corner post at (3.286, 6.810) — 2 wall(s), 0 room vertex
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(3.2857, 6.8104, 1.5)
)
post_obj_p8 = bpy.context.active_object
post_obj_p8.name = 'WallPost_p8'
post_obj_p8.scale = (0.195, 0.195, 3.05)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Corner post at (1.953, 6.820) — 2 wall(s), 0 room vertex
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(1.9533, 6.8201, 1.5)
)
post_obj_p9 = bpy.context.active_object
post_obj_p9.name = 'WallPost_p9'
post_obj_p9.scale = (0.195, 0.195, 3.05)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Corner post at (1.990, 5.761) — 2 wall(s), 0 room vertex
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(1.9898, 5.7606, 1.5)
)
post_obj_p10 = bpy.context.active_object
post_obj_p10.name = 'WallPost_p10'
post_obj_p10.scale = (0.195, 0.195, 3.05)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


# ── Openings (Doors & Windows) ───────────────────────────
# Door: door_1
bpy.ops.mesh.primitive_cube_add(size=1, location=(5.2585, 1.74525, 1.125))
cut_door_1 = bpy.context.active_object
cut_door_1.name = 'Cutter_door_1'
cut_door_1.scale = (0.9, 0.39, 2.25)
cut_door_1.rotation_euler[2] = 1.5707963267948966
cut_door_1.display_type = 'WIRE'
wall_target_door_1 = bpy.data.objects.get('Wall_wall_joined_ec62e23c')
if wall_target_door_1:
    bool_mod_door_1 = wall_target_door_1.modifiers.new('Cut_door_1', 'BOOLEAN')
    bool_mod_door_1.operation = 'DIFFERENCE'
    bool_mod_door_1.object = cut_door_1
    cut_door_1.hide_render = True

# Door: door_2
bpy.ops.mesh.primitive_cube_add(size=1, location=(6.747, 2.436604, 1.125))
cut_door_2 = bpy.context.active_object
cut_door_2.name = 'Cutter_door_2'
cut_door_2.scale = (0.9, 0.39, 2.25)
cut_door_2.rotation_euler[2] = 0.0
cut_door_2.display_type = 'WIRE'
wall_target_door_2 = bpy.data.objects.get('Wall_wall_joined_418cd61b')
if wall_target_door_2:
    bool_mod_door_2 = wall_target_door_2.modifiers.new('Cut_door_2', 'BOOLEAN')
    bool_mod_door_2.operation = 'DIFFERENCE'
    bool_mod_door_2.object = cut_door_2
    cut_door_2.hide_render = True

# Door: door_3
bpy.ops.mesh.primitive_cube_add(size=1, location=(7.743945500000001, 5.342999999999999, 1.125))
cut_door_3 = bpy.context.active_object
cut_door_3.name = 'Cutter_door_3'
cut_door_3.scale = (0.9, 0.39, 2.25)
cut_door_3.rotation_euler[2] = 1.5707963267948966
cut_door_3.display_type = 'WIRE'
wall_target_door_3 = bpy.data.objects.get('Wall_wall_joined_e722bb35')
if wall_target_door_3:
    bool_mod_door_3 = wall_target_door_3.modifiers.new('Cut_door_3', 'BOOLEAN')
    bool_mod_door_3.operation = 'DIFFERENCE'
    bool_mod_door_3.object = cut_door_3
    cut_door_3.hide_render = True

# Door: door_4
bpy.ops.mesh.primitive_cube_add(size=1, location=(3.09075, 5.7611705, 1.125))
cut_door_4 = bpy.context.active_object
cut_door_4.name = 'Cutter_door_4'
cut_door_4.scale = (0.9, 0.39, 2.25)
cut_door_4.rotation_euler[2] = 0.0
cut_door_4.display_type = 'WIRE'
wall_target_door_4 = bpy.data.objects.get('Wall_wall_joined_d8fde741')
if wall_target_door_4:
    bool_mod_door_4 = wall_target_door_4.modifiers.new('Cut_door_4', 'BOOLEAN')
    bool_mod_door_4.operation = 'DIFFERENCE'
    bool_mod_door_4.object = cut_door_4
    cut_door_4.hide_render = True

# Door: door_5
bpy.ops.mesh.primitive_cube_add(size=1, location=(2.83725, 6.815250000000001, 1.125))
cut_door_5 = bpy.context.active_object
cut_door_5.name = 'Cutter_door_5'
cut_door_5.scale = (0.9, 0.39, 2.25)
cut_door_5.rotation_euler[2] = 0.0
cut_door_5.display_type = 'WIRE'
wall_target_door_5 = bpy.data.objects.get('Wall_wall_joined_76dbe59a')
if wall_target_door_5:
    bool_mod_door_5 = wall_target_door_5.modifiers.new('Cut_door_5', 'BOOLEAN')
    bool_mod_door_5.operation = 'DIFFERENCE'
    bool_mod_door_5.object = cut_door_5
    cut_door_5.hide_render = True

# Window: window_1
bpy.ops.mesh.primitive_cube_add(size=1, location=(2.3399999999999994, 2.436604, 1.5))
cut_window_1 = bpy.context.active_object
cut_window_1.name = 'Cutter_window_1'
cut_window_1.scale = (1.2, 0.39, 1.2000000000000002)
cut_window_1.rotation_euler[2] = 0.0
cut_window_1.display_type = 'WIRE'
wall_target_window_1 = bpy.data.objects.get('Wall_wall_joined_418cd61b')
if wall_target_window_1:
    bool_mod_window_1 = wall_target_window_1.modifiers.new('Cut_window_1', 'BOOLEAN')
    bool_mod_window_1.operation = 'DIFFERENCE'
    bool_mod_window_1.object = cut_window_1
    cut_window_1.hide_render = True

# Window: window_2
bpy.ops.mesh.primitive_cube_add(size=1, location=(7.743945500000001, 6.6885, 1.5))
cut_window_2 = bpy.context.active_object
cut_window_2.name = 'Cutter_window_2'
cut_window_2.scale = (1.2, 0.39, 1.2000000000000002)
cut_window_2.rotation_euler[2] = 1.5707963267948966
cut_window_2.display_type = 'WIRE'
wall_target_window_2 = bpy.data.objects.get('Wall_wall_joined_e722bb35')
if wall_target_window_2:
    bool_mod_window_2 = wall_target_window_2.modifiers.new('Cut_window_2', 'BOOLEAN')
    bool_mod_window_2.operation = 'DIFFERENCE'
    bool_mod_window_2.object = cut_window_2
    cut_window_2.hide_render = True

# Window: window_3
bpy.ops.mesh.primitive_cube_add(size=1, location=(7.743945500000001, 8.092499999999998, 1.5))
cut_window_3 = bpy.context.active_object
cut_window_3.name = 'Cutter_window_3'
cut_window_3.scale = (1.2, 0.39, 1.2000000000000002)
cut_window_3.rotation_euler[2] = 1.5707963267948966
cut_window_3.display_type = 'WIRE'
wall_target_window_3 = bpy.data.objects.get('Wall_wall_joined_e722bb35')
if wall_target_window_3:
    bool_mod_window_3 = wall_target_window_3.modifiers.new('Cut_window_3', 'BOOLEAN')
    bool_mod_window_3.operation = 'DIFFERENCE'
    bool_mod_window_3.object = cut_window_3
    cut_window_3.hide_render = True

# Window: window_4
bpy.ops.mesh.primitive_cube_add(size=1, location=(6.71775, 9.264937499999998, 1.5))
cut_window_4 = bpy.context.active_object
cut_window_4.name = 'Cutter_window_4'
cut_window_4.scale = (1.2, 0.39, 1.2000000000000002)
cut_window_4.rotation_euler[2] = 0.0
cut_window_4.display_type = 'WIRE'
wall_target_window_4 = bpy.data.objects.get('Wall_wall_joined_56653c97')
if wall_target_window_4:
    bool_mod_window_4 = wall_target_window_4.modifiers.new('Cut_window_4', 'BOOLEAN')
    bool_mod_window_4.operation = 'DIFFERENCE'
    bool_mod_window_4.object = cut_window_4
    cut_window_4.hide_render = True




# ── Furniture (Placeholder Cubes) ────────────────────────

# ── Materials ────────────────────────────────────────────
# Wall pattern: none (WallMaterial)
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
# 2) Apply chosen wall colour
wall_bsdf.inputs['Base Color'].default_value = (0.8470588235294118, 0.7843137254901961, 0.7215686274509804, 1.0)
mat.diffuse_color = (0.8470588235294118, 0.7843137254901961, 0.7215686274509804, 1.0)
wall_bsdf.inputs['Roughness'].default_value = 0.82
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

for obj in bpy.data.objects:
    if obj.name.startswith('WallPost_'):
        if obj.type == 'MESH' and obj.data and hasattr(obj.data, 'materials'):
            obj.data.materials.clear()
            obj.data.materials.append(bpy.data.materials['WallMaterial'])
            obj.active_material_index = 0

if 'FloorMaterial' in bpy.data.materials:
    bpy.data.materials.remove(bpy.data.materials['FloorMaterial'])
mat = bpy.data.materials.new(name='FloorMaterial')
mat.diffuse_color = (0.9098039215686274, 0.8901960784313725, 0.8509803921568627, 1.0)
mat.use_nodes = True
_tree = mat.node_tree
for _n in list(_tree.nodes):
    _tree.nodes.remove(_n)
_bsdf = _tree.nodes.new('ShaderNodeBsdfPrincipled')
_out = _tree.nodes.new('ShaderNodeOutputMaterial')
_tree.links.new(_bsdf.outputs['BSDF'], _out.inputs['Surface'])
_bsdf.location = (0, 0)
_out.location = (300, 0)
_bsdf.inputs['Base Color'].default_value = (0.9098039215686274, 0.8901960784313725, 0.8509803921568627, 1.0)
_bsdf.inputs['Roughness'].default_value = 0.55
_bsdf.inputs['Metallic'].default_value = 0.0

_tree = mat.node_tree
for _n in list(_tree.nodes):
    _tree.nodes.remove(_n)
floor_bsdf = _tree.nodes.new('ShaderNodeBsdfPrincipled')
_out = _tree.nodes.new('ShaderNodeOutputMaterial')
_tree.links.new(floor_bsdf.outputs['BSDF'], _out.inputs['Surface'])
floor_bsdf.location = (0, 0)
_out.location = (400, 0)
nodes = mat.node_tree.nodes
links = mat.node_tree.links
texcoord = nodes.new('ShaderNodeTexCoord')
mapping = nodes.new('ShaderNodeMapping')
mapping.inputs['Scale'].default_value = (2.5, 2.5, 2.5)
links.new(texcoord.outputs['Object'], mapping.inputs['Vector'])
tiles = nodes.new('ShaderNodeTexBrick')
tiles.inputs['Color1'].default_value = (0.9098039215686274, 0.8901960784313725, 0.8509803921568627, 1.0)
tiles.inputs['Color2'].default_value = (0.7215686274509804, 0.7098039215686275, 0.6823529411764706, 1.0)
tiles.inputs['Mortar'].default_value = (0.6588235294117647, 0.6431372549019608, 0.611764705882353, 1.0)
tiles.inputs['Mortar Size'].default_value = 0.025
tiles.offset = 0.0
tiles.offset_frequency = 1
tiles.squash = 1.0
links.new(mapping.outputs['Vector'], tiles.inputs['Vector'])
links.new(tiles.outputs['Color'], floor_bsdf.inputs['Base Color'])
bump = nodes.new('ShaderNodeBump')
bump.inputs['Strength'].default_value = 0.12
bump.inputs['Distance'].default_value = 0.02
links.new(tiles.outputs['Fac'], bump.inputs['Height'])
links.new(bump.outputs['Normal'], floor_bsdf.inputs['Normal'])

for obj in bpy.data.objects:
    if obj.name.startswith('Floor_'):
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
bpy.ops.object.camera_add(location=(4.320875, 5.2195, 13.118500000000001))
cam_top = bpy.context.active_object
cam_top.name = 'Camera_TopDown'
cam_top.rotation_euler = (0, 0, 0)
cam_top.data.type = 'ORTHO'
cam_top.data.ortho_scale = 9.7422

# Camera 2: Perspective (exterior corner view)
bpy.ops.object.camera_add(location=(9.191975, 0.3483999999999998, 4.0592500000000005))
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




# ── Apply Boolean modifiers before scale baking ─────────────────────
# Step 1: Apply scale on all Cutter objects first so their geometry
#         is correctly sized before the Boolean operation executes.
for _obj in bpy.data.objects:
    if _obj.type != 'MESH':
        continue
    if not _obj.name.startswith('Cutter_'):
        continue
    bpy.context.view_layer.objects.active = _obj
    _obj.select_set(True)
    try:
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    except Exception:
        pass
    _obj.select_set(False)

# Step 2: Apply all pending Boolean modifiers on wall objects so the
#         openings are permanently cut into the mesh before export.
for _obj in bpy.data.objects:
    if _obj.type != 'MESH':
        continue
    if _obj.name.startswith('Cutter_'):
        continue
    _bool_mods = [m for m in _obj.modifiers if m.type == 'BOOLEAN']
    if not _bool_mods:
        continue
    bpy.context.view_layer.objects.active = _obj
    _obj.select_set(True)
    for _mod in _bool_mods:
        try:
            bpy.ops.object.modifier_apply(modifier=_mod.name)
        except Exception:
            pass
    _obj.select_set(False)

# Step 3: Hide cutter objects from viewport and render (they are consumed)
for _obj in bpy.data.objects:
    if _obj.name.startswith('Cutter_'):
        _obj.hide_viewport = True
        _obj.hide_render = True

# ── Origin Centring ─────────────────────────────────────────────────
# Bake every geometry object's scale into its mesh, then recompute the bbox
# in world space and translate the entire scene so the base centre sits at
# the world origin. This makes the result robust to any base-plate padding
# or scale changes upstream.
for _obj in bpy.data.objects:
    if _obj.type == 'CAMERA' or _obj.type == 'LIGHT':
        continue
    if _obj.name.startswith('Cutter_'):
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
    if _obj.name.startswith('Cutter_'):
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
