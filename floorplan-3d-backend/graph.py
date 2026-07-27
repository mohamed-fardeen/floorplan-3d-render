from langgraph.graph import StateGraph, START, END
from schema import PipelineState
from nodes import (
    perception_node,
    vectorizer_node,
    topology_node,
    geometry_validation_node,
    ocr_extraction_node,
    scene_graph_builder_node,
    blender_mcp_node,
)

def build_graph():
    workflow = StateGraph(PipelineState)

    # --- Nodes ---
    workflow.add_node("perception",          perception_node)
    workflow.add_node("vectorizer",          vectorizer_node)
    workflow.add_node("topology",            topology_node)
    workflow.add_node("geometry_validation", geometry_validation_node)
    workflow.add_node("ocr_enrichment",      ocr_extraction_node)
    workflow.add_node("scene_graph_builder", scene_graph_builder_node)
    workflow.add_node("blender_mcp",         blender_mcp_node)

    # --- Edges ---
    workflow.add_edge(START, "perception")
    workflow.add_edge("perception", "vectorizer")
    workflow.add_edge("vectorizer", "topology")
    workflow.add_edge("topology", "geometry_validation")

    # After validation: proceed to OCR
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

    # Blender execution is terminal
    workflow.add_conditional_edges(
        "blender_mcp",
        lambda s: "done",
        {"done": END}
    )

    return workflow.compile()
