"""Evaluation framework for agent planning.

Each dataset entry contains:
- ``id``: short identifier
- ``prompt``: user message
- ``selection``: synthetic selection payload
- ``expected_intent``: one of design/geometry/mixed/clarify/reject
- ``expected_tools``: tools we expect to appear (subset)
- ``expected_min_operations``: minimum number of design ops expected

The ``evaluate`` function runs the orchestrator with no LLM (rules only)
or with a real provider, scores the result, and produces a ``Report``.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvalCase:
    id: str
    prompt: str
    selection: Dict[str, Any]
    expected_intent: str
    expected_tools: List[str] = field(default_factory=list)
    expected_min_operations: int = 0


def _selection(mesh: str, face_count: int = 4) -> Dict[str, Any]:
    return {
        "meshRefs": [{"objectName": mesh}],
        "faceRefs": [{"faceIndex": i} for i in range(face_count)],
        "metadata": {},
    }


DEFAULT_DATASET: List[EvalCase] = [
    EvalCase(
        id="design-sage-coils",
        prompt="Make this wall sage with stacked coils",
        selection=_selection("Wall_a"),
        expected_intent="design",
        expected_min_operations=2,
    ),
    EvalCase(
        id="geometry-curve-wall",
        prompt="Curve this wall by 0.5m on the z axis",
        selection=_selection("Wall_a"),
        expected_intent="geometry",
        expected_tools=["curve_wall"],
    ),
    EvalCase(
        id="mixed-design-geometry",
        prompt="Round this entrance and paint it white",
        selection=_selection("Wall_door_1"),
        expected_intent="mixed",
        expected_min_operations=1,
        expected_tools=["curve_wall", "bevel_region", "fillet_region", "smooth_region"],
    ),
    EvalCase(
        id="clarify-vague",
        prompt="do something",
        selection=_selection("Wall_a"),
        expected_intent="clarify",
    ),
    EvalCase(
        id="reject-no-selection",
        prompt="Make this wall sage",
        selection=_selection(""),  # empty selection
        expected_intent="clarify",
    ),
    EvalCase(
        id="reject-small-talk",
        prompt="hi there",
        selection=_selection("Wall_a"),
        expected_intent="reject",
    ),
]


@dataclass
class CaseScore:
    case_id: str
    intent_correct: bool
    tool_selection_correct: bool
    validation_success: bool
    clarification_used: bool
    latency_ms: float
    notes: List[str] = field(default_factory=list)


@dataclass
class Report:
    total: int
    intent_accuracy: float
    tool_selection_accuracy: float
    clarification_rate: float
    validation_success_rate: float
    avg_latency_ms: float
    cases: List[CaseScore] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "intent_accuracy": self.intent_accuracy,
            "tool_selection_accuracy": self.tool_selection_accuracy,
            "clarification_rate": self.clarification_rate,
            "validation_success_rate": self.validation_success_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "cases": [
                {
                    "case_id": c.case_id,
                    "intent_correct": c.intent_correct,
                    "tool_selection_correct": c.tool_selection_correct,
                    "validation_success": c.validation_success,
                    "clarification_used": c.clarification_used,
                    "latency_ms": c.latency_ms,
                    "notes": c.notes,
                }
                for c in self.cases
            ],
        }


def evaluate(
    orchestrator,
    dataset: Optional[List[EvalCase]] = None,
    project_prefix: str = "eval",
) -> Report:
    dataset = dataset or DEFAULT_DATASET
    scores: List[CaseScore] = []

    async def run_case(case: EvalCase) -> CaseScore:
        t0 = time.perf_counter()
        result = await orchestrator.run(
            prompt=case.prompt,
            selection=case.selection,
            project_id=f"{project_prefix}:{case.id}",
            available_patterns=["stacked_coils", "woven_rope", "smooth", "wave", "ribbed", "brick", "honeycomb"],
            available_materials=["warm_modern", "painted_white", "sage", "navy", "charcoal"],
        )
        latency_ms = (time.perf_counter() - t0) * 1000

        intent_correct = result.intent == case.expected_intent
        tools = {inv.get("tool") for inv in result.execution_invocations}
        tools |= {call.get("tool") for call in result.geometry_tool_calls}
        tool_selection_correct = (
            not case.expected_tools
            or any(t in tools for t in case.expected_tools)
        )
        # For reject / clarify, the orchestrator intentionally sets `error`;
        # that's the expected behaviour, not a failure.
        validation_success = (
            result.error is None
            or result.intent in {"clarify", "reject"}
        )
        clarification_used = result.intent == "clarify"
        notes: List[str] = []
        if not intent_correct:
            notes.append(f"intent mismatch: {result.intent} != {case.expected_intent}")
        if not validation_success:
            notes.append(f"validation error: {result.error}")

        return CaseScore(
            case_id=case.id,
            intent_correct=intent_correct,
            tool_selection_correct=tool_selection_correct,
            validation_success=validation_success,
            clarification_used=clarification_used,
            latency_ms=latency_ms,
            notes=notes,
        )

    async def runner() -> List[CaseScore]:
        out = []
        for case in dataset:
            out.append(await run_case(case))
        return out

    scores = asyncio.run(runner())
    total = len(scores)
    return Report(
        total=total,
        intent_accuracy=sum(1 for s in scores if s.intent_correct) / max(total, 1),
        tool_selection_accuracy=sum(1 for s in scores if s.tool_selection_correct) / max(total, 1),
        clarification_rate=sum(1 for s in scores if s.clarification_used) / max(total, 1),
        validation_success_rate=sum(1 for s in scores if s.validation_success) / max(total, 1),
        avg_latency_ms=sum(s.latency_ms for s in scores) / max(total, 1),
        cases=scores,
    )


def main() -> None:
    """CLI: ``python -m agents.eval`` writes a JSON report."""
    from .orchestrator import Orchestrator
    from .registry import default_registry

    registry = default_registry()
    orch = Orchestrator(registry)
    report = evaluate(orch)
    out_path = os.environ.get("EVAL_REPORT", "agents/eval_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2)
    print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()


__all__ = ["EvalCase", "CaseScore", "Report", "DEFAULT_DATASET", "evaluate", "main"]