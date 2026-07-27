"""
parsers/adapters.py
===================
Parser adapter classes.  Each class implements BaseFloorPlanParser and returns
a canonical SceneGraph.

- CubiCasaParser  — full implementation via HuggingFace (segmentation model)
- YytsiParser     — full implementation (delegates to yytsi_parser.py)
- DeepFloorplanParser  — stub (raises NotImplementedError)
- RasterToVectorParser — stub (raises NotImplementedError)
- HuggingFaceParser    — generic stub (raises NotImplementedError)
- MockParser           — returns a simple mock SceneGraph for testing
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base import BaseFloorPlanParser
from schema import SceneGraph, Wall, Door, Window, Room, Metadata


# ---------------------------------------------------------------------------
# Yytsi (primary real parser)
# ---------------------------------------------------------------------------

class YytsiParser(BaseFloorPlanParser):
    """
    Real parser using the Yytsi/floorplan-to-3d-walls HuggingFace model.
    Delegates to parsers.yytsi_parser.YytsiParser.
    """

    def __init__(self, **kwargs):
        from parsers.yytsi_parser import YytsiParser as _YytsiParser
        self._impl = _YytsiParser(**kwargs)

    def parse(self, image_path: str) -> SceneGraph:
        return self._impl.parse(image_path)


# ---------------------------------------------------------------------------
# CubiCasa  (uses the same Yytsi UNet trained on CubiCasa5K data —
#            functionally identical at inference time for our purposes)
# ---------------------------------------------------------------------------

class CubiCasaParser(BaseFloorPlanParser):
    """
    Production CubiCasa parser.

    Uses the Yytsi model (UNet trained on CubiCasa5K) as the underlying
    inference engine.  If you later replace this with an official CubiCasa
    API or a custom-trained checkpoint, only this adapter class needs updating.
    """

    def __init__(self, **kwargs):
        from parsers.yytsi_parser import YytsiParser as _YytsiParser
        self._impl = _YytsiParser(**kwargs)

    def parse(self, image_path: str) -> SceneGraph:
        return self._impl.parse(image_path)


# ---------------------------------------------------------------------------
# Stubs — to be implemented in future phases
# ---------------------------------------------------------------------------

class DeepFloorplanParser(BaseFloorPlanParser):
    """
    DeepFloorplan (VGG + boundary-guided attention).
    Not yet integrated.
    """

    def parse(self, image_path: str) -> SceneGraph:
        raise NotImplementedError(
            "DeepFloorplanParser is not yet implemented. "
            "Set parser.provider to 'yytsi' or 'cubicasa' in config.yaml."
        )


class RasterToVectorParser(BaseFloorPlanParser):
    """
    Raster-to-Vector approach (GAN-based vectorisation).
    Not yet integrated.
    """

    def parse(self, image_path: str) -> SceneGraph:
        raise NotImplementedError(
            "RasterToVectorParser is not yet implemented. "
            "Set parser.provider to 'yytsi' or 'cubicasa' in config.yaml."
        )


class HuggingFaceParser(BaseFloorPlanParser):
    """
    Generic HuggingFace parser stub.
    Specify a concrete model_id via config.yaml to use this.
    """

    def parse(self, image_path: str) -> SceneGraph:
        raise NotImplementedError(
            "HuggingFaceParser requires a concrete model_id. "
            "Use 'yytsi' or 'cubicasa' providers instead."
        )

class MockParser(BaseFloorPlanParser):
    """
    Returns a static mock SceneGraph (a 10x10m square room with a door).
    Useful for testing the pipeline when ML dependencies are unavailable.
    """
    def parse(self, image_path: str) -> SceneGraph:
        return SceneGraph(
            metadata=Metadata(units="meters", scale_pixel_to_meter=0.0195, confidence_score=0.99),
            walls=[
                Wall(id="w1", start=(-5.0, -5.0), end=(5.0, -5.0), thickness=0.15),
                Wall(id="w2", start=(5.0, -5.0), end=(5.0, 5.0), thickness=0.15),
                Wall(id="w3", start=(5.0, 5.0), end=(-5.0, 5.0), thickness=0.15),
                Wall(id="w4", start=(-5.0, 5.0), end=(-5.0, -5.0), thickness=0.15),
            ],
            doors=[
                Door(id="d1", wall_id="w1", center=(0.0, -5.0), width=0.9)
            ],
            windows=[
                Window(id="win1", wall_id="w3", center=(0.0, 5.0), width=1.2)
            ],
            rooms=[
                Room(id="r1", type="Room", polygon=[(-5.0, -5.0), (5.0, -5.0), (5.0, 5.0), (-5.0, 5.0)], centroid=(0.0, 0.0))
            ]
        )

