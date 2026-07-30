"""Ollama (local) provider.

Talks to a local Ollama daemon on ``http://localhost:11434`` via its
OpenAI-compatible chat endpoint. Falls back to the native ``/api/chat``
endpoint if the OpenAI compatibility layer is unavailable.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .base import (
    CompletionRequest,
    CompletionResult,
    Message,
    ProviderUnavailable,
)


class OllamaProvider:
    name = "ollama"

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.1")

    def is_available(self) -> bool:
        try:
            import urllib.request
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=1) as resp:
                return resp.status == 200
        except Exception:
            return False

    def complete(self, request: CompletionRequest) -> CompletionResult:
        try:
            import urllib.request
        except ImportError as exc:  # pragma: no cover
            raise ProviderUnavailable("OllamaProvider: urllib missing") from exc

        url = f"{self.base_url}/api/chat"
        messages: List[Dict[str, Any]] = []
        for msg in request.messages:
            images = [img.data for img in msg.images]
            entry: Dict[str, Any] = {"role": msg.role, "content": msg.content}
            if images:
                entry["images"] = images
            messages.append(entry)

        payload: Dict[str, Any] = {
            "model": request.model or self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }
        if request.json_schema is not None:
            payload["format"] = request.json_schema
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise ProviderUnavailable(f"OllamaProvider: {exc}") from exc
        text = data.get("message", {}).get("content", "")
        structured: Optional[Dict[str, Any]] = None
        if request.json_schema is not None:
            try:
                structured = json.loads(text)
            except json.JSONDecodeError:
                structured = None
        return CompletionResult(text=text, structured=structured, provider=self.name, model=self.model)


__all__ = ["OllamaProvider"]