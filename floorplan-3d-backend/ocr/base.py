from abc import ABC, abstractmethod
from typing import List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import OCRDetection

class BaseOCREngine(ABC):
    @abstractmethod
    def extract_text(self, image_path: str) -> List[OCRDetection]:
        """
        Extracts text and returns a list of OCRDetection objects.
        """
        pass
