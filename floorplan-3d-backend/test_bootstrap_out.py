import os, sys, traceback, socket, time

# ── logging helper ────────────────────────────────────────────────────────
_LOG = 'c:\\Users\\Abdullah\\Documents\\3d\\floorplan-3d-backend\\test_bootstrap.log'

def _log(msg):
    try:
        with open(_LOG, 'a', encoding='utf-8') as _f:
            _f.write(str(msg) + '\n')
    except Exception:
        pass
    print(msg)

_log('[bootstrap] starting')

# ── optional GLB import ───────────────────────────────────────────────────

# ── stop any other MCP addon already listening on 9876 ───────────────────
try:
    import bpy
    if hasattr(bpy.ops, 'preferences'):
        pass  # can't easily unregister other addons, so we just try our port
except Exception:
    pass

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
