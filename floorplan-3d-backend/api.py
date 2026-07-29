import os
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import shutil
import uuid
import uvicorn
from pydantic import BaseModel, Field
from typing import Literal

from schema import PipelineState, SceneGraph
from nodes import (
    perception_node,
    vectorizer_node,
    topology_node,
    geometry_validation_node,
    ocr_extraction_node,
    scene_graph_builder_node,
    blender_mcp_node
)

app = FastAPI(title="Floor Plan 3D API", version="1.0.0")

# Enable CORS for local React app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount output directory for static file serving
os.makedirs("output", exist_ok=True)
app.mount("/output", StaticFiles(directory="output"), name="output")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ValidateRequest(BaseModel):
    scene_graph: SceneGraph

class WallMaterialOptions(BaseModel):
    theme: Literal["warm_modern", "painted_white", "cool_modern", "sage", "sand", "navy", "clay", "blush", "charcoal", "olive", "sky", "custom"] = "warm_modern"
    color: str = Field("#D8C8B8", pattern=r"^#[0-9A-Fa-f]{6}$")
    pattern: Literal["none", "woven_rope", "stacked_coils"] = "none"
    # Kept for API compatibility; ridges always use `color` (wall colour).
    pattern_color: str = Field("#A8907A", pattern=r"^#[0-9A-Fa-f]{6}$")

