from schema import SceneGraph, Wall, Room, Door, Window, Metadata, OCRDetection
from enrichment import enrich_scene_graph
from enrichment import is_dimension, parse_dimension_to_meters

CONFIDENCE_THRESHOLD = 0.8

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def make_simple_scene() -> SceneGraph:
    """A 5×5 Bedroom polygon with one wall along x=0."""
    return SceneGraph(
        metadata=Metadata(confidence_score=0.9),
        walls=[Wall(id="w1", start=(0, 0), end=(0, 5))],
        rooms=[Room(id="r1", type="Unknown", polygon=[(0, 0), (0, 5), (5, 5), (5, 0)])],
    )


def ocr(id_, text, conf, cx, cy, w=0.5, h=0.3) -> OCRDetection:
    """Quick-build an OCRDetection centred at (cx, cy)."""
    return OCRDetection(
        id=id_, text=text, confidence=conf,
        bounding_box=(cx - w, cy - h, cx + w, cy + h),
        polygon=[(cx-w, cy-h), (cx+w, cy-h), (cx+w, cy+h), (cx-w, cy+h)],
    )


# ──────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────
def test_room_label_assigned():
    sg = make_simple_scene()
    dets = [ocr("d1", "MASTER BEDROOM", 0.98, 2.5, 2.5)]
    enriched, log = enrich_scene_graph(sg, dets)
    room = enriched.rooms[0]
    assert room.label == "MASTER BEDROOM", f"Expected 'MASTER BEDROOM', got '{room.label}'"
    assert room.type == "MASTER BEDROOM"
    assert room.label_confidence == 0.98
    print("[PASS] test_room_label_assigned")


def test_low_confidence_does_not_overwrite():
    sg = make_simple_scene()
    sg.rooms[0].type = "Living Room"   # parser already labelled this
    dets = [ocr("d1", "Bedroom", 0.5, 2.5, 2.5)]  # low conf
    enriched, log = enrich_scene_graph(sg, dets)
    assert enriched.rooms[0].type == "Living Room", \
        f"Low-confidence OCR should NOT override. Got: {enriched.rooms[0].type}"
    print("[PASS] test_low_confidence_does_not_overwrite")


def test_conflict_resolution_logged():
    sg = make_simple_scene()
    sg.rooms[0].type = "Living Room"
    dets = [ocr("d1", "Bedroom", 0.95, 2.5, 2.5)]  # high conf → override
    enriched, log = enrich_scene_graph(sg, dets)
    assert enriched.rooms[0].type == "Bedroom"
    assert any("OVERRIDE" in msg for msg in log), "Expected OVERRIDE entry in audit log"
    print("[PASS] test_conflict_resolution_logged")


def test_dimension_assigned_to_nearest_wall():
    sg = make_simple_scene()
    # Text very close to wall w1 at x=0, placed at x=0.05
    dets = [ocr("d1", "16' 4\"", 0.95, 0.05, 2.5)]
    enriched, log = enrich_scene_graph(sg, dets)
    assert enriched.walls[0].dimension_label == "16' 4\"", \
        f"Dimension not assigned to wall. Got: {enriched.walls[0].dimension_label}"
    print("[PASS] test_dimension_assigned_to_nearest_wall")


def test_project_metadata_extracted():
    sg = make_simple_scene()
    dets = [ocr("d1", "PROJECT VILLA OCEANA", 0.99, 20, 20)]
    enriched, log = enrich_scene_graph(sg, dets)
    assert enriched.metadata.project_name is not None, "Project name should have been set."
    print("[PASS] test_project_metadata_extracted")


def test_ocr_detections_stored_in_graph():
    sg = make_simple_scene()
    dets = [ocr("d1", "kitchen", 0.92, 2.5, 2.5), ocr("d2", "3.5m", 0.91, 0.05, 4.0)]
    enriched, _ = enrich_scene_graph(sg, dets)
    assert len(enriched.ocr_detections) == 2, "All detections should be stored on the scene graph."
    print("[PASS] test_ocr_detections_stored_in_graph")


def test_empty_drawing_no_crash():
    sg = SceneGraph()  # no walls, no rooms
    dets = [ocr("d1", "BEDROOM", 0.98, 2.5, 2.5)]
    enriched, log = enrich_scene_graph(sg, dets)
    assert enriched is not None
    print("[PASS] test_empty_drawing_no_crash")


def test_no_ocr_detections_no_crash():
    sg = make_simple_scene()
    enriched, log = enrich_scene_graph(sg, [])
    assert len(enriched.rooms) == 1  # scene graph unchanged
    print("[PASS] test_no_ocr_detections_no_crash")


def test_text_outside_all_polygons_no_association():
    sg = make_simple_scene()
    # Text is far away from the room polygon (0,0)-(5,5) and wall at x=0
    dets = [ocr("d1", "GARAGE", 0.98, 50, 50)]
    enriched, log = enrich_scene_graph(sg, dets)
    assert enriched.rooms[0].label is None, "Label should not be assigned to a room that doesn't contain the text."
    print("[PASS] test_text_outside_all_polygons_no_association")


# ──────────────────────────────────────────────
# Dimension classification & parsing
# ──────────────────────────────────────────────

