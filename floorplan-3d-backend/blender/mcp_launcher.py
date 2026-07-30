"""Launch a Blender subprocess pre-loaded with the Floorplan MCP addon.

Two strategies are supported:

1. **Install into user prefs first, then launch.** The bootstrap calls
   ``bpy.ops.preferences.addon_install`` followed by
   ``bpy.ops.preferences.addon_enable``. After that the addon module is
   registered and the socket server can be started with the
   ``floorplan.start_mcp`` operator.

2. **One-off bootstrap that imports the addon module directly** when
   Blender is launched with our bootstrap script. This works even
   when the addon isn't installed (the user runs Blender once via
   "Launch" and the addon auto-registers for that session).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import List, Optional

ADDON_DIR_NAME = "floorplan_mcp_addon"
ADDON_MODULE = "floorplan_mcp_addon"
LOG_FILENAME = "blender_mcp_launch.log"


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


def _make_bootstrap_script(addon_dir: str, log_path: str) -> str:
    # The script:
    #  - adds the addon dir to sys.path so `import floorplan_mcp_addon` works
    #  - registers + enables the module
    #  - starts the socket server
    # NB: we deliberately do NOT use an f-string here so the bootstrap can
    # contain its own f-strings (escaping would print literal {{...}}).
    header = (
        "import os, sys, traceback\n"
        f"LOG = {log_path!r}\n"
        "def _log(msg):\n"
        "    try:\n"
        "        with open(LOG, 'a', encoding='utf-8') as f:\n"
        "            f.write(msg + chr(10))\n"
        "    except Exception:\n"
        "        pass\n"
        "    print(msg)\n\n"
        "_log('[bootstrap] starting')\n\n"
        "try:\n"
        f"    if {addon_dir!r} not in sys.path:\n"
        f"        sys.path.insert(0, {addon_dir!r})\n"
        "    import floorplan_mcp_addon\n"
        "    try:\n"
        "        floorplan_mcp_addon.register()\n"
        "        _log('[bootstrap] addon registered')\n"
        "    except ValueError as ve:\n"
        "        _log('[bootstrap] addon already registered: ' + repr(ve))\n"
        "    except Exception as exc:\n"
        "        _log('[bootstrap] register failed: ' + repr(exc))\n"
        "        _log(traceback.format_exc())\n"
        "        raise\n\n"
        "try:\n"
        "    ok = floorplan_mcp_addon.SERVER.start()\n"
        "    _log('[bootstrap] server.start -> ' + repr(ok))\n"
        "except Exception as exc:\n"
        "    _log('[bootstrap] server start failed: ' + repr(exc))\n"
        "    _log(traceback.format_exc())\n\n"
        "_log('[bootstrap] done — server thread running')\n"
    )
    return header


def _open_log(path: str) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"[launcher] starting at {time.time()}\n")
            f.write(f"[launcher] addon dir = {os.path.dirname(__file__)}\n")
    except Exception:
        pass


def launch_blender_with_mcp(
    blend_path: Optional[str] = None,
    log_dir: Optional[str] = None,
) -> Optional[subprocess.Popen]:
    """Spawn Blender with the MCP server listening on the default port."""
    exe = _find_blender_executable()
    if not exe:
        return None

    addon_dir = os.path.abspath(os.path.dirname(__file__))
    addon_root = os.path.dirname(addon_dir)
    log_path = os.path.join(log_dir or addon_root, LOG_FILENAME)
    _open_log(log_path)

    bootstrap = tempfile.NamedTemporaryFile(
        delete=False, suffix=".py", mode="w", encoding="utf-8"
    )
    bootstrap.write(_make_bootstrap_script(addon_dir, log_path))
    bootstrap.close()

    cmd: List[str] = [exe]
    if blend_path and os.path.isfile(blend_path):
        cmd.append(blend_path)
    # `factory-startup` runs the script after the UI is fully ready; this
    # is required for `bpy.ops.preferences.addon_*` and the socket server.
    cmd.extend(["--python", bootstrap.name, "--factory-startup"])

    try:
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"[launcher] exec = {cmd}\n")
            proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    except Exception as exc:
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"[launcher] Popen failed: {exc!r}\n")
        return None

    return proc


def tail_log(path: Optional[str] = None, limit: int = 4000) -> str:
    """Read the most recent lines from the launch log."""
    addon_root = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
    log_path = path or os.path.join(addon_root, LOG_FILENAME)
    if not os.path.isfile(log_path):
        return ""
    with open(log_path, "r", encoding="utf-8") as f:
        data = f.read()
    return data[-limit:]


__all__ = ["launch_blender_with_mcp", "tail_log", "ADDON_MODULE"]