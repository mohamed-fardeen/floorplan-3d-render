from typing import Dict, Any
import yaml
import os

from schema import (
    PipelineState, BlenderResult, ParserConfidenceSchema,
    SceneGraph, Metadata
)
from perception import run_perception
from vectorizer import run_vectorization
from topology import run_topology
from validation import validate_and_repair_topology
from ocr.factory import get_ocr_engine
from enrichment import enrich_scene_graph

def perception_node(state: PipelineState) -> Dict[str, Any]:
    """Node 1: AI Perception (Pixel Space Only)"""
    print(f"--> [1/6] Perception Node: Running AI inference on {state.image_path}")
    perception_res = run_perception(state.image_path, model=state.perception_model)
    
    scores = perception_res.confidence_scores
    conf_schema = ParserConfidenceSchema(
        walls=scores.get("walls"),
        doors=scores.get("doors"),
        windows=scores.get("windows"),
        rooms=scores.get("rooms"),
        overall=scores.get("overall"),
    )
    
    return {
        "perception_result": perception_res,
        "parser_confidence": conf_schema,
        "status": "perceived"
    }

def vectorizer_node(state: PipelineState) -> Dict[str, Any]:
    """Node 2: Deterministic Vectorizer"""
    print("--> [2/6] Vectorizer Node: Converting masks to vector primitives...")
    if not state.perception_result:
        return {"status": "vectorization_failed", "audit_log": ["[ERROR] Missing perception result."]}
        
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    pixel_to_meter = 0.0195
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
            pixel_to_meter = float(cfg.get("parser", {}).get("pixel_to_meter", 0.0195))

    vector_geom = run_vectorization(state.perception_result, pixel_to_meter=pixel_to_meter)
    return {
        "vector_geometry": vector_geom,
        "status": "vectorized"
    }

def topology_node(state: PipelineState) -> Dict[str, Any]:
    """Node 3: Deterministic Topology Builder"""
    print("--> [3/6] Topology Node: Constructing room graph and connecting walls...")
    if not state.vector_geometry:
        return {"status": "topology_failed", "audit_log": ["[ERROR] Missing vector geometry."]}

    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    pixel_to_meter = 0.0195
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
            pixel_to_meter = float(cfg.get("parser", {}).get("pixel_to_meter", 0.0195))

    topo_data = run_topology(state.vector_geometry, pixel_to_meter=pixel_to_meter)
    return {
        "topology_data": topo_data,
        "status": "topology_built"
    }

def geometry_validation_node(state: PipelineState) -> Dict[str, Any]:
    """Node 4: Geometry Validation & Repair (Shapely/NetworkX)"""
    print("--> [4/6] Geometry Validation: Checking topology consistency...")
    if not state.topology_data:
        return {"status": "validation_failed", "validation_report": ["[ERROR] No topology data to validate."]}
        
    corrected_topo, report = validate_and_repair_topology(state.topology_data)
    for msg in report:
        print("    " + msg)
        
    status = "validated" if not any("[ERROR]" in msg for msg in report) else "validation_failed"
    return {
        "topology_data": corrected_topo,
        "validation_report": report,
        "status": status
    }

def ocr_extraction_node(state: PipelineState) -> Dict[str, Any]:
    """Node 5: OCR Node (Attach Labels to Topology Rooms)"""
    print("--> [5/6] OCR Node: Attaching room labels & text regions...")

    if not state.topology_data:
        return {"status": "ocr_skipped", "audit_log": ["[WARN] No topology data available for OCR."]}

    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}

    ocr_cfg = config.get("ocr", {})
    provider = ocr_cfg.get("provider", "mock")
    lang = ocr_cfg.get("lang", "en")
    confidence_threshold = float(ocr_cfg.get("confidence_threshold", 0.6))
    snap_distance = float(ocr_cfg.get("dimension_snap_distance", 1.0))

    # Temporarily assemble intermediate scene graph for OCR enrichment helper
    temp_sg = SceneGraph(
        walls=state.topology_data.connected_walls,
        doors=state.topology_data.assigned_doors,
        windows=state.topology_data.assigned_windows,
        rooms=state.topology_data.rooms,
        adjacency_graph=state.topology_data.adjacency_graph,
    )

    ocr_engine = get_ocr_engine(
        provider,
        pixel_to_meter=0.0195,
        lang=lang,
        confidence_threshold=confidence_threshold,
    )
    try:
        detections = ocr_engine.extract_text(state.image_path)
    except Exception as e:
        print(f"    [ERROR] OCR failed: {e}. Continuing without enrichment.")
        return {"status": "ocr_error", "audit_log": [f"[ERROR] OCR error: {e}"]}

    enriched_sg, audit_log = enrich_scene_graph(
        temp_sg,
        detections,
        dimension_snap_distance=snap_distance,
    )

    # Put enriched elements back into topology_data
    state.topology_data.rooms = enriched_sg.rooms
    state.topology_data.connected_walls = enriched_sg.walls

    return {
        "topology_data": state.topology_data,
        "audit_log": audit_log,
        "status": "ocr_completed"
    }