def test_is_dimension_accepts_units():
    """Measurements with unit suffixes qualify as dimensions."""
    for s in ["16' 4\"", '16 ft 4"', "3.5m", "3500mm", "350 cm", '4"', "12 ft"]:
        assert is_dimension(s), f"Expected '{s}' to be a dimension"
    print("[PASS] test_is_dimension_accepts_units")


def test_is_dimension_rejects_bare_numbers():
    """Bare integers / sheet titles with numbers are NOT dimensions."""
    for s in ["VILLA 12", "PLAN 101", "BEDROOM", "MASTER BATH"]:
        assert not is_dimension(s), f"'{s}' should NOT be a dimension"
    print("[PASS] test_is_dimension_rejects_bare_numbers")


def test_parse_imperial_feet_inches():
    """16' 4\" ≈ 4.978 m."""
    m = parse_dimension_to_meters('16\' 4"')
    assert m is not None, "Should parse imperial"
    assert abs(m - (16 * 0.3048 + 4 * 0.0254)) < 1e-6
    print("[PASS] test_parse_imperial_feet_inches")


def test_parse_metric_units():
    assert abs(parse_dimension_to_meters("3.5m")    - 3.5)  < 1e-6
    assert abs(parse_dimension_to_meters("3500mm")  - 3.5)  < 1e-6
    assert abs(parse_dimension_to_meters("350 cm")  - 3.5)  < 1e-6
    print("[PASS] test_parse_metric_units")


def test_parse_inches_only():
    assert abs(parse_dimension_to_meters('4"')      - 0.1016) < 1e-4
    assert abs(parse_dimension_to_meters('12 in')   - 0.3048) < 1e-4
    print("[PASS] test_parse_inches_only")


def test_parse_returns_none_for_non_dimension():
    assert parse_dimension_to_meters("BEDROOM") is None
    assert parse_dimension_to_meters("VILLA 12") is None
    print("[PASS] test_parse_returns_none_for_non_dimension")


def test_dimension_preserves_geometric_length_on_mismatch():
    """
    A wall whose geometric length disagrees with the OCR label by more than
    `length_match_tolerance` should keep its geometric value.
    """
    sg = make_simple_scene()
    sg.walls[0].length = 5.0          # geometric length is 5m
    enriched, log = enrich_scene_graph(
        sg,
        [ocr("d1", "12' 4\"", 0.95, 0.05, 2.5)],   # ~3.76 m  → 1.24 m discrepancy
    )
    assert enriched.walls[0].dimension_label == "12' 4\""
    assert enriched.walls[0].length == 5.0, \
        f"Geometric length should be preserved when OCR disagrees (>0.30m tol). Got {enriched.walls[0].length}"
    assert any("disagrees" in m for m in log)
    print("[PASS] test_dimension_preserves_geometric_length_on_mismatch")


def test_dimension_snaps_wall_length_within_tolerance():
    """A label whose parsed value matches the wall length should snap."""
    sg = make_simple_scene()
    # Pre-compute wall length (as geometry validator would do)
    sg.walls[0].length = 5.0
    # Place a "5m" label close to wall w1 at x=0
    enriched, log = enrich_scene_graph(
        sg,
        [ocr("d1", "5m", 0.95, 0.05, 2.5)],
    )
    assert enriched.walls[0].dimension_label == "5m"
    assert abs(enriched.walls[0].length - 5.0) < 1e-3
    assert any("OCR matches" in m for m in log), "Expected 'OCR matches' audit entry"
    print("[PASS] test_dimension_snaps_wall_length_within_tolerance")


def test_dimension_fills_wall_length_when_missing():
    """If the wall has no length yet, OCR can supply it."""
    sg = make_simple_scene()
    # Wall w1 was created without a length
    assert sg.walls[0].length is None
    enriched, log = enrich_scene_graph(
        sg,
        [ocr("d1", "5m", 0.95, 0.05, 2.5)],
    )
    assert enriched.walls[0].length == 5.0, \
        f"OCR should populate missing wall.length. Got {enriched.walls[0].length}"
    assert any("from OCR" in m for m in log)
    print("[PASS] test_dimension_fills_wall_length_when_missing")


# ──────────────────────────────────────────────
# Runner
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  OCR & SEMANTIC ENRICHMENT TEST SUITE")
    print("=" * 50)
    test_room_label_assigned()
    test_low_confidence_does_not_overwrite()
    test_conflict_resolution_logged()
    test_dimension_assigned_to_nearest_wall()
    test_project_metadata_extracted()
    test_ocr_detections_stored_in_graph()
    test_empty_drawing_no_crash()
    test_no_ocr_detections_no_crash()
    test_text_outside_all_polygons_no_association()
    test_is_dimension_accepts_units()
    test_is_dimension_rejects_bare_numbers()
    test_parse_imperial_feet_inches()
    test_parse_metric_units()
    test_parse_inches_only()
    test_parse_returns_none_for_non_dimension()
    test_dimension_snaps_wall_length_within_tolerance()
    test_dimension_preserves_geometric_length_on_mismatch()
    test_dimension_fills_wall_length_when_missing()
    print("=" * 50)
    print("  ALL TESTS PASSED")
    print("=" * 50)
