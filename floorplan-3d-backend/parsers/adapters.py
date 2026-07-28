"""
parsers/adapters.py
===================
Parser adapter classes.  Each class implements BaseFloorPlanParser and returns
a canonical SceneGraph.

- CubiCasaParser           — full implementation via HuggingFace (segmentation model)
- YytsiParser              — full implementation (delegates to yytsi_parser.py)
- Mask2FormerParserAdapter — adapter for Mask2FormerParser (semantic segmentation)
- ArchitectYOLOParserAdapter — adapter for ArchitectYOLOParser (door/window/furniture detection)
- DeepFloorplanParser      — stub (raises NotImplementedError)
- RasterToVectorParser     — stub (raises NotImplementedError)
- HuggingFaceParser        — generic stub (raises NotImplementedError)
- MockParser               — returns a simple mock SceneGraph for testing
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
# Mask2Former semantic segmentation adapter
# ---------------------------------------------------------------------------

class Mask2FormerParserAdapter(BaseFloorPlanParser):
    """
    Adapter for Mask2FormerParser (semantic segmentation).
    Wraps parsers.mask2former_parser.Mask2FormerParser and exposes
    a minimal SceneGraph via parse() for factory compatibility.
    Use perception.py _run_multi_model() for the full multi-model pipeline.
    """

    def __init__(
        self,
        model_id: str = "facebook/mask2former-swin-large-ade-semantic",
        device=None,
        **kwargs,
    ):
        from parsers.mask2former_parser import Mask2FormerParser
        self._impl = Mask2FormerParser(model_id=model_id, device=device)

    def parse(self, image_path: str) -> SceneGraph:
        import numpy as np
        wall_mask, room_mask, door_mask, window_mask, confidence = self._impl.infer(image_path)

        # Return a minimal SceneGraph; full topology is built downstream
        return SceneGraph(
            metadata=Metadata(
                units="pixels",
                scale_pixel_to_meter=10.0 / 512,
                confidence_score=confidence.get("overall", 0.0),
            ),
        )


# ---------------------------------------------------------------------------
# CubiCasa segmentation adapter
# ---------------------------------------------------------------------------

class CubiCasaSegmentationParserAdapter(BaseFloorPlanParser):
    """
    Adapter for CubiCasaParser used by the multi-model perception pipeline.
    """

    def __init__(
        self,
        model_id: str = "cubicasa/cubicasa5k",
        repo_path: str = "models/cubicasa5k",
        weights_path: str = "models/cubicasa5k/model_best_val_loss_var.pkl",
        device=None,
        **kwargs,
    ):
        from parsers.cubicasa_parser import CubiCasaParser
        self._impl = CubiCasaParser(
            model_id=model_id,
            repo_path=repo_path,
            weights_path=weights_path,
            device=device,
        )

    def parse(self, image_path: str) -> SceneGraph:
        wall_mask, room_mask, door_mask, window_mask, confidence = self._impl.infer(image_path)
        return SceneGraph(
            metadata=Metadata(
                units="pixels",
                scale_pixel_to_meter=10.0 / 512,
                confidence_score=confidence.get("overall", 0.0),
            ),
        )


# ---------------------------------------------------------------------------
# ArchitectYOLO detection adapter
# ---------------------------------------------------------------------------

class ArchitectYOLOParserAdapter(BaseFloorPlanParser):
    """
    Adapter for ArchitectYOLOParser (architectural symbol detection).
    Wraps parsers.yolo_parser.ArchitectYOLOParser and exposes
    a minimal SceneGraph via parse() for factory compatibility.
    Use perception.py _run_multi_model() for the full multi-model pipeline.
    """

    def __init__(
        self,
        model_id: str = "SamirShabani/Architect",
        confidence: float = 0.25,
        device=None,
        **kwargs,
    ):
        from parsers.yolo_parser import ArchitectYOLOParser
        self._impl = ArchitectYOLOParser(
            model_id=model_id, confidence=confidence, device=device
        )

    def parse(self, image_path: str) -> SceneGraph:
        out = self._impl.infer(image_path)

        # Build Door / Window objects from YOLO boxes for the SceneGraph
        doors = []
        for i, (x1, y1, x2, y2, conf, cls) in enumerate(out.get("door_boxes", [])):
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            doors.append(Door(id=f"d{i+1}", wall_id="w1", center=(cx, cy), width=(x2-x1)))

        windows = []
        for i, (x1, y1, x2, y2, conf, cls) in enumerate(out.get("window_boxes", [])):
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            windows.append(Window(id=f"win{i+1}", wall_id="w1", center=(cx, cy), width=(x2-x1)))

        return SceneGraph(
            metadata=Metadata(
                units="pixels",
                scale_pixel_to_meter=10.0 / 512,
                confidence_score=out["confidence"].get("overall", 0.0),
            ),
            doors=doors,
            windows=windows,
        )


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
