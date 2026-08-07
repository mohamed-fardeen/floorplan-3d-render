import os
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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


class AgentChatRequest(BaseModel):
    prompt: str
    selection: Dict[str, Any] = Field(default_factory=dict)
    project_id: Optional[str] = None
    conversation: Optional[List[Dict[str, Any]]] = None
    available_patterns: Optional[List[str]] = None
    available_materials: Optional[List[str]] = None
    viewport_image: Optional[str] = None  # base64-encoded PNG (data URL or raw b64)
    llm_provider: Optional[str] = None
    # Authoritative scene graph; the backend uses this to rebuild the
    # full scene (walls, corner posts, per-room floors, ceilings) before
    # executing the agent's tool invocations, so the live Blender always
    # has the latest geometry in sync with the editor.
    scene_graph: Optional[Dict[str, Any]] = None
    include_base: bool = True
    include_roof: bool = False
    material_options: Optional[Dict[str, Any]] = None


class AgentChatResponse(BaseModel):
    intent: str
    invoked_agents: List[str] = Field(default_factory=list)
    design_operations: List[Dict[str, Any]] = Field(default_factory=list)
    geometry_tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    execution_invocations: List[Dict[str, Any]] = Field(default_factory=list)
    fallback_to_script: bool = False
    clarification: Optional[str] = None
    error: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    trace_ids: List[str] = Field(default_factory=list)
    runner: Optional[Dict[str, Any]] = None
    recommendations: List[str] = Field(default_factory=list)
    explain: Dict[str, Any] = Field(default_factory=dict)
    rule_report: Optional[Dict[str, Any]] = None

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
    from design.progress import emit

    emit("validation", "Validating design actions")
    ops = [DesignOperation(**op.model_dump()) for op in req.operations]
    errors = validate_operations(ops)
    if errors:
        emit("error", "Validation failed", errors=errors)
        raise HTTPException(status_code=400, detail={"validation_errors": errors})

    selection = SelectionPayload(
        id=req.selection.id,
        meshRefs=req.selection.meshRefs,
        faceRefs=req.selection.faceRefs,
        metadata=req.selection.metadata,
    )
    emit("translation", "Translating to Blender ops")
    translated = translate_to_blender_options(
        ops,
        req.material_options.model_dump(),
        selection,
    )

    # Prefer the live MCP client when a Blender instance is reachable.
    from blender.mcp_client import (
        assign_region_material,
        export_glb,
        is_blender_mcp_available,
    )

    use_live_mcp = False
    export_paths: List[str] = []
    warnings: List[str] = []

    if is_blender_mcp_available():
        use_live_mcp = True
        emit("mcp", "Live MCP detected — regenerating full scene then applying ops")
        from blender.mcp_client import send_command
        from blender.script_builder import build_script
        import tempfile as _tf
        import os as _os

        output_dir = _os.path.abspath("output")
        _os.makedirs(output_dir, exist_ok=True)

        try:
            # Build the full script with the LATEST scene graph. This is
            # executed before any per-room material ops so the live Blender
            # always has the current geometry (walls, corner posts, per-room
            # floors, ceilings, doors, windows) fresh from the script — the
            # previous version only sent material code, which left the live
            # scene with whatever stale meshes it had before.
            tmp = _tf.NamedTemporaryFile(
                prefix="floorplan3d_live_", suffix=".py", delete=False
            )
            tmp.close()
            live_cfg = {
                "include_base": req.include_base,
                "include_roof": req.include_roof,
                "material_options": translated["material_options"],
                "region_overrides": translated["region_overrides"],
                "export": {"output_dir": output_dir, "formats": ["glb"]},
            }
            build_script(req.scene_graph, live_cfg, output_dir, tmp.name)
            with open(tmp.name, "r", encoding="utf-8") as _f:
                full_code = _f.read()
            ok, payload = send_command({"type": "execute_code", "code": full_code})
            if not ok:
                warnings.append(f"[WARN] MCP full-scene execute_code failed: {payload}")
        except Exception as exc:
            warnings.append(f"[WARN] live MCP scene rebuild failed: {exc}")
        else:
            # Bind each region's material to its face set. The full script
            # already emitted + assigned the RegionMaterial_<idx> slots, so
            # this is just a re-bind step to be safe.
            for idx, override in enumerate(translated["region_overrides"]):
                mat_name = f"RegionMaterial_{idx}"
                faces_by_object: Dict[str, List[int]] = {}
                for fr in override.get("face_refs", []) or []:
                    obj_name = fr.get("objectName") if isinstance(fr, dict) else None
                    fi = fr.get("faceIndex") if isinstance(fr, dict) else None
                    if not obj_name or fi is None:
                        continue
                    faces_by_object.setdefault(obj_name, []).append(int(fi))
                ok, payload = assign_region_material(
                    override.get("object_names", []) or [],
                    faces_by_object,
                    mat_name,
                )
                if not ok:
                    warnings.append(f"[WARN] MCP assign failed for {mat_name}: {payload}")
        # The full script already exported the GLB to <output_dir>/<project>.glb
        # so the browser hot-reloads from the existing file.
        project = (req.scene_graph.metadata.project_name or "building").replace(" ", "_")
        glb_path = _os.path.join(output_dir, f"{project}.glb")
        if _os.path.isfile(glb_path):
            export_paths = [glb_path]
        else:
            warnings.append(f"[WARN] expected GLB not on disk after MCP run: {glb_path}")

    if not use_live_mcp or not export_paths:
        state = PipelineState(
            image_path="",
            scene_graph=req.scene_graph,
            blender_options={
                "include_base": req.include_base,
                "include_roof": req.include_roof,
                "material_options": translated["material_options"],
                "region_overrides": translated["region_overrides"],
                "open_blender": False,
                "progress_emitter": emit,
            },
        )

        try:
            emit("blender", "Dispatching to Blender (script mode)")
            blender_result_dict = blender_mcp_node(state)
            br = blender_result_dict.get("blender_result")
            if not br or not br.success:
                warnings.extend(br.warnings if br else ["Unknown Blender Error"])
                emit("error", "Blender sync failed", warnings=warnings)
                return {
                    "status": "error",
                    "detail": "; ".join(warnings),
                    "export_paths": br.export_paths if br else [],
                    "warnings": warnings,
                }
            export_paths = br.export_paths
        except Exception as e:
            emit("error", f"Exception: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    emit("done", "Blender sync complete", export_paths=export_paths)
    return {
        "status": "success",
        "export_paths": export_paths,
        "warnings": warnings,
        "translated": translated,
        "live_mcp": use_live_mcp,
    }


@app.get("/api/design/stream")
async def design_stream():
    """Server-Sent Events stream of design progress."""
    from design.progress import stream
    return StreamingResponse(stream(), media_type="text/event-stream")


class LaunchMcpRequest(BaseModel):
    blend_path: Optional[str] = None


@app.post("/api/mcp/launch")
async def launch_mcp(req: Optional[LaunchMcpRequest] = None, blend_path: Optional[str] = Query(None)):
    """Spawn a Blender subprocess with the MCP addon loaded."""
    from blender.mcp_launcher import launch_blender_with_mcp, tail_log

    target_path = (req.blend_path if req else None) or blend_path
    if not target_path or not os.path.isfile(target_path):
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        if os.path.isdir(output_dir):
            candidates = []
            for root, _, files in os.walk(output_dir):
                for f in files:
                    if f.lower().endswith((".blend", ".glb", ".gltf")):
                        p = os.path.join(root, f)
                        candidates.append((os.path.getmtime(p), p))
            if candidates:
                candidates.sort(reverse=True)
                target_path = candidates[0][1]

    proc = launch_blender_with_mcp(target_path)
    if proc is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Blender executable not found. Install Blender 4.0+ and make sure "
                "it is on PATH, or place it under C:\\Program Files\\Blender Foundation\\."
            ),
        )
    return {
        "status": "started",
        "pid": proc.pid,
        "target_path": target_path,
        "log": tail_log(),
    }


