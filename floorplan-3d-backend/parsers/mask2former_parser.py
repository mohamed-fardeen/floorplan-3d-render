"""
parsers/mask2former_parser.py
==============================
Mask2Former semantic segmentation parser for floor plan images.

Model : facebook/mask2former-swin-large-ade-semantic
Task  : Semantic segmentation (ADE20K-150 classes)
Output: Per-pixel binary masks for wall, room/floor, door, window

ADE20K-150 class indices used
------------------------------
  0  → wall
  3  → floor / room area
  8  → windowpane
 14  → door

All HuggingFace / torch imports are lazy so the module can be imported
in environments where ML deps are absent (mock/test modes).
"""

from __future__ import annotations

import numpy as np
from typing import Tuple, Optional


# ---------------------------------------------------------------------------
# ADE20K-150 class indices relevant to floor-plan parsing
# ---------------------------------------------------------------------------

_ADE_WALL       = 0
_ADE_FLOOR      = 3
_ADE_WINDOWPANE = 8
_ADE_DOOR       = 14

_DEFAULT_MODEL_ID = "facebook/mask2former-swin-large-ade-semantic"
_TARGET_SIZE      = 512   # resize output masks to this square


class Mask2FormerParser:
    """
    Semantic segmentation of floor plan images using Mask2Former.

    Parameters
    ----------
    model_id : str
        HuggingFace model repository.
    device : str | None
        ``"cuda"`` / ``"cpu"`` / ``None`` (auto-detect).
    target_size : int
        Side length (pixels) to which all output masks are resized.
    """

    def __init__(
        self,
        model_id: str = _DEFAULT_MODEL_ID,
        device:    Optional[str] = None,
        target_size: int = _TARGET_SIZE,
    ):
        self.model_id    = model_id
        self._device     = device
        self.target_size = target_size
        self._processor  = None   # lazy
        self._model      = None   # lazy

    # ------------------------------------------------------------------
    # Lazy loader
    # ------------------------------------------------------------------

    def _load(self):
        """Download / load model weights on first use."""
        if self._model is not None:
            return

        try:
            import torch
            from transformers import (
                AutoImageProcessor,
                Mask2FormerForUniversalSegmentation,
            )
        except ImportError as exc:
            raise ImportError(
                "transformers and torch are required for Mask2FormerParser. "
                "Install with: pip install transformers torch"
            ) from exc

        print(f"    [Mask2Former] Loading model: {self.model_id}")

        self._processor = AutoImageProcessor.from_pretrained(self.model_id)
        self._model = Mask2FormerForUniversalSegmentation.from_pretrained(
            self.model_id
        )

        if self._device is None:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"

        self._model = self._model.to(self._device)
        self._model.eval()
        self._torch = torch
        print(f"    [Mask2Former] Model loaded on {self._device}.")

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def infer(self, image_path: str) -> Tuple[
        np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict
    ]:
        """
        Run Mask2Former inference on *image_path*.

        Returns
        -------
        wall_mask   : np.ndarray  (H, W)  uint8  — 1 where wall predicted
        room_mask   : np.ndarray  (H, W)  uint8  — 1 where floor/room predicted
        door_mask   : np.ndarray  (H, W)  uint8  — 1 where door predicted
        window_mask : np.ndarray  (H, W)  uint8  — 1 where windowpane predicted
        confidence  : dict  {wall, rooms, doors, windows, overall}
        """
        self._load()

        from PIL import Image
        import torch
        import torch.nn.functional as F

        img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = img.size

        print(f"    [Mask2Former] Inferring {image_path} ({orig_w}x{orig_h})...")

        # Preprocess
        inputs = self._processor(images=img, return_tensors="pt")
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)

        # Post-process → semantic segmentation map (H, W) with ADE20K class IDs
        result = self._processor.post_process_semantic_segmentation(
            outputs,
            target_sizes=[(orig_h, orig_w)],
        )
        seg_map = result[0].cpu().numpy().astype(np.int32)  # (H, W)

        # Resize seg map to target_size × target_size
        import cv2
        seg_resized = cv2.resize(
            seg_map.astype(np.float32),
            (self.target_size, self.target_size),
            interpolation=cv2.INTER_NEAREST,
        ).astype(np.int32)

        # Extract binary masks
        wall_mask   = (seg_resized == _ADE_WALL).astype(np.uint8)
        room_mask   = (seg_resized == _ADE_FLOOR).astype(np.uint8)
        door_mask   = (seg_resized == _ADE_DOOR).astype(np.uint8)
        window_mask = (seg_resized == _ADE_WINDOWPANE).astype(np.uint8)

        # Morphological clean-up
        wall_mask   = _clean_mask(wall_mask,   kernel_size=5)
        room_mask   = _clean_mask(room_mask,   kernel_size=7)
        door_mask   = _clean_mask(door_mask,   kernel_size=3)
        window_mask = _clean_mask(window_mask, kernel_size=3)

        # Confidence: mean pixel fraction per class as a proxy
        total = seg_resized.size
        confidence = {
            "walls":   round(float(np.sum(wall_mask))   / total, 4),
            "rooms":   round(float(np.sum(room_mask))   / total, 4),
            "doors":   round(float(np.sum(door_mask))   / total, 4),
            "windows": round(float(np.sum(window_mask)) / total, 4),
            "overall": round(
                float(np.mean([
                    np.sum(wall_mask) / total,
                    np.sum(room_mask) / total,
                ])),
                4,
            ),
        }

        print(
            f"    [Mask2Former] Masks → wall={wall_mask.sum()}, room={room_mask.sum()}, "
            f"door={door_mask.sum()}, window={window_mask.sum()} px"
        )
        return wall_mask, room_mask, door_mask, window_mask, confidence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_mask(mask: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """Morphological open+close to remove noise and fill small holes."""
    import cv2
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    m = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  k)
    m = cv2.morphologyEx(m,    cv2.MORPH_CLOSE, k)
    return m
