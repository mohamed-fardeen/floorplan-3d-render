"""
parsers/yolo_parser.py
=======================
YOLO-based detector for floor plan architectural symbols.

Model : SamirShabani/Architect  (YOLOv8m, FloorPlanCAD, 28 classes)
        Loaded automatically from HuggingFace Hub via the ultralytics package.
        Falls back to GreenMap/yolo11x-blueprint-layout-detector if primary
        model is unavailable.

Detects
-------
  Doors    : single-door, double-door, sliding-door, bifold-door, …
  Windows  : window (all variants)
  Furniture: sofa, bed, chair, dining-table, desk, bathtub, toilet, sink,
             refrigerator, washing-machine, stair, kitchen-counter, …

Output
------
  door_boxes      : List[(x1,y1,x2,y2,conf,class_name)]   pixel coords
  window_boxes    : List[(x1,y1,x2,y2,conf,class_name)]   pixel coords
  furniture_boxes : List[(x1,y1,x2,y2,conf,class_name)]   pixel coords
  door_mask       : np.ndarray (target_size×target_size)   uint8
  window_mask     : np.ndarray (target_size×target_size)   uint8
  furniture_mask  : np.ndarray (target_size×target_size)   uint8
  confidence      : dict
"""

from __future__ import annotations

import numpy as np
from typing import List, Tuple, Optional, Dict


# ---------------------------------------------------------------------------
# Model identifiers (primary + fallback)
# ---------------------------------------------------------------------------

_PRIMARY_MODEL   = "SamirShabani/Architect"
_FALLBACK_MODEL  = "GreenMap/yolo11x-blueprint-layout-detector"
_TARGET_SIZE     = 512   # output mask resolution

# Class name sets (lower-case substring match)
_DOOR_KEYWORDS      = {"door", "entrance", "gate"}
_WINDOW_KEYWORDS    = {"window"}
_FURNITURE_KEYWORDS = {
    "sofa", "couch", "bed", "chair", "table", "desk",
    "bathtub", "tub", "toilet", "sink", "basin", "refrigerator",
    "fridge", "washer", "washing", "stair", "step", "counter",
    "kitchen", "wardrobe", "cabinet", "closet", "shelf",
}

Box = Tuple[float, float, float, float, float, str]  # x1,y1,x2,y2,conf,cls


