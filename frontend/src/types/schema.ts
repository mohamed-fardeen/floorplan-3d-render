export interface Metadata {
  units: string;
  scale_pixel_to_meter: number;
  confidence_score: number;
  project_name?: string;
  floor_number?: string;
  sheet_title?: string;
}

export interface OCRDetection {
  id: string;
  text: string;
  confidence: number;
  bounding_box: [number, number, number, number];
  polygon: [number, number][];
  rotation: number;
  language?: string;
}

export interface Wall {
  id: string;
  start: [number, number];
  end: [number, number];
  thickness: number;
  length?: number;
  dimension_label?: string;
  notes?: string;
}

export interface Door {
  id: string;
  wall_id: string;
  center: [number, number];
  width: number;
  is_open: boolean;
}

export interface FloorWindow {
  id: string;
  wall_id: string;
  center: [number, number];
  width: number;
}

export interface Room {
  id: string;
  type: string;
  polygon: [number, number][];
  area?: number;
  centroid?: [number, number];
  label?: string;
  label_confidence?: number;
  ocr_source?: string;
}

export interface Adjacency {
  from: string;
  to: string;
  via: string;
}

export interface SceneGraph {
  metadata: Metadata;
  walls: Wall[];
  doors: Door[];
  windows: FloorWindow[];
  rooms: Room[];
  adjacency_graph: Adjacency[];
  ocr_detections: OCRDetection[];
}
