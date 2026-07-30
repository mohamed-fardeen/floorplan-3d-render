"""Versioned prompt management.

Each prompt lives in a single text file under ``agents/prompts/text/``.
Filenames are the agent key; the version is the leading ``vN_`` prefix.

Loading rules:
- If ``prompt_version`` is provided in the constructor, that exact file is loaded.
- Otherwise the lexicographically last ``vN_*.txt`` is loaded.
- ``list_versions()`` returns the available versions for testing/UI.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional


PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts", "text")


@dataclass(frozen=True)
class PromptVersion:
    key: str
    version: str  # e.g. "v1", "v2"
    path: str
    body: str


class PromptRegistry:
    def __init__(self, base_dir: str = PROMPTS_DIR) -> None:
        self.base_dir = base_dir

    def list_keys(self) -> List[str]:
        seen: Dict[str, bool] = {}
        if not os.path.isdir(self.base_dir):
            return []
        for name in os.listdir(self.base_dir):
            if name.endswith(".txt") and "_" in name:
                key = name.split("_", 1)[0]
                seen[key] = True
        return sorted(seen.keys())

    def list_versions(self, key: str) -> List[str]:
        if not os.path.isdir(self.base_dir):
            return []
        out: List[str] = []
        prefix = f"{key}_"
        for name in sorted(os.listdir(self.base_dir)):
            if name.startswith(prefix) and name.endswith(".txt"):
                ver = name[len(prefix):-4]
                out.append(ver)
        return out

    def latest_version(self, key: str) -> Optional[str]:
        versions = self.list_versions(key)
        return versions[-1] if versions else None

    def load(self, key: str, version: Optional[str] = None) -> PromptVersion:
        if version is None:
            version = self.latest_version(key)
            if version is None:
                raise FileNotFoundError(f"no prompts registered for {key!r}")
        path = os.path.join(self.base_dir, f"{key}_{version}.txt")
        with open(path, "r", encoding="utf-8") as f:
            body = f.read()
        return PromptVersion(key=key, version=version, path=path, body=body)


GLOBAL_REGISTRY = PromptRegistry()


def load(key: str, version: Optional[str] = None) -> str:
    return GLOBAL_REGISTRY.load(key, version).body


__all__ = [
    "PromptRegistry",
    "PromptVersion",
    "GLOBAL_REGISTRY",
    "load",
]