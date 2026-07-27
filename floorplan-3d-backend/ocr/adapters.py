"""
ocr/adapters.py
===============

Concrete OCR adapters.

- MockSuryaAdapter  — returns three hard-coded detections (used by tests).
- SuryaOCRAdapter   — real implementation backed by `surya-ocr`.
                      Heavy model imports happen lazily so the package can
                      still be loaded on machines where `surya-ocr` is not
                      installed.
- PaddleOCRAdapter  — placeholder; raise if invoked.
"""

from __future__ import annotations

import time
import logging
from typing import List, Optional

from .base import BaseOCREngine

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import OCRDetection  # noqa: E402

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Mock — original scaffolding behavior
# ─────────────────────────────────────────────────────────────────────────────

class MockSuryaAdapter(BaseOCREngine):
    """
    Simulates the Surya OCR engine for scaffolding purposes.
    Returns the same three detections every call so unit tests stay
    deterministic.
    """

    def extract_text(self, image_path: str) -> List[OCRDetection]:
        time.sleep(0.1)  # Simulate inference time
        return [
            # A label that should fall inside our mock Bedroom (0,0 to 5,5)
            OCRDetection(
                id="ocr_1",
                text="MASTER BEDROOM",
                confidence=0.98,
                bounding_box=(1.0, 1.0, 3.0, 2.0),
                polygon=[(1.0, 1.0), (3.0, 1.0), (3.0, 2.0), (1.0, 2.0)],
                language="en",
            ),
            # A dimension label near a wall (e.g., our mock wall at x=0)
            OCRDetection(
                id="ocr_2",
                text='16\' 4"',
                confidence=0.95,
                bounding_box=(-0.1, 2.0, 0.1, 2.5),
                polygon=[(-0.1, 2.0), (0.1, 2.0), (0.1, 2.5), (-0.1, 2.5)],
                language="en",
            ),
            # A project title metadata
            OCRDetection(
                id="ocr_3",
                text="PROJECT VILLA",
                confidence=0.99,
                bounding_box=(10.0, 10.0, 15.0, 11.0),
                polygon=[(10.0, 10.0), (15.0, 10.0), (15.0, 11.0), (10.0, 11.0)],
                language="en",
            ),
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Real Surya-OCR adapter
# ─────────────────────────────────────────────────────────────────────────────

class SuryaOCRAdapter(BaseOCREngine):
    """
    Real OCR adapter backed by the `surya-ocr` library.

    Parameters
    ----------
    pixel_to_meter : float
        Scale used by the parser (1 image pixel == `pixel_to_meter` metres).
        Surya returns coordinates in *pixel space*, but the rest of the
        pipeline (Scene Graph, Blender) works in metres, so we convert here.
    device : str | None
        Torch device override, e.g. ``"cpu"`` / ``"cuda:0"``.  If ``None``,
        surya picks automatically.
    languages : list[str] | None
        Languages to recognise.  ``None`` lets surya auto-detect per line.
    """

    def __init__(
        self,
        pixel_to_meter: float = 0.0195,
        device: Optional[str] = None,
        languages: Optional[List[str]] = None,
    ):
        self.pixel_to_meter = pixel_to_meter
        self.device = device
        self.languages = languages
        self._detector = None
        self._recogniser = None

    # ── Lazy model loaders ──────────────────────────────────────────────────

    def _ensure_loaded(self):
        """Instantiate the surya predictors on first use."""
        if self._recogniser is not None and self._detector is not None:
            return
        try:
            from surya.recognition import RecognitionPredictor
            from surya.detection import DetectionPredictor
        except ImportError as e:
            raise ImportError(
                "surya-ocr is not installed.  Run "
                "`pip install surya-ocr` to use the 'surya' OCR provider."
            ) from e

        kwargs = {}
        if self.device:
            kwargs["device"] = self.device
        self._detector = DetectionPredictor(**kwargs)
        self._recogniser = RecognitionPredictor(**kwargs)

    # ── Inference ──────────────────────────────────────────────────────────

    def extract_text(self, image_path: str) -> List[OCRDetection]:
        self._ensure_loaded()

        try:
            from PIL import Image
        except ImportError as e:
            raise ImportError("Pillow is required for the surya OCR provider.") from e

        image = Image.open(image_path).convert("RGB")
        logger.info("surya: running OCR on %s (%dx%d)", image_path, *image.size)

        # Newer surya versions accept languages=…; older ones do not.
        call_kwargs = {}
        if self.languages:
            call_kwargs["languages"] = self.languages

        result = self._recogniser(
            [image],
            det_predictor=self._detector,
            **call_kwargs,
        )

        # `result` is a list of RecognitionResult, one per input image.
        page = result[0]
        text_lines = getattr(page, "text_lines", None) or page.get("text_lines", [])

        detections: List[OCRDetection] = []
        scale = self.pixel_to_meter  # pixels → metres

        for idx, line in enumerate(text_lines):
            # Some surya versions return dicts; others return objects.
            text = getattr(line, "text", None) or line.get("text", "")
            confidence = (
                getattr(line, "confidence", None) or line.get("confidence", 0.0) or 0.0
            )
            polygon = (
                getattr(line, "polygon", None)
                or line.get("polygon")
                or line.get("bbox")
                or []
            )
            language = (
                getattr(line, "language", None) or line.get("language") or None
            )

            if not text or not polygon:
                continue

            # Normalise polygon to a flat list of (x, y) tuples in metres.
            poly_pts: List[tuple] = []
            for pt in polygon:
                if len(pt) >= 2:
                    x_px, y_px = float(pt[0]), float(pt[1])
                    poly_pts.append((x_px * scale, y_px * scale))

            if not poly_pts:
                continue

            xs = [p[0] for p in poly_pts]
            ys = [p[1] for p in poly_pts]
            bbox = (min(xs), min(ys), max(xs), max(ys))

            detections.append(
                OCRDetection(
                    id=f"ocr_surya_{idx}",
                    text=str(text).strip(),
                    confidence=float(confidence),
                    bounding_box=bbox,
                    polygon=poly_pts,
                    language=language,
                )
            )

        logger.info("surya: extracted %d text regions", len(detections))
        return detections


# ─────────────────────────────────────────────────────────────────────────────
# PaddleOCR placeholder
# ─────────────────────────────────────────────────────────────────────────────

class PaddleOCRAdapter(BaseOCREngine):
    """Placeholder — raise if invoked."""

    def extract_text(self, image_path: str) -> List[OCRDetection]:
        raise NotImplementedError(
            "Paddle OCR integration not yet implemented. "
            "Install paddleocr and fill in PaddleOCRAdapter.extract_text, "
            "or set ocr.provider to 'mock' / 'surya' in config.yaml."
        )
