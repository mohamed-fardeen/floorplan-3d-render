"""
Launch a Blender subprocess pre-loaded with the Floorplan MCP addon and an
empty scene. Keeps the process handle so callers can shut it down.

This is a thin wrapper around the existing `executor._find_blender_executable`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import List, Optional

ADDON_REL_PATH = os.path.join("blender", "blender_mcp_addon.py")


def _find_blender_executable() -> str | None:
    candidates = [
        "blender",
        r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
        "/usr/bin/blender",
        "/Applications/Blender.app/Contents/MacOS/Blender",
    ]
    for c in candidates:
        if shutil.which(c):
            return c
        if os.path.isfile(c):
            return c
    return None


def _make_bootstrap_script(addon_path: str) -> str:
    return (
        "import bpy, addon_utils\n"
        f"addon_utils.enable(path_override={addon_path!r})\n"
        "try:\n"
        "    bpy.ops.floorplan_mcp.start()\n"
        "except Exception as _exc:\n"
        "    print('MCP start failed:', _exc)\n"
    )


def launch_blender_with_mcp(blend_path: Optional[str] = None) -> Optional[subprocess.Popen]:
    """Spawn Blender with the MCP server listening on the default port.

    Returns the Popen handle, or None if Blender is not installed.
    """
    exe = _find_blender_executable()
    if not exe:
        return None

    addon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ADDON_REL_PATH))
    if not os.path.isfile(addon_path):
        return None

    bootstrap = tempfile.NamedTemporaryFile(
        delete=False, suffix=".py", mode="w", encoding="utf-8"
    )
    bootstrap.write(_make_bootstrap_script(addon_path))
    bootstrap.close()

    cmd = [exe]
    if blend_path and os.path.isfile(blend_path):
        cmd.append(blend_path)
    cmd.extend(["--python", bootstrap.name])

    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)