class FloorMaterialOptions(BaseModel):
    design: Literal["square_grid", "checker", "terracotta", "marble", "slate", "wood", "mosaic", "sandstone", "granite", "solid", "custom"] = "square_grid"
    primary_color: str = Field("#E8E3D9", pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: str = Field("#B8B5AE", pattern=r"^#[0-9A-Fa-f]{6}$")
    grout_color: str = Field("#A8A49C", pattern=r"^#[0-9A-Fa-f]{6}$")
    tile_size_m: float = Field(0.4, ge=0.05, le=5.0)

class MaterialOptions(BaseModel):
    walls: WallMaterialOptions = Field(default_factory=WallMaterialOptions)
    floor: FloorMaterialOptions = Field(default_factory=FloorMaterialOptions)

class ExportRequest(BaseModel):
    scene_graph: SceneGraph
    include_base: bool = True
    include_roof: bool = True
    material_options: MaterialOptions = Field(default_factory=MaterialOptions)
    open_blender: bool = False

class AnnotateRequest(BaseModel):
    image_path: str
    scene_graph: SceneGraph

class SelectionPayloadModel(BaseModel):
    id: str
    meshRefs: List[Dict[str, Any]] = Field(default_factory=list)
    faceRefs: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DesignOperationModel(BaseModel):
    type: Literal["apply_pattern", "set_color", "set_material_preset"]
    pattern: Optional[str] = None
    value: Optional[str] = None
    preset: Optional[str] = None

class DesignApplyRequest(BaseModel):
    scene_graph: SceneGraph
    selection: SelectionPayloadModel
    operations: List[DesignOperationModel]
    material_options: MaterialOptions = Field(default_factory=MaterialOptions)
    include_base: bool = True
    include_roof: bool = False

class AIPlanRequest(BaseModel):
    prompt: str
    selection_summary: Optional[Dict[str, Any]] = None

@app.post("/api/upload")
async def upload_image(
    file: UploadFile = File(...),
    model: str = Form("multi"),
):
    """Uploads an image, parses it via the selected perception model, and returns canonical Scene Graph."""
    supported_models = {
        "multi", "yytsi", "cubicasa", "mask2former", "architect-yolo",
        "deepfloorplan", "raster-to-vector", "huggingface",
    }
    if model not in supported_models:
        raise HTTPException(status_code=400, detail=f"Unsupported model: {model}")
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    ext = os.path.splitext(file.filename)[1]
    unique_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{unique_id}{ext}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Initialize state
    state = PipelineState(image_path=file_path, perception_model=model)
    
    # Run modular pipeline steps
    try:
        # 1. Perception
        p_res = perception_node(state)
        state.perception_result = p_res.get("perception_result")
        state.parser_confidence = p_res.get("parser_confidence")
        
        # 2. Vectorization
        v_res = vectorizer_node(state)
        state.vector_geometry = v_res.get("vector_geometry")
        
        # 3. Topology
        t_res = topology_node(state)
        state.topology_data = t_res.get("topology_data")
        
        # 4. Validate Topology
        val_result = geometry_validation_node(state)
        state.topology_data = val_result.get("topology_data")
        state.validation_report = val_result.get("validation_report", [])
        
        # 5. OCR
        ocr_result = ocr_extraction_node(state)
        state.topology_data = ocr_result.get("topology_data", state.topology_data)
        state.audit_log.extend(ocr_result.get("audit_log", []))
        
        # 6. Scene Graph Builder
        sg_res = scene_graph_builder_node(state)
        state.scene_graph = sg_res.get("scene_graph")
        
        return {
            "status": "success",
            "scene_graph": state.scene_graph,
            "parser_confidence": state.parser_confidence,
            "validation_report": state.validation_report,
            "failure_report": state.failure_report,
            "audit_log": state.audit_log
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/validate")
async def validate_graph(req: ValidateRequest):
    """Validates and repairs a modified Scene Graph."""
    state = PipelineState(image_path="", scene_graph=req.scene_graph)
    
    try:
        val_result = geometry_validation_node(state)
        return {
            "status": "success",
            "scene_graph": val_result.get("scene_graph"),
            "validation_report": val_result.get("validation_report", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/export")
async def export_blender(req: ExportRequest):
    """Runs the Blender generator on the provided Scene Graph."""
    state = PipelineState(
        image_path="",
        scene_graph=req.scene_graph,
        blender_options={
            "include_base": req.include_base,
            "include_roof": req.include_roof,
            "material_options": req.material_options.model_dump(),
            "open_blender": req.open_blender,
        }
    )

    try:
        blender_result_dict = blender_mcp_node(state)
        br = blender_result_dict.get("blender_result")
        if not br or not br.success:
            warnings = br.warnings if br else ["Unknown Blender Error"]
            print("    [WARN] Blender export failed, returning partial success to allow frontend editing.")
            return {
                "status": "success",
                "export_paths": [],
                "warnings": warnings,
                "script_path": br.script_path if br else None,
                "blender_success": False
            }

        return {
            "status": "success",
            "export_paths": br.export_paths,
            "warnings": br.warnings,
            "script_path": br.script_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/design/apply")
async def apply_design_actions(req: DesignApplyRequest):
    """Validate structured design actions, translate to Blender ops, re-export GLB."""
    from design.actions import (
        DesignOperation,
        SelectionPayload,
        validate_operations,
        translate_to_blender_options,
    )

    ops = [DesignOperation(**op.model_dump()) for op in req.operations]
    errors = validate_operations(ops)
    if errors:
        raise HTTPException(status_code=400, detail={"validation_errors": errors})

    selection = SelectionPayload(
        id=req.selection.id,
        meshRefs=req.selection.meshRefs,
        faceRefs=req.selection.faceRefs,
        metadata=req.selection.metadata,
    )
    translated = translate_to_blender_options(
        ops,
        req.material_options.model_dump(),
        selection,
    )

    state = PipelineState(
        image_path="",
        scene_graph=req.scene_graph,
        blender_options={
            "include_base": req.include_base,
            "include_roof": req.include_roof,
            "material_options": translated["material_options"],
            "region_overrides": translated["region_overrides"],
            "open_blender": False,
        },
    )

    try:
        blender_result_dict = blender_mcp_node(state)
        br = blender_result_dict.get("blender_result")
        if not br or not br.success:
            warnings = br.warnings if br else ["Unknown Blender Error"]
            return {
                "status": "error",
                "detail": "; ".join(warnings),
                "export_paths": br.export_paths if br else [],
                "warnings": warnings,
            }
        return {
            "status": "success",
            "export_paths": br.export_paths,
            "warnings": br.warnings,
            "translated": translated,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/design/ai-plan")
async def ai_design_plan(req: AIPlanRequest):
    """Plan structured design actions from a natural-language prompt."""
    from design.ai_planner import plan_from_prompt

    try:
        plan = plan_from_prompt(req.prompt, req.selection_summary)
        return {
            "status": "success",
            "plan": plan.model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/annotate")
async def annotate(req: AnnotateRequest):
    """
    Re-runs the OCR pass on a previously-parsed scene graph.

    Workflow:
        1. Frontend uploads image  -> POST /api/upload        (parses + OCRs)
        2. User edits labels in AnnotationPage
        3. Frontend POSTs the edited graph + image_path here
        4. Backend re-extracts text and reapplies semantic enrichment
           WITHOUT re-running the parser or geometry validation.
    """
    if not req.image_path or not os.path.isfile(req.image_path):
        raise HTTPException(
            status_code=400,
            detail=f"image_path not found: {req.image_path!r}. "
                   "Re-upload the floor plan or supply the path returned by /api/upload.",
        )

    state = PipelineState(image_path=req.image_path, scene_graph=req.scene_graph)

    try:
        ocr_result = ocr_extraction_node(state)
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    new_sg = ocr_result.get("scene_graph", req.scene_graph)
    return {
        "status": ocr_result.get("status", "unknown"),
        "scene_graph": new_sg,
        "audit_log": ocr_result.get("audit_log", []),
    }

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
