from __future__ import annotations

import logging

from .base import BaseOCREngine
from .adapters import MockSuryaAdapter, SuryaOCRAdapter, PaddleOCRAdapter

logger = logging.getLogger(__name__)


def get_ocr_engine(provider_name: str, **kwargs) -> BaseOCREngine:
    """
    Provider switch.

    Extra keyword arguments are forwarded to the adapter's constructor —
    useful for passing ``pixel_to_meter`` to the real Surya adapter.

    Falls back to the mock provider if the requested real provider can't be
    loaded (missing dependency, version mismatch, etc.). This keeps the
    pipeline running while logging the real failure.
    """
    provider_name = (provider_name or "mock").lower().strip()

    if provider_name == "mock":
        return MockSuryaAdapter()

    if provider_name == "surya":
        try:
            return SuryaOCRAdapter(**kwargs)
        except Exception as exc:
            logger.warning("Surya OCR unavailable (%s); falling back to mock", exc)
            return MockSuryaAdapter()

    if provider_name in {"paddle", "paddleocr", "ppocr", "pp-ocrv6"}:
        try:
            return PaddleOCRAdapter(**kwargs)
        except Exception as exc:
            logger.warning("PaddleOCR unavailable (%s); falling back to mock", exc)
            return MockSuryaAdapter()

    logger.warning("Unknown OCR provider %r; falling back to mock", provider_name)
    return MockSuryaAdapter()


__all__ = ["get_ocr_engine"]