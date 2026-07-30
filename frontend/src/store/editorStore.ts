import { create } from 'zustand';
import type { SceneGraph, Wall, Room, Door, FloorWindow } from '../types/schema';
import type {
  Selection,
  SelectionTool,
  SyncStatus,
  DesignActionPlan,
  ViewportOptions,
  MeshReference,
} from '../types/selection';
import { mergeFaceRefs } from '../lib/selectionGeometry';
import {
  deriveProjectId,
  loadProjectState,
  saveProjectState,
} from '../lib/persistence';
import type { MaterialOptions } from '../api/client';

function mergeMeshRefs(a: MeshReference[], b: MeshReference[]): MeshReference[] {
  const seen = new Set<string>();
  const out: MeshReference[] = [];
  const push = (m: MeshReference) => {
    const key = m.meshUuid ?? m.objectName;
    if (seen.has(key)) return;
    seen.add(key);
    out.push(m);
  };
  for (const m of a) push(m);
  for (const m of b) push(m);
  return out;
}

interface EditorState {
  sceneGraph: SceneGraph | null;
  glbUrl: string | null;
  glbVersion: number;
  syncStatus: SyncStatus;
  syncError: string | null;
  syncStage: string | null;
  syncMessage: string | null;
  syncStartedAt: number | null;

  /** Legacy object selection (2D Konva editor). */
  selectedObjectId: string | null;
  selectedObjectType: 'wall' | 'room' | 'door' | 'window' | 'ocr' | null;

  /** Geometry-agnostic 3D selections. */
  selections: Selection[];
  activeSelectionId: string | null;
  selectionTool: SelectionTool;
  brushRadius: number;

  materialOptions: MaterialOptions;
  includeBase: boolean;
  includeRoof: boolean;

  history: SceneGraph[];
  historyIndex: number;

  /** Selection-only history, separate from sceneGraph history. */
  selectionHistory: Selection[][];
  selectionHistoryIndex: number;

  viewport: ViewportOptions;

  setSceneGraph: (graph: SceneGraph) => void;
  setGlbUrl: (url: string | null) => void;
  bumpGlbVersion: () => void;
  setSyncStatus: (status: SyncStatus, error?: string | null) => void;
  setSyncStage: (stage: string | null, message: string | null) => void;
  setMaterialOptions: (opts: MaterialOptions) => void;
  setExportOptions: (includeBase: boolean, includeRoof: boolean) => void;

  selectObject: (id: string | null, type: 'wall' | 'room' | 'door' | 'window' | 'ocr' | null) => void;
  setSelectionTool: (tool: SelectionTool) => void;
  setBrushRadius: (radius: number) => void;
  setActiveSelection: (id: string | null) => void;
  addSelection: (selection: Selection, merge?: boolean) => void;
  removeSelection: (id: string) => void;
  updateSelectionMetadata: (id: string, metadata: Partial<Selection['metadata']>) => void;
  renameSelection: (id: string, name: string) => void;
  clearSelections: () => void;

  /** Replace the faceRefs of the active selection with a transformed set. */
  transformActiveSelectionFaces: (transformer: (refs: Selection['faceRefs']) => Selection['faceRefs']) => void;
  saveSelectionAsNamed: (id: string, name: string) => void;
  recallNamedSelection: (name: string) => void;
  namedSelections: Record<string, Selection['faceRefs']>;

  updateWall: (id: string, updates: Partial<Wall>) => void;
  updateRoom: (id: string, updates: Partial<Room>) => void;
  updateDoor: (id: string, updates: Partial<Door>) => void;
  updateWindow: (id: string, updates: Partial<FloorWindow>) => void;

  undo: () => void;
  redo: () => void;
  pushHistory: () => void;

  pushSelectionHistory: () => void;
  undoSelection: () => void;
  redoSelection: () => void;

  getActiveSelection: () => Selection | null;
  applyDesignPlanLocally: (plan: DesignActionPlan) => void;

  setViewportOptions: (opts: Partial<ViewportOptions>) => void;
  invalidateMeshUuids: () => void;

  loadProject: (projectId: string) => void;
  persistProject: (projectId?: string) => void;
  resetSelectionsToPersisted: () => void;
}

