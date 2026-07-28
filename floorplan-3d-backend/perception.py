"""
perception.py
==============
AI Perception Node for the 2D Floor Plan Perception Pipeline.

Responsibilities
----------------
- Run the three-model multi-provider perception pipeline on a floor plan image.
- Output raw segmentation masks, detection boxes, OCR detections, and
  confidence scores — all in pixel space.
- NO topology, NO polygons, NO room graph, NO Blender awareness.

Provider modes (set via config.yaml ``perception.provider``)
------------------------------------------------------------
  multi   — Three-model pipeline (default):
              1. CubiCasa     (walls + rooms + door/window fallback)
              2. ArchitectYOLO (doors + windows + furniture)
              3. PaddleOCR     (room labels + dimensions)
  yytsi   — Legacy single-model pipeline (Yytsi UNet, kept for compatibility)
"""

from typing import Dict, Any, Tuple
import os
import yaml
import numpy as np

from schema import PerceptionResult, ParserConfidenceSchema


def run_perception(image_path: str, config_path: str = "config.yaml", model: str = None) -> PerceptionResult:
    """
    Run AI perception on *image_path*.

    Returns
    -------
    PerceptionResult
        Pixel-space segmentation masks and confidence scores.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at path: {image_path}")

    # ── Load config ──────────────────────────────────────────────────────────
    if not os.path.isabs(config_path):
        config_path = os.path.join(os.path.dirname(__file__), config_path)

    config: Dict[str, Any] = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}

    perception_cfg = config.get("perception", {})
    provider = perception_cfg.get("provider", "multi")

    if model:
        if model == "multi":
            provider = "multi"
        else:
            provider = "legacy"
            config["parser"] = {**config.get("parser", {}), "provider": model}

    print(f"    [Perception] Provider: {provider}")

    # ── Route to correct pipeline ────────────────────────────────────────────
    if provider == "multi":
        return _run_multi_model(image_path, config)
    else:
        # Legacy Yytsi single-model path (unchanged)
        return _run_legacy(image_path, config)


# ---------------------------------------------------------------------------
# Multi-model pipeline
# ---------------------------------------------------------------------------

def _run_multi_model(image_path: str, config: Dict[str, Any]) -> PerceptionResult:
    """Three-model pipeline: CubiCasa + ArchitectYOLO + PaddleOCR."""

    perception_cfg = config.get("perception", {})
    ocr_cfg        = config.get("ocr", {})
    parser_cfg     = config.get("parser", {})
    pixel_to_meter = parser_cfg.get("pixel_to_meter", 10.0 / 512)

    seg_model_id   = perception_cfg.get(
        "segmentation_model", "cubicasa/cubicasa5k"
    )
    cubicasa_repo_path = perception_cfg.get("cubicasa_repo_path", "models/cubicasa5k")
    cubicasa_weights_path = perception_cfg.get(
        "cubicasa_weights_path",
        "models/cubicasa5k/model_best_val_loss_var.pkl",
    )
    det_model_id   = perception_cfg.get(
        "detection_model", "SamirShabani/Architect"
    )
    det_conf       = perception_cfg.get("detection_confidence", 0.25)
    yolo_fallback  = perception_cfg.get(
        "yolo_fallback_to_segmentation",
        perception_cfg.get("yolo_fallback_to_m2f", True),
    )
    device         = perception_cfg.get("device", parser_cfg.get("device", None))

    # ── 1. CubiCasa ──────────────────────────────────────────────────────────
    print(f"    [Perception] Step 1/3 — CubiCasa ({seg_model_id})")
    from parsers.cubicasa_parser import CubiCasaParser
    seg = CubiCasaParser(
        model_id=seg_model_id,
        repo_path=cubicasa_repo_path,
        weights_path=cubicasa_weights_path,
        device=device,
    )
    wall_mask, room_mask, door_mask_seg, window_mask_seg, seg_conf = seg.infer(image_path)

    seg_out = {
        "wall_mask":   wall_mask,
        "room_mask":   room_mask,
        "door_mask":   door_mask_seg,
        "window_mask": window_mask_seg,
        "confidence":  seg_conf,
    }

    # ── 2. ArchitectYOLO ─────────────────────────────────────────────────────
    print(f"    [Perception] Step 2/3 — ArchitectYOLO ({det_model_id})")
    from parsers.yolo_parser import ArchitectYOLOParser
    yolo = ArchitectYOLOParser(
        model_id=det_model_id,
        confidence=det_conf,
        device=device,
    )
    yolo_out = yolo.infer(image_path)

    # ── 3. PaddleOCR ─────────────────────────────────────────────────────────
    ocr_provider = ocr_cfg.get("provider", "paddleocr")
    print(f"    [Perception] Step 3/3 — OCR ({ocr_provider})")
    ocr_detections = _run_ocr(image_path, ocr_cfg, pixel_to_meter)

    # ── 4. Fuse ───────────────────────────────────────────────────────────────
    print("    [Perception] Fusing outputs...")
    from parsers.perception_fusion import fuse
    result = fuse(seg_out, yolo_out, ocr_detections, yolo_fallback_to_m2f=yolo_fallback)

    return result


def _run_ocr(image_path: str, ocr_cfg: Dict[str, Any], pixel_to_meter: float):
    """Run OCR and return a list of OCRDetection objects."""
    provider = ocr_cfg.get("provider", "paddleocr")
    conf_thr = ocr_cfg.get("confidence_threshold", 0.6)
    lang     = ocr_cfg.get("lang", "en")

    try:
        if provider == "paddleocr":
            from ocr.adapters import PaddleOCRAdapter
            engine = PaddleOCRAdapter(
                pixel_to_meter=pixel_to_meter,
                lang=lang,
                confidence_threshold=conf_thr,
            )
            return engine.extract_text(image_path)

        elif provider == "surya":
            from ocr.adapters import SuryaOCRAdapter
            engine = SuryaOCRAdapter(pixel_to_meter=pixel_to_meter)
            return engine.extract_text(image_path)

        elif provider == "mock":
            from ocr.adapters import MockSuryaAdapter
            engine = MockSuryaAdapter()
            return engine.extract_text(image_path)

        else:
            print(f"    [Perception] Unknown OCR provider '{provider}', using mock.")
            from ocr.adapters import MockSuryaAdapter
            return MockSuryaAdapter().extract_text(image_path)

    except Exception as e:
        print(f"    [Perception] OCR failed ({e}), returning empty detections.")
        return []


# ---------------------------------------------------------------------------
# Legacy single-model pipeline (Yytsi UNet — unchanged)
# ---------------------------------------------------------------------------

def _run_legacy(image_path: str, config: Dict[str, Any]) -> PerceptionResult:
    """Original Yytsi UNet pipeline kept intact for backward compatibility."""
    parser_cfg = config.get("parser", {})
    provider   = parser_cfg.get("provider", "yytsi")

    print(f"    [Perception] Running legacy AI perception module (provider: {provider})...")

    from parsers.factory import get_parser
    parser = get_parser(
        provider,
        **{k: v for k, v in parser_cfg.items() if k in ["device", "pixel_to_meter"]}
    )

    impl = getattr(parser, "_impl", parser)
    if hasattr(impl, "_infer"):
        label_mask, prob_mask = impl._infer(image_path)

        wall_mask   = (label_mask == 2).astype(np.uint8)
        door_mask   = (label_mask == 3).astype(np.uint8)
        window_mask = (label_mask == 4).astype(np.uint8)
        room_mask   = (label_mask == 1).astype(np.uint8)

        from parsers.normalizer import normalize_confidence
        per_class_conf = getattr(impl, "_last_confidence", None)
        if per_class_conf and isinstance(per_class_conf, dict):
            conf_norm = normalize_confidence(per_class_conf)
        else:
            conf_norm = normalize_confidence(0.85)

        confidence_scores = {
            "walls":   conf_norm.walls   or 0.8,
            "doors":   conf_norm.doors   or 0.8,
            "windows": conf_norm.windows or 0.8,
            "rooms":   conf_norm.rooms   or 0.8,
            "overall": conf_norm.overall or 0.8,
        }

        return PerceptionResult(
            wall_masks=wall_mask,
            room_masks=room_mask,
            door_masks=door_mask,
            window_masks=window_mask,
            junction_heatmaps=None,
            confidence_scores=confidence_scores,
            raw_predictions={"label_mask": label_mask, "prob_mask": prob_mask},
        )
    else:
        sg = parser.parse(image_path)
        return PerceptionResult(
            wall_masks=np.zeros((512, 512), dtype=np.uint8),
            room_masks=np.zeros((512, 512), dtype=np.uint8),
            door_masks=np.zeros((512, 512), dtype=np.uint8),
            window_masks=np.zeros((512, 512), dtype=np.uint8),
            confidence_scores={"overall": sg.metadata.confidence_score},
            raw_predictions={"fallback_scene_graph": sg},
        )
