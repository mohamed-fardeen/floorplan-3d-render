"""
parsers/cubicasa_parser.py
==========================
Official CubiCasa5K multi-task model adapter.

This parser loads the model code from the official GitHub repo:
https://github.com/cubicasa/cubicasa5k

The repo does not expose a pip/Hugging Face model identifier. It expects:
  - a local clone of the CubiCasa5K repo
  - the official weights file, model_best_val_loss_var.pkl

The model output has 44 channels:
  - 21 heatmap channels
  - 12 room channels
  - 11 icon channels

We map those outputs into the perception pipeline's mask contract:
  wall_mask   <- room class "Wall" (index 2)
  room_mask   <- semantic room classes (Kitchen, Living Room, Bedroom, ...)
  door_mask   <- icon class "Door" (index 2)
  window_mask <- icon class "Window" (index 1)
"""

from __future__ import annotations

import os
import sys
from typing import Optional, Tuple

import numpy as np


_DEFAULT_REPO_PATH = "models/cubicasa5k"
_DEFAULT_WEIGHTS_PATH = "models/cubicasa5k/model_best_val_loss_var.pkl"
_HEATMAP_CHANNELS = 21
_ROOM_CLASSES = [
    "Background",
    "Outdoor",
    "Wall",
    "Kitchen",
    "Living Room",
    "Bedroom",
    "Bath",
    "Hallway",
    "Railing",
    "Storage",
    "Garage",
    "Other rooms",
]
_ICON_CLASSES = [
    "Empty",
    "Window",
    "Door",
    "Closet",
    "Electrical Appliance",
    "Toilet",
    "Sink",
    "Sauna Bench",
    "Fire Place",
    "Bathtub",
    "Chimney",
]

_ROOM_WALL = _ROOM_CLASSES.index("Wall")
_ROOM_USABLE = {
    _ROOM_CLASSES.index("Kitchen"),
    _ROOM_CLASSES.index("Living Room"),
    _ROOM_CLASSES.index("Bedroom"),
    _ROOM_CLASSES.index("Bath"),
    _ROOM_CLASSES.index("Hallway"),
    _ROOM_CLASSES.index("Storage"),
    _ROOM_CLASSES.index("Garage"),
    _ROOM_CLASSES.index("Other rooms"),
}
_ICON_WINDOW = _ICON_CLASSES.index("Window")
_ICON_DOOR = _ICON_CLASSES.index("Door")


