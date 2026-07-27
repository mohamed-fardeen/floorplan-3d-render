"""
benchmark.py
============
Extended parser benchmark suite for the floorplan-3d pipeline.

Metrics computed per parser
---------------------------
  wall_iou            — Intersection-over-Union of wall masks
  room_iou            — Intersection-over-Union of room polygons
  door_precision      — precision of detected door centres
  door_recall         — recall of detected door centres
  window_precision    — precision of detected window centres
  window_recall       — recall of detected window centres
  inference_time_s    — wall-clock time for parser.parse()
  memory_mb           — peak memory usage during parsing (resident set size delta)
  validation_errors   — number of [ERROR] messages from geometry validation
  automatic_repairs   — number of [FIXED] messages from geometry validation
  failure_issues      — total issues from failure analysis
  blender_success     — 1 / 0 (1 = Blender produced at least one export)

Usage
-----
  python benchmark.py                              # uses config.yaml test images
  python benchmark.py --images path/to/*.png       # explicit image list
  python benchmark.py --providers yytsi cubicasa   # specific providers

The script generates:
  output/benchmark_report_<timestamp>.txt
  output/benchmark_summary.json
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any

import psutil

from parsers.factory import get_parser, list_providers
from validation import validate_and_repair_scene
from parsers.failure_analysis import analyze_failures

# ---------------------------------------------------------------------------
# Optional: import visualization (non-fatal if opencv missing)
# ---------------------------------------------------------------------------
try:
    from parsers.visualization import visualize_scene_graph
    _VIZ_AVAILABLE = True
except ImportError:
    _VIZ_AVAILABLE = False

# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def _iou_masks(
    pred_mask: "np.ndarray",
    gt_mask:   "np.ndarray",
) -> float:
    """Binary IoU between two boolean numpy masks."""
    import numpy as np
    intersection = np.logical_and(pred_mask, gt_mask).sum()
    union        = np.logical_or(pred_mask, gt_mask).sum()
    return float(intersection) / float(union) if union > 0 else 0.0


def _render_walls_to_mask(scene_graph, img_h: int, img_w: int, scale_m_to_px: float):
    """Rasterize wall line segments onto a binary mask for IoU computation."""
    import numpy as np
    import cv2
    mask = np.zeros((img_h, img_w), dtype=np.uint8)
    for wall in scene_graph.walls:
        p1 = (int(wall.start[0] * scale_m_to_px), img_h - int(wall.start[1] * scale_m_to_px))
        p2 = (int(wall.end[0]   * scale_m_to_px), img_h - int(wall.end[1]   * scale_m_to_px))
        thickness_px = max(2, int(wall.thickness * scale_m_to_px))
        cv2.line(mask, p1, p2, 255, thickness_px)
    return mask > 0


def _render_rooms_to_mask(scene_graph, img_h: int, img_w: int, scale_m_to_px: float):
    """Rasterize room polygons onto a binary mask for IoU computation."""
    import numpy as np
    import cv2
    mask = np.zeros((img_h, img_w), dtype=np.uint8)
    for room in scene_graph.rooms:
        pts = []
        for x, y in room.polygon:
            px = int(x * scale_m_to_px)
            py = img_h - int(y * scale_m_to_px)
            pts.append([px, py])
        if len(pts) >= 3:
            cv2.fillPoly(mask, [np.array(pts, dtype=np.int32)], 255)
    return mask > 0


def _centre_precision_recall(
    pred_centres: list,
    gt_centres: list,
    tol_m: float = 0.5,
) -> tuple[float, float]:
    """Compute centre-distance precision / recall for doors or windows."""
    import math
    if not gt_centres:
        return (1.0, 1.0) if not pred_centres else (0.0, 1.0)
    if not pred_centres:
        return (1.0, 0.0)

    matched_gt   = set()
    matched_pred = set()
    for pi, pc in enumerate(pred_centres):
        for gi, gc in enumerate(gt_centres):
            d = math.hypot(pc[0] - gc[0], pc[1] - gc[1])
            if d <= tol_m and gi not in matched_gt:
                matched_gt.add(gi)
                matched_pred.add(pi)
                break

    precision = len(matched_pred) / len(pred_centres)
    recall    = len(matched_gt)   / len(gt_centres)
    return precision, recall


# ---------------------------------------------------------------------------
# Ground truth loading
# ---------------------------------------------------------------------------

def _load_ground_truth(image_path: str) -> Optional[Dict]:
    """
    Load ground truth from a sidecar JSON file next to the image.
    E.g. datasets/benchmark/apartment_01.png  →  datasets/benchmark/apartment_01_gt.json

    Expected schema:
    {
      "walls":   [{"start": [x, y], "end": [x, y]}, ...],
      "rooms":   [{"polygon": [[x, y], ...]}, ...],
      "doors":   [{"center": [x, y]}, ...],
      "windows": [{"center": [x, y]}, ...]
    }
    All coordinates in metres.
    """
    base  = os.path.splitext(image_path)[0]
    gt_path = base + "_gt.json"
    if not os.path.isfile(gt_path):
        return None
    with open(gt_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Single-image benchmark
# ---------------------------------------------------------------------------

def _benchmark_image(
    provider: str,
    image_path: str,
    output_dir: str,
    save_viz: bool = True,
) -> Dict[str, Any]:
    """Run the full pipeline on a single image and return metrics."""

    result: Dict[str, Any] = {
        "provider":         provider,
        "image":            os.path.basename(image_path),
        "wall_iou":         None,
        "room_iou":         None,
        "door_precision":   None,
        "door_recall":      None,
        "window_precision": None,
        "window_recall":    None,
        "inference_time_s": None,
        "memory_mb":        None,
        "validation_errors": 0,
        "automatic_repairs": 0,
        "failure_issues":   0,
        "blender_success":  0,
        "status":           "pending",
        "error":            None,
    }

    # ---- Parse ----
    try:
        parser = get_parser(provider)
    except Exception as e:
        result["status"] = "load_error"
        result["error"]  = str(e)
        return result

    proc = psutil.Process(os.getpid())
    mem_before = proc.memory_info().rss / 1024 / 1024  # MB

    t0 = time.perf_counter()
    try:
        scene_graph = parser.parse(image_path)
    except NotImplementedError:
        result["status"] = "not_implemented"
        return result
    except Exception as e:
        result["status"] = "parse_error"
        result["error"]  = traceback.format_exc()
        return result
    finally:
        result["inference_time_s"] = round(time.perf_counter() - t0, 3)

    mem_after = proc.memory_info().rss / 1024 / 1024
    result["memory_mb"] = round(mem_after - mem_before, 1)

    # ---- Failure analysis ----
    fa = analyze_failures(scene_graph)
    result["failure_issues"] = len(fa.issues)

    # ---- Geometry validation ----
    corrected_sg, val_report = validate_and_repair_scene(scene_graph)
    result["validation_errors"] = sum(1 for m in val_report if "[ERROR]" in m)
    result["automatic_repairs"] = sum(1 for m in val_report if "[FIXED]" in m)

    # ---- Ground truth metrics ----
    gt = _load_ground_truth(image_path)
    if gt is not None:
        try:
            import cv2, numpy as np
            scale_m_to_px = 1.0 / scene_graph.metadata.scale_pixel_to_meter
            img = cv2.imread(image_path)
            img_h, img_w = img.shape[:2]

            # Wall IoU
            pred_wall_mask = _render_walls_to_mask(corrected_sg, img_h, img_w, scale_m_to_px)
            gt_sg_stub     = _gt_to_scene_graph_stub(gt, scene_graph.metadata.scale_pixel_to_meter)
            gt_wall_mask   = _render_walls_to_mask(gt_sg_stub, img_h, img_w, scale_m_to_px)
            result["wall_iou"] = round(_iou_masks(pred_wall_mask, gt_wall_mask), 4)

            # Room IoU
            pred_room_mask = _render_rooms_to_mask(corrected_sg, img_h, img_w, scale_m_to_px)
            gt_room_mask   = _render_rooms_to_mask(gt_sg_stub, img_h, img_w, scale_m_to_px)
            result["room_iou"] = round(_iou_masks(pred_room_mask, gt_room_mask), 4)

            # Door precision/recall
            pred_doors = [tuple(d.center) for d in corrected_sg.doors]
            gt_doors   = [tuple(d["center"]) for d in gt.get("doors", [])]
            dp, dr     = _centre_precision_recall(pred_doors, gt_doors)
            result["door_precision"] = round(dp, 4)
            result["door_recall"]    = round(dr, 4)

            # Window precision/recall
            pred_wins = [tuple(w.center) for w in corrected_sg.windows]
            gt_wins   = [tuple(w["center"]) for w in gt.get("windows", [])]
            wp, wr    = _centre_precision_recall(pred_wins, gt_wins)
            result["window_precision"] = round(wp, 4)
            result["window_recall"]    = round(wr, 4)
        except Exception as e:
            result["error"] = f"GT metric computation failed: {e}"

    # ---- Visualization ----
    if save_viz and _VIZ_AVAILABLE:
        try:
            viz_dir = os.path.join(output_dir, "debug_viz")
            visualize_scene_graph(corrected_sg, image_path, output_dir=viz_dir,
                                  filename_suffix=f"_{provider}")
        except Exception as e:
            pass  # Visualization errors are non-fatal

    # ---- Blender success (lightweight check: just verify script generation) ----
    try:
        import yaml
        cfg_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f)
        from blender.script_builder import build_script
        script_path = os.path.join(output_dir, f"_bench_{provider}.py")
        build_script(corrected_sg, cfg, output_dir, script_path)
        result["blender_success"] = 1
        if os.path.exists(script_path):
            os.remove(script_path)
    except Exception:
        result["blender_success"] = 0

    result["status"] = "success"
    return result


def _gt_to_scene_graph_stub(gt: Dict, scale: float):
    """Convert a ground truth dict to a minimal SceneGraph-like object for mask rendering."""
    from schema import SceneGraph, Metadata, Wall, Room, Door, Window
    walls   = [Wall(id=f"gw{i}", start=tuple(w["start"]), end=tuple(w["end"]))
               for i, w in enumerate(gt.get("walls", []))]
    rooms   = [Room(id=f"gr{i}", type="Room", polygon=[tuple(p) for p in r["polygon"]])
               for i, r in enumerate(gt.get("rooms", []))]
    doors   = [Door(id=f"gd{i}", wall_id="gw0", center=tuple(d["center"]))
               for i, d in enumerate(gt.get("doors", []))]
    windows = [Window(id=f"gwin{i}", wall_id="gw0", center=tuple(w["center"]))
               for i, w in enumerate(gt.get("windows", []))]
    return SceneGraph(
        metadata=Metadata(scale_pixel_to_meter=scale),
        walls=walls, rooms=rooms, doors=doors, windows=windows,
    )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _print_table(results: List[Dict]) -> str:
    cols = [
        ("Provider",   "provider",          18),
        ("Image",      "image",             20),
        ("Time (s)",   "inference_time_s",  10),
        ("Mem MB",     "memory_mb",          8),
        ("WallIoU",    "wall_iou",           9),
        ("RoomIoU",    "room_iou",           9),
        ("D-Prec",     "door_precision",     8),
        ("D-Rec",      "door_recall",        7),
        ("W-Prec",     "window_precision",   8),
        ("W-Rec",      "window_recall",      7),
        ("VErr",       "validation_errors",  5),
        ("Fixes",      "automatic_repairs",  5),
        ("Blender",    "blender_success",    7),
        ("Status",     "status",            14),
    ]

    def fmt(v: Any, w: int) -> str:
        if v is None:
            return "N/A".ljust(w)
        if isinstance(v, float):
            return f"{v:.3f}".ljust(w)
        return str(v).ljust(w)

    header = " | ".join(name.ljust(w) for name, _, w in cols)
    sep    = "-" * len(header)
    lines  = ["=" * len(header), "  BENCHMARK RESULTS", "=" * len(header),
              header, sep]
    for r in results:
        row = " | ".join(fmt(r.get(key), w) for _, key, w in cols)
        lines.append(row)
    lines.append("=" * len(header))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_benchmark(
    providers: Optional[List[str]] = None,
    image_paths: Optional[List[str]] = None,
    output_dir: str = "output",
    save_viz: bool = True,
) -> List[Dict]:
    os.makedirs(output_dir, exist_ok=True)

    if providers is None:
        providers = ["yytsi", "cubicasa"]

    if image_paths is None:
        # Default: scan datasets/benchmark directory
        benchmark_dir = os.path.join(os.path.dirname(__file__), "datasets", "benchmark")
        patterns = [
            os.path.join(benchmark_dir, "**", "*.png"),
            os.path.join(benchmark_dir, "**", "*.jpg"),
        ]
        image_paths = []
        for p in patterns:
            image_paths += glob.glob(p, recursive=True)
        if not image_paths:
            print("[WARN] No benchmark images found. "
                  "Add images to datasets/benchmark/ or pass --images.")
            return []

    print(f"\n{'='*55}")
    print(f"  PARSER BENCHMARK  ({len(providers)} provider(s), {len(image_paths)} image(s))")
    print(f"{'='*55}\n")

    all_results: List[Dict] = []
    for provider in providers:
        for img_path in image_paths:
            print(f"  [{provider}] → {os.path.basename(img_path)}")
            r = _benchmark_image(provider, img_path, output_dir, save_viz=save_viz)
            all_results.append(r)
            status_str = r["status"]
            if r["inference_time_s"]:
                status_str += f"  ({r['inference_time_s']:.2f}s)"
            print(f"    Status: {status_str}")

    # Print table
    table = _print_table(all_results)
    print("\n" + table)

    # Save reports
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    txt_path  = os.path.join(output_dir, f"benchmark_report_{ts}.txt")
    json_path = os.path.join(output_dir, "benchmark_summary.json")

    with open(txt_path, "w") as f:
        f.write(table)
    with open(json_path, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n  Report saved → {txt_path}")
    print(f"  JSON   saved → {json_path}")
    return all_results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parser Benchmark Suite")
    parser.add_argument(
        "--providers", nargs="+",
        default=None,
        help="Provider names to benchmark (default: yytsi cubicasa)",
    )
    parser.add_argument(
        "--images", nargs="+", dest="images",
        default=None,
        help="Image paths to use (default: datasets/benchmark/**/*.png)",
    )
    parser.add_argument(
        "--output-dir", default="output",
        help="Directory for reports and visualizations",
    )
    parser.add_argument(
        "--no-viz", action="store_true",
        help="Disable visualization output",
    )
    args = parser.parse_args()

    run_benchmark(
        providers  = args.providers,
        image_paths= args.images,
        output_dir = args.output_dir,
        save_viz   = not args.no_viz,
    )
