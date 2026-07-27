"""
executor.py
Dispatches the generated bpy script to Blender.

Primary mode : headless subprocess  (blender --background --python script.py)
Fallback mode: MCP socket           (ahujasid/blender-mcp on port 9999)

Double-launch prevention
------------------------
_running_blender holds the Popen handle for any headless Blender we launched.
Before starting a new instance we poll() the handle; if the process is still
alive we route the new script through the MCP socket that Blender exposes,
avoiding a second window opening.
"""
import subprocess
import socket
import json
import shutil
import os
from typing import Tuple, List, Optional

BLENDER_MCP_HOST = "localhost"
BLENDER_MCP_PORT = 9999
SOCKET_TIMEOUT   = 5          # seconds — only for connection probe

# Module-level reference to the last headless Blender process we launched.
# None until a process has been started; thereafter holds the Popen object.
_running_blender: Optional[subprocess.Popen] = None

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

def _mcp_socket_available() -> bool:
    """Check whether the Blender MCP socket server is listening."""
    try:
        with socket.create_connection((BLENDER_MCP_HOST, BLENDER_MCP_PORT),
                                      timeout=SOCKET_TIMEOUT):
            return True
    except (ConnectionRefusedError, OSError):
        return False

def _execute_via_socket(script_path: str) -> Tuple[bool, str]:
    """Send the script content to the running Blender MCP addon."""
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            code = f.read()

        payload = json.dumps({"type": "execute_code", "code": code}) + "\n"
        with socket.create_connection((BLENDER_MCP_HOST, BLENDER_MCP_PORT),
                                      timeout=60) as sock:
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

def _execute_headless(script_path: str, blender_exe: str) -> Tuple[bool, str, List[str]]:
    """Run Blender with the generated script, opening the UI.
    
    Stores the launched Popen handle in _running_blender so subsequent calls
    can detect that an instance is already alive.
    """
    global _running_blender
    cmd = [blender_exe, "--python", script_path]
    try:
        # Launch Blender; do NOT wait — user interacts with the window.
        proc = subprocess.Popen(cmd)
        _running_blender = proc
        return True, "Launched Blender in foreground.", []
    except FileNotFoundError:
        return False, f"Blender not found at: {blender_exe}", []
    except Exception as e:
        return False, str(e), []

def execute_script(script_path: str) -> Tuple[bool, List[str], List[str]]:
    """
    Execute the bpy script. Returns (success, export_paths, warnings).

    Execution order
    ---------------
    1. If a previously-launched headless Blender is still alive → send the
       script via its MCP socket (avoids opening a second window).
    2. Else if the MCP socket is reachable (user has Blender + addon open) →
       send via socket.
    3. Else if a Blender executable is found on disk → launch headless.
    4. Otherwise log a warning and return the script path for manual use.
    """
    global _running_blender
    warnings: List[str] = []
    export_paths: List[str] = []

    # ── Step 1: reuse an already-running headless instance via MCP ──────────
    if _running_blender is not None and _running_blender.poll() is None:
        # The process is still alive.  Route via socket if the MCP addon is
        # listening; otherwise the script will just run next time Blender is
        # restarted — emit a warning instead of spawning a duplicate.
        print("    [Executor] Existing Blender process detected — reusing via MCP socket.")
        if _mcp_socket_available():
            success, response = _execute_via_socket(script_path)
            if not success:
                warnings.append(f"[ERROR] MCP socket execution failed: {response}")
            return success, export_paths, warnings
        else:
            warnings.append(
                "[WARN] Blender is already running but MCP socket is not available. "
                "The new script was NOT sent to avoid opening a duplicate window. "
                "Enable the Blender MCP addon (port 9999) for live updates, or "
                "close the existing Blender window first."
            )
            return False, [], warnings

    # ── Step 2: MCP socket only (user has Blender open with addon) ──────────
    if _mcp_socket_available():
        print("    [Executor] MCP socket mode (user-managed Blender instance).")
        success, response = _execute_via_socket(script_path)
        if not success:
            warnings.append(f"[ERROR] MCP socket execution failed: {response}")
        return success, export_paths, warnings

    # ── Step 3: launch a new headless Blender window ────────────────────────
    blender_exe = _find_blender_executable()
    if blender_exe:
        print(f"    [Executor] Launching Blender via: {blender_exe}")
        success, stdout, w = _execute_headless(script_path, blender_exe)
        warnings += w

        # Extract export paths from stdout lines (only meaningful when blocking)
        for line in stdout.splitlines():
            for marker in ["Exported GLB ->", "Exported FBX ->", "Exported OBJ ->", "Saved .blend ->"]:
                if marker in line:
                    export_paths.append(line.split("->")[-1].strip())

        if not success:
            warnings.append(f"[ERROR] Headless execution failed. stdout: {stdout[:500]}")

        return success, export_paths, warnings

    # ── Step 4: nothing found ────────────────────────────────────────────────
    msg = (
        "[WARN] Blender not found and MCP socket not available. "
        "Script generated but not executed. "
        f"To run manually: blender --background --python {script_path}"
    )
    warnings.append(msg)
    return False, [], warnings
