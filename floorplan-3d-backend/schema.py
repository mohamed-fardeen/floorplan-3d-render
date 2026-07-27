from typing import List, Tuple, Optional, Dict, Any
from pydantic import BaseModel, Field

class Metadata(BaseModel):
    units: str = "meters"
    scale_pixel_to_meter: float = 0.05
    confidence_score: float = 1.0
    project_name: Optional[str] = None
    floor_number: Optional[str] = None
    sheet_title: Optional[str] = None

class OCRDetection(BaseModel):
    id: str
    text: str
    confidence: float
    bounding_box: Tuple[float, float, float, float]
    polygon: List[Tuple[float, float]]
    rotation: float = 0.0
    language: Optional[str] = None

class Wall(BaseModel):
    id: str
    start: Tuple[float, float]
    end: Tuple[float, float]
    thickness: float = 0.15
    length: Optional[float] = None
    dimension_label: Optional[str] = None
    notes: Optional[str] = None

class Door(BaseModel):
    id: str
    wall_id: str
    center: Tuple[float, float]
    width: float = 0.9
    is_open: bool = True

class Window(BaseModel):
    id: str
    wall_id: str
    center: Tuple[float, float]
    width: float = 1.2

class Room(BaseModel):
    id: str
    type: str = "Unknown"
    polygon: List[Tuple[float, float]]
    area: Optional[float] = None
    centroid: Optional[Tuple[float, float]] = None
    label: Optional[str] = None
    label_confidence: Optional[float] = None
    ocr_source: Optional[str] = None

class ParserConfidenceSchema(BaseModel):
    """Normalised per-class confidence produced by the parser."""
    walls:   Optional[float] = None
    doors:   Optional[float] = None
    windows: Optional[float] = None
    rooms:   Optional[float] = None
    overall: Optional[float] = None

class Adjacency(BaseModel):
    from_room: str = Field(alias="from")
    to_room: str = Field(alias="to")
    via: str

class SceneGraph(BaseModel):
    metadata: Metadata = Field(default_factory=Metadata)
    walls: List[Wall] = Field(default_factory=list)
    doors: List[Door] = Field(default_factory=list)
    windows: List[Window] = Field(default_factory=list)
    rooms: List[Room] = Field(default_factory=list)
    adjacency_graph: List[Adjacency] = Field(default_factory=list)
    ocr_detections: List[OCRDetection] = Field(default_factory=list)

class BlenderResult(BaseModel):
    success: bool = False
    export_paths: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    script_path: Optional[str] = None

class PipelineState(BaseModel):
    image_path: str
    scene_graph: Optional[SceneGraph] = None
    status: str = "started"
    error_message: Optional[str] = None
    validation_report: List[str] = Field(default_factory=list)
    audit_log: List[str] = Field(default_factory=list)
    blender_result: Optional[BlenderResult] = None
    # Phase 2 additions
    parser_confidence: Optional[ParserConfidenceSchema] = None
    failure_report: List[str] = Field(default_factory=list)
    blender_options: Dict[str, Any] = Field(default_factory=dict)

