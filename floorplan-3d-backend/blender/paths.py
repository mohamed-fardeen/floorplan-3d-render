"""Shared Blender executable discovery."""

from __future__ import annotations

import os
import shutil
from typing import List


def find_blender_executable() -> str | None:
    """Search PATH and common install locations for a Blender binary."""
    candidates: List[str] = [
        "blender",
        r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
        "/usr/bin/blender",
        "/Applications/Blender.app/Contents/MacOS/Blender",
    ]

    foundation = r"C:\Program Files\Blender Foundation"
    if os.path.isdir(foundation):
        for name in sorted(os.listdir(foundation), reverse=True):
            candidates.append(os.path.join(foundation, name, "blender.exe"))

    seen: set[str] = set()
    for c in candidates:
        norm = os.path.normcase(os.path.normpath(c))
        if norm in seen:
            continue
        seen.add(norm)
        if shutil.which(c):
            return c
        if os.path.isfile(c):
            return c
    return None
