"""Google Gemini provider.

Uses ``google-generativeai``. Supports ``response_schema`` for native
structured output.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from .base import (
    CompletionRequest,
    CompletionResult,
    ProviderUnavailable,
)


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def complete(self, request: CompletionRequest) -> CompletionResult:
        if not self.is_available():
            raise ProviderUnavailable("GeminiProvider: missing GOOGLE_API_KEY")
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError as exc:
            raise ProviderUnavailable(f"GeminiProvider: google-generativeai not installed ({exc})") from exc

        genai.configure(api_key=self.api_key)
        generation_config: Dict[str, Any] = {
            "temperature": request.temperature,
            "max_output_tokens": request.max_tokens,
        }
        if request.json_schema is not None:
            generation_config["response_mime_type"] = "application/json"
            generation_config["response_schema"] = request.json_schema

        model = genai.GenerativeModel(request.model or self.model, generation_config=generation_config)

        # Build content parts (text + images).
        parts: list[Any] = []
        for msg in request.messages:
            if msg.role == "system":
                parts.append(f"[SYSTEM]\n{msg.content}")
            elif msg.role == "user":
                parts.append(msg.content)
                for img in msg.images:
                    try:
                        import base64
                        from google.generativeai.types import content_types  # type: ignore
                        blob = content_types.Blob(
                            mime_type=img.mime_type,
                            data=base64.b64decode(img.data),
                        )
                        parts.append(blob)
                    except Exception:
                        # Fallback: pass base64 string; SDK will decode.
                        parts.append({"mime_type": img.mime_type, "data": img.data})
            elif msg.role == "assistant":
                parts.append(f"[ASSISTANT]\n{msg.content}")
        response = model.generate_content(parts)
        text = response.text or ""
        structured: Optional[Dict[str, Any]] = None
        if request.json_schema is not None:
            try:
                structured = json.loads(text)
            except json.JSONDecodeError:
                structured = None
        return CompletionResult(text=text, structured=structured, provider=self.name, model=self.model)


__all__ = ["GeminiProvider"]