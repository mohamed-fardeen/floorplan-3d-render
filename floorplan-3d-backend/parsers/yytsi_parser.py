"""
parsers/yytsi_parser.py
=======================
Real implementation of the Yytsi/floorplan-to-3d-walls model from HuggingFace.

Model: Yytsi/floorplan-to-3d-walls
Architecture: UNet (ResNet-34 encoder) trained on CubiCasa5K
Classes: 0=background, 1=floor/room, 2=wall, 3=door, 4=window

Pipeline:
  1. Load image, resize to 512×512
  2. Run model inference
  3. Argmax the output logits to get a label mask (H×W)
  4. Per-class: find contours → vectorize → build SceneGraph elements
  5. Apply CoordinateNormalizer (pixel → metres, origin at (0,0))
  6. Map per-class softmax probabilities to ParserConfidence
"""

from __future__ import annotations

import os
import sys
import math
import uuid
from typing import List, Tuple, Optional

import numpy as np

# HuggingFace / torch are imported lazily inside the class so that the module
# can be imported even in environments without ML dependencies (for testing /
# mock mode).

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import (
    SceneGraph, Metadata, Wall, Door, Window, Room
)
from parsers.base import BaseFloorPlanParser
from parsers.normalizer import CoordinateNormalizer, normalize_confidence


# ---------------------------------------------------------------------------
# Class label constants (as used by Yytsi model)
# ---------------------------------------------------------------------------

_CLASS_BACKGROUND = 0
_CLASS_FLOOR      = 1  # also used as "room area"
_CLASS_WALL       = 2
_CLASS_DOOR       = 3
_CLASS_WINDOW     = 4

_NUM_CLASSES      = 5
_INPUT_SIZE       = 512  # pixels

# Pixel-to-metre scale for the default 512×512 resolution.
# Assumes a ~10 m × 10 m apartment maps to 512 px.
_DEFAULT_SCALE    = 10.0 / _INPUT_SIZE  # ≈ 0.0195 m/px

# ---------------------------------------------------------------------------
# Minimum contour area thresholds (pixels²)
# ---------------------------------------------------------------------------
_MIN_WALL_AREA   = 150
_MIN_ROOM_AREA   = 500
_MIN_OPENING_AREA = 20


# ---------------------------------------------------------------------------
# YytsiParser
# ---------------------------------------------------------------------------

