"""
Blender MCP socket client.

Granular command dispatch against a running Blender instance with the
Floorplan 3D ``floorplan_mcp_addon`` server installed.
"""

from __future__ import annotations

import json
import socket
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

BLENDER_MCP_HOST = "localhost"
BLENDER_MCP_PORTS = (6789,)
CONNECT_TIMEOUT = 2.0
PING_TIMEOUT = 3.0
COMMAND_TIMEOUT = 60.0


def _pick_port() -> Optional[int]:
    for port in BLENDER_MCP_PORTS:
        try:
            with socket.create_connection((BLENDER_MCP_HOST, port), timeout=CONNECT_TIMEOUT):
                return port
        except (ConnectionRefusedError, OSError, socket.timeout):
            continue
    return None


def send_command(
    command: Dict[str, Any],
    timeout: float = COMMAND_TIMEOUT,
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
            deadline = time.monotonic() + timeout
            while not buf.endswith(b"\n"):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False, {"error": "timeout waiting for MCP response"}
                sock.settimeout(remaining)
                chunk = sock.recv(8192)
                if not chunk:
                    break
                buf += chunk
        if not buf:
            return False, {"error": "empty MCP response (wrong addon on port?)"}
        try:
            return True, json.loads(buf.decode())
        except json.JSONDecodeError:
            return False, {
                "error": "invalid MCP response (install floorplan_mcp_addon, not BlenderMCP)",
                "raw": buf.decode(errors="replace")[:500],
            }
    except (ConnectionRefusedError, OSError, socket.timeout) as exc:
        return False, {"error": str(exc)}


def assign_region_material(
    object_names: Iterable[str],
    faces_by_object: Dict[str, List[int]],
    material_name: str,
) -> Tuple[bool, Dict[str, Any]]:
    return send_command(
        {
            "type": "assign_region_material",
            "object_names": list(object_names),
            "faces_by_object": faces_by_object,
            "material_name": material_name,
        }
    )


def export_glb(output_path: str) -> Tuple[bool, Dict[str, Any]]:
    return send_command({"type": "export_glb", "output_path": output_path})


def ping() -> Tuple[bool, Dict[str, Any]]:
    return send_command({"type": "ping"}, timeout=PING_TIMEOUT)


def is_blender_mcp_available() -> bool:
    ok, payload = ping()
    return ok and isinstance(payload, dict) and payload.get("pong") is True
