# Blender MCP addon (server).
#
# Install this addon into Blender (Edit > Preferences > Add-ons > Install
# from Disk… pick `blender_mcp_addon.py`). Enable it, then start the socket
# server from the 3D View > Sidebar (N) > "MCP" tab.
#
# Once running, the `mcp_client.py` backend can send granular commands
# without having to regenerate and re-run the entire bpy script on each
# material edit.
#
# Wire protocol: newline-delimited JSON. Each command is a single object;
# the response is a single object terminated by a newline.

bl_info = {
    "name": "Floorplan 3D MCP Server",
    "author": "Floorplan 3D",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > MCP",
    "description": "Live MCP server for Floorplan 3D editor (assign material, export GLB).",
    "category": "Development",
}

import json
import socket
import threading

import bpy

HOST = "localhost"
PORTS = (9876, 9999)


def _send(sock: socket.socket, payload: dict) -> None:
    sock.sendall((json.dumps(payload) + "\n").encode())


def _handle_command(cmd: dict) -> dict:
    kind = cmd.get("type")
    if kind == "ping":
        return {"pong": True}
    if kind == "assign_region_material":
        return _assign_region_material(cmd)
    if kind == "set_object_color":
        return _set_object_color(cmd)
    if kind == "set_object_pattern":
        return _set_object_pattern(cmd)
    if kind == "export_glb":
        return _export_glb(cmd)
    if kind == "execute_code":
        return _execute_code(cmd)
    if kind == "tool_dispatch":
        # Generic dispatch through geometry_handlers.py / patterns / etc.
        try:
            from . import geometry_handlers as _gh
        except ImportError:  # in-tree addons use absolute import
            import geometry_handlers as _gh  # type: ignore
        return _gh.dispatch(cmd.get("tool", ""), cmd)
    return {"error": f"unknown command type: {kind!r}"}


def _assign_region_material(cmd: dict) -> dict:
    obj_names = set(cmd.get("object_names", []) or [])
    faces_by_object = cmd.get("faces_by_object", {}) or {}
    mat_name = cmd.get("material_name")
    mat = bpy.data.materials.get(mat_name) if mat_name else None
    if mat is None:
        return {"error": f"material not found: {mat_name!r}"}

    applied: list[str] = []
    for obj in bpy.data.objects:
        if obj.name not in obj_names:
            continue
        if obj.type != "MESH" or not obj.data:
            continue
        # Ensure material slot exists.
        slot = -1
        for i, m in enumerate(obj.data.materials):
            if m is mat:
                slot = i
                break
        if slot < 0:
            obj.data.materials.append(mat)
            slot = len(obj.data.materials) - 1
        faces = faces_by_object.get(obj.name)
        if faces:
            face_set = set(int(f) for f in faces)
            for poly in obj.data.polygons:
                if poly.index in face_set:
                    poly.material_index = slot
        else:
            for poly in obj.data.polygons:
                poly.material_index = slot
        obj.active_material_index = slot
        applied.append(obj.name)
    return {"ok": True, "applied": applied}


def _set_object_color(cmd: dict) -> dict:
    obj_name = cmd.get("object")
    color_hex = cmd.get("color") or "#FFFFFF"
    obj = bpy.data.objects.get(obj_name) if obj_name else None
    if obj is None or obj.type != "MESH" or not obj.data:
        return {"error": f"object not found: {obj_name!r}"}
    if not (isinstance(color_hex, str) and len(color_hex) == 7 and color_hex.startswith("#")):
        return {"error": f"invalid color: {color_hex!r}"}

    mat_name = f"Color_{obj_name}"
    if mat_name in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[mat_name])
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    tree = mat.node_tree
    for n in list(tree.nodes):
        tree.nodes.remove(n)
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    r = int(color_hex[1:3], 16) / 255
    g = int(color_hex[3:5], 16) / 255
    b = int(color_hex[5:7], 16) / 255
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    mat.diffuse_color = (r, g, b, 1.0)

    slot = -1
    for i, m in enumerate(obj.data.materials):
        if m is mat:
            slot = i
            break
    if slot < 0:
        obj.data.materials.append(mat)
        slot = len(obj.data.materials) - 1
    for poly in obj.data.polygons:
        poly.material_index = slot
    obj.active_material_index = slot
    return {"ok": True, "material": mat_name}


