"""
Blender MCP socket client.

Granular command dispatch against a running Blender instance with the
accompanying `blender_mcp_addon.py` server installed. Falls back to running
the full bpy script when granular commands are not supported.
"""

from __future__ import annotations

import json
import socket
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

BLENDER_MCP_HOST = "localhost"
BLENDER_MCP_PORTS = (9876, 9999)
SOCKET_TIMEOUT = 10


def _pick_port() -> Optional[int]:
    for port in BLENDER_MCP_PORTS:
        try:
            with socket.create_connection((BLENDER_MCP_HOST, port), timeout=2):
                return port
        except (ConnectionRefusedError, OSError):
            continue
    return None


def send_command(
    command: Dict[str, Any],
    timeout: float = 60.0,
) -> Tuple[bool, Dict[str, Any]]:
    """Send a single MCP command and wait for the JSON response."""
    port = _pick_port()
    if port is None:
        return False, {"error": "blender-mcp socket not available"}

    payload = json.dumps(command).encode() + b"\n"
    try:
        with socket.create_connection((BLENDER_MCP_HOST, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(payload)
            buf = b""
            while not buf.endswith(b"\n"):
                chunk = sock.recv(8192)
                if not chunk:
                    break
                buf += chunk
        try:
            return True, json.loads(buf.decode())
        except json.JSONDecodeError:
            return True, {"raw": buf.decode(errors="replace")}
    except (ConnectionRefusedError, OSError, socket.timeout) as exc:
        return False, {"error": str(exc)}


def assign_region_material(
    object_names: Iterable[str],
    faces_by_object: Dict[str, List[int]],
    material_name: str,
) -> Dict[str, Any]:
    return send_command(
        {
            "type": "assign_region_material",
            "object_names": list(object_names),
            "faces_by_object": faces_by_object,
            "material_name": material_name,
        }
    )


def export_glb(output_path: str) -> Dict[str, Any]:
    return send_command({"type": "export_glb", "output_path": output_path})


def ping() -> Dict[str, Any]:
    return send_command({"type": "ping"})


def is_blender_mcp_available() -> bool:
    res = ping()
    return bool(res and isinstance(res[1], dict) and res[1].get("pong") is True)