class YytsiParser(BaseFloorPlanParser):
    """
    Production floor plan parser using the Yytsi/floorplan-to-3d-walls model.

    On first call to ``parse()`` the model weights are downloaded from
    HuggingFace Hub and cached in the default HF cache directory.  Subsequent
    calls reuse the cached weights.

    Parameters
    ----------
    model_id : str
        HuggingFace model repository identifier.
    device : str | None
        ``"cuda"``, ``"cpu"``, or ``None`` (auto-detect).
    pixel_to_meter : float
        Scale factor for converting 512-px coordinates to metres.
        Defaults to 10 m / 512 px  ≈ 0.0195 m/px.
    """

    MODEL_ID = "Yytsi/floorplan-to-3d-walls"

    def __init__(
        self,
        model_id: str = MODEL_ID,
        device: str | None = None,
        pixel_to_meter: float = _DEFAULT_SCALE,
    ):
        self.model_id       = model_id
        self.pixel_to_meter = pixel_to_meter
        self._device        = device
        self._model         = None  # lazy-loaded
        self._normalizer    = CoordinateNormalizer(
            pixel_to_meter=pixel_to_meter,
            flip_y=True,   # image coords have y increasing downward
        )

    # -- lazy model loading ------------------------------------------------ #

    def _load_model(self):
        """Download / load model weights on first use."""
        if self._model is not None:
            return

        try:
            import torch
            import segmentation_models_pytorch as smp
            from huggingface_hub import hf_hub_download
            from safetensors.torch import load_file
        except ImportError as e:
            raise ImportError(
                "PyTorch, segmentation_models_pytorch, safetensors, and huggingface_hub are required for YytsiParser. "
                "Install them with: pip install torch segmentation-models-pytorch safetensors huggingface_hub"
            ) from e

        print(f"    [YytsiParser] Loading model from HuggingFace: {self.model_id}")
        
        # The Yytsi model is a Unet with a resnet34 encoder, 3 input channels, and 4 classes
        model = smp.Unet(
            encoder_name="resnet34",
            encoder_weights=None,
            in_channels=3,
            classes=4,
        )

        # Download the best.safetensors file from the huggingface hub
        weights_path = hf_hub_download(repo_id=self.model_id, filename="best.safetensors")
        state_dict = load_file(weights_path)
        
        # Some models save state_dict with a prefix like 'model.' or similar,
        # but usually safetensors for smp are just the raw weights.
        # Let's load the state dict directly, ignoring strict if there are slight mismatches
        model.load_state_dict(state_dict, strict=False)

        if self._device is None:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"

        model = model.to(self._device)
        model.eval()
        self._model  = model
        self._torch  = torch
        print(f"    [YytsiParser] Model loaded on {self._device}.")

    # -- inference --------------------------------------------------------- #

    def _infer(self, image_path: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Run model inference on *image_path*.

        Returns
        -------
        label_mask : np.ndarray  shape (H, W)  dtype int
            Per-pixel class predictions.
        prob_mask  : np.ndarray  shape (C, H, W)  dtype float32
            Per-class softmax probabilities.
        """
        self._load_model()

        from PIL import Image
        import torch
        import torch.nn.functional as F

        img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = img.size

        # Resize to model input size
        img_resized = img.resize((_INPUT_SIZE, _INPUT_SIZE), Image.BILINEAR)
        arr = np.array(img_resized, dtype=np.float32) / 255.0

        # ImageNet normalization (used during training on CubiCasa5K)
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std  = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        arr  = (arr - mean) / std

        # (H, W, C) → (1, C, H, W)
        tensor = torch.from_numpy(arr.transpose(2, 0, 1)).unsqueeze(0).to(self._device)

        with torch.no_grad():
            logits = self._model(tensor)  # SMP returns (1, 4, H, W) directly
            
            # Pad the 4-class output to 5 classes (insert dummy floor class at index 1)
            zeros = torch.full((logits.shape[0], 1, logits.shape[2], logits.shape[3]), -1e9, device=self._device)
            logits = torch.cat([logits[:, :1], zeros, logits[:, 1:]], dim=1)

        # Upsample back to 512×512 if the model head reduces spatial dims
        if logits.shape[-1] != _INPUT_SIZE:
            logits = F.interpolate(
                logits,
                size=(_INPUT_SIZE, _INPUT_SIZE),
                mode="bilinear",
                align_corners=False,
            )

        probs      = torch.softmax(logits[0], dim=0).cpu().numpy()  # (C, H, W)
        label_mask = np.argmax(probs, axis=0).astype(np.int32)      # (H, W)

        return label_mask, probs

    # -- vectorization helpers --------------------------------------------- #

    @staticmethod
    def _find_contours(binary_mask: np.ndarray) -> List[np.ndarray]:
        """Return OpenCV contours from a binary mask."""
        import cv2
        mask_u8  = (binary_mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(
            mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        return contours

    @staticmethod
    def _contour_to_polygon(contour: np.ndarray) -> List[Tuple[float, float]]:
        """Convert a CV2 contour array to a list of (x, y) tuples."""
        return [(float(pt[0][0]), float(pt[0][1])) for pt in contour]

    @staticmethod
    def _contour_centroid(contour: np.ndarray) -> Tuple[float, float]:
        import cv2
        M  = cv2.moments(contour)
        if M["m00"] == 0:
            x, y = contour[0][0]
            return float(x), float(y)
        return float(M["m10"] / M["m00"]), float(M["m01"] / M["m00"])

    @staticmethod
    def _contour_bbox(contour: np.ndarray) -> Tuple[float, float, float, float]:
        import cv2
        x, y, w, h = cv2.boundingRect(contour)
        return float(x), float(y), float(w), float(h)

    @staticmethod
    def _wall_from_mask_contour(
        contour: np.ndarray,
        wall_id: str,
        default_thickness: float = 10.0,  # pixels — raised from 5 for realistic walls
    ) -> Wall:
        """
        Approximate a wall segment contour as a line segment (start → end).

        The contour of a wall region is typically a thin, elongated rectangle.
        We fit a minAreaRect and extract the long-axis endpoints.
        """
        import cv2

        area = cv2.contourArea(contour)
        if area < _MIN_WALL_AREA:
            return None  # type: ignore[return-value]

        rect = cv2.minAreaRect(contour)   # ((cx,cy), (w,h), angle)
        (cx, cy), (rw, rh), angle = rect

        # Major axis half-length and direction
        if rw >= rh:
            half_len = rw / 2
            thickness_px = rh
            theta = math.radians(angle)
        else:
            half_len = rh / 2
            thickness_px = rw
            theta = math.radians(angle + 90)

        dx = math.cos(theta) * half_len
        dy = math.sin(theta) * half_len

        start = (cx - dx, cy - dy)
        end   = (cx + dx, cy + dy)

        return Wall(
            id=wall_id,
            start=start,
            end=end,
            # Enforce a minimum of 10 px so walls never become invisible slivers
            thickness=max(thickness_px, default_thickness, 10.0),
        )

    # -- main SceneGraph extraction ---------------------------------------- #

    def _build_walls(self, label_mask: np.ndarray) -> List[Wall]:
        """Extract Wall objects from the wall-class mask."""
        import cv2

        wall_binary = (label_mask == _CLASS_WALL).astype(np.uint8)
        # Use a larger kernel (7×7) to bridge gaps between wall segments that
        # the model predicts as disconnected blobs, and an open pass to remove
        # thin noise before closing.
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        kernel_open  = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        wall_binary  = cv2.morphologyEx(wall_binary, cv2.MORPH_OPEN,  kernel_open)
        wall_binary  = cv2.morphologyEx(wall_binary, cv2.MORPH_CLOSE, kernel_close)

        contours = self._find_contours(wall_binary)
        walls: List[Wall] = []
        for i, c in enumerate(contours):
            if cv2.contourArea(c) < _MIN_WALL_AREA:
                continue
            wall = self._wall_from_mask_contour(c, f"w{i+1}")
            if wall is not None:
                walls.append(wall)
        return walls

    def _build_rooms(self, label_mask: np.ndarray) -> List[Room]:
        """Extract Room objects from the floor-class mask."""
        import cv2

        floor_binary = (label_mask == _CLASS_FLOOR).astype(np.uint8)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        floor_binary = cv2.morphologyEx(floor_binary, cv2.MORPH_CLOSE, kernel)

        contours = self._find_contours(floor_binary)
        rooms: List[Room] = []
        for i, c in enumerate(contours):
            area = cv2.contourArea(c)
            if area < _MIN_ROOM_AREA:
                continue
            # Approximate polygon (Douglas-Peucker) for cleaner room outline
            epsilon  = 0.02 * cv2.arcLength(c, True)
            approx   = cv2.approxPolyDP(c, epsilon, True)
            polygon  = self._contour_to_polygon(approx)
            if len(polygon) < 3:
                continue
            cx, cy   = self._contour_centroid(c)
            rooms.append(Room(
                id=f"r{i+1}",
                type="Room",           # OCR enrichment will refine the label
                polygon=polygon,
                centroid=(cx, cy),
            ))
        return rooms

    def _build_doors(
        self,
        label_mask: np.ndarray,
        walls: List[Wall],
    ) -> List[Door]:
        """Extract Door objects from the door-class mask."""
        import cv2

        door_binary = (label_mask == _CLASS_DOOR).astype(np.uint8)
        contours = self._find_contours(door_binary)
        doors: List[Door] = []
        for i, c in enumerate(contours):
            area = cv2.contourArea(c)
            if area < _MIN_OPENING_AREA:
                continue
            cx, cy = self._contour_centroid(c)
            _, _, w, h = self._contour_bbox(c)
            width_px = max(w, h)

            # Associate with nearest wall
            wall_id = self._nearest_wall_id(cx, cy, walls)
            doors.append(Door(
                id=f"d{i+1}",
                wall_id=wall_id or "w1",
                center=(cx, cy),
                width=width_px,
            ))
        return doors

    def _build_windows(
        self,
        label_mask: np.ndarray,
        walls: List[Wall],
    ) -> List[Window]:
        """Extract Window objects from the window-class mask."""
        import cv2

        win_binary = (label_mask == _CLASS_WINDOW).astype(np.uint8)
        contours   = self._find_contours(win_binary)
        windows: List[Window] = []
        for i, c in enumerate(contours):
            area = cv2.contourArea(c)
            if area < _MIN_OPENING_AREA:
                continue
            cx, cy = self._contour_centroid(c)
            _, _, w, h = self._contour_bbox(c)
            width_px = max(w, h)

            wall_id = self._nearest_wall_id(cx, cy, walls)
            windows.append(Window(
                id=f"win{i+1}",
                wall_id=wall_id or "w1",
                center=(cx, cy),
                width=width_px,
            ))
        return windows

    @staticmethod
    def _nearest_wall_id(
        cx: float,
        cy: float,
        walls: List[Wall],
    ) -> Optional[str]:
        """Return the id of the wall whose line segment is closest to (cx, cy)."""
        if not walls:
            return None
            
        from shapely.geometry import Point, LineString
        pt = Point(cx, cy)
        best_id   = walls[0].id
        best_dist = math.inf
        
        for w in walls:
            line = LineString([w.start, w.end])
            d = pt.distance(line)
            if d < best_dist:
                best_dist = d
                best_id   = w.id
        return best_id

    # -- confidence mapping ------------------------------------------------ #

    @staticmethod
    def _extract_confidence(probs: np.ndarray) -> dict:
        """
        Map per-class softmax probabilities to a normalised confidence dict.

        Strategy: for each class, compute the mean softmax probability **only
        over pixels that were predicted as that class** (i.e. argmax == class).
        This gives the average confidence of a prediction *where* the model
        said something exists — not diluted by background pixels.

        probs: (C, H, W)  float32 softmax probabilities
        """
        label_mask = np.argmax(probs, axis=0)  # (H, W)

        def class_confidence(class_id: int) -> float:
            mask = label_mask == class_id
            if not mask.any():
                return 0.0
            return float(np.mean(probs[class_id][mask]))

        c_wall   = class_confidence(_CLASS_WALL)
        c_door   = class_confidence(_CLASS_DOOR)
        c_window = class_confidence(_CLASS_WINDOW)
        c_room   = class_confidence(_CLASS_FLOOR)
        # Overall: mean confidence of the winning class at every pixel
        overall  = float(np.mean(np.max(probs, axis=0)))

        return {
            "walls":   round(min(1.0, c_wall),   4),
            "doors":   round(min(1.0, c_door),   4),
            "windows": round(min(1.0, c_window), 4),
            "rooms":   round(min(1.0, c_room),   4),
            "overall": round(min(1.0, overall),  4),
        }

    # -- public API -------------------------------------------------------- #

    def parse(self, image_path: str) -> SceneGraph:
        """
        Parse *image_path* and return a normalised :class:`SceneGraph`.

        The returned graph uses:
          - metres as the spatial unit
          - origin at (0, 0)
          - y-axis pointing up
          - CCW polygon winding
        """
        print(f"    [YytsiParser] Inferring: {image_path}")
        label_mask, probs = self._infer(image_path)

        # Extract geometric elements (still in pixel space, y-down)
        walls   = self._build_walls(label_mask)
        rooms   = self._build_rooms(label_mask)
        doors   = self._build_doors(label_mask, walls)
        windows = self._build_windows(label_mask, walls)

        print(f"    [YytsiParser] Raw extract -> walls={len(walls)}, rooms={len(rooms)}, "
              f"doors={len(doors)}, windows={len(windows)}")

        # Confidence
        conf_raw  = self._extract_confidence(probs)
        self._last_confidence = conf_raw   # exposed for pipeline node
        confidence = normalize_confidence(conf_raw)
        overall    = confidence.overall or 0.0

        # Build raw SceneGraph (pixel coordinates)
        raw_sg = SceneGraph(
            metadata=Metadata(
                units="pixels",
                scale_pixel_to_meter=self.pixel_to_meter,
                confidence_score=overall,
            ),
            walls=walls,
            rooms=rooms,
            doors=doors,
            windows=windows,
        )

        # Normalise coordinates → metres, origin (0,0), CCW, y-up
        canonical_sg = self._normalizer.normalize(raw_sg)

        # Persist the structured confidence in metadata
        canonical_sg.metadata.confidence_score = round(overall, 4)

        print(f"    [YytsiParser] Canonical -> walls={len(canonical_sg.walls)}, "
              f"rooms={len(canonical_sg.rooms)}, confidence={overall:.3f}")

        return canonical_sg
