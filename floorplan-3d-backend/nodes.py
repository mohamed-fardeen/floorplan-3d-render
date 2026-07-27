from typing import Dict, Any
import yaml
import os
from schema import PipelineState, BlenderResult, ParserConfidenceSchema
from validation import validate_and_repair_scene
from parsers.factory import get_parser
from parsers.failure_analysis import analyze_failures
from ocr.factory import get_ocr_engine
from enrichment import enrich_scene_graph

def parse_floorplan_node(state: PipelineState) -> Dict[str, Any]:
    print(f"--> Parsing floor plan: {state.image_path}")
    
    # Load Config
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        
    parser_cfg = config.get("parser", {})
    provider   = parser_cfg.get("provider", "yytsi")
    print(f"    Using parser provider: {provider}")
    
    # Build optional kwargs from config (device, pixel_to_meter)
    parser_kwargs = {}
    if "device" in parser_cfg:
        parser_kwargs["device"] = parser_cfg["device"]
    if "pixel_to_meter" in parser_cfg:
        parser_kwargs["pixel_to_meter"] = float(parser_cfg["pixel_to_meter"])
    
    # Fetch and run the parser
    parser = get_parser(provider, **parser_kwargs)
    scene_graph = parser.parse(state.image_path)
    
    # --- Failure Analysis ---
    fa_report = analyze_failures(scene_graph)
    fa_lines  = [str(i) for i in fa_report.issues]
    if fa_report.has_critical_failures:
        print(f"    [WARN] Parser failure analysis detected {len(fa_report.errors)} error(s).")
    for line in fa_lines:
        print(f"    {line}")
    
    # --- Extract structured confidence ---
    # YytsiParser stores per-class confidence in _last_confidence dict after inference.
    from parsers.normalizer import normalize_confidence
    conf_raw = scene_graph.metadata.confidence_score
    # Some parser impls expose last_confidence dict after inference
    impl = getattr(parser, "_impl", parser)
    per_class_conf = getattr(impl, "_last_confidence", None)
    if per_class_conf and isinstance(per_class_conf, dict):
        normalized_conf = normalize_confidence(per_class_conf)
    else:
        normalized_conf = normalize_confidence(float(conf_raw))
    parser_confidence = ParserConfidenceSchema(
        walls   = normalized_conf.walls,
        doors   = normalized_conf.doors,
        windows = normalized_conf.windows,
        rooms   = normalized_conf.rooms,
        overall = normalized_conf.overall,
    )
    print(f"    Parser confidence: {normalized_conf}")

    # --- Optional debug visualization ---
    try:
        export_cfg = config.get("export", {})
        output_dir = os.path.abspath(export_cfg.get("output_dir", "output"))
        from parsers.visualization import visualize_scene_graph
        visualize_scene_graph(
            scene_graph, state.image_path,
            output_dir=os.path.join(output_dir, "debug_viz"),
            show_labels=True,
            show_confidence=True,
        )
    except Exception as viz_err:
        print(f"    [INFO] Visualization skipped: {viz_err}")
    
    return {
        "scene_graph":       scene_graph,
        "status":            "parsed",
        "parser_confidence": parser_confidence,
        "failure_report":    fa_lines,
    }