class CubiCasaParser:
    """
    Adapter for the official CubiCasa5K model.

    Parameters
    ----------
    repo_path:
        Local path to a clone of https://github.com/cubicasa/cubicasa5k.
    weights_path:
        Local path to model_best_val_loss_var.pkl.
    device:
        "cuda", "cpu", or None for auto-detect.
    target_size:
        Output mask size for this pipeline. Defaults to 512x512.
    """

    def __init__(
        self,
        model_id: Optional[str] = None,
        repo_path: str = _DEFAULT_REPO_PATH,
        weights_path: str = _DEFAULT_WEIGHTS_PATH,
        device: Optional[str] = None,
        target_size: int = 512,
    ):
        # model_id is accepted for config compatibility. If it points to a
        # directory, use it as repo_path.
        if model_id and model_id not in {"cubicasa/cubicasa5k", "CubiCasa/CubiCasa5k"}:
            repo_path = model_id

        self.repo_path = repo_path
        self.weights_path = weights_path
        self._device = device
        self.target_size = target_size
        self._model = None
        self._torch = None

    def _resolve_path(self, path: str) -> str:
        if os.path.isabs(path):
            return path
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", path))

    def _load(self):
        if self._model is not None:
            return

        repo_path = self._resolve_path(self.repo_path)
        weights_path = self._resolve_path(self.weights_path)

        if not os.path.isdir(repo_path):
            raise FileNotFoundError(
                "Official CubiCasa5K repo not found. Clone "
                "https://github.com/cubicasa/cubicasa5k to "
                f"{repo_path!r}, or set perception.cubicasa_repo_path."
            )
        if not os.path.isfile(weights_path):
            raise FileNotFoundError(
                "Official CubiCasa5K weights not found. Download "
                "model_best_val_loss_var.pkl from the CubiCasa5K README "
                f"and place it at {weights_path!r}, or set "
                "perception.cubicasa_weights_path."
            )

        try:
            import torch
        except ImportError as exc:
            raise ImportError("PyTorch is required for CubiCasaParser.") from exc

        if repo_path not in sys.path:
            sys.path.insert(0, repo_path)

        try:
            from floortrans.models import get_model
        except ImportError as exc:
            raise ImportError(
                "Could not import floortrans.models from the official "
                f"CubiCasa5K repo at {repo_path!r}."
            ) from exc

        if self._device is None:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"

        split = [_HEATMAP_CHANNELS, len(_ROOM_CLASSES), len(_ICON_CLASSES)]
        n_classes = sum(split)

        print(f"    [CubiCasa] Loading official model from {repo_path}")
        old_cwd = os.getcwd()
        try:
            # The official init_weights() uses a repo-relative path:
            # floortrans/models/model_1427.pth
            os.chdir(repo_path)
            model = get_model("hg_furukawa_original", 51)
        finally:
            os.chdir(old_cwd)
        model.conv4_ = torch.nn.Conv2d(256, n_classes, bias=True, kernel_size=1)
        model.upsample = torch.nn.ConvTranspose2d(
            n_classes,
            n_classes,
            kernel_size=4,
            stride=4,
        )

        checkpoint = torch.load(weights_path, map_location=self._device)
        state_dict = checkpoint.get("model_state", checkpoint)
        model.load_state_dict(state_dict)
        model.eval()
        model.to(self._device)

        self._model = model
        self._torch = torch
        print(f"    [CubiCasa] Model loaded on {self._device}.")

    def infer(self, image_path: str) -> Tuple[
        np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict
    ]:
        self._load()

        import cv2
        import torch.nn.functional as F

        torch = self._torch
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Could not read image: {image_path}")

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        orig_h, orig_w = img.shape[:2]
        img = 2 * (img.astype(np.float32) / 255.0) - 1.0
        img = np.moveaxis(img, -1, 0)
        tensor = torch.from_numpy(np.expand_dims(img, axis=0)).to(self._device)

        # Official inference averages four rotations. Keep only even spatial
        # dimensions to avoid transposed-conv shape drift on odd-sized inputs.
        height = tensor.shape[2] - (tensor.shape[2] % 2)
        width = tensor.shape[3] - (tensor.shape[3] % 2)
        tensor = tensor[:, :, :height, :width]

        n_classes = _HEATMAP_CHANNELS + len(_ROOM_CLASSES) + len(_ICON_CLASSES)
        predictions = []
        with torch.no_grad():
            for turns in (0, 1, 2, 3):
                rotated = torch.rot90(tensor, turns, dims=(-2, -1))
                pred = self._model(rotated)
                pred = torch.rot90(pred, -turns, dims=(-2, -1))
                pred = F.interpolate(
                    pred,
                    size=(height, width),
                    mode="bilinear",
                    align_corners=True,
                )
                predictions.append(pred[0, :n_classes])

        logits = torch.stack(predictions, dim=0).mean(dim=0)
        room_logits = logits[
            _HEATMAP_CHANNELS:_HEATMAP_CHANNELS + len(_ROOM_CLASSES)
        ]
        icon_logits = logits[_HEATMAP_CHANNELS + len(_ROOM_CLASSES):]

        room_probs = torch.softmax(room_logits, dim=0).cpu().numpy()
        icon_probs = torch.softmax(icon_logits, dim=0).cpu().numpy()
        room_labels = np.argmax(room_probs, axis=0).astype(np.int32)
        icon_labels = np.argmax(icon_probs, axis=0).astype(np.int32)

        wall_mask = (room_labels == _ROOM_WALL).astype(np.uint8)
        room_mask = np.isin(room_labels, list(_ROOM_USABLE)).astype(np.uint8)
        door_mask = (icon_labels == _ICON_DOOR).astype(np.uint8)
        window_mask = (icon_labels == _ICON_WINDOW).astype(np.uint8)

        wall_mask = _resize_and_clean(wall_mask, self.target_size, 5)
        room_mask = _resize_and_clean(room_mask, self.target_size, 7)
        door_mask = _resize_and_clean(door_mask, self.target_size, 3)
        window_mask = _resize_and_clean(window_mask, self.target_size, 3)

        confidence = _confidence(room_probs, icon_probs, room_labels, icon_labels)

        print(
            f"    [CubiCasa] Inferring {image_path} ({orig_w}x{orig_h}) -> "
            f"wall={wall_mask.sum()}, room={room_mask.sum()}, "
            f"door={door_mask.sum()}, window={window_mask.sum()} px"
        )
        return wall_mask, room_mask, door_mask, window_mask, confidence


def _resize_and_clean(mask: np.ndarray, target_size: int, kernel_size: int) -> np.ndarray:
    import cv2

    resized = cv2.resize(
        mask.astype(np.float32),
        (target_size, target_size),
        interpolation=cv2.INTER_NEAREST,
    ).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    cleaned = cv2.morphologyEx(resized, cv2.MORPH_OPEN, k)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, k)
    return cleaned


def _confidence(
    room_probs: np.ndarray,
    icon_probs: np.ndarray,
    room_labels: np.ndarray,
    icon_labels: np.ndarray,
) -> dict:
    def mean_selected(probs: np.ndarray, labels: np.ndarray, class_id: int) -> float:
        mask = labels == class_id
        if not mask.any():
            return 0.0
        return float(np.mean(probs[class_id][mask]))

    room_conf_values = [
        mean_selected(room_probs, room_labels, class_id)
        for class_id in _ROOM_USABLE
        if (room_labels == class_id).any()
    ]
    room_conf = float(np.mean(room_conf_values)) if room_conf_values else 0.0
    wall_conf = mean_selected(room_probs, room_labels, _ROOM_WALL)
    door_conf = mean_selected(icon_probs, icon_labels, _ICON_DOOR)
    window_conf = mean_selected(icon_probs, icon_labels, _ICON_WINDOW)

    return {
        "walls": round(min(1.0, wall_conf), 4),
        "rooms": round(min(1.0, room_conf), 4),
        "doors": round(min(1.0, door_conf), 4),
        "windows": round(min(1.0, window_conf), 4),
        "overall": round(
            min(1.0, float(np.mean(np.max(room_probs, axis=0)))),
            4,
        ),
    }
