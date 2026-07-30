"""LLM Provider data structures.

Every provider speaks these three messages: ``system``, ``user`` and
``assistant``. Vision providers also accept base64 images attached to a
user message.

Concrete providers live in sibling modules:

* ``openai_provider.py``
* ``anthropic_provider.py``
* ``gemini_provider.py``
* ``ollama_provider.py``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Union


LLMRole = Literal["system", "user", "assistant"]


@dataclass
class ImagePart:
    """Base64 image attached to a user message."""

    data: str  # base64-encoded image bytes
    mime_type: str = "image/png"


@dataclass
class Message:
    role: LLMRole
    content: str
    images: List[ImagePart] = field(default_factory=list)


@dataclass
class CompletionRequest:
    messages: List[Message]
    model: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 1024
    json_schema: Optional[Dict[str, Any]] = None  # if set, request structured output


@dataclass
class CompletionResult:
    text: str
    structured: Optional[Dict[str, Any]] = None
    provider: str = ""
    model: str = ""
    raw: Optional[Dict[str, Any]] = None


class ProviderUnavailable(RuntimeError):
    """Raised when a provider is requested but not configured / installed."""


class LLMProvider:
    name: str = "base"

    def is_available(self) -> bool:  # pragma: no cover - provider specific
        return False

    def complete(self, request: CompletionRequest) -> CompletionResult:  # pragma: no cover
        raise NotImplementedError

    def structured(
        self,
        request: CompletionRequest,
        schema: Dict[str, Any],
        max_retries: int = 1,
    ) -> Dict[str, Any]:
        """Request a JSON response matching ``schema``.

        Providers with native structured output set
        ``request.json_schema = schema`` and parse ``result.structured``.
        Providers without it send a JSON instruction and call
        ``validate_json`` to ensure the response matches ``schema``.
        """
        last_err: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            req = CompletionRequest(
                messages=list(request.messages),
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                json_schema=schema,
            )
            result = self.complete(req)
            try:
                import json
                if result.structured is None:
                    data = json.loads(result.text)
                else:
                    data = result.structured
                validate_json(data, schema)
                return data
            except Exception as exc:
                last_err = exc
                # Append a correction message and retry once.
                req.messages.append(Message(
                    role="user",
                    content=(
                        "Your previous response did not match the required schema: "
                        f"{exc}. Return only valid JSON matching the schema."
                    ),
                ))
        raise RuntimeError(f"structured() failed after retries: {last_err}")


def validate_json(data: Any, schema: Dict[str, Any]) -> None:
    """Minimal JSON-schema validator for the small subset we need.

    Supports: ``type`` (object/array/string/integer/number/boolean),
    ``properties`` with ``type`` + ``enum``, ``required``, ``items``,
    and ``additionalProperties=False``.
    """
    def fail(path: str, msg: str) -> None:
        raise ValueError(f"{path}: {msg}")

    expected = schema.get("type")
    if expected is None:
        return
    t = type(data).__name__
    mapping = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool}
    want = mapping.get(expected)
    if want is None:
        return
    if expected == "integer" and isinstance(data, bool):
        fail("$", "expected integer, got boolean")
    if not isinstance(data, want):
        fail("$", f"expected {expected}, got {t}")

    if expected == "object":
        required = schema.get("required", []) or []
        for key in required:
            if key not in data:
                fail(f".{key}", "missing required property")
        props = schema.get("properties", {}) or {}
        for key, val in data.items():
            if key in props:
                validate_json(val, props[key])
            elif schema.get("additionalProperties") is False:
                fail(f".{key}", "additional property not allowed")
    elif expected == "array":
        items = schema.get("items")
        if items is not None:
            for i, item in enumerate(data):
                validate_json(item, items)

    if "enum" in schema:
        if data not in schema["enum"]:
            fail("$", f"value not in enum {schema['enum']!r}")


__all__ = [
    "LLMProvider",
    "CompletionRequest",
    "CompletionResult",
    "Message",
    "ImagePart",
    "ProviderUnavailable",
    "LLMRole",
    "validate_json",
]