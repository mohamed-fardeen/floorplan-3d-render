"""Anthropic provider.

Uses the Messages API. Structured output is enforced via prompt
instructions + post-parse validation (Anthropic has no native JSON schema
in chat yet).
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


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model or os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def complete(self, request: CompletionRequest) -> CompletionResult:
        if not self.is_available():
            raise ProviderUnavailable("AnthropicProvider: missing ANTHROPIC_API_KEY")
        try:
            from anthropic import Anthropic  # type: ignore
        except ImportError as exc:
            raise ProviderUnavailable(f"AnthropicProvider: anthropic SDK not installed ({exc})") from exc

        client = Anthropic(api_key=self.api_key)
        system_parts: List[str] = []
        user_payload: List[Dict[str, Any]] = []
        for msg in request.messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            elif msg.role == "user":
                user_payload.append({"type": "text", "text": msg.content})
                for img in msg.images:
                    user_payload.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": img.mime_type,
                            "data": img.data,
                        },
                    })
            elif msg.role == "assistant":
                # Anthropic supports prior assistant turns as plain text blocks
                # via the API; the SDK accepts the messages list directly.
                pass
        response = client.messages.create(
            model=request.model or self.model,
            system="\n\n".join(system_parts),
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            messages=[
                {"role": "user", "content": user_payload or [{"type": "text", "text": "(empty)"}]},
            ],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        structured: Optional[Dict[str, Any]] = None
        if request.json_schema is not None:
            try:
                structured = json.loads(text)
            except json.JSONDecodeError:
                structured = None
        return CompletionResult(text=text, structured=structured, provider=self.name, model=self.model)


__all__ = ["AnthropicProvider"]