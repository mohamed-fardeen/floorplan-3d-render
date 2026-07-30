"""LLM Provider abstraction.

The agents never talk to a provider directly — they ask a
``LLMProvider`` for a structured completion. Switching providers is a
configuration change, not a code change.

Out of the box we ship:

* ``OpenAIProvider``   — chat completions with structured JSON output
* ``AnthropicProvider``— Messages API, system + user messages, JSON mode
* ``GeminiProvider``   — generateContent with responseSchema
* ``OllamaProvider``   — local OpenAI-compatible endpoint

All providers must implement ``complete`` returning a
``CompletionResult`` (text + optional images) and ``structured`` which
takes a JSON schema and returns validated JSON. If a provider doesn't
support native structured output, ``structured`` falls back to a JSON
instruction in the prompt and validates locally.

A provider can be missing from the environment (no API key, no SDK).
In that case it raises ``ProviderUnavailable`` so the caller can fall
back to a different provider or the rule-based planner.
"""

from .base import (
    LLMProvider,
    CompletionRequest,
    CompletionResult,
    Message,
    ProviderUnavailable,
    LLMRole,
    ImagePart,
    validate_json,
)
from .registry import ProviderRegistry, ProviderEntry, default_provider, default_registry as default_llm_registry

__all__ = [
    "LLMProvider",
    "CompletionRequest",
    "CompletionResult",
    "Message",
    "ImagePart",
    "ProviderUnavailable",
    "LLMRole",
    "validate_json",
    "ProviderRegistry",
    "ProviderEntry",
    "default_provider",
    "default_llm_registry",
]