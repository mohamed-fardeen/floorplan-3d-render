"""Install and enable floorplan_mcp_addon via Blender CLI (background mode)."""

from __future__ import annotations

import os
import sys
import zipfile

import bpy

ADDON_MODULE = "floorplan_mcp_addon"
ADDON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "floorplan_mcp_addon")
ZIP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{ADDON_MODULE}.zip")


def _make_addon_zip() -> str:
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(ADDON_DIR):
            for name in files:
                if name.endswith(".pyc") or name == "__pycache__":
                    continue
                full = os.path.join(root, name)
                arc = os.path.join(ADDON_MODULE, os.path.relpath(full, ADDON_DIR))
                zf.write(full, arc)
    return ZIP_PATH


def main() -> int:
    if not os.path.isdir(ADDON_DIR):
        print(f"[install] addon directory not found: {ADDON_DIR}", file=sys.stderr)
        return 1

    zip_path = _make_addon_zip()
    print(f"[install] created {zip_path}")

    try:
        bpy.ops.preferences.addon_install(filepath=zip_path, overwrite=True)
        bpy.ops.preferences.addon_enable(module=ADDON_MODULE)
        bpy.ops.wm.save_userpref()
    except Exception as exc:
        print(f"[install] failed: {exc!r}", file=sys.stderr)
        return 1

    enabled = ADDON_MODULE in bpy.context.preferences.addons
    print(f"[install] module={ADDON_MODULE} enabled={enabled}")
    return 0 if enabled else 1


if __name__ == "__main__":
    raise SystemExit(main())
