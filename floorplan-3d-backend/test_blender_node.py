"""
test_blender_node.py
Tests the script builder end-to-end without requiring Blender to be installed.
We verify that the generated Python is valid and contains the expected sections.
"""
import ast
import os
import tempfile

from schema import SceneGraph, Wall, Room, Door, Window, Metadata, OCRDetection
from blender.script_builder import build_script

# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

BASE_CFG = {
    "building": {"wall_height": 3.0, "wall_thickness_default": 0.15,
                 "floor_thickness": 0.20, "ceiling_enabled": True},
    "materials": {"walls": "painted_white", "floor": "oak_wood", "ceiling": "plaster_white"},
    "assets": {"bedroom": ["bed_double", "wardrobe"]},
    "lighting": {"enable_sun": True, "sun_strength": 3.0, "sun_angle_deg": 45,
                 "enable_hdri": False, "enable_interior_lights": False},
    "export": {"formats": ["glb"], "output_dir": "output"},
}

def one_room_scene(room_type="Bedroom") -> SceneGraph:
    sg = SceneGraph(metadata=Metadata(project_name="TestProject"))
    sg.walls.append(Wall(id="w1", start=(0,0), end=(5,0)))
    sg.walls.append(Wall(id="w2", start=(5,0), end=(5,5)))
    sg.walls.append(Wall(id="w3", start=(5,5), end=(0,5)))
    sg.walls.append(Wall(id="w4", start=(0,5), end=(0,0)))
    sg.rooms.append(Room(id="r1", type=room_type, label=room_type,
                         polygon=[(0,0),(5,0),(5,5),(0,5)],
                         area=25.0, centroid=(2.5, 2.5)))
    return sg

def two_bedroom_scene() -> SceneGraph:
    sg = SceneGraph(metadata=Metadata(project_name="TwoBedroom"))
    sg.walls += [Wall(id=f"w{i}", start=s, end=e) for i,(s,e) in enumerate([
        ((0,0),(10,0)), ((10,0),(10,5)), ((10,5),(0,5)), ((0,5),(0,0)),
        ((5,0),(5,5)),
    ])]
    sg.doors.append(Door(id="d1", wall_id="w4", center=(0,2.5), width=0.9))
    sg.rooms += [
        Room(id="r1", type="Bedroom",   label="Bedroom",
             polygon=[(0,0),(5,0),(5,5),(0,5)], area=25.0, centroid=(2.5,2.5)),
        Room(id="r2", type="Kitchen",   label="Kitchen",
             polygon=[(5,0),(10,0),(10,5),(5,5)], area=25.0, centroid=(7.5,2.5)),
    ]
    return sg

def l_shaped_scene() -> SceneGraph:
    sg = SceneGraph(metadata=Metadata(project_name="LShaped"))
    sg.walls.append(Wall(id="w1", start=(0,0), end=(6,0)))
    sg.walls.append(Wall(id="w2", start=(6,0), end=(6,3)))
    sg.walls.append(Wall(id="w3", start=(6,3), end=(3,3)))
    sg.walls.append(Wall(id="w4", start=(3,3), end=(3,6)))
    sg.walls.append(Wall(id="w5", start=(3,6), end=(0,6)))
    sg.walls.append(Wall(id="w6", start=(0,6), end=(0,0)))
    sg.rooms.append(Room(id="r1", type="Living Room", label="Living Room",
                         polygon=[(0,0),(6,0),(6,3),(3,3),(3,6),(0,6)],
                         area=27.0, centroid=(2.5,3.0)))
    return sg

# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def generate(scene_graph, cfg=None) -> str:
    cfg = cfg or BASE_CFG
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, "test_scene.py")
        build_script(scene_graph, cfg, tmpdir, script_path)
        with open(script_path, "r") as f:
            return f.read()

def assert_valid_python(code: str, label: str):
    try:
        ast.parse(code)
        print(f"[PASS] {label}: valid Python syntax")
    except SyntaxError as e:
        raise AssertionError(f"[FAIL] {label}: SyntaxError — {e}")

def assert_contains(code: str, snippet: str, label: str):
    assert snippet in code, f"[FAIL] {label}: expected '{snippet}' in script"
    print(f"[PASS] {label}: '{snippet}' found in script")

# ──────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────

def test_one_room_apartment():
    code = generate(one_room_scene())
    assert_valid_python(code, "One-room apartment")
    assert_contains(code, "Floor_Bedroom", "Floor object named correctly")
    assert_contains(code, "Wall_w1",       "Wall object created")
    assert_contains(code, "Ceiling_Bedroom","Ceiling created")
    assert_contains(code, "Sun_Light",     "Sun lamp added")
    assert_contains(code, "Camera_TopDown","Top-down camera added")
    assert_contains(code, "export_scene.gltf", "GLB export added")

