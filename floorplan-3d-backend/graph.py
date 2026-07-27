from langgraph.graph import StateGraph, START, END
from schema import PipelineState
from nodes import (
    parse_floorplan_node,
    ocr_extraction_node,
    geometry_validation_node,
    scene_graph_builder_node,
    blender_mcp_node,
)

def build_graph():
    workflow = StateGraph(PipelineState)

    # --- Nodes ---
    workflow.add_node("parse_floorplan",      parse_floorplan_node)
    workflow.add_node("geometry_validation",  geometry_validation_node)
    workflow.add_node("ocr_enrichment",       ocr_extraction_node)
    workflow.add_node("scene_graph_builder",  scene_graph_builder_node)
    workflow.add_node("blender_mcp",          blender_mcp_node)

    # --- Edges ---
    workflow.add_edge(START, "parse_floorplan")
    workflow.add_edge("parse_floorplan", "geometry_validation")

    # After validation: proceed or terminate
    workflow.add_conditional_edges(
        "geometry_validation",
        lambda s: "success" if s.status == "validated" else "fail",
        {"success": "ocr_enrichment", "fail": END}
    )

    # OCR is best-effort: always continue to scene_graph_builder
    workflow.add_conditional_edges(
        "ocr_enrichment",
        lambda s: "next",
        {"next": "scene_graph_builder"}
    )

    workflow.add_edge("scene_graph_builder", "blender_mcp")

    # Blender execution may succeed, skip (no exe), or fail — all are terminal
    workflow.add_conditional_edges(
        "blender_mcp",
        lambda s: "done",
        {"done": END}
    )

    return workflow.compile()
