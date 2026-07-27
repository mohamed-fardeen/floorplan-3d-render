import os
import json
import pytest
import time
import hashlib
from schema import PipelineState
from nodes import (
    parse_floorplan_node,
    geometry_validation_node,
    ocr_extraction_node,
    scene_graph_builder_node,
    blender_mcp_node
)

# You can define a few specific test images here.
# For CI/CD regression tests, we use files from the benchmark dataset.
TEST_IMAGES = [
    os.path.join("datasets", "benchmark", "apartment_01.png")
]

def hash_string(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def get_snapshot_path(image_name: str) -> str:
    return os.path.join(os.path.dirname(__file__), f"regression_snapshot_{image_name}.json")

@pytest.mark.parametrize("image_path", TEST_IMAGES)
def test_pipeline_regression(image_path):
    if not os.path.exists(image_path):
        pytest.skip(f"Test image not found: {image_path}")
        
    img_name = os.path.splitext(os.path.basename(image_path))[0]
    snapshot_path = get_snapshot_path(img_name)
    
    state = PipelineState(image_path=image_path)
    
    t0 = time.perf_counter()
    
    # 1. Parse
    update = parse_floorplan_node(state)
    state.scene_graph = update["scene_graph"]
    state.status = update["status"]
    
    # 2. Geometry Validation
    update = geometry_validation_node(state)
    state.scene_graph = update["scene_graph"]
    state.status = update["status"]
    val_errors = sum(1 for m in update.get("validation_report", []) if "[ERROR]" in m)
    
    # 3. OCR (Skip or include depending on stable OCR availability)
    update = ocr_extraction_node(state)
    if "scene_graph" in update:
        state.scene_graph = update["scene_graph"]
        
    # 4. Final SG
    update = scene_graph_builder_node(state)
    sg_json = state.scene_graph.model_dump_json(indent=2)
    sg_hash = hash_string(sg_json)
    
    # 5. Blender
    update = blender_mcp_node(state)
    state.blender_result = update.get("blender_result")
    
    blender_script_path = state.blender_result.script_path if state.blender_result else None
    script_hash = ""
    if blender_script_path and os.path.exists(blender_script_path):
        with open(blender_script_path, "r") as f:
            script_hash = hash_string(f.read())
            
    runtime = time.perf_counter() - t0
            
    # Load snapshot if exists, else create it
    if not os.path.exists(snapshot_path):
        snapshot = {
            "scene_graph_hash": sg_hash,
            "blender_script_hash": script_hash,
            "validation_errors": val_errors,
            "max_runtime_s": runtime * 1.5 # 50% margin
        }
        with open(snapshot_path, "w") as f:
            json.dump(snapshot, f, indent=2)
        pytest.skip("Created new snapshot. Run again to test.")
        
    with open(snapshot_path, "r") as f:
        snapshot = json.load(f)
        
    # Assertions
    assert sg_hash == snapshot["scene_graph_hash"], f"Scene Graph regression for {img_name}"
    assert script_hash == snapshot["blender_script_hash"], f"Blender Script regression for {img_name}"
    assert val_errors <= snapshot["validation_errors"], f"Validation errors increased for {img_name}"
    assert runtime <= snapshot["max_runtime_s"], f"Runtime regression for {img_name} ({runtime:.2f}s > {snapshot['max_runtime_s']:.2f}s)"
