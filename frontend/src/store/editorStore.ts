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

  viewport: ViewportOptions;

  setSceneGraph: (graph: SceneGraph) => void;
  setGlbUrl: (url: string | null) => void;
  bumpGlbVersion: () => void;
  setSyncStatus: (status: SyncStatus, error?: string | null) => void;
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

  updateWall: (id: string, updates: Partial<Wall>) => void;
  updateRoom: (id: string, updates: Partial<Room>) => void;
  updateDoor: (id: string, updates: Partial<Door>) => void;
  updateWindow: (id: string, updates: Partial<FloorWindow>) => void;

  undo: () => void;
  redo: () => void;
  pushHistory: () => void;

  getActiveSelection: () => Selection | null;
  applyDesignPlanLocally: (plan: DesignActionPlan) => void;

  setViewportOptions: (opts: Partial<ViewportOptions>) => void;
  invalidateMeshUuids: () => void;
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

  selectedObjectId: null,
  selectedObjectType: null,

  selections: [],
  activeSelectionId: null,
  selectionTool: 'click',
  brushRadius: 0.15,

  materialOptions: DEFAULT_MATERIALS,
  includeBase: true,
  includeRoof: false,

  history: [],
  historyIndex: -1,

  viewport: { showAxes: true, showGrid: true, background: 'slate' },

  setSceneGraph: (graph) =>
    set({
      sceneGraph: graph,
      history: [graph],
      historyIndex: 0,
      selectedObjectId: null,
      selectedObjectType: null,
      selections: [],
      activeSelectionId: null,
    }),

  setGlbUrl: (url) => set({ glbUrl: url }),
  bumpGlbVersion: () => set((s) => ({ glbVersion: s.glbVersion + 1 })),
  setSyncStatus: (status, error = null) => set({ syncStatus: status, syncError: error }),
  setMaterialOptions: (opts) => set({ materialOptions: opts }),
  setExportOptions: (includeBase, includeRoof) => set({ includeBase, includeRoof }),

  selectObject: (id, type) => set({ selectedObjectId: id, selectedObjectType: type }),

  setSelectionTool: (tool) => set({ selectionTool: tool }),
  setBrushRadius: (radius) => set({ brushRadius: radius }),
  setActiveSelection: (id) => set({ activeSelectionId: id }),

  addSelection: (selection, merge) =>
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
    }),

  removeSelection: (id) =>
    set((state) => ({
      selections: state.selections.filter((s) => s.id !== id),
      activeSelectionId: state.activeSelectionId === id ? null : state.activeSelectionId,
    })),

  renameSelection: (id, name) =>
    set((state) => ({
      selections: state.selections.map((s) => (s.id === id ? { ...s, name } : s)),
    })),

  updateSelectionMetadata: (id, metadata) =>
    set((state) => ({
      selections: state.selections.map((s) =>
        s.id === id ? { ...s, metadata: { ...s.metadata, ...metadata } } : s,
      ),
    })),

  clearSelections: () => set({ selections: [], activeSelectionId: null }),

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
}));
