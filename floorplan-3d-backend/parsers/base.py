from abc import ABC, abstractmethod
import sys
import os

# Add parent directory to path so we can import schema
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import SceneGraph

class BaseFloorPlanParser(ABC):
    """
    Abstract base class for all floor plan parsers.
    """
    
    @abstractmethod
    def parse(self, image_path: str) -> SceneGraph:
        """
        Parses an input image and returns a canonical SceneGraph.
        """
        pass
