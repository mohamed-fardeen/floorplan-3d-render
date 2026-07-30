"""OpenAI provider.

Uses the official SDK if installed (``openai>=1``). Falls back to a
plain HTTPS call otherwise. The structured output path uses
``response_format={"type": "json_schema", ...}`` when a schema is given.
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


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def complete(self, request: CompletionRequest) -> CompletionResult:
        if not self.is_available():
            raise ProviderUnavailable("OpenAIProvider: missing OPENAI_API_KEY")
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:
            raise ProviderUnavailable(f"OpenAIProvider: openai SDK not installed ({exc})") from exc

        client = OpenAI(api_key=self.api_key)
        messages = self._build_messages(request)
        kwargs: Dict[str, Any] = {
            "model": request.model or self.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.json_schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured",
                    "schema": request.json_schema,
                    "strict": True,
                },
            }
        response = client.chat.completions.create(**kwargs)
        text = response.choices[0].message.content or ""
        structured: Optional[Dict[str, Any]] = None
        if request.json_schema is not None:
            try:
                structured = json.loads(text)
            except json.JSONDecodeError:
                structured = None
        return CompletionResult(
            text=text,
            structured=structured,
            provider=self.name,
            model=kwargs["model"],
        )

    def _build_messages(self, request: CompletionRequest) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for msg in request.messages:
            if msg.images:
                content: List[Dict[str, Any]] = [{"type": "text", "text": msg.content}]
                for img in msg.images:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{img.mime_type};base64,{img.data}"},
                    })
                out.append({"role": msg.role, "content": content})
            else:
                out.append({"role": msg.role, "content": msg.content})
        return out


__all__ = ["OpenAIProvider"]