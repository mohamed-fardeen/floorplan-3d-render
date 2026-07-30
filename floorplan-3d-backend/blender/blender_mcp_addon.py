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
    if kind == "export_glb":
        return _export_glb(cmd)
    if kind == "execute_code":
        return _execute_code(cmd)
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