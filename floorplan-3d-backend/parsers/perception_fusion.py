"""
parsers/perception_fusion.py
==============================
Fuses outputs from Mask2Former, ArchitectYOLO, and PaddleOCR into a
single PerceptionResult.

Fusion Rules
------------
  walls       → Mask2Former  (primary, always)
  rooms       → Mask2Former  (primary, always)
  doors       → YOLO masks   (primary if any detection found)
                Mask2Former  (fallback if YOLO finds nothing AND yolo_fallback=True)
  windows     → YOLO masks   (primary if any detection found)
                Mask2Former  (fallback if YOLO finds nothing AND yolo_fallback=True)
  furniture   → YOLO masks   (only source)
  confidence  → per-model averages weighted by coverage
  raw_predictions → full box lists, OCR detections, per-model dumps
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import PerceptionResult


def fuse(
    m2f_out:  Dict[str, Any],
    yolo_out: Dict[str, Any],
    ocr_out:  List[Any],
    yolo_fallback_to_m2f: bool = True,
) -> PerceptionResult:
    """
    Combine outputs from the three perception models.

    Parameters
    ----------
    m2f_out : dict
        Output of ``Mask2FormerParser.infer()``:
        {wall_mask, room_mask, door_mask, window_mask, confidence}
    yolo_out : dict
        Output of ``ArchitectYOLOParser.infer()``:
        {door_mask, window_mask, furniture_mask,
         door_boxes, window_boxes, furniture_boxes, confidence}
    ocr_out : list
        List of ``OCRDetection`` objects from PaddleOCRAdapter.
    yolo_fallback_to_m2f : bool
        If True, use Mask2Former door/window masks when YOLO finds no
        detections for that class.

    Returns
    -------
    PerceptionResult
    """

    # ── Structural masks: always from Mask2Former ─────────────────────────
    wall_mask = m2f_out["wall_mask"]
    room_mask = m2f_out["room_mask"]

    # ── Door mask: YOLO primary, Mask2Former fallback ─────────────────────
    yolo_has_doors = yolo_out["door_mask"].any()
    if yolo_has_doors:
        door_mask = yolo_out["door_mask"]
        door_source = "yolo"
    elif yolo_fallback_to_m2f:
        door_mask = m2f_out["door_mask"]
        door_source = "segmentation_fallback"
    else:
        door_mask = np.zeros_like(wall_mask)
        door_source = "none"

    # ── Window mask: YOLO primary, Mask2Former fallback ──────────────────
    yolo_has_windows = yolo_out["window_mask"].any()
    if yolo_has_windows:
        window_mask = yolo_out["window_mask"]
        window_source = "yolo"
    elif yolo_fallback_to_m2f:
        window_mask = m2f_out["window_mask"]
        window_source = "segmentation_fallback"
    else:
        window_mask = np.zeros_like(wall_mask)
        window_source = "none"

    # ── Furniture: YOLO only ──────────────────────────────────────────────
    furniture_mask = yolo_out["furniture_mask"]

    # ── Confidence fusion ────────────────────────────────────────────────
    m2f_conf  = m2f_out.get("confidence", {})
    yolo_conf = yolo_out.get("confidence", {})

    # Walls + rooms confidence come from Mask2Former
    # Door / window confidence from whichever source was used
    door_conf   = yolo_conf.get("doors",   0.0) if yolo_has_doors   else m2f_conf.get("doors",   0.0)
    window_conf = yolo_conf.get("windows", 0.0) if yolo_has_windows else m2f_conf.get("windows", 0.0)

    confidence_scores = {
        "walls":     m2f_conf.get("walls",   0.0),
        "rooms":     m2f_conf.get("rooms",   0.0),
        "doors":     round(door_conf,   4),
        "windows":   round(window_conf, 4),
        "furniture": yolo_conf.get("furniture", 0.0),
        "overall":   round(
            float(np.mean([
                m2f_conf.get("overall", 0.0),
                yolo_conf.get("overall", 0.0),
            ])),
            4,
        ),
    }

    # ── Raw predictions: expose everything for downstream enrichment ──────
    raw_predictions: Dict[str, Any] = {
        # YOLO structured boxes (for SceneGraph builder)
        "door_boxes":      yolo_out.get("door_boxes", []),
        "window_boxes":    yolo_out.get("window_boxes", []),
        "furniture_boxes": yolo_out.get("furniture_boxes", []),
        # Source tracing
        "door_source":     door_source,
        "window_source":   window_source,
        # OCR raw detections
        "ocr_detections":  ocr_out,
        # Per-model confidence dumps
        "segmentation_confidence": m2f_conf,
        "yolo_confidence":        yolo_conf,
    }

    print(
        f"    [Fusion] wall_px={wall_mask.sum()}, room_px={room_mask.sum()}, "
        f"door_px={door_mask.sum()} ({door_source}), "
        f"window_px={window_mask.sum()} ({window_source}), "
        f"furniture_px={furniture_mask.sum()}, "
        f"ocr_regions={len(ocr_out)}, "
        f"overall_conf={confidence_scores['overall']:.3f}"
    )

    return PerceptionResult(
        wall_masks=wall_mask,
        room_masks=room_mask,
        door_masks=door_mask,
        window_masks=window_mask,
        furniture_masks=furniture_mask,
        junction_heatmaps=None,
        confidence_scores=confidence_scores,
        raw_predictions=raw_predictions,
    )
