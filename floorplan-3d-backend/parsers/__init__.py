"""
parsers package
===============
Public API for the floor plan parser layer.

    from parsers import get_parser, list_providers
    from parsers.normalizer import CoordinateNormalizer, normalize_confidence
    from parsers.visualization import visualize_scene_graph
    from parsers.failure_analysis import analyze_failures
"""

from .factory import get_parser, list_providers
from .base import BaseFloorPlanParser

__all__ = [
    "get_parser",
    "list_providers",
    "BaseFloorPlanParser",
]
