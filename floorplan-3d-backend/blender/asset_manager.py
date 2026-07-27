"""
asset_manager.py
Maps room semantic labels to furniture asset lists.
The mapping is read from config.yaml, so it can be changed without touching code.
"""
from typing import List, Dict

# Default fallback mapping (overridden by config.yaml)
DEFAULT_MAPPING: Dict[str, List[str]] = {
    "bedroom":      ["bed_double", "wardrobe", "side_table"],
    "master bedroom": ["bed_double", "wardrobe", "side_table", "dresser"],
    "kitchen":      ["kitchen_counter", "refrigerator", "sink"],
    "bathroom":     ["toilet", "sink_basin", "bathtub"],
    "living room":  ["sofa", "coffee_table", "tv_stand"],
    "dining room":  ["dining_table", "dining_chairs"],
    "hallway":      [],
    "corridor":     [],
    "stairs":       ["stair_railing"],
    "garage":       [],
    "store":        ["shelving_unit"],
}

def get_assets_for_room(room_type: str, cfg: dict) -> List[str]:
    """Return the list of asset names for the given room type."""
    assets_cfg = cfg.get("assets", {})
    key = room_type.lower().strip()

    # Config override takes priority
    if key in assets_cfg:
        return assets_cfg[key]

    return DEFAULT_MAPPING.get(key, [])

def build_furniture_code(scene_graph, cfg) -> str:
    """
    Generates bpy code to place simple placeholder cubes at room centroids
    as stand-ins for real GLB furniture assets (to be swapped with an asset library).
    """
    lines = ["# ── Furniture (Placeholder Cubes) ────────────────────────"]
    for room in scene_graph.rooms:
        room_type = (room.label or room.type or "unknown")
        assets    = get_assets_for_room(room_type, cfg)
        cx, cy    = room.centroid if room.centroid else (0.0, 0.0)

        for i, asset_name in enumerate(assets):
            offset_x = i * 0.8
            lines += [
                f"# Asset: {asset_name} in {room.id}",
                f"bpy.ops.mesh.primitive_cube_add(",
                f"    size=0.6,",
                f"    location=({cx + offset_x}, {cy}, 0.3)",
                f")",
                f"bpy.context.active_object.name = 'Asset_{room.id}_{asset_name}'",
                "",
            ]
    return "\n".join(lines)
