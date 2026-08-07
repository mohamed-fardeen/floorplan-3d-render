"""Launch a Blender subprocess pre-loaded with the Floorplan MCP addon.

Strategy: one-off bootstrap that imports the addon module directly so
it works even when the addon isn't installed in Blender's user prefs.
The bootstrap also kills any other server on port 9876 (e.g. the stock
BlenderMCP addon) before starting our socket server.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from typing import List, Optional

ADDON_DIR_NAME = "floorplan_mcp_addon"
ADDON_MODULE = "floorplan_mcp_addon"
LOG_FILENAME = "blender_mcp_launch.log"


def _find_blender_executable() -> str | None:
    from blender.paths import find_blender_executable
    return find_blender_executable()


def _make_bootstrap_script(addon_dir: str, log_path: str, model_path: Optional[str] = None) -> str:
    """Build a syntactically-valid Python script that Blender runs on startup."""

    # GLB import block (only when model_path is a .glb/.gltf)
    if model_path and os.path.isfile(model_path) and model_path.lower().endswith((".glb", ".gltf")):
        glb_block = f"""\
try:
    import bpy
    for _obj in list(bpy.data.objects):
        bpy.data.objects.remove(_obj, do_unlink=True)
    bpy.ops.import_scene.gltf(filepath={model_path!r})
    _log('[bootstrap] imported GLB: ' + {model_path!r})
except Exception as _exc:
    _log('[bootstrap] GLB import failed: ' + repr(_exc))

"""
    else:
        glb_block = ""

    script = f"""\
import os, sys, traceback, socket, time

# ── logging helper ────────────────────────────────────────────────────────
_LOG = {log_path!r}

def _log(msg):
    try:
        with open(_LOG, 'a', encoding='utf-8') as _f:
            _f.write(str(msg) + '\\n')
            _f.flush()
    except Exception:
        pass
    print(msg, flush=True)

_log('[bootstrap] starting')

# ── optional GLB import ───────────────────────────────────────────────────
{glb_block}
# ── disable stock BlenderMCP addon so it doesn't own port 9876 ──────────
# The stock BlenderMCP addon (if installed) starts automatically and grabs
# port 9876 before our script runs. We disable and unregister it here.
try:
    import bpy
    _STOCK_ADDONS = ['blender_mcp', 'BlenderMCP', 'io_scene_mcp']
    for _mod_name in _STOCK_ADDONS:
        if _mod_name in bpy.context.preferences.addons:
            try:
                bpy.ops.preferences.addon_disable(module=_mod_name)
                _log('[bootstrap] disabled stock addon: ' + _mod_name)
            except Exception as _e:
                _log('[bootstrap] could not disable ' + _mod_name + ': ' + repr(_e))
        # Also try to stop any running server from the module directly
        try:
            _m = sys.modules.get(_mod_name)
            if _m and hasattr(_m, 'server') and hasattr(_m.server, 'stop'):
                _m.server.stop()
                _log('[bootstrap] stopped server from module: ' + _mod_name)
            elif _m and hasattr(_m, 'SERVER') and hasattr(_m.SERVER, 'stop'):
                _m.SERVER.stop()
                _log('[bootstrap] stopped SERVER from module: ' + _mod_name)
        except Exception as _e:
            _log('[bootstrap] stop attempt for ' + _mod_name + ': ' + repr(_e))
    # Give the port time to be released
    time.sleep(0.5)
except Exception as _exc:
    _log('[bootstrap] BlenderMCP disable step failed (non-fatal): ' + repr(_exc))

# ── load our addon from source (works without installation) ──────────────
_ADDON_DIR = {addon_dir!r}
try:
    if _ADDON_DIR not in sys.path:
        sys.path.insert(0, _ADDON_DIR)
    import floorplan_mcp_addon as _addon
    _log('[bootstrap] addon imported from: ' + _ADDON_DIR)
except Exception as _exc:
    _log('[bootstrap] FAILED to import addon: ' + repr(_exc))
    _log(traceback.format_exc())
    raise SystemExit(1)

# ── register bpy types ────────────────────────────────────────────────────
try:
    _addon.register()
    _log('[bootstrap] addon registered')
except ValueError as _ve:
    _log('[bootstrap] addon already registered (ok): ' + repr(_ve))
except Exception as _exc:
    _log('[bootstrap] register() failed: ' + repr(_exc))
    _log(traceback.format_exc())

# ── start the socket server ───────────────────────────────────────────────
try:
    _ok = _addon.SERVER.start()
    _log('[bootstrap] SERVER.start() -> ' + repr(_ok))
except Exception as _exc:
    _log('[bootstrap] SERVER.start() failed: ' + repr(_exc))
    _log(traceback.format_exc())

_log('[bootstrap] done -- floorplan MCP server thread running on port 6789')
"""
    return script


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
    """Spawn Blender with the Floorplan MCP server listening on port 9876."""
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
    bootstrap.write(_make_bootstrap_script(addon_dir, log_path, model_path=blend_path))
    bootstrap.close()

    cmd: List[str] = [exe]
    if blend_path and os.path.isfile(blend_path) and blend_path.lower().endswith(".blend"):
        cmd.append(blend_path)
    cmd.extend(["--python", bootstrap.name])

    try:
        log_file = open(log_path, "a", encoding="utf-8")
        log_file.write(f"[launcher] exec = {cmd}\n")
        log_file.flush()
        proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    except Exception as exc:
        with open(log_path, "a", encoding="utf-8") as err_log:
            err_log.write(f"[launcher] Popen failed: {exc!r}\n")
        return None

    return proc


def tail_log(path: Optional[str] = None, limit: int = 4000) -> str:
    """Read the most recent characters from the launch log."""
    addon_root = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
    log_path = path or os.path.join(addon_root, LOG_FILENAME)
    if not os.path.isfile(log_path):
        return ""
    with open(log_path, "r", encoding="utf-8") as f:
        data = f.read()
    return data[-limit:]


__all__ = ["launch_blender_with_mcp", "tail_log", "ADDON_MODULE"]