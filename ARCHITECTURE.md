# Floorplan 3D — Architecture (Phase 4)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                  BROWSER                                     │
│                                                                              │
│  ┌────────────┐  ┌──────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │ 3D Viewport │  │ Selection Tools  │  │ Editing Panel  │  │ AI Chat      │  │
│  │ (R3F)       │  │ (click/brush/    │  │ (color/preset/ │  │ (multi-agent │  │
│  │             │  │  box/lasso)      │  │  pattern/metric)│  │  orchestrator│  │
│  └─────┬───────┘  └────────┬─────────┘  └───────┬────────┘  └──────┬───────┘  │
│        │                   │                    │                  │          │
│        └─────────┬─────────┴────────────────────┘                  │          │
│                  ▼                                               │          │
│  ┌────────────────────────────────────────────────────┐         │          │
│  │ editorStore (Zustand) — selections, history,        │         │          │
│  │ material options, viewport options, persisted state  │         │          │
│  └─────────────────┬──────────────────────────────────┘         │          │
│                    │                                            │          │
│        ┌───────────┼───────────┬─────────────────┐              │          │
│        ▼           ▼           ▼                 ▼              ▼          │
│   selectionGe-   metrics     persistence      AI client    SceneGraph     │
│   ometry.ts      .ts         .ts (localStorage) (HTTP)       state          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼  HTTP (FastAPI)
┌──────────────────────────────────────────────────────────────────────────────┐
│                                  BACKEND                                     │
│                                                                              │
│  /api/agent/chat ──► Orchestrator                                             │
│                       │   classifies intent (design/geometry/mixed/clarify)  │
│                       ▼                                                        │
│              ┌────────┴─────────┐                                              │
│              ▼                  ▼                                              │
│       Design Agent        Geometry Agent                                       │
│              │                  │                                              │
│              └─────┬────────────┘                                              │
│                    ▼                                                           │
│          Execution Agent (dispatches Tool Invocations)                        │
│                    │                                                           │
│                    ▼                                                           │
│         Construction Rules Engine  ◄── validates before Blender dispatch       │
│                    │                                                           │
│                    ▼                                                           │
│         Runner (batched, deduped, granular progress)                          │
│                    │                                                           │
│                    ▼                                                           │
│              Blender MCP  ──►  geometry_handlers.py  ──►  live Blender       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Blender Tool Library

Defined in `agents/tool_registry.py`. 30 tools across 4 categories.

| Category | Count | Tools |
|---|---|---|
| geometry | 11 | curve_wall, bend_wall, offset_wall, extrude_region, bevel_region, fillet_region, smooth_region, split_region, merge_region, duplicate_region, project_region |
| pattern  |  9 | apply_stacked_coils, apply_wave_pattern, apply_ribbed_pattern, apply_honeycomb_pattern, apply_woven_pattern, adjust_pattern_depth, adjust_pattern_spacing, mirror_pattern, align_pattern |
| material |  5 | set_color, set_material, copy_material, mirror_material, replace_material |
| utility  |  5 | measure_area, measure_length, calculate_volume, export_glb, refresh_preview |

Each tool exposes:
- name
- description
- category
- required_params / optional_params
- supported_geometry (which object kinds it can target)
- supported_materials (which materials accept this op)
- is_implemented (orchestrator refuses to dispatch `False`)
- notes

The Orchestrator receives the registry snapshot in `request.available_tools` so it never invents tools.

## Tool Registry

`agents/tool_registry.py` — runtime metadata table. The Execution Agent consults it before dispatch; the Orchestrator uses it for capability checks.

`agents/tools.py` — fast validation table with arg schemas (`BlenderTool.validate`).

## Construction Rules

`agents/rules.py` enforces deterministic constraints before any tool runs:

| Rule | Default | Severity |
|---|---|---|
| min wall thickness | 0.05 m | error |
| max printable pattern depth | 0.08 m | warning |
| min printable pattern depth | 0.005 m | warning |
| max curvature radius | 8.0 m | warning |
| pattern spacing range | [0.02, 0.5] m | warning |
| pattern-incompatible materials | oak_wood, marble, granite | warning |

Errors abort the run. Warnings flow back to the browser in the chat response and trace log.

## Selection Workflow

The selection model remains geometry-agnostic (Phase 1). Phase 4 adds:

| Tool | Purpose |
|---|---|
| growFaces | expand to faces sharing edges |
| shrinkFaces | drop border faces |
| invertFaces | every face not currently selected |
| expandToMeshFaces | every face of every mesh in the selection |
| connectedFaces | flood-fill connected faces |

Named selections persist to the store (`namedSelections`) and can be recalled to create a fresh active selection.

## Execution Pipeline

`agents/runner.py` — invoked from `/api/agent/chat`:

1. **Dedupe** identical consecutive invocations.
2. **Batch** by `(tool, object)` to minimise MCP round-trips.
3. **Validate** against `ToolRegistry`.
4. **Dispatch** MCP commands; geometric / pattern / utility ops go through `tool_dispatch` and `geometry_handlers.py` inside the addon.
5. **Auto-export GLB** at the end of any non-utility run so the browser can hot-reload.
6. **Trace** every step into the `AgentTraceLog`.

## DesignAction Lifecycle

```
user prompt
    │
    ▼
AI Chat (browser)
    │
    ▼
Orchestrator (intent classification + agent dispatch)
    │
    ▼
Design Agent     Geometry Agent
    │                  │
    ▼                  ▼
design_operations  geometry_tool_calls
    │                  │
    └────────┬─────────┘
             ▼
Execution Agent (tool invocations)
             │
             ▼
Construction Rules Engine (validate)
             │
             ▼
Runner (dedupe + batch + dispatch)
             │
             ▼
Blender MCP live socket OR script fallback
             │
             ▼
GLB hot-reload in browser
```

## Performance notes

- GLB hot-reload uses a cache-busting `?v=` query string.
- Mesh UUIDs are invalidated on hot-reload; selections re-resolve by canonical object name.
- Selection transforms (grow/shrink/invert/connected/expandToMesh) are O(faces × iterations) on a single mesh.
- Depth-mask picking renders into an off-screen `WebGLRenderTarget` once per pick.
- The runner dedupes + batches to keep MCP round-trips minimal.

## Future agent extensions

Register new agents via `AgentRegistry.register()`. The Orchestrator will pick them up automatically when the LLM-backed planner arrives in Phase 5.