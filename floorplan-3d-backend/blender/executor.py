"""
executor.py
Dispatches the generated bpy script to Blender.

Approve flow     : headless export only (GLB + .blend on disk, no GUI)
Open in Blender  : open the saved .blend once; skip if Blender is already running
"""
import subprocess
import socket
import json
import shutil
import os
from typing import Tuple, List, Optional

BLENDER_MCP_HOST = "localhost"
BLENDER_MCP_PORTS = (9876, 9999)
SOCKET_TIMEOUT = 5
EXECUTION_TIMEOUT = 600

_gui_blender_proc: Optional[subprocess.Popen] = None


def _find_blender_executable() -> str | None:
    """Search common install locations and PATH for a Blender binary."""
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


def _get_mcp_port() -> int | None:
    """Return the first reachable Blender MCP port."""
    for port in BLENDER_MCP_PORTS:
        try:
            with socket.create_connection((BLENDER_MCP_HOST, port), timeout=SOCKET_TIMEOUT):
                return port
        except (ConnectionRefusedError, OSError):
            continue
    return None


def _extract_export_paths(stdout: str) -> List[str]:
    export_paths: List[str] = []
    for line in stdout.splitlines():
        for marker in ["Exported GLB ->", "Exported FBX ->", "Exported OBJ ->", "Saved .blend ->"]:
            if marker in line:
                export_paths.append(line.split("->")[-1].strip())
    return export_paths


def _execute_via_socket(script_path: str) -> Tuple[bool, str]:
    """Send the script content to the running Blender MCP addon."""
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            code = f.read()

        port = _get_mcp_port()
        if port is None:
            return False, "Blender MCP socket not available."

        payload = json.dumps({"type": "execute_code", "code": code}) + "\n"
        with socket.create_connection((BLENDER_MCP_HOST, port), timeout=60) as sock:
            sock.sendall(payload.encode())
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk

        return True, response.decode(errors="replace")
    except Exception as e:
        return False, str(e)


def _execute_background(script_path: str, blender_exe: str) -> Tuple[bool, str, List[str]]:
    """Run Blender headless and wait for the script to finish."""
    cmd = [blender_exe, "--background", "--python", script_path]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        combined = "\n".join(part for part in (stdout, stderr) if part)
        return proc.returncode == 0, combined, _extract_export_paths(combined)
    except FileNotFoundError:
        return False, f"Blender not found at: {blender_exe}", []
    except subprocess.TimeoutExpired:
        return False, f"Blender timed out after {EXECUTION_TIMEOUT}s", []
    except Exception as e:
        return False, str(e), []


def _open_blend_gui(blender_exe: str, blend_path: str) -> bool:
    """Open the .blend file in Blender. Returns False if a window is already open."""
    global _gui_blender_proc

    if not os.path.isfile(blend_path):
        return False

    if _gui_blender_proc is not None and _gui_blender_proc.poll() is None:
        print("    [Executor] Blender is already open — not launching another window.")
        return False

    print(f"    [Executor] Opening Blender GUI -> {blend_path}")
    _gui_blender_proc = subprocess.Popen([blender_exe, blend_path])
    return True


def open_existing_blend(
    blend_path: str,
    expected_exports: Optional[List[str]] = None,
) -> Tuple[bool, List[str], List[str]]:
    """Open an already-exported .blend without re-running the export."""
    warnings: List[str] = []
    expected_exports = expected_exports or []

    blender_exe = _find_blender_executable()
    if not blender_exe:
        warnings.append("[ERROR] Blender executable not found.")
        return False, [], warnings

    if not os.path.isfile(blend_path):
        warnings.append(f"[ERROR] Blend file not found: {blend_path}")
        return False, [], warnings

    export_paths = [p for p in expected_exports if os.path.isfile(p)]
    if blend_path not in export_paths:
        export_paths.append(blend_path)

    opened = _open_blend_gui(blender_exe, blend_path)
    if not opened:
        warnings.append("[INFO] Blender window already open.")

    return True, export_paths, warnings


def execute_script(
    script_path: str,
    expected_exports: Optional[List[str]] = None,
    open_gui: bool = False,
) -> Tuple[bool, List[str], List[str]]:
    """
    Execute the bpy script. Returns (success, export_paths, warnings).

    By default exports headless only. Pass open_gui=True to also launch Blender.
    """
    warnings: List[str] = []
    expected_exports = expected_exports or []

    blender_exe = _find_blender_executable()
    if blender_exe:
        print(f"    [Executor] Exporting via headless Blender: {blender_exe}")
        _, output, export_paths = _execute_background(script_path, blender_exe)

        if not export_paths and expected_exports:
            export_paths = [p for p in expected_exports if os.path.isfile(p)]

        blend_path = next((p for p in export_paths if p.lower().endswith(".blend")), None)
        if blend_path is None:
            blend_path = next((p for p in expected_exports if p.lower().endswith(".blend")), None)

        has_exports = bool(export_paths) or any(os.path.isfile(p) for p in expected_exports)
        if not has_exports:
            warnings.append(f"[ERROR] Blender export produced no files. Output: {output[:800]}")
            return False, export_paths, warnings

        if open_gui and blend_path and os.path.isfile(blend_path):
            opened = _open_blend_gui(blender_exe, blend_path)
            if not opened:
                warnings.append("[INFO] Blender window already open.")

        return True, export_paths, warnings

    port = _get_mcp_port()
    if port is not None:
        print(f"    [Executor] MCP socket mode on port {port} (user-managed Blender instance).")
        success, response = _execute_via_socket(script_path)
        if not success:
            warnings.append(f"[ERROR] MCP socket execution failed: {response}")
        return success, [], warnings

    msg = (
        "[WARN] Blender not found and MCP socket not available. "
        "Script generated but not executed. "
        f"To run manually: blender --python {script_path}"
    )
    warnings.append(msg)
    return False, [], warnings