def test_two_bedroom_house():
    code = generate(two_bedroom_scene())
    assert_valid_python(code, "Two-bedroom house")
    assert_contains(code, "Floor_Bedroom", "Bedroom floor")
    assert_contains(code, "Floor_Kitchen",  "Kitchen floor")
    assert_contains(code, "Cutter_d1",      "Door Boolean cutter")

def test_l_shaped_house():
    code = generate(l_shaped_scene())
    assert_valid_python(code, "L-shaped house")
    assert_contains(code, "Floor_Living_Room", "L-shaped floor polygon")

def test_missing_furniture_no_crash():
    sg = one_room_scene("Unknown")
    code = generate(sg)   # No furniture mapped for "Unknown"
    assert_valid_python(code, "Missing furniture (Unknown room)")

def test_missing_ocr_labels_no_crash():
    sg = one_room_scene()
    sg.rooms[0].label = None   # Strip the label
    code = generate(sg)
    assert_valid_python(code, "No OCR labels")

def test_irregular_polygon():
    sg = SceneGraph(metadata=Metadata(project_name="Irregular"))
    # Hexagonal room
    import math
    n = 6
    pts = [(3 + 3*math.cos(2*math.pi*i/n), 3 + 3*math.sin(2*math.pi*i/n)) for i in range(n)]
    sg.rooms.append(Room(id="r_hex", type="Studio", polygon=pts, area=23.0, centroid=(3,3)))
    code = generate(sg)
    assert_valid_python(code, "Irregular hexagonal polygon")

def test_ceiling_disabled():
    cfg = {**BASE_CFG, "building": {**BASE_CFG["building"], "ceiling_enabled": False}}
    code = generate(one_room_scene(), cfg)
    assert_valid_python(code, "Ceiling disabled")
    assert "Ceiling disabled" in code, "Disabled ceiling comment should appear"

def test_roof_disabled_keeps_walls_closed():
    cfg = {**BASE_CFG, "include_roof": False}
    code = generate(one_room_scene(), cfg)
    assert_valid_python(code, "Roof disabled")
    assert "Ceiling_Bedroom" not in code
    assert "top_faces" not in code
    assert "bmesh.ops.delete" not in code

def test_custom_wall_colour():
    cfg = {
        **BASE_CFG,
        "material_options": {
            "walls": {"theme": "custom", "color": "#336699"},
            "floor": {"design": "solid"},
        },
    }
    code = generate(one_room_scene(), cfg)
    assert_valid_python(code, "Custom wall colour")
    assert "WallMaterial" in code
    assert "bpy.data.materials.new(name='WallMaterial')" in code
    assert "mat.diffuse_color = (0.2, 0.4, 0.6, 1.0)" in code
    assert "wall_bsdf.inputs['Base Color'].default_value = (0.2, 0.4, 0.6, 1.0)" in code


def test_materials_export_with_modifiers():
    code = generate(one_room_scene())
    assert code.index("Materials") < code.index("Export")
    assert "export_apply=True" in code
    assert "export_materials='EXPORT'" in code
    assert "Apply Modifiers" not in code
    assert "primitive_cylinder_add" not in code
    assert "obj.data.materials.clear()" in code


def test_stacked_coils_wall_pattern():
    cfg = {
        **BASE_CFG,
        "material_options": {
            "walls": {
                "theme": "navy",
                "color": "#34495E",
                "pattern": "stacked_coils",
                "pattern_color": "#FF0000",
            },
            "floor": {"design": "solid"},
        },
    }
    code = generate(one_room_scene(), cfg)
    assert_valid_python(code, "Stacked coils pattern")
    assert "ShaderNodeNewGeometry" in code
    assert "ShaderNodeTexWave" in code
    assert "ShaderNodeValToRGB" in code
    assert "# Wall pattern: stacked_coils" in code
    assert "ShaderNodeBump" in code
    assert "_hz_scale.inputs[1].default_value = 10.0" in code
    assert "Apply Modifiers" not in code
    assert "primitive_cylinder_add" not in code
    assert "bpy.ops.object.join()" not in code
    assert code.count("bpy.data.materials.new(name='WallMaterial')") == 1
    assert "0.20392156862745098, 0.28627450980392155, 0.3686274509803922" in code
    assert "Base Color'].default_value = (1.0, 0.0, 0.0" not in code


def test_woven_rope_wall_pattern():
    cfg = {
        **BASE_CFG,
        "material_options": {
            "walls": {"theme": "warm_modern", "color": "#D8C8B8", "pattern": "woven_rope"},
            "floor": {"design": "solid"},
        },
    }
    code = generate(one_room_scene(), cfg)
    assert_valid_python(code, "Woven rope pattern")
    assert "ShaderNodeNewGeometry" in code
    assert "_wx_scale.inputs[1].default_value = 4.0" in code
    assert "_ridge_mix.operation = 'MAXIMUM'" in code
    assert "Apply Modifiers" not in code
    assert "primitive_cylinder_add" not in code
    assert "bpy.ops.object.join()" not in code


