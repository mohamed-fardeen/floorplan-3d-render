"""Structured-output schemas for agent responses.

These JSON-schema dicts are passed to LLM providers that support native
structured output (OpenAI, Gemini). Providers without it fall back to a
JSON instruction in the prompt and ``validate_json`` from
``agents/llm/base.py``.
"""

from __future__ import annotations

from typing import Any, Dict


DESIGN_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["operations"],
    "properties": {
        "operations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["type"],
                "properties": {
                    "type": {"type": "string", "enum": ["apply_pattern", "set_color", "set_material_preset"]},
                    "pattern": {"type": "string"},
                    "value": {"type": "string"},
                    "preset": {"type": "string"},
                },
            },
        },
        "recommendations": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
}


GEOMETRY_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["tool_calls"],
    "properties": {
        "tool_calls": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["tool", "arguments"],
                "properties": {
                    "tool": {"type": "string"},
                    "arguments": {"type": "object"},
                },
            },
        },
        "recommendations": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
}


ORCHESTRATOR_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["intent"],
    "properties": {
        "intent": {"type": "string", "enum": ["design", "geometry", "mixed", "clarify", "reject"]},
        "invoked_agents": {"type": "array", "items": {"type": "string"}},
        "clarification": {"type": "string"},
        "reason": {"type": "string"},
    },
}


SUMMARISER_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary"],
    "properties": {
        "summary": {"type": "string"},
        "active_selections": {"type": "array", "items": {"type": "string"}},
        "recent_tools": {"type": "array", "items": {"type": "string"}},
        "recent_materials": {"type": "array", "items": {"type": "string"}},
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
}


__all__ = [
    "DESIGN_OUTPUT_SCHEMA",
    "GEOMETRY_OUTPUT_SCHEMA",
    "ORCHESTRATOR_OUTPUT_SCHEMA",
    "SUMMARISER_OUTPUT_SCHEMA",
]