def _set_object_pattern(cmd: dict) -> dict:
    obj_name = cmd.get("object")
    pattern = cmd.get("pattern") or "none"
    obj = bpy.data.objects.get(obj_name) if obj_name else None
    if obj is None or obj.type != "MESH" or not obj.data:
        return {"error": f"object not found: {obj_name!r}"}
    if pattern not in {"none", "smooth", "stacked_coils", "woven_rope"}:
        return {"error": f"unsupported pattern: {pattern!r}"}

    mat_name = f"Pattern_{obj_name}_{pattern}"
    if mat_name in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[mat_name])
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    tree = mat.node_tree
    for n in list(tree.nodes):
        tree.nodes.remove(n)
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (0.84, 0.78, 0.71, 1.0)
    mat.diffuse_color = (0.84, 0.78, 0.71, 1.0)

    if pattern in {"stacked_coils", "woven_rope"}:
        geo = tree.nodes.new("ShaderNodeNewGeometry")
        sep = tree.nodes.new("ShaderNodeSeparateXYZ")
        tree.links.new(geo.outputs["Position"], sep.inputs["Vector"])
        scale = tree.nodes.new("ShaderNodeMath")
        scale.operation = "MULTIPLY"
        scale.inputs[1].default_value = 10.0
        tree.links.new(sep.outputs["Z"], scale.inputs[0])
        comb = tree.nodes.new("ShaderNodeCombineXYZ")
        comb.inputs["X"].default_value = 0.0
        comb.inputs["Y"].default_value = 0.0
        tree.links.new(scale.outputs["Value"], comb.inputs["Z"])
        wave = tree.nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.bands_direction = "Z"
        wave.inputs["Scale"].default_value = 1.0
        tree.links.new(comb.outputs["Vector"], wave.inputs["Vector"])
        ramp = tree.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.40
        ramp.color_ramp.elements.new(0.60)
        ramp.color_ramp.elements[1].position = 0.60
        tree.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
        bump = tree.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 1.0
        bump.inputs["Distance"].default_value = 0.045
        tree.links.new(ramp.outputs["Color"], bump.inputs["Height"])
        tree.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    slot = -1
    for i, m in enumerate(obj.data.materials):
        if m is mat:
            slot = i
            break
    if slot < 0:
        obj.data.materials.append(mat)
        slot = len(obj.data.materials) - 1
    for poly in obj.data.polygons:
        poly.material_index = slot
    obj.active_material_index = slot
    return {"ok": True, "material": mat_name, "pattern": pattern}


def _export_glb(cmd: dict) -> dict:
    out = cmd.get("output_path")
    if not out:
        return {"error": "output_path required"}
    try:
        bpy.ops.export_scene.gltf(
            filepath=out,
            export_format="GLB",
            export_apply=True,
            export_materials="EXPORT",
        )
    except Exception as exc:
        return {"error": f"export failed: {exc}"}
    return {"ok": True, "path": out}


def _execute_code(cmd: dict) -> dict:
    code = cmd.get("code") or ""
    try:
        exec(code, {"__name__": "__main__", "bpy": bpy})
    except Exception as exc:
        return {"error": f"execute_code failed: {exc}"}
    return {"ok": True}


class FloorplanMCP_OT_Start(bpy.types.Operator):
    bl_idname = "floorplan_mcp.start"
    bl_label = "Start MCP server"
    bl_description = "Listen on localhost:9876 for Floorplan 3D MCP commands"

    _thread: threading.Thread | None = None
    _stop = threading.Event()

    def execute(self, context):
        if FloorplanMCP_OT_Start._thread and FloorplanMCP_OT_Start._thread.is_alive():
            self.report({"WARNING"}, "MCP server already running")
            return {"CANCELLED"}
        FloorplanMCP_OT_Start._stop.clear()
        FloorplanMCP_OT_Start._thread = threading.Thread(
            target=_serve, args=(FloorplanMCP_OT_Start._stop,), daemon=True
        )
        FloorplanMCP_OT_Start._thread.start()
        self.report({"INFO"}, f"Floorplan MCP server listening on {HOST}:{PORTS[0]}")
        return {"FINISHED"}


class FloorplanMCP_OT_Stop(bpy.types.Operator):
    bl_idname = "floorplan_mcp.stop"
    bl_label = "Stop MCP server"

    def execute(self, context):
        FloorplanMCP_OT_Start._stop.set()
        self.report({"INFO"}, "Floorplan MCP server stopping")
        return {"FINISHED"}


class FloorplanMCP_PT_Panel(bpy.types.Panel):
    bl_label = "Floorplan 3D MCP"
    bl_idname = "FLOORPLAN_MCP_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MCP"

    def draw(self, context):
        col = self.layout.column(align=True)
        col.operator(FloorplanMCP_OT_Start.bl_idname, text="Start server")
        col.operator(FloorplanMCP_OT_Stop.bl_idname, text="Stop server")


def _serve(stop_event: threading.Event) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORTS[0]))
    server.listen(5)
    server.settimeout(0.5)
    while not stop_event.is_set():
        try:
            conn, _ = server.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        threading.Thread(target=_handle_client, args=(conn,), daemon=True).start()
    server.close()


def _handle_client(conn: socket.socket) -> None:
    try:
        conn.settimeout(30)
        buf = b""
        while True:
            chunk = conn.recv(8192)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                try:
                    cmd = json.loads(line.decode())
                except json.JSONDecodeError:
                    _send(conn, {"error": "invalid JSON"})
                    continue
                response = _handle_command(cmd)
                _send(conn, response)
    except OSError:
        pass
    finally:
        conn.close()


_CLASSES = (
    FloorplanMCP_OT_Start,
    FloorplanMCP_OT_Stop,
    FloorplanMCP_PT_Panel,
)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)