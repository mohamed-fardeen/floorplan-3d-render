from schema import PipelineState
from graph import build_graph

def run_pipeline(image_path: str):
    print("====================================")
    print(f"Starting pipeline for: {image_path}")
    print("====================================")
    
    app = build_graph()
    initial_state = PipelineState(image_path=image_path)
    
    # Run the graph
    result_state = app.invoke(initial_state.model_dump())
    
    print("\n====================================")
    print("Pipeline Execution Finished")
    print("Final Status:", result_state.get("status"))
    print("\nFinal Scene Graph JSON:")
    if "scene_graph" in result_state and result_state["scene_graph"]:
        print(result_state["scene_graph"].model_dump_json(indent=2))

    br = result_state.get("blender_result")
    if br:
        print("\nBlender Result:")
        print(f"  Success      : {br.success}")
        print(f"  Script path  : {br.script_path}")
        print(f"  Export paths : {br.export_paths}")
        if br.warnings:
            print("  Warnings:")
            for w in br.warnings:
                print("    " + w)
    print("====================================")

if __name__ == "__main__":
    run_pipeline("sample_floorplan.png")
