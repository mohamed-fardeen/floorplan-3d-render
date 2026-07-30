"""Provider registry + the project default.

``ProviderRegistry`` lets the rest of the codebase ask for a provider by
name without caring which SDK is installed. ``default_provider`` picks
the first available provider in priority order:

  1. ``openai``     (OPENAI_API_KEY)
  2. ``anthropic``  (ANTHROPIC_API_KEY)
  3. ``gemini``     (GOOGLE_API_KEY)
  4. ``ollama``     (running daemon)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .base import LLMProvider, ProviderUnavailable


@dataclass
class ProviderEntry:
    name: str
    factory: Callable[[], LLMProvider]


class ProviderRegistry:
    def __init__(self) -> None:
        self._entries: Dict[str, ProviderEntry] = {}

    def register(self, entry: ProviderEntry) -> None:
        self._entries[entry.name] = entry

    def names(self) -> List[str]:
        return list(self._entries.keys())

    def get(self, name: str) -> LLMProvider:
        entry = self._entries.get(name)
        if entry is None:
            raise KeyError(f"provider not registered: {name!r}")
        return entry.factory()

    def first_available(self) -> Optional[LLMProvider]:
        for name, entry in self._entries.items():
            try:
                provider = entry.factory()
            except Exception:
                continue
            if provider.is_available():
                return provider
            else:  # pragma: no cover
                continue
        return None


def _safe_register(reg: ProviderRegistry, name: str, factory) -> None:
    """Register only if the SDK is importable."""
    try:
        provider = factory()
    except Exception:
        return
    reg.register(ProviderEntry(name=name, factory=factory))


def default_registry() -> ProviderRegistry:
    from .openai_provider import OpenAIProvider
    from .anthropic_provider import AnthropicProvider
    from .gemini_provider import GeminiProvider
    from .ollama_provider import OllamaProvider

    reg = ProviderRegistry()
    _safe_register(reg, "openai", OpenAIProvider)
    _safe_register(reg, "anthropic", AnthropicProvider)
    _safe_register(reg, "gemini", GeminiProvider)
    _safe_register(reg, "ollama", OllamaProvider)
    return reg


def default_provider(name: Optional[str] = None) -> LLMProvider:
    """Return the configured provider.

    - If ``name`` is given, instantiate that one (raises ``ProviderUnavailable``
      when it's missing).
    - Otherwise pick the first available provider in priority order.
    - When none are available, raise ``ProviderUnavailable`` so callers can
      fall back to the rule-based planner.
    """
    reg = default_registry()
    if name:
        return reg.get(name)
    provider = reg.first_available()
    if provider is None:
        raise ProviderUnavailable("no LLM provider is configured (set OPENAI_API_KEY etc.)")
    return provider


__all__ = [
    "ProviderRegistry",
    "ProviderEntry",
    "default_registry",
    "default_provider",
]