def ocr_extraction_node(state: PipelineState) -> Dict[str, Any]:
    print("--> OCR & Semantic Enrichment...")

    if not state.scene_graph:
        return {"status": "ocr_skipped",
                "audit_log": ["[WARN] No scene graph available for OCR enrichment."]}

    # Load config
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    ocr_cfg = config.get("ocr", {})
    provider = ocr_cfg.get("provider", "mock")
    snap_distance = float(ocr_cfg.get("dimension_snap_distance", 1.0))
    print(f"    Using OCR provider: {provider}")

    # Pixel → metre scale comes from the scene graph the parser produced.
    pixel_to_meter = state.scene_graph.metadata.scale_pixel_to_meter

    ocr_kwargs: Dict[str, Any] = {"pixel_to_meter": pixel_to_meter}

    # Extract text
    ocr_engine = get_ocr_engine(provider, **ocr_kwargs)
    try:
        detections = ocr_engine.extract_text(state.image_path)
    except NotImplementedError:
        print(f"    [WARN] OCR provider '{provider}' not implemented. Skipping enrichment.")
        return {"status": "ocr_skipped", "audit_log": [f"[WARN] OCR provider '{provider}' not implemented."]}
    except Exception as e:
        print(f"    [ERROR] OCR failed: {e}. Continuing without enrichment.")
        return {"status": "ocr_error", "audit_log": [f"[ERROR] OCR error: {e}"]}

    print(f"    Extracted {len(detections)} text regions.")

    # Spatial enrichment (passes snap distance from OCR config)
    enriched_sg, audit_log = enrich_scene_graph(
        state.scene_graph,
        detections,
        dimension_snap_distance=snap_distance,
    )
    for msg in audit_log:
        print("    " + msg)

    return {"scene_graph": enriched_sg, "audit_log": audit_log, "status": "ocr_completed"}


def reannotate_scene_graph_node(state: PipelineState) -> Dict[str, Any]:
    """
    Re-runs the OCR node on an already-parsed scene graph.

    Used by the /api/annotate endpoint so a user-edited scene graph can be
    re-enriched (or have its previous OCR overlay refreshed) without
    re-running the parser or geometry validation.

    The endpoint must populate ``state.image_path`` and ``state.scene_graph``
    before invoking this node.
    """
    return ocr_extraction_node(state)

def geometry_validation_node(state: PipelineState) -> Dict[str, Any]:
    print("--> Validating geometry (Shapely/NetworkX)...")
    if not state.scene_graph:
        return {"status": "validation_failed", "validation_report": ["[ERROR] No scene graph to validate."]}
        
    corrected_sg, report = validate_and_repair_scene(state.scene_graph)
    for msg in report:
        print("    " + msg)
        
    status = "validated" if not any("[ERROR]" in msg for msg in report) else "validation_failed"
    return {"scene_graph": corrected_sg, "validation_report": report, "status": status}

def scene_graph_builder_node(state: PipelineState) -> Dict[str, Any]:
    """Final node that marks the scene graph as canonical and ready for Blender."""
    print("--> Finalising canonical Scene Graph...")
    sg = state.scene_graph
    if sg:
        print(f"    Rooms   : {len(sg.rooms)}")
        print(f"    Walls   : {len(sg.walls)}")
        print(f"    Doors   : {len(sg.doors)}")
        print(f"    Windows : {len(sg.windows)}")
        print(f"    OCR tags: {len(sg.ocr_detections)}")
    return {"status": "scene_graph_ready"}

def blender_mcp_node(state: PipelineState) -> Dict[str, Any]:
    print("--> Blender MCP: Generating 3D model...")

    if not state.scene_graph:
        return {
            "status": "blender_failed",
            "blender_result": BlenderResult(success=False,
                                            warnings=["[ERROR] No scene graph available."])
        }

    # Load config
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    # Apply options from state
    if hasattr(state, "blender_options") and state.blender_options:
        cfg.update(state.blender_options)

    output_dir  = os.path.abspath(cfg.get("export", {}).get("output_dir", "output"))
    script_path = os.path.join(output_dir, "blender_scene.py")

    # Build the bpy script
    from blender.script_builder import build_script
    from blender.executor import execute_script

    try:
        build_script(state.scene_graph, cfg, output_dir, script_path)
        print(f"    Script written -> {script_path}")
    except Exception as e:
        return {
            "status": "blender_failed",
            "blender_result": BlenderResult(success=False,
                                            warnings=[f"[ERROR] Script generation failed: {e}"],
                                            script_path=script_path)
        }

    # Execute
    success, export_paths, warnings = execute_script(script_path)
    for w in warnings:
        print("    " + w)

    result = BlenderResult(
        success=success,
        export_paths=export_paths,
        warnings=warnings,
        script_path=script_path,
    )
    return {
        "blender_result": result,
        "status": "completed" if success else "blender_no_exe",
    }

