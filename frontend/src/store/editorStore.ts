import { create } from 'zustand';
import type { SceneGraph, Wall, Room, Door, FloorWindow } from '../types/schema';

interface EditorState {
  sceneGraph: SceneGraph | null;
  selectedObjectId: string | null;
  selectedObjectType: 'wall' | 'room' | 'door' | 'window' | 'ocr' | null;
  history: SceneGraph[];
  historyIndex: number;
  
  // Actions
  setSceneGraph: (graph: SceneGraph) => void;
  selectObject: (id: string | null, type: 'wall' | 'room' | 'door' | 'window' | 'ocr' | null) => void;
  
  // Edits
  updateWall: (id: string, updates: Partial<Wall>) => void;
  updateRoom: (id: string, updates: Partial<Room>) => void;
  updateDoor: (id: string, updates: Partial<Door>) => void;
  updateWindow: (id: string, updates: Partial<FloorWindow>) => void;
  
  // History
  undo: () => void;
  redo: () => void;
  pushHistory: () => void;
}

export const useEditorStore = create<EditorState>((set, get) => ({
  sceneGraph: null,
  selectedObjectId: null,
  selectedObjectType: null,
  history: [],
  historyIndex: -1,

  setSceneGraph: (graph) => set({ 
    sceneGraph: graph, 
    history: [graph], 
    historyIndex: 0,
    selectedObjectId: null,
    selectedObjectType: null
  }),

  selectObject: (id, type) => set({ selectedObjectId: id, selectedObjectType: type }),

  pushHistory: () => {
    const { sceneGraph, history, historyIndex } = get();
    if (!sceneGraph) return;
    
    // If we were at a past state, truncate the future history
    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push(JSON.parse(JSON.stringify(sceneGraph))); // Deep copy
    
    set({
      history: newHistory,
      historyIndex: newHistory.length - 1
    });
  },

  updateWall: (id, updates) => {
    const { sceneGraph } = get();
    if (!sceneGraph) return;
    
    get().pushHistory();
    set((state) => {
      if (!state.sceneGraph) return state;
      const walls = state.sceneGraph.walls.map(w => w.id === id ? { ...w, ...updates } : w);
      return { sceneGraph: { ...state.sceneGraph, walls } };
    });
  },

  updateRoom: (id, updates) => {
    const { sceneGraph } = get();
    if (!sceneGraph) return;
    
    get().pushHistory();
    set((state) => {
      if (!state.sceneGraph) return state;
      const rooms = state.sceneGraph.rooms.map(r => r.id === id ? { ...r, ...updates } : r);
      return { sceneGraph: { ...state.sceneGraph, rooms } };
    });
  },

  updateDoor: (id, updates) => {
    const { sceneGraph } = get();
    if (!sceneGraph) return;
    
    get().pushHistory();
    set((state) => {
      if (!state.sceneGraph) return state;
      const doors = state.sceneGraph.doors.map(d => d.id === id ? { ...d, ...updates } : d);
      return { sceneGraph: { ...state.sceneGraph, doors } };
    });
  },

  updateWindow: (id, updates) => {
    const { sceneGraph } = get();
    if (!sceneGraph) return;
    
    get().pushHistory();
    set((state) => {
      if (!state.sceneGraph) return state;
      const windows = state.sceneGraph.windows.map(w => w.id === id ? { ...w, ...updates } : w);
      return { sceneGraph: { ...state.sceneGraph, windows } };
    });
  },

  undo: () => {
    const { history, historyIndex } = get();
    if (historyIndex > 0) {
      set({
        sceneGraph: JSON.parse(JSON.stringify(history[historyIndex - 1])),
        historyIndex: historyIndex - 1
      });
    }
  },

  redo: () => {
    const { history, historyIndex } = get();
    if (historyIndex < history.length - 1) {
      set({
        sceneGraph: JSON.parse(JSON.stringify(history[historyIndex + 1])),
        historyIndex: historyIndex + 1
      });
    }
  }
}));
