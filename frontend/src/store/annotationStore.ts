/**
 * annotationStore.ts
 * Zustand store for the interactive annotation review editor.
 *
 * The store holds a *deep-cloned* mutable copy of the scene graph so edits
 * never mutate the original result from the backend.
 *
 * History / undo-redo
 * -------------------
 * Every destructive action calls _pushHistory() first, which snapshots the
 * current scene graph into the `history` stack (max 50 entries).
 * `silent = true` skips the history push — used for drag updates so that
 * thousands of mousemove events don't pollute the history.
 * On mouseup, the calling code calls _pushHistory() once to commit.
 */

import { create } from 'zustand';
import type { SceneGraph, Wall, Door, FloorWindow, Room } from '../types/schema';

function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj)) as T;
}

// ─────────────────────────────────────────────────────────────────────────────
// Store shape
// ─────────────────────────────────────────────────────────────────────────────

export interface AnnotationStore {
  sceneGraph: SceneGraph | null;
  imageUrl: string | null;
  history: SceneGraph[];   // undo stack (oldest first)
  future: SceneGraph[];    // redo stack (most-recent first)

  // Setup
  setAnnotationData: (sg: SceneGraph, url: string) => void;

  // Internal – exposed so drag code can push history at end of drag
  _pushHistory: () => void;

  // Walls
  updateWall: (id: string, updates: Partial<Wall>, silent?: boolean) => void;
  addWall: (wall: Wall) => void;
  deleteWall: (id: string) => void;

  // Rooms
  updateRoom: (id: string, updates: Partial<Room>) => void;
  deleteRoom: (id: string) => void;

  // Doors
  updateDoor: (id: string, updates: Partial<Door>, silent?: boolean) => void;
  addDoor: (door: Door) => void;
  deleteDoor: (id: string) => void;

  // Windows
  updateWindow: (id: string, updates: Partial<FloorWindow>, silent?: boolean) => void;
  addWindow: (win: FloorWindow) => void;
  deleteWindow: (id: string) => void;

  // History
  undo: () => void;
  redo: () => void;

  // Cleanup
  reset: () => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Store implementation
// ─────────────────────────────────────────────────────────────────────────────

export const useAnnotationStore = create<AnnotationStore>((set, get) => ({
  sceneGraph: null,
  imageUrl: null,
  history: [],
  future: [],

  // ── Setup ────────────────────────────────────────────────────────────────

  setAnnotationData: (sg, url) =>
    set({ sceneGraph: deepClone(sg), imageUrl: url, history: [], future: [] }),

  // ── Internal ─────────────────────────────────────────────────────────────

  _pushHistory: () => {
    const { sceneGraph, history } = get();
    if (!sceneGraph) return;
    set({ history: [...history.slice(-49), deepClone(sceneGraph)], future: [] });
  },

  // ── Walls ────────────────────────────────────────────────────────────────

  updateWall: (id, updates, silent = false) => {
    if (!silent) get()._pushHistory();
    set(s => {
      if (!s.sceneGraph) return s;
      const sg = deepClone(s.sceneGraph);
      const i = sg.walls.findIndex(w => w.id === id);
      if (i >= 0) sg.walls[i] = { ...sg.walls[i], ...updates };
      return { sceneGraph: sg };
    });
  },

  addWall: (wall) => {
    get()._pushHistory();
    set(s => {
      if (!s.sceneGraph) return s;
      const sg = deepClone(s.sceneGraph);
      sg.walls.push(wall);
      return { sceneGraph: sg };
    });
  },

  deleteWall: (id) => {
    get()._pushHistory();
    set(s => {
      if (!s.sceneGraph) return s;
      const sg = deepClone(s.sceneGraph);
      sg.walls = sg.walls.filter(w => w.id !== id);
      return { sceneGraph: sg };
    });
  },

  // ── Rooms ────────────────────────────────────────────────────────────────

  updateRoom: (id, updates) => {
    get()._pushHistory();
    set(s => {
      if (!s.sceneGraph) return s;
      const sg = deepClone(s.sceneGraph);
      const i = sg.rooms.findIndex(r => r.id === id);
      if (i >= 0) sg.rooms[i] = { ...sg.rooms[i], ...updates };
      return { sceneGraph: sg };
    });
  },

  deleteRoom: (id) => {
    get()._pushHistory();
    set(s => {
      if (!s.sceneGraph) return s;
      const sg = deepClone(s.sceneGraph);
      sg.rooms = sg.rooms.filter(r => r.id !== id);
      return { sceneGraph: sg };
    });
  },

  // ── Doors ────────────────────────────────────────────────────────────────

  updateDoor: (id, updates, silent = false) => {
    if (!silent) get()._pushHistory();
    set(s => {
      if (!s.sceneGraph) return s;
      const sg = deepClone(s.sceneGraph);
      const i = sg.doors.findIndex(d => d.id === id);
      if (i >= 0) sg.doors[i] = { ...sg.doors[i], ...updates };
      return { sceneGraph: sg };
    });
  },

  addDoor: (door) => {
    get()._pushHistory();
    set(s => {
      if (!s.sceneGraph) return s;
      const sg = deepClone(s.sceneGraph);
      sg.doors.push(door);
      return { sceneGraph: sg };
    });
  },

  deleteDoor: (id) => {
    get()._pushHistory();
    set(s => {
      if (!s.sceneGraph) return s;
      const sg = deepClone(s.sceneGraph);
      sg.doors = sg.doors.filter(d => d.id !== id);
      return { sceneGraph: sg };
    });
  },

  // ── Windows ──────────────────────────────────────────────────────────────

  updateWindow: (id, updates, silent = false) => {
    if (!silent) get()._pushHistory();
    set(s => {
      if (!s.sceneGraph) return s;
      const sg = deepClone(s.sceneGraph);
      const i = sg.windows.findIndex(w => w.id === id);
      if (i >= 0) sg.windows[i] = { ...sg.windows[i], ...updates };
      return { sceneGraph: sg };
    });
  },

  addWindow: (win) => {
    get()._pushHistory();
    set(s => {
      if (!s.sceneGraph) return s;
      const sg = deepClone(s.sceneGraph);
      sg.windows.push(win);
      return { sceneGraph: sg };
    });
  },

  deleteWindow: (id) => {
    get()._pushHistory();
    set(s => {
      if (!s.sceneGraph) return s;
      const sg = deepClone(s.sceneGraph);
      sg.windows = sg.windows.filter(w => w.id !== id);
      return { sceneGraph: sg };
    });
  },

  // ── History ──────────────────────────────────────────────────────────────

  undo: () => {
    const { history, sceneGraph, future } = get();
    if (!history.length) return;
    const prev = history[history.length - 1];
    set({
      sceneGraph: prev,
      history: history.slice(0, -1),
      future: sceneGraph ? [sceneGraph, ...future] : future,
    });
  },

  redo: () => {
    const { future, sceneGraph, history } = get();
    if (!future.length) return;
    const next = future[0];
    set({
      sceneGraph: next,
      future: future.slice(1),
      history: sceneGraph ? [...history, sceneGraph] : history,
    });
  },

  // ── Cleanup ──────────────────────────────────────────────────────────────

  reset: () => set({ sceneGraph: null, imageUrl: null, history: [], future: [] }),
}));
