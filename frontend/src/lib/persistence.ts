/**
 * Persist per-project viewport + selection state to localStorage.
 *
 * State is namespaced by project ID so multiple projects do not collide.
 * FaceRefs are stripped of meshUuid hints on save (UUIDs change between
 * sessions); the canonical objectName is the persistent identity.
 */

import type { Selection, SelectionTool, ViewportOptions } from '../types/selection';

const KEY_PREFIX = 'floorplan-3d:project:';
const SCHEMA_VERSION = 1;

export interface PersistedSelection extends Omit<Selection, 'meshRefs' | 'faceRefs'> {
  meshRefs: Array<{ objectName: string }>;
  faceRefs: Array<{ meshRef: { objectName: string }; faceIndex: number }>;
}

export interface PersistedState {
  version: number;
  projectId: string;
  viewport: ViewportOptions;
  selections: PersistedSelection[];
  activeSelectionId: string | null;
  selectionTool: SelectionTool;
  brushRadius: number;
  savedAt: number;
}

export function projectKey(projectId: string): string {
  return `${KEY_PREFIX}${projectId}`;
}

export function stripMeshUuids(s: Selection): PersistedSelection {
  return {
    ...s,
    meshRefs: s.meshRefs.map((m) => ({ objectName: m.objectName })),
    faceRefs: s.faceRefs.map((f) => ({
      meshRef: { objectName: f.meshRef.objectName },
      faceIndex: f.faceIndex,
    })),
  };
}

export function saveProjectState(projectId: string, state: Omit<PersistedState, 'version' | 'projectId' | 'savedAt'>) {
  if (typeof window === 'undefined' || !window.localStorage) return;
  try {
    const payload: PersistedState = {
      version: SCHEMA_VERSION,
      projectId,
      savedAt: Date.now(),
      ...state,
      selections: state.selections.map(stripMeshUuids),
    };
    window.localStorage.setItem(projectKey(projectId), JSON.stringify(payload));
  } catch (err) {
    console.warn('[persistence] save failed', err);
  }
}

export function loadProjectState(projectId: string): PersistedState | null {
  if (typeof window === 'undefined' || !window.localStorage) return null;
  try {
    const raw = window.localStorage.getItem(projectKey(projectId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedState;
    if (parsed.version !== SCHEMA_VERSION) return null;
    return parsed;
  } catch (err) {
    console.warn('[persistence] load failed', err);
    return null;
  }
}

export function clearProjectState(projectId: string) {
  if (typeof window === 'undefined' || !window.localStorage) return;
  window.localStorage.removeItem(projectKey(projectId));
}

export function deriveProjectId(graph: { metadata?: { project_name?: string } } | null | undefined): string {
  if (!graph || !graph.metadata) return 'unsaved';
  const name = (graph.metadata.project_name ?? 'unsaved').trim() || 'unsaved';
  return name.replace(/\s+/g, '_').toLowerCase();
}