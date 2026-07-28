"""
parsers/factory.py
==================
Returns the correct parser adapter for a given provider name string.
Parser selection is configuration-driven: changing ``parser.provider``
in config.yaml is all that is needed to switch parsers.

Supported providers
-------------------
  yytsi            — Yytsi/floorplan-to-3d-walls (HuggingFace, primary)
  cubicasa         — CubiCasa5K model (HuggingFace, same backbone as yytsi)
  mask2former      — Mask2Former swin-large semantic segmentation (facebook/)
  architect-yolo   — SamirShabani/Architect YOLOv8m (28 floor-plan classes)
  yolo             — alias for architect-yolo
  deepfloorplan    — DeepFloorplan (stub, not yet integrated)
  raster-to-vector — R2V approach (stub, not yet integrated)
  r2v              — alias for raster-to-vector
  huggingface      — generic HF stub
  hf               — alias for huggingface
"""

from __future__ import annotations

from .base import BaseFloorPlanParser
from .adapters import (
    CubiCasaParser,
    YytsiParser,
    Mask2FormerParserAdapter,
    CubiCasaSegmentationParserAdapter,
    ArchitectYOLOParserAdapter,
    DeepFloorplanParser,
    RasterToVectorParser,
    HuggingFaceParser,
    MockParser,
)

_REGISTRY: dict[str, type] = {
    "yytsi":            YytsiParser,
    "cubicasa":         CubiCasaParser,
    # New multi-model providers
    "mask2former":      Mask2FormerParserAdapter,
    "cubicasa-seg":     CubiCasaSegmentationParserAdapter,
    "architect-yolo":   ArchitectYOLOParserAdapter,
    "yolo":             ArchitectYOLOParserAdapter,
    # Stubs
    "deepfloorplan":    DeepFloorplanParser,
    "raster-to-vector": RasterToVectorParser,
    "r2v":              RasterToVectorParser,
    "huggingface":      HuggingFaceParser,
    "hf":               HuggingFaceParser,
    "mock":             MockParser,
}


def get_parser(provider_name: str, **kwargs) -> BaseFloorPlanParser:
    """
    Return an instantiated parser for *provider_name*.

    Parameters
    ----------
    provider_name : str
        One of the keys in the registry (case-insensitive).
    **kwargs
        Forwarded to the parser constructor (e.g. ``pixel_to_meter``,
        ``device``).

    Raises
    ------
    ValueError
        If *provider_name* is not recognised.
    """
    key = provider_name.lower().strip()
    cls = _REGISTRY.get(key)
    if cls is None:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise ValueError(
            f"Unknown parser provider: '{provider_name}'. "
            f"Available providers: {available}"
        )
    return cls(**kwargs)


def list_providers() -> list[str]:
    """Return a sorted list of all registered provider names."""
    return sorted(set(_REGISTRY.keys()))