@app.get("/api/mcp/status")
async def mcp_status():
    import asyncio
    from blender.mcp_client import is_blender_mcp_available, ping

    def _probe():
        available = is_blender_mcp_available()
        info = ping()[1] if available else None
        return available, info

    available, info = await asyncio.to_thread(_probe)
    return {"available": available, "info": info}


@app.get("/api/mcp/log")
async def mcp_log(limit: int = 4000):
    from blender.mcp_launcher import tail_log
    return {"log": tail_log(limit=limit)}


@app.get("/api/mcp/info")
async def mcp_info():
    """Return paths + addon module name so the browser can show install hints."""
    import shutil as _shutil
    from blender.mcp_launcher import _find_blender_executable
    exe = _find_blender_executable()
    return {
        "blender_executable": exe,
        "blender_on_path": bool(_shutil.which("blender")),
        "addon_module": "floorplan_mcp_addon",
        "socket_port": 6789,
    }


@app.post("/api/agent/chat")
async def agent_chat(req: AgentChatRequest) -> AgentChatResponse:
    """Run the multi-agent orchestrator + execution runner for a user prompt."""
    from agents import default_registry, default_provider
    from agents.llm.registry import ProviderRegistry
    from agents.orchestrator import Orchestrator
    from agents.runner import run_invocations
    from agents.tool_registry import TOOL_REGISTRY
    from agents.trace import trace

    registry = default_registry()
    available_tools = [n for n, m in TOOL_REGISTRY.items() if m.is_implemented]
    provider = None
    try:
        provider = default_provider(req.llm_provider)
    except Exception:
        provider = None

    orchestrator = Orchestrator(registry, provider=provider)
    entry = trace("api.agent_chat", project_id=req.project_id, prompt=req.prompt, provider=provider.name if provider else "rules")
    result = await orchestrator.run(
        prompt=req.prompt,
        selection=req.selection,
        project_id=req.project_id,
        conversation=req.conversation,
        available_patterns=req.available_patterns,
        available_materials=req.available_materials,
        available_tools=available_tools,
        viewport_image_b64=req.viewport_image,
    )

    runner_payload: Optional[Dict[str, Any]] = None
    if result.execution_invocations and not result.error:
        project_name = (req.project_id or "building").replace(" ", "_")

        # Rebuild the full scene in the live Blender BEFORE running the
        # agent's tool invocations. The runner only dispatches material /
        # pattern ops to the MCP, so without this step the live Blender
        # would keep whatever stale geometry it had (potentially missing
        # corner posts, per-room floors, etc.).
        if req.scene_graph is not None:
            try:
                from blender.mcp_client import is_blender_mcp_available, send_command
                from blender.script_builder import build_script
                from schema import SceneGraph
                import tempfile as _tf
                import os as _os

                if is_blender_mcp_available():
                    output_dir = _os.path.abspath("output")
                    _os.makedirs(output_dir, exist_ok=True)
                    sg = SceneGraph.model_validate(req.scene_graph)
                    tmp = _tf.NamedTemporaryFile(
                        prefix="floorplan3d_agent_", suffix=".py", delete=False
                    )
                    tmp.close()
                    cfg = {
                        "include_base": req.include_base,
                        "include_roof": req.include_roof,
                        "material_options": req.material_options or {},
                        "region_overrides": [],
                        "export": {"output_dir": output_dir, "formats": ["glb"]},
                    }
                    build_script(sg, cfg, output_dir, tmp.name)
                    with open(tmp.name, "r", encoding="utf-8") as _f:
                        full_code = _f.read()
                    ok, payload = send_command({"type": "execute_code", "code": full_code})
                    if not ok:
                        result.notes.append(f"[WARN] agent_chat scene rebuild via MCP failed: {payload}")
            except Exception as exc:
                result.notes.append(f"[WARN] agent_chat scene rebuild skipped: {exc}")

        runner_result = await run_invocations(
            invocations=result.execution_invocations,
            selection_payload=req.selection,
            project_name=project_name,
        )
        runner_payload = {
            "applied": runner_result.applied,
            "deferred": runner_result.deferred,
            "warnings": runner_result.warnings,
            "fallback_to_script": runner_result.fallback_to_script,
            "export_paths": runner_result.export_paths,
        }
        entry = trace(
            "api.agent_chat.runner",
            project_id=req.project_id,
            applied=len(runner_result.applied),
            deferred=len(runner_result.deferred),
            warnings=runner_result.warnings,
        )
        result.trace_ids.append(entry["id"])
        if runner_result.fallback_to_script:
            result.fallback_to_script = True
            result.notes.append("runner fell back to legacy script path")

    return AgentChatResponse(
        intent=result.intent,
        invoked_agents=result.invoked_agents,
        design_operations=result.design_operations,
        geometry_tool_calls=result.geometry_tool_calls,
        execution_invocations=result.execution_invocations,
        fallback_to_script=result.fallback_to_script,
        clarification=result.clarification,
        error=result.error,
        notes=result.notes,
        trace_ids=result.trace_ids,
        runner=runner_payload,
        recommendations=result.recommendations,
        explain=result.explain,
        rule_report=result.rule_report,
    )


@app.get("/api/agent/log")
async def agent_log(project_id: Optional[str] = None, limit: int = 50):
    from agents.trace import TRACE_LOG
    items = TRACE_LOG.recent(project_id=project_id, limit=limit)
    return {"items": items}


@app.get("/api/agent/providers")
async def agent_providers():
    from agents.llm.registry import default_registry as default_llm_registry
    reg = default_llm_registry()
    status = []
    for name in reg.names():
        try:
            provider = reg.get(name)
            status.append({"name": name, "available": provider.is_available()})
        except Exception:
            status.append({"name": name, "available": False})
    return {"providers": status}


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