class ArchitectYOLOParser:
    """
    Floor-plan architectural symbol detector.

    Parameters
    ----------
    model_id : str
        HuggingFace / ultralytics model identifier.
    confidence : float
        Minimum YOLO confidence threshold (0–1).
    device : str | None
        ``"cuda"`` / ``"cpu"`` / ``None`` (auto).
    target_size : int
        Side length (pixels) for output binary masks.
    """

    def __init__(
        self,
        model_id:    str   = _PRIMARY_MODEL,
        confidence:  float = 0.25,
        device:      Optional[str] = None,
        target_size: int   = _TARGET_SIZE,
    ):
        self.model_id    = model_id
        self.confidence  = confidence
        self._device     = device
        self.target_size = target_size
        self._model      = None   # lazy

    # ------------------------------------------------------------------
    # Lazy loader
    # ------------------------------------------------------------------

    def _load(self):
        """Download / load model weights on first use."""
        if self._model is not None:
            return

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ImportError(
                "ultralytics is required for ArchitectYOLOParser. "
                "Install with: pip install ultralytics"
            ) from exc

        print(f"    [ArchitectYOLO] Loading model: {self.model_id}")
        try:
            self._model = YOLO(_resolve_yolo_model_path(self.model_id))
        except Exception as primary_err:
            print(
                f"    [ArchitectYOLO] Primary model failed ({primary_err}), "
                f"trying fallback: {_FALLBACK_MODEL}"
            )
            try:
                self._model = YOLO(_resolve_yolo_model_path(_FALLBACK_MODEL))
                self.model_id = _FALLBACK_MODEL
            except Exception as fallback_err:
                raise RuntimeError(
                    f"Both YOLO models failed to load.\n"
                    f"  Primary  ({_PRIMARY_MODEL}): {primary_err}\n"
                    f"  Fallback ({_FALLBACK_MODEL}): {fallback_err}\n"
                    "Make sure `ultralytics` is installed and HuggingFace Hub is reachable."
                ) from fallback_err

        print(f"    [ArchitectYOLO] Model loaded: {self.model_id}")

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def infer(self, image_path: str) -> Dict:
        """
        Run YOLO inference on *image_path*.

        Returns
        -------
        dict with keys:
            door_boxes      : List[Box]
            window_boxes    : List[Box]
            furniture_boxes : List[Box]
            door_mask       : np.ndarray (H,W) uint8
            window_mask     : np.ndarray (H,W) uint8
            furniture_mask  : np.ndarray (H,W) uint8
            confidence      : dict
        """
        self._load()

        from PIL import Image

        img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = img.size
        print(f"    [ArchitectYOLO] Inferring {image_path} ({orig_w}x{orig_h})...")

        # Run YOLO
        results = self._model.predict(
            source=image_path,
            conf=self.confidence,
            verbose=False,
            device=self._device,
        )

        door_boxes:      List[Box] = []
        window_boxes:    List[Box] = []
        furniture_boxes: List[Box] = []

        if results and results[0].boxes is not None:
            boxes   = results[0].boxes
            names   = results[0].names   # {int: str}

            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf  = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = names.get(cls_id, str(cls_id)).lower()

                if _matches(cls_name, _DOOR_KEYWORDS):
                    door_boxes.append((x1, y1, x2, y2, conf, cls_name))
                elif _matches(cls_name, _WINDOW_KEYWORDS):
                    window_boxes.append((x1, y1, x2, y2, conf, cls_name))
                elif _matches(cls_name, _FURNITURE_KEYWORDS):
                    furniture_boxes.append((x1, y1, x2, y2, conf, cls_name))

        print(
            f"    [ArchitectYOLO] Detections → "
            f"doors={len(door_boxes)}, windows={len(window_boxes)}, "
            f"furniture={len(furniture_boxes)}"
        )

        # Scale boxes → target_size coordinate space
        scale_x = self.target_size / orig_w
        scale_y = self.target_size / orig_h

        door_mask      = _boxes_to_mask(door_boxes,      orig_w, orig_h, self.target_size)
        window_mask    = _boxes_to_mask(window_boxes,    orig_w, orig_h, self.target_size)
        furniture_mask = _boxes_to_mask(furniture_boxes, orig_w, orig_h, self.target_size)

        # Rescale box coords to target_size space
        def _rescale(boxes: List[Box]) -> List[Box]:
            return [
                (x1*scale_x, y1*scale_y, x2*scale_x, y2*scale_y, c, n)
                for x1, y1, x2, y2, c, n in boxes
            ]

        conf_doors   = _mean_conf(door_boxes)
        conf_windows = _mean_conf(window_boxes)
        conf_furn    = _mean_conf(furniture_boxes)
        overall      = float(np.mean([c for c in [conf_doors, conf_windows, conf_furn] if c > 0] or [0.0]))

        return {
            "door_boxes":      _rescale(door_boxes),
            "window_boxes":    _rescale(window_boxes),
            "furniture_boxes": _rescale(furniture_boxes),
            "door_mask":       door_mask,
            "window_mask":     window_mask,
            "furniture_mask":  furniture_mask,
            "confidence": {
                "doors":     round(conf_doors,   4),
                "windows":   round(conf_windows, 4),
                "furniture": round(conf_furn,    4),
                "overall":   round(overall,      4),
            },
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _matches(name: str, keywords: set) -> bool:
    """True if any keyword is a substring of *name*."""
    return any(kw in name for kw in keywords)


def _resolve_yolo_model_path(model_id: str) -> str:
    """
    Return a local model path/load string that Ultralytics can consume.

    Some Ultralytics installs accept Hugging Face repo IDs directly, while
    others only accept local files. For HF repo IDs, download the likely weight
    artifact first, then pass the cached file path to YOLO().
    """
    import os

    if os.path.exists(model_id):
        return model_id

    is_hf_repo = "/" in model_id and not model_id.lower().endswith((".pt", ".pth"))
    if not is_hf_repo:
        return model_id

    try:
        from huggingface_hub import hf_hub_download, list_repo_files
    except ImportError as exc:
        raise ImportError(
            "huggingface_hub is required to load YOLO models from Hugging Face. "
            "Install with: pip install huggingface_hub"
        ) from exc

    files = list_repo_files(model_id)
    preferred_names = [
        "model.pt",
        "best.pt",
        "weights.pt",
        "yolo.pt",
        "Architect.pt",
        "Architect",
    ]

    for name in preferred_names:
        if name in files:
            return hf_hub_download(repo_id=model_id, filename=name)

    weight_files = [
        f for f in files
        if f.lower().endswith((".pt", ".pth")) and not f.lower().startswith("optimizer")
    ]
    if weight_files:
        return hf_hub_download(repo_id=model_id, filename=weight_files[0])

    raise FileNotFoundError(
        f"No YOLO weight file found in Hugging Face repo '{model_id}'. "
        f"Available files: {files}"
    )


def _boxes_to_mask(
    boxes: List[Box],
    orig_w: int,
    orig_h: int,
    target_size: int,
) -> np.ndarray:
    """
    Convert a list of bounding boxes to a filled binary mask at *target_size*.
    Boxes are in *original image* pixel coordinates.
    """
    mask = np.zeros((target_size, target_size), dtype=np.uint8)
    if not boxes:
        return mask

    import cv2
    scale_x = target_size / orig_w
    scale_y = target_size / orig_h

    for x1, y1, x2, y2, *_ in boxes:
        tx1 = max(0, int(x1 * scale_x))
        ty1 = max(0, int(y1 * scale_y))
        tx2 = min(target_size - 1, int(x2 * scale_x))
        ty2 = min(target_size - 1, int(y2 * scale_y))
        cv2.rectangle(mask, (tx1, ty1), (tx2, ty2), 1, thickness=-1)

    return mask


def _mean_conf(boxes: List[Box]) -> float:
    if not boxes:
        return 0.0
    return float(np.mean([b[4] for b in boxes]))
