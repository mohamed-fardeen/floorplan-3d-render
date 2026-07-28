from .base import BaseOCREngine
from .adapters import MockSuryaAdapter, SuryaOCRAdapter, PaddleOCRAdapter


def get_ocr_engine(provider_name: str, **kwargs) -> BaseOCREngine:
    """
    Provider switch.

    Extra keyword arguments are forwarded to the adapter's constructor —
    useful for passing ``pixel_to_meter`` to the real Surya adapter.
    """
    provider_name = provider_name.lower().strip()

    if provider_name == "mock":
        return MockSuryaAdapter()
    elif provider_name == "surya":
        return SuryaOCRAdapter(**kwargs)
    elif provider_name in {"paddle", "paddleocr", "ppocr", "pp-ocrv6"}:
        return PaddleOCRAdapter(**kwargs)
    else:
        raise ValueError(f"Unknown OCR provider: {provider_name}")