const DEFAULT_MATERIALS: MaterialOptions = {
  walls: {
    theme: 'warm_modern',
    color: '#D8C8B8',
    pattern: 'none',
    pattern_color: '#D8C8B8',
  },
  floor: {
    design: 'square_grid',
    primary_color: '#E8E3D9',
    secondary_color: '#B8B5AE',
    grout_color: '#A8A49C',
    tile_size_m: 0.4,
  },
};

export const useEditorStore = create<EditorState>((set, get) => ({
  sceneGraph: null,
  glbUrl: null,
  glbVersion: 0,
  syncStatus: 'idle',
  syncError: null,
  syncStage: null,
  syncMessage: null,
  syncStartedAt: null,

  selectedObjectId: null,
  selectedObjectType: null,

  selections: [],
  activeSelectionId: null,
  selectionTool: 'click',
  brushRadius: 0.15,
  namedSelections: {},

  materialOptions: DEFAULT_MATERIALS,
  includeBase: true,
  includeRoof: false,

  history: [],
  historyIndex: -1,

  selectionHistory: [[]],
  selectionHistoryIndex: 0,

  viewport: { showAxes: true, showGrid: true, background: 'slate' },

  setSceneGraph: (graph) => {
    const projectId = deriveProjectId(graph);
    const persisted = loadProjectState(projectId);
    const baseSelections = persisted
      ? (persisted.selections as Selection[])
      : [];
    set({
      sceneGraph: graph,
      history: [graph],
      historyIndex: 0,
      selectedObjectId: null,
      selectedObjectType: null,
      selections: baseSelections,
      activeSelectionId: persisted?.activeSelectionId ?? null,
      selectionHistory: [baseSelections],
      selectionHistoryIndex: 0,
      viewport: persisted
        ? { ...get().viewport, ...persisted.viewport }
        : get().viewport,
      selectionTool: persisted?.selectionTool ?? get().selectionTool,
      brushRadius: persisted?.brushRadius ?? get().brushRadius,
    });
  },

  setGlbUrl: (url) => set({ glbUrl: url }),
  bumpGlbVersion: () => set((s) => ({ glbVersion: s.glbVersion + 1 })),
  setSyncStatus: (status, error = null) =>
    set((s) => ({
      syncStatus: status,
      syncError: error,
      syncStartedAt: status === 'syncing' ? Date.now() : s.syncStartedAt,
    })),

  setSyncStage: (stage, message) =>
    set({ syncStage: stage, syncMessage: message }),
  setMaterialOptions: (opts) => set({ materialOptions: opts }),
  setExportOptions: (includeBase, includeRoof) => set({ includeBase, includeRoof }),

  selectObject: (id, type) => set({ selectedObjectId: id, selectedObjectType: type }),

  setSelectionTool: (tool) => set({ selectionTool: tool }),
  setBrushRadius: (radius) => set({ brushRadius: radius }),
  setActiveSelection: (id) => set({ activeSelectionId: id }),

  addSelection: (selection, merge) => {
    get().pushSelectionHistory();
    set((state) => {
      const existing = state.selections.find((s) => s.id === selection.id);
      const baseList = state.selections.filter((s) => s.id !== selection.id);
      const merged = merge && existing
        ? {
            ...selection,
            faceRefs: mergeFaceRefs(existing.faceRefs, selection.faceRefs),
            meshRefs: mergeMeshRefs(existing.meshRefs, selection.meshRefs),
            bounding: existing.bounding,
            name: selection.name ?? existing.name,
            metadata: { ...existing.metadata, ...selection.metadata },
          }
        : selection;
      return {
        selections: [...baseList, merged],
        activeSelectionId: selection.id,
      };
    });
  },

  removeSelection: (id) => {
    get().pushSelectionHistory();
    set((state) => ({
      selections: state.selections.filter((s) => s.id !== id),
      activeSelectionId: state.activeSelectionId === id ? null : state.activeSelectionId,
    }));
  },

  renameSelection: (id, name) => {
    get().pushSelectionHistory();
    set((state) => ({
      selections: state.selections.map((s) => (s.id === id ? { ...s, name } : s)),
    }));
  },

  updateSelectionMetadata: (id, metadata) => {
    get().pushSelectionHistory();
    set((state) => ({
      selections: state.selections.map((s) =>
        s.id === id ? { ...s, metadata: { ...s.metadata, ...metadata } } : s,
      ),
    }));
  },

  clearSelections: () => {
    get().pushSelectionHistory();
    set({ selections: [], activeSelectionId: null });
  },

  transformActiveSelectionFaces: (transformer) => {
    get().pushSelectionHistory();
    set((state) => {
      const active = state.selections.find((s) => s.id === state.activeSelectionId);
      if (!active) return state;
      const next = transformer(active.faceRefs);
      return {
        selections: state.selections.map((s) =>
          s.id === active.id ? { ...s, faceRefs: next } : s,
        ),
      };
    });
  },

  saveSelectionAsNamed: (id, name) => {
    const sel = get().selections.find((s) => s.id === id);
    if (!sel) return;
    set((state) => ({
      namedSelections: { ...state.namedSelections, [name]: sel.faceRefs },
      selections: state.selections.map((s) => (s.id === id ? { ...s, name } : s)),
    }));
  },

  recallNamedSelection: (name) => {
    const refs = get().namedSelections[name];
    if (!refs) return;
    get().pushSelectionHistory();
    set((state) => {
      const id = `sel_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
      const meshRefs = Array.from(
        new Map(
          refs.map((r) => [
            r.meshRef.meshUuid ?? r.meshRef.objectName,
            r.meshRef,
          ]),
        ).values(),
      );
      const selection: Selection = {
        id,
        name,
        meshRefs,
        faceRefs: refs,
        bounding: { min: [0, 0, 0], max: [0, 0, 0], center: [0, 0, 0] },
        metadata: {},
        createdAt: Date.now(),
      };
      return {
        selections: [...state.selections, selection],
        activeSelectionId: id,
      };
    });
  },

  getActiveSelection: () => {
    const { selections, activeSelectionId } = get();
    return selections.find((s) => s.id === activeSelectionId) ?? null;
  },

  applyDesignPlanLocally: (plan) => {
    const { activeSelectionId, materialOptions } = get();
    const targetId = plan.selection === 'current' ? activeSelectionId : plan.selection;
    if (!targetId) return;

    let meta: Partial<Selection['metadata']> = {};
    let walls = { ...materialOptions.walls };

    for (const op of plan.operations) {
      if (op.type === 'set_color') {
        meta.color = op.value;
        walls.color = op.value;
        walls.theme = 'custom';
      } else if (op.type === 'apply_pattern') {
        meta.pattern = op.pattern;
        walls.pattern = op.pattern;
      } else if (op.type === 'set_material_preset') {
        meta.materialPreset = op.preset;
      }
    }

    set((state) => ({
      selections: state.selections.map((s) =>
        s.id === targetId ? { ...s, metadata: { ...s.metadata, ...meta } } : s,
      ),
      materialOptions: { ...materialOptions, walls },
    }));
  },

  pushHistory: () => {
    const { sceneGraph, history, historyIndex } = get();
    if (!sceneGraph) return;
    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push(JSON.parse(JSON.stringify(sceneGraph)));
    set({ history: newHistory, historyIndex: newHistory.length - 1 });
  },

  pushSelectionHistory: () => {
    const { selections, selectionHistory, selectionHistoryIndex } = get();
    const newHistory = selectionHistory.slice(0, selectionHistoryIndex + 1);
    newHistory.push(JSON.parse(JSON.stringify(selections)));
    if (newHistory.length > 64) newHistory.shift();
    set({
      selectionHistory: newHistory,
      selectionHistoryIndex: newHistory.length - 1,
    });
  },

  undoSelection: () => {
    const { selectionHistory, selectionHistoryIndex } = get();
    if (selectionHistoryIndex > 0) {
      const idx = selectionHistoryIndex - 1;
      const restored = selectionHistory[idx];
      set({
        selections: JSON.parse(JSON.stringify(restored)),
        selectionHistoryIndex: idx,
        activeSelectionId: null,
      });
    }
  },

  redoSelection: () => {
    const { selectionHistory, selectionHistoryIndex } = get();
    if (selectionHistoryIndex < selectionHistory.length - 1) {
      const idx = selectionHistoryIndex + 1;
      const restored = selectionHistory[idx];
      set({
        selections: JSON.parse(JSON.stringify(restored)),
        selectionHistoryIndex: idx,
        activeSelectionId: null,
      });
    }
  },

  updateWall: (id, updates) => {
    const { sceneGraph } = get();
    if (!sceneGraph) return;
    get().pushHistory();
    set((state) => {
      if (!state.sceneGraph) return state;
      const walls = state.sceneGraph.walls.map((w) => (w.id === id ? { ...w, ...updates } : w));
      return { sceneGraph: { ...state.sceneGraph, walls } };
    });
  },

  updateRoom: (id, updates) => {
    const { sceneGraph } = get();
    if (!sceneGraph) return;
    get().pushHistory();
    set((state) => {
      if (!state.sceneGraph) return state;
      const rooms = state.sceneGraph.rooms.map((r) => (r.id === id ? { ...r, ...updates } : r));
      return { sceneGraph: { ...state.sceneGraph, rooms } };
    });
  },

  updateDoor: (id, updates) => {
    const { sceneGraph } = get();
    if (!sceneGraph) return;
    get().pushHistory();
    set((state) => {
      if (!state.sceneGraph) return state;
      const doors = state.sceneGraph.doors.map((d) => (d.id === id ? { ...d, ...updates } : d));
      return { sceneGraph: { ...state.sceneGraph, doors } };
    });
  },

  updateWindow: (id, updates) => {
    const { sceneGraph } = get();
    if (!sceneGraph) return;
    get().pushHistory();
    set((state) => {
      if (!state.sceneGraph) return state;
      const windows = state.sceneGraph.windows.map((w) => (w.id === id ? { ...w, ...updates } : w));
      return { sceneGraph: { ...state.sceneGraph, windows } };
    });
  },

  undo: () => {
    const { history, historyIndex } = get();
    if (historyIndex > 0) {
      set({
        sceneGraph: JSON.parse(JSON.stringify(history[historyIndex - 1])),
        historyIndex: historyIndex - 1,
      });
    }
  },

  redo: () => {
    const { history, historyIndex } = get();
    if (historyIndex < history.length - 1) {
      set({
        sceneGraph: JSON.parse(JSON.stringify(history[historyIndex + 1])),
        historyIndex: historyIndex + 1,
      });
    }
  },

  setViewportOptions: (opts) => set((s) => ({ viewport: { ...s.viewport, ...opts } })),
  invalidateMeshUuids: () => set((state) => ({
    selections: state.selections.map((s) => ({
      ...s,
      meshRefs: s.meshRefs.map((m) => ({ objectName: m.objectName })),
      faceRefs: s.faceRefs.map((f) => ({ ...f, meshRef: { objectName: f.meshRef.objectName } })),
    })),
  })),

  loadProject: (projectId) => {
    const persisted = loadProjectState(projectId);
    if (!persisted) return;
    set((state) => ({
      viewport: { ...state.viewport, ...persisted.viewport },
      selectionTool: persisted.selectionTool ?? state.selectionTool,
      brushRadius: persisted.brushRadius ?? state.brushRadius,
      selections: persisted.selections.map((s) => ({
        ...s,
        meshRefs: s.meshRefs.map((m) => ({ ...m })),
        faceRefs: s.faceRefs.map((f) => ({ ...f })),
      })) as Selection[],
      activeSelectionId: persisted.activeSelectionId,
      selectionHistory: [persisted.selections as Selection[]],
      selectionHistoryIndex: 0,
    }));
  },

  persistProject: (projectId) => {
    const { sceneGraph, viewport, selections, activeSelectionId, selectionTool, brushRadius } = get();
    const id = projectId ?? deriveProjectId(sceneGraph);
    saveProjectState(id, {
      viewport,
      selections,
      activeSelectionId,
      selectionTool,
      brushRadius,
    });
  },

  resetSelectionsToPersisted: () => {
    const { sceneGraph } = get();
    const id = deriveProjectId(sceneGraph);
    const persisted = loadProjectState(id);
    if (!persisted) return;
    set({
      selections: persisted.selections as Selection[],
      activeSelectionId: persisted.activeSelectionId,
    });
  },
}));