def test_walls_are_merged_and_bridged():
    from topology import _merge_collinear_walls
    walls = [
        Wall(id="a", start=(0.0, 0.0), end=(2.0, 0.0)),
        Wall(id="b", start=(2.1, 0.0), end=(4.0, 0.0)),
        Wall(id="c", start=(0.0, 0.0), end=(0.0, 5.0)),
    ]
    merged = _merge_collinear_walls(walls, gap_tolerance=0.30, angle_tolerance_deg=8.0)
    assert len(merged) == 2, f"Expected 2 merged walls, got {len(merged)}"
    spans = {tuple(sorted([w.start, w.end])) for w in merged}
    assert ((0.0, 0.0), (4.0, 0.0)) in spans
    assert ((0.0, 0.0), (0.0, 5.0)) in spans


def test_walls_do_not_merge_across_corners():
    from topology import _merge_collinear_walls
    walls = [
        Wall(id="left",  start=(0.0, 0.0), end=(0.0, 5.0)),
        Wall(id="bottom", start=(0.0, 0.0), end=(5.0, 0.0)),
        Wall(id="right", start=(5.0, 0.0), end=(5.0, 5.0)),
        Wall(id="top",   start=(0.0, 5.0), end=(5.0, 5.0)),
    ]
    merged = _merge_collinear_walls(walls, gap_tolerance=0.30, angle_tolerance_deg=8.0)
    assert len(merged) == 4, f"Perimeter walls must stay separate, got {len(merged)}"


def test_walls_snapped_to_90_degrees():
    from topology import _snap_to_axis
    wall = Wall(id="x", start=(0.0, 0.2), end=(4.0, -0.1))
    snapped = _snap_to_axis(wall)
    assert snapped.start[1] == snapped.end[1]
    assert snapped.start[1] == 0.05

    wall = Wall(id="y", start=(0.1, 0.0), end=(-0.05, 5.0))
    snapped = _snap_to_axis(wall)
    assert snapped.start[0] == snapped.end[0]
    assert snapped.start[0] == 0.025


def test_checker_floor_material():
    cfg = {
        **BASE_CFG,
        "material_options": {
            "walls": {"theme": "painted_white"},
            "floor": {
                "design": "checker",
                "primary_color": "#FFFFFF",
                "secondary_color": "#000000",
                "tile_size_m": 0.5,
            },
        },
    }
    code = generate(one_room_scene(), cfg)
    assert_valid_python(code, "Checker floor")
    assert "ShaderNodeTexChecker" in code
    assert "FloorMaterial" in code


def test_multiple_export_formats():
    cfg = {**BASE_CFG, "export": {"formats": ["glb", "fbx"], "output_dir": "output"}}
    code = generate(one_room_scene(), cfg)
    assert_valid_python(code, "Multi-format export")
    assert_contains(code, "export_scene.gltf", "GLB export present")
    assert_contains(code, "export_scene.fbx",  "FBX export present")

def test_large_building():
    sg = SceneGraph(metadata=Metadata(project_name="LargeBuilding"))
    for i in range(20):
        ox, oy = (i % 5) * 6, (i // 5) * 6
        sg.walls += [
            Wall(id=f"w{i}_a", start=(ox,oy),      end=(ox+5, oy)),
            Wall(id=f"w{i}_b", start=(ox+5,oy),    end=(ox+5, oy+5)),
            Wall(id=f"w{i}_c", start=(ox+5,oy+5),  end=(ox,   oy+5)),
            Wall(id=f"w{i}_d", start=(ox,oy+5),    end=(ox,   oy)),
        ]
        sg.rooms.append(Room(id=f"r{i}", type="Bedroom",
                              polygon=[(ox,oy),(ox+5,oy),(ox+5,oy+5),(ox,oy+5)],
                              area=25.0, centroid=(ox+2.5, oy+2.5)))
    code = generate(sg)
    assert_valid_python(code, "Large building (20 rooms)")
    print(f"      Script length: {len(code):,} chars")

# ──────────────────────────────────────────────────────────────────────
# Runner
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  BLENDER NODE TEST SUITE")
    print("=" * 60)
    test_one_room_apartment()
    test_two_bedroom_house()
    test_l_shaped_house()
    test_missing_furniture_no_crash()
    test_missing_ocr_labels_no_crash()
    test_irregular_polygon()
    test_ceiling_disabled()
    test_custom_wall_colour()
    test_materials_export_with_modifiers()
    test_stacked_coils_wall_pattern()
    test_woven_rope_wall_pattern()
    test_multiple_export_formats()
    test_large_building()
    print("=" * 60)
    print("  ALL TESTS PASSED")
    print("=" * 60)