def scene_graph_builder_node(state: PipelineState) -> Dict[str, Any]:
    """Node 6: Final Scene Graph Builder"""
    print("--> [6/6] Scene Graph Builder: Finalizing canonical SceneGraph...")
    if not state.topology_data:
        return {"status": "builder_failed", "audit_log": ["[ERROR] Missing topology data for SceneGraph creation."]}

    topo = state.topology_data
    overall_conf = state.parser_confidence.overall if state.parser_confidence else 0.85

    meta = Metadata(
        units="meters",
        scale_pixel_to_meter=0.0195,
        confidence_score=overall_conf
    )

    sg = SceneGraph(
        metadata=meta,
        walls=topo.connected_walls,
        doors=topo.assigned_doors,
        windows=topo.assigned_windows,
        rooms=topo.rooms,
        adjacency_graph=topo.adjacency_graph
    )

    print(f"    Final SceneGraph built: {len(sg.rooms)} rooms, {len(sg.walls)} walls, {len(sg.doors)} doors, {len(sg.windows)} windows.")

    return {
        "scene_graph": sg,
        "status": "scene_graph_ready"
    }

def reannotate_scene_graph_node(state: PipelineState) -> Dict[str, Any]:
    return ocr_extraction_node(state)

def blender_mcp_node(state: PipelineState) -> Dict[str, Any]:
    print("--> Blender MCP: Generating 3D model...")

    if not state.scene_graph:
        return {
            "status": "blender_failed",
            "blender_result": BlenderResult(success=False,
                                            warnings=["[ERROR] No scene graph available."])
        }

    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f) or {}

    if hasattr(state, "blender_options") and state.blender_options:
        cfg.update(state.blender_options)

    output_dir = os.path.abspath(cfg.get("export", {}).get("output_dir", "output"))
    os.makedirs(output_dir, exist_ok=True)

    emit = cfg.get("progress_emitter")

    def _emit(stage: str, message: str, **extra) -> None:
        if emit is None:
            return
        try:
            emit(stage, message, **extra)
        except Exception as e:
            print(f"    [WARN] progress emit failed: {e}")

    _emit("script", "Building Blender script")
    import tempfile
    import shutil

    script_path = os.path.join(tempfile.gettempdir(), "floorplan3d_blender_scene.py")
    snapshot_path = os.path.join(output_dir, "blender_scene.py")

    from blender.script_builder import build_script
    from blender.executor import execute_script, open_existing_blend

    open_blender = bool(cfg.get("open_blender", False))
    project = (state.scene_graph.metadata.project_name or "building").replace(" ", "_")
    formats = cfg.get("export", {}).get("formats", ["glb"])
    expected_exports = [os.path.join(output_dir, f"{project}.{fmt}") for fmt in formats]
    blend_path = next((p for p in expected_exports if p.lower().endswith(".blend")), None)

    if open_blender and blend_path and os.path.isfile(blend_path):
        print("    Opening existing .blend (no re-export)")
        _emit("blender", "Opening existing .blend")
        success, export_paths, warnings = open_existing_blend(blend_path, expected_exports)
        for w in warnings:
            print("    " + w)
        result = BlenderResult(
            success=success,
            export_paths=export_paths,
            warnings=warnings,
            script_path=snapshot_path,
        )
        return {
            "blender_result": result,
            "status": "completed" if success else "blender_no_exe",
        }

    try:
        build_script(state.scene_graph, cfg, output_dir, script_path)
        print(f"    Script written -> {script_path}")
        _emit("script", "Script written", path=script_path)
    except Exception as e:
        _emit("error", f"Script generation failed: {e}")
        return {
            "status": "blender_failed",
            "blender_result": BlenderResult(success=False,
                                            warnings=[f"[ERROR] Script generation failed: {e}"],
                                            script_path=snapshot_path)
        }

    _emit("execute", "Executing Blender", mode="headless")
    success, export_paths, warnings = execute_script(
        script_path,
        expected_exports=expected_exports,
        open_gui=open_blender,
    )
    for w in warnings:
        print("    " + w)

    try:
        shutil.copy2(script_path, snapshot_path)
        print(f"    Script snapshot -> {snapshot_path}")
    except OSError as e:
        warnings.append(f"[WARN] Could not copy script snapshot: {e}")

    _emit("export", "Export complete", paths=export_paths)

    result = BlenderResult(
        success=success,
        export_paths=export_paths,
        warnings=warnings,
        script_path=snapshot_path,
    )
    return {
        "blender_result": result,
        "status": "completed" if success else "blender_no_exe",
    }
