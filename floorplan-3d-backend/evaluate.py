import os
import glob
import json
import traceback
import argparse
from typing import Dict, Any

from schema import PipelineState
from nodes import (
    perception_node,
    vectorizer_node,
    topology_node,
    geometry_validation_node,
    ocr_extraction_node,
    scene_graph_builder_node,
    blender_mcp_node
)
from parsers.visualization import visualize_scene_graph
from evaluation.profiler import Profiler, calculate_aggregates
from evaluation.categorization import ErrorCategorizer
from evaluation.dashboard import generate_dashboard
from evaluation.visual_comparison import create_side_by_side_comparison

def run_evaluation(dataset_dir: str, results_dir: str):
    os.makedirs(results_dir, exist_ok=True)
    
    # Find images
    image_paths = []
    for ext in ["*.png", "*.jpg", "*.jpeg"]:
        image_paths.extend(glob.glob(os.path.join(dataset_dir, "**", ext), recursive=True))
        
    print(f"Found {len(image_paths)} images for evaluation.")
    
    all_results = []
    all_metrics = []
    categorizer = ErrorCategorizer()
    
    for img_path in image_paths:
        img_name = os.path.basename(img_path)
        print(f"\n--- Evaluating: {img_name} ---")
        
        run_results_dir = os.path.join(results_dir, os.path.splitext(img_name)[0])
        os.makedirs(run_results_dir, exist_ok=True)
        
        profiler = Profiler()
        state = PipelineState(image_path=img_path)
        
        run_result = {
            "image_name": img_name,
            "parser_error": None,
            "validation_report": [],
            "validation_error_count": 0,
            "ocr_error": None,
            "blender_error": None,
            "export_success": False,
            "visual_comparison_path": ""
        }
        
        # 1. Perception & Vectorization & Topology
        profiler.start("parser")
        try:
            p_update = perception_node(state)
            state.perception_result = p_update.get("perception_result")
            state.parser_confidence = p_update.get("parser_confidence")
            
            v_update = vectorizer_node(state)
            state.vector_geometry = v_update.get("vector_geometry")
            
            t_update = topology_node(state)
            state.topology_data = t_update.get("topology_data")
            state.status = t_update.get("status")
        except Exception as e:
            run_result["parser_error"] = str(e)
            print(f"[ERROR] Perception/Vectorizer failed: {e}")
        profiler.stop("parser")
        
        # 2. Validation
        if state.topology_data and not run_result["parser_error"]:
            profiler.start("validation")
            try:
                update = geometry_validation_node(state)
                state.topology_data = update.get("topology_data")
                state.status = update.get("status")
                state.validation_report = update.get("validation_report", [])
                
                run_result["validation_report"] = state.validation_report
                run_result["validation_error_count"] = sum(1 for m in state.validation_report if "[ERROR]" in m)
            except Exception as e:
                run_result["validation_error_count"] += 1
                run_result["validation_report"].append(f"[ERROR] Exception in validation: {e}")
                print(f"[ERROR] Validation failed: {e}")
            profiler.stop("validation")
            
        # 3. OCR
        if state.status != "validation_failed" and not run_result["parser_error"]:
            profiler.start("ocr")
            try:
                update = ocr_extraction_node(state)
                if update.get("topology_data"):
                    state.topology_data = update.get("topology_data")
                state.status = update.get("status", state.status)
                state.audit_log = update.get("audit_log", [])
            except Exception as e:
                run_result["ocr_error"] = str(e)
                print(f"[ERROR] OCR failed: {e}")
            profiler.stop("ocr")
            
            # 4. Final Scene Graph
            profiler.start("scene_graph")
            try:
                update = scene_graph_builder_node(state)
                state.scene_graph = update.get("scene_graph")
                state.status = update.get("status")
                
                # Save JSON
                sg_path = os.path.join(run_results_dir, "scene_graph.json")
                with open(sg_path, "w") as f:
                    f.write(state.scene_graph.model_dump_json(indent=2))
            except Exception as e:
                print(f"[ERROR] SG Builder failed: {e}")
            profiler.stop("scene_graph")
            
            # 5. Blender Generation
            profiler.start("blender")
            try:
                update = blender_mcp_node(state)
                state.blender_result = update.get("blender_result")
                
                if state.blender_result:
                    run_result["export_success"] = state.blender_result.success
                    if not state.blender_result.success:
                        run_result["blender_error"] = str(state.blender_result.warnings)
            except Exception as e:
                run_result["blender_error"] = str(e)
                print(f"[ERROR] Blender failed: {e}")
            profiler.stop("blender")
            
            # Visual Comparison
            try:
                viz_output = os.path.join(run_results_dir, "parser_viz.png")
                visualize_scene_graph(state.scene_graph, img_path, output_dir=run_results_dir, filename_suffix="_viz")
                # visualize_scene_graph creates <basename>_viz.png
                gen_viz_path = os.path.join(run_results_dir, os.path.splitext(img_name)[0] + "_viz.png")
                
                comp_path = os.path.join(run_results_dir, "comparison.png")
                if create_side_by_side_comparison([img_path, gen_viz_path], comp_path):
                    run_result["visual_comparison_path"] = os.path.join(os.path.splitext(img_name)[0], "comparison.png")
            except Exception as e:
                print(f"[ERROR] Visualization failed: {e}")
                
        metrics = profiler.get_metrics()
        all_metrics.append(metrics)
        all_results.append(run_result)
        categorizer.analyze_pipeline_result(run_result)
        
    print("\n--- Evaluation Complete ---")
    aggregates = calculate_aggregates(all_metrics)
    summary = categorizer.get_summary()
    
    dashboard_path = os.path.join(results_dir, "dashboard.html")
    generate_dashboard(all_results, aggregates, summary, dashboard_path)
    print(f"Quality Dashboard generated at: {dashboard_path}")
    
    return all_results, aggregates, summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", default="datasets/evaluation", help="Path to evaluation dataset")
    parser.add_argument("--results-dir", default="results", help="Path to output results")
    args = parser.parse_args()
    
    run_evaluation(args.dataset_dir, args.results_dir)
