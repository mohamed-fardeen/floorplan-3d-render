import os, sys, traceback, socket, time

# ── logging helper ────────────────────────────────────────────────────────
_LOG = 'c:\\Users\\Abdullah\\Documents\\3d\\floorplan-3d-backend\\blender_mcp_launch.log'

def _log(msg):
    try:
        with open(_LOG, 'a', encoding='utf-8') as _f:
            _f.write(str(msg) + '\n')
    except Exception:
        pass
    print(msg)

_log('[bootstrap] starting')

# ── optional GLB import ───────────────────────────────────────────────────

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
_ADDON_DIR = 'c:\\Users\\Abdullah\\Documents\\3d\\floorplan-3d-backend\\blender'
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

_log('[bootstrap] done -- floorplan MCP server thread running on port 9876')
