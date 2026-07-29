/** Geometry-agnostic selection model — decoupled from walls. */

export interface MeshReference {
  /** Blender object name, e.g. `Wall_abc123` or `Floor_Living`. */
  objectName: string;
  /** Three.js mesh UUID for browser-side lookup. */
  meshUuid?: string;
}

export interface FaceReference {
  meshRef: MeshReference;
  faceIndex: number;
  /** World-space face normal at pick time (optional, for future curved geometry). */
  normal?: [number, number, number];
}

export interface BoundingInfo {
  min: [number, number, number];
  max: [number, number, number];
  center: [number, number, number];
}

export interface SelectionEditMetadata {
  color?: string;
  pattern?: string;
  materialPreset?: string;
}

export interface Selection {
  id: string;
  meshRefs: MeshReference[];
  faceRefs: FaceReference[];
  bounding: BoundingInfo;
  metadata: SelectionEditMetadata;
  createdAt: number;
}

export type DesignOperation =
  | { type: 'apply_pattern'; pattern: string }
  | { type: 'set_color'; value: string }
  | { type: 'set_material_preset'; preset: string };

export interface DesignActionPlan {
  selection: string | 'current';
  operations: DesignOperation[];
}

export type SelectionTool = 'click' | 'brush' | 'box';

export type SyncStatus = 'idle' | 'syncing' | 'synced' | 'error';
