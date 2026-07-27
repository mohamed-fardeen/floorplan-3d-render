/**
 * AnnotationPage.tsx
 * Full-screen interactive floor-plan annotation editor.
 *
 * Coordinate systems
 * ------------------
 * The scene graph stores coordinates in **metres** with y increasing upward
 * (standard math convention, as produced by the CoordinateNormalizer).
 *
 * The SVG canvas uses **pixels** with y increasing downward (standard SVG).
 *
 * Conversion:
 *   screenX = x_m * mToPx + PAD
 *   screenY = canvasH - y_m * mToPx - PAD
 *
 * where  mToPx = 1 / scale_pixel_to_meter  ≈ 51.2 px/m
 *        PAD   = 48 px margin around the drawing
 *        canvasH = max_y_m * mToPx + 2 * PAD
 */

import React, {
  useState, useRef, useCallback, useEffect, useMemo,
} from 'react';
import { useAnnotationStore } from '../store/annotationStore';
import type { SceneGraph, Wall, Door, FloorWindow } from '../types/schema';
import { exportBlender } from '../api/client';

// ─────────────────────────────────────────────────────────────────────────────
// Constants & types
// ─────────────────────────────────────────────────────────────────────────────

const PAD = 48;            // canvas padding in px
const HANDLE_R = 8;        // drag handle radius in px
const MIN_WALL_PX = 4;     // minimum rendered wall thickness in px

type Tool = 'select' | 'add-wall' | 'add-door' | 'add-window';
type ElementType = 'wall' | 'room' | 'door' | 'window';
type Selection = { type: ElementType; id: string } | null;
type DragState = {
  handle: 'wall-start' | 'wall-end' | 'door' | 'window';
  id: string;
} | null;

// SVG colours
const C = {
  wall:       '#ef4444',   // red-500
  wallSel:    '#f97316',   // orange-500
  room:       '#22c55e',   // green-500
  door:       '#3b82f6',   // blue-500
  window:     '#06b6d4',   // cyan-500
  handle:     '#f97316',   // orange-500
  ghost:      'rgba(239,68,68,0.45)',
  roomFill:   'rgba(34,197,94,0.15)',
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

let _idCounter = 1;
const newId = (prefix: string) => `${prefix}_${Date.now()}_${_idCounter++}`;

function wallLength(w: Wall): number {
  const dx = w.end[0] - w.start[0];
  const dy = w.end[1] - w.start[1];
  return Math.sqrt(dx * dx + dy * dy);
}

// ─────────────────────────────────────────────────────────────────────────────
// Props
// ─────────────────────────────────────────────────────────────────────────────

interface AnnotationPageProps {
  onApprove: (sceneGraph: SceneGraph) => void;
  onBack: () => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// AnnotationPage
// ─────────────────────────────────────────────────────────────────────────────

export const AnnotationPage: React.FC<AnnotationPageProps> = ({ onApprove, onBack }) => {
  const store = useAnnotationStore();

  // ── Editor state ────────────────────────────────────────────────────────

  const svgRef                         = useRef<SVGSVGElement>(null);
  const [activeTool, setActiveTool]    = useState<Tool>('select');
  const [selection, setSelection]      = useState<Selection>(null);
  const [dragState, setDragState]      = useState<DragState>(null);
  const [wallStart, setWallStart]      = useState<[number,number] | null>(null);
  const [ghostPt, setGhostPt]          = useState<[number,number] | null>(null);
  const [isExporting, setIsExporting]  = useState(false);
  const [exportError, setExportError]  = useState<string | null>(null);

  const { sceneGraph, imageUrl, history, future } = store;

  // ── Coordinate math ─────────────────────────────────────────────────────

  const mToPx = sceneGraph
    ? 1.0 / sceneGraph.metadata.scale_pixel_to_meter
    : 51.2;

  const { canvasW, canvasH } = useMemo(() => {
    if (!sceneGraph) return { canvasW: 512 + PAD * 2, canvasH: 512 + PAD * 2 };
    const { walls, rooms, doors, windows } = sceneGraph;
    const xs = [
      ...walls.flatMap(w  => [w.start[0], w.end[0]]),
      ...rooms.flatMap(r  => r.polygon.map(p => p[0])),
      ...doors.map(d       => d.center[0]),
      ...windows.map(w    => w.center[0]),
    ];
    const ys = [
      ...walls.flatMap(w  => [w.start[1], w.end[1]]),
      ...rooms.flatMap(r  => r.polygon.map(p => p[1])),
      ...doors.map(d       => d.center[1]),
      ...windows.map(w    => w.center[1]),
    ];
    const maxX = xs.length ? Math.max(...xs) : 10;
    const maxY = ys.length ? Math.max(...ys) : 10;
    return {
      canvasW: maxX * mToPx + PAD * 2,
      canvasH: maxY * mToPx + PAD * 2,
    };
  }, [sceneGraph, mToPx]);

  /** metres → SVG pixels */
  const toSvg = useCallback((xm: number, ym: number) => ({
    x: xm * mToPx + PAD,
    y: canvasH - ym * mToPx - PAD,
  }), [mToPx, canvasH]);

  /** SVG pixels → metres */
  const fromSvg = useCallback((sx: number, sy: number) => ({
    x: Math.max(0, (sx - PAD) / mToPx),
    y: Math.max(0, (canvasH - sy - PAD) / mToPx),
  }), [mToPx, canvasH]);

  /** Get SVG-space coordinates from a mouse event (accounts for CSS scaling) */
  const getSvgPt = useCallback((e: MouseEvent | React.MouseEvent) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const rect = svg.getBoundingClientRect();
    const scaleX = canvasW / rect.width;
    const scaleY = canvasH / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top)  * scaleY,
    };
  }, [canvasW, canvasH]);

  // ── Keyboard shortcuts ──────────────────────────────────────────────────

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === 'INPUT') return; // don't eat input field events
      if (e.key === 'Escape') {
        setWallStart(null);
        setGhostPt(null);
        setActiveTool('select');
      }
      if ((e.key === 'Delete' || e.key === 'Backspace') && selection) {
        deleteSelected(selection);
        setSelection(null);
      }
      if (e.ctrlKey && e.key === 'z') { e.preventDefault(); store.undo(); setSelection(null); }
      if (e.ctrlKey && e.key === 'y') { e.preventDefault(); store.redo(); setSelection(null); }
      if (e.key === 'v') setActiveTool('select');
      if (e.key === 'w') setActiveTool('add-wall');
      if (e.key === 'd') setActiveTool('add-door');
      if (e.key === 'n') setActiveTool('add-window');
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selection, store]);

  const deleteSelected = (sel: Selection) => {
    if (!sel) return;
    if (sel.type === 'wall')   store.deleteWall(sel.id);
    if (sel.type === 'door')   store.deleteDoor(sel.id);
    if (sel.type === 'window') store.deleteWindow(sel.id);
    if (sel.type === 'room')   store.deleteRoom(sel.id);
  };

  // ── Global drag tracking ────────────────────────────────────────────────

  useEffect(() => {
    if (!dragState) return;
    const onMove = (e: MouseEvent) => {
      const pt = getSvgPt(e);
      const m  = fromSvg(pt.x, pt.y);
      if (dragState.handle === 'wall-start')
        store.updateWall(dragState.id, { start: [m.x, m.y] }, true);
      else if (dragState.handle === 'wall-end')
        store.updateWall(dragState.id, { end: [m.x, m.y] }, true);
      else if (dragState.handle === 'door')
        store.updateDoor(dragState.id, { center: [m.x, m.y] }, true);
      else if (dragState.handle === 'window')
        store.updateWindow(dragState.id, { center: [m.x, m.y] }, true);
    };
    const onUp = () => {
      store._pushHistory(); // commit drag to history as one action
      setDragState(null);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [dragState, getSvgPt, fromSvg, store]);

  // ── SVG canvas interactions ──────────────────────────────────────────────

  const handleSvgMouseMove = (e: React.MouseEvent) => {
    const pt = getSvgPt(e);
    const m  = fromSvg(pt.x, pt.y);
    setGhostPt([m.x, m.y]);
  };

  const handleSvgClick = (e: React.MouseEvent) => {
    if (e.target === svgRef.current) {
      // Clicked empty canvas
      if (activeTool === 'select') {
        setSelection(null);
        return;
      }
    }

    if (activeTool === 'add-wall') {
      const pt = getSvgPt(e);
      const m  = fromSvg(pt.x, pt.y);
      if (!wallStart) {
        setWallStart([m.x, m.y]);
      } else {
        // Commit new wall
        const defaultThick = sceneGraph?.metadata
          ? (sceneGraph.metadata.scale_pixel_to_meter * 10) // ~0.2m
          : 0.20;
        store.addWall({
          id: newId('w'),
          start: wallStart,
          end: [m.x, m.y],
          thickness: defaultThick,
          length: undefined,
        });
        setWallStart(null);
        setGhostPt(null);
      }
      return;
    }

    if (activeTool === 'add-door') {
      const pt = getSvgPt(e);
      const m  = fromSvg(pt.x, pt.y);
      const defW = sceneGraph
        ? sceneGraph.metadata.scale_pixel_to_meter * 40  // ~0.8m door
        : 0.8;
      store.addDoor({
        id: newId('d'),
        wall_id: '',
        center: [m.x, m.y],
        width: defW,
        is_open: false,
      });
      return;
    }

    if (activeTool === 'add-window') {
      const pt = getSvgPt(e);
      const m  = fromSvg(pt.x, pt.y);
      const defW = sceneGraph
        ? sceneGraph.metadata.scale_pixel_to_meter * 60  // ~1.2m window
        : 1.2;
      store.addWindow({
        id: newId('win'),
        wall_id: '',
        center: [m.x, m.y],
        width: defW,
      });
    }
  };

  // ── Approve & export ─────────────────────────────────────────────────────

  const handleApprove = async () => {
    if (!sceneGraph) return;
    setIsExporting(true);
    setExportError(null);
    try {
      onApprove(sceneGraph);
    } catch (err: any) {
      setExportError(err.message || String(err));
      setIsExporting(false);
    }
  };

  // ── Guard ────────────────────────────────────────────────────────────────

  if (!sceneGraph || !imageUrl) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950 text-gray-400">
        No annotation data — go back and upload a floor plan.
      </div>
    );
  }

  const { walls, doors, windows, rooms } = sceneGraph;
  const scale = sceneGraph.metadata.scale_pixel_to_meter;
  const conf  = Math.round((sceneGraph.metadata.confidence_score ?? 0) * 100);

  // ── Render ──────────────────────────────────────────────────────────────

  const toolBtn = (tool: Tool, label: string, shortcut: string, icon: React.ReactNode) => (
    <button
      key={tool}
      title={`${label} (${shortcut})`}
      onClick={() => { setActiveTool(tool); setWallStart(null); setGhostPt(null); }}
      className={`flex flex-col items-center gap-1 px-2 py-3 rounded-lg transition-all text-xs
        ${activeTool === tool
          ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-900/50'
          : 'text-gray-400 hover:bg-gray-800 hover:text-gray-100'}`}
    >
      <span className="text-lg">{icon}</span>
      <span className="leading-none">{shortcut}</span>
    </button>
  );

  const selWall   = selection?.type === 'wall'   ? walls.find(w => w.id === selection.id)   : null;
  const selDoor   = selection?.type === 'door'   ? doors.find(d => d.id === selection.id)   : null;
  const selWindow = selection?.type === 'window' ? windows.find(w => w.id === selection.id) : null;
  const selRoom   = selection?.type === 'room'   ? rooms.find(r => r.id === selection.id)   : null;

  return (
    <div
      className="flex flex-col h-screen w-screen bg-gray-950 text-gray-100 overflow-hidden select-none"
      style={{ fontFamily: "'Inter', system-ui, sans-serif" }}
    >
      {/* ── Top bar ──────────────────────────────────────────────────────── */}
      <header className="flex items-center gap-4 px-5 py-3 bg-gray-900 border-b border-gray-800 shrink-0 z-10">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-gray-400 hover:text-gray-100 transition-colors text-sm font-medium"
        >
          <span>←</span>
          <span>Back</span>
        </button>

        <div className="w-px h-5 bg-gray-700" />

        <h1 className="text-sm font-semibold text-gray-100">
          Annotation Review
          <span className="ml-2 text-xs font-normal text-gray-500">— review &amp; edit before 3D generation</span>
        </h1>

        {/* Confidence badge */}
        <span
          className={`ml-2 px-2 py-0.5 rounded-full text-xs font-semibold
            ${conf >= 70 ? 'bg-green-900 text-green-300'
              : conf >= 45 ? 'bg-yellow-900 text-yellow-300'
              : 'bg-red-900 text-red-300'}`}
        >
          {conf}% confidence
        </span>

        {/* Stats */}
        <div className="flex items-center gap-3 ml-2 text-xs text-gray-500">
          <span><span className="text-red-400 font-medium">{walls.length}</span> walls</span>
          <span><span className="text-green-400 font-medium">{rooms.length}</span> rooms</span>
          <span><span className="text-blue-400 font-medium">{doors.length}</span> doors</span>
          <span><span className="text-cyan-400 font-medium">{windows.length}</span> windows</span>
        </div>

        <div className="flex-1" />

        {/* Undo / Redo */}
        <button
          onClick={() => { store.undo(); setSelection(null); }}
          disabled={!history.length}
          title="Undo (Ctrl+Z)"
          className="px-3 py-1.5 text-xs rounded-md bg-gray-800 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >↺ Undo</button>
        <button
          onClick={() => { store.redo(); setSelection(null); }}
          disabled={!future.length}
          title="Redo (Ctrl+Y)"
          className="px-3 py-1.5 text-xs rounded-md bg-gray-800 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >↻ Redo</button>

        <div className="w-px h-5 bg-gray-700" />

        {/* Approve */}
        <button
          onClick={handleApprove}
          disabled={isExporting}
          className="flex items-center gap-2 px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500
            disabled:opacity-50 disabled:cursor-not-allowed
            text-white text-sm font-semibold shadow-lg shadow-indigo-900/40
            transition-all active:scale-95"
        >
          {isExporting ? (
            <><span className="animate-spin">⟳</span> Opening Blender…</>
          ) : (
            <>✓ Approve &amp; Generate 3D</>
          )}
        </button>
      </header>

      {exportError && (
        <div className="mx-4 mt-2 p-3 bg-red-950 border border-red-800 rounded-lg text-red-300 text-sm">
          {exportError}
        </div>
      )}

      {/* ── Main layout ──────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── Left toolbar ──────────────────────────────────────────────── */}
        <aside className="flex flex-col items-center gap-1.5 w-16 bg-gray-900 border-r border-gray-800 py-4 shrink-0">
          {toolBtn('select',      'Select',      'V', '↖')}
          {toolBtn('add-wall',    'Draw Wall',   'W', '▬')}
          {toolBtn('add-door',    'Add Door',    'D', '🚪')}
          {toolBtn('add-window',  'Add Window',  'N', '⬜')}

          <div className="w-8 h-px bg-gray-700 my-1" />

          {/* Legend */}
          <div className="flex flex-col items-start gap-1.5 px-1 mt-1">
            {[
              { color: '#ef4444', label: 'Wall'   },
              { color: '#22c55e', label: 'Room'   },
              { color: '#3b82f6', label: 'Door'   },
              { color: '#06b6d4', label: 'Window' },
            ].map(({ color, label }) => (
              <div key={label} className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-sm" style={{ background: color }} />
                <span className="text-gray-500 text-[9px]">{label}</span>
              </div>
            ))}
          </div>
        </aside>

        {/* ── Canvas ────────────────────────────────────────────────────── */}
        <main className="flex-1 overflow-auto bg-gray-950 flex items-start justify-center p-6">
          <div
            className="relative rounded-xl overflow-hidden shadow-2xl border border-gray-800"
            style={{ width: canvasW, height: canvasH, minWidth: 200, minHeight: 200 }}
          >
            <svg
              ref={svgRef}
              width={canvasW}
              height={canvasH}
              viewBox={`0 0 ${canvasW} ${canvasH}`}
              onClick={handleSvgClick}
              onMouseMove={handleSvgMouseMove}
              onMouseLeave={() => setGhostPt(null)}
              style={{
                cursor: activeTool === 'select' ? 'default'
                  : activeTool === 'add-wall' && wallStart ? 'crosshair'
                  : 'crosshair',
                display: 'block',
              }}
            >
              {/* Background image — stretched to cover the coordinate space */}
              <image
                href={imageUrl}
                x={0} y={0}
                width={canvasW} height={canvasH}
                preserveAspectRatio="xMidYMid slice"
                opacity={0.80}
              />

              {/* Dark vignette around edges */}
              <defs>
                <radialGradient id="vig" cx="50%" cy="50%" r="70%">
                  <stop offset="0%"   stopColor="transparent" />
                  <stop offset="100%" stopColor="rgba(0,0,0,0.35)" />
                </radialGradient>
              </defs>
              <rect x={0} y={0} width={canvasW} height={canvasH} fill="url(#vig)" />

              {/* ── Rooms ──────────────────────────────────────────────── */}
              {rooms.map(room => {
                if (room.polygon.length < 3) return null;
                const pts = room.polygon.map(([x, y]) => {
                  const s = toSvg(x, y);
                  return `${s.x},${s.y}`;
                }).join(' ');
                const isSel = selection?.id === room.id;
                return (
                  <g key={room.id}>
                    <polygon
                      points={pts}
                      fill={C.roomFill}
                      stroke={isSel ? C.wallSel : C.room}
                      strokeWidth={isSel ? 2.5 : 1.5}
                      strokeDasharray={isSel ? '6 3' : undefined}
                      onClick={e => { e.stopPropagation(); if (activeTool === 'select') setSelection({ type: 'room', id: room.id }); }}
                      style={{ cursor: 'pointer' }}
                    />
                    {room.centroid && (() => {
                      const c = toSvg(room.centroid[0], room.centroid[1]);
                      return (
                        <text
                          x={c.x} y={c.y}
                          textAnchor="middle" dominantBaseline="middle"
                          fontSize={11} fontWeight="600"
                          fill={C.room} stroke="rgba(0,0,0,0.6)" strokeWidth={3} paintOrder="stroke"
                          style={{ pointerEvents: 'none' }}
                        >
                          {room.label || room.type || room.id}
                        </text>
                      );
                    })()}
                  </g>
                );
              })}

              {/* ── Walls ──────────────────────────────────────────────── */}
              {walls.map(wall => {
                const p1     = toSvg(wall.start[0], wall.start[1]);
                const p2     = toSvg(wall.end[0],   wall.end[1]);
                const thickPx = Math.max(wall.thickness / scale, MIN_WALL_PX);
                const isSel  = selection?.id === wall.id;
                const len    = wallLength(wall);
                const midX   = (p1.x + p2.x) / 2;
                const midY   = (p1.y + p2.y) / 2;

                return (
                  <g key={wall.id}>
                    {/* Wider invisible hit area */}
                    <line
                      x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                      stroke="transparent"
                      strokeWidth={Math.max(thickPx + 12, 20)}
                      onClick={e => { e.stopPropagation(); if (activeTool === 'select') setSelection({ type: 'wall', id: wall.id }); }}
                      style={{ cursor: 'pointer' }}
                    />
                    {/* Visible wall */}
                    <line
                      x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                      stroke={isSel ? C.wallSel : C.wall}
                      strokeWidth={thickPx}
                      strokeLinecap="square"
                      style={{ pointerEvents: 'none' }}
                    />
                    {/* Selection dashes */}
                    {isSel && (
                      <line
                        x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                        stroke="white" strokeWidth={1.5}
                        strokeLinecap="square"
                        strokeDasharray="6 4"
                        opacity={0.6}
                        style={{ pointerEvents: 'none' }}
                      />
                    )}
                    {/* Length label */}
                    <text
                      x={midX} y={midY - thickPx / 2 - 4}
                      textAnchor="middle"
                      fontSize={9} fontWeight="500"
                      fill={isSel ? C.wallSel : C.wall}
                      stroke="rgba(0,0,0,0.7)" strokeWidth={2.5} paintOrder="stroke"
                      style={{ pointerEvents: 'none' }}
                    >
                      {len.toFixed(2)}m
                    </text>
                    {/* Drag handles (only when selected) */}
                    {isSel && (
                      <>
                        <circle
                          cx={p1.x} cy={p1.y} r={HANDLE_R}
                          fill={C.handle} stroke="white" strokeWidth={2}
                          onMouseDown={e => { e.stopPropagation(); setDragState({ handle: 'wall-start', id: wall.id }); }}
                          style={{ cursor: 'grab' }}
                        />
                        <circle
                          cx={p2.x} cy={p2.y} r={HANDLE_R}
                          fill={C.handle} stroke="white" strokeWidth={2}
                          onMouseDown={e => { e.stopPropagation(); setDragState({ handle: 'wall-end', id: wall.id }); }}
                          style={{ cursor: 'grab' }}
                        />
                      </>
                    )}
                  </g>
                );
              })}

              {/* ── Doors ──────────────────────────────────────────────── */}
              {doors.map(door => {
                const c   = toSvg(door.center[0], door.center[1]);
                const hw  = Math.max((door.width / scale) / 2, 10);
                const isSel = selection?.id === door.id;
                return (
                  <g key={door.id}
                    onClick={e => { e.stopPropagation(); if (activeTool === 'select') setSelection({ type: 'door', id: door.id }); }}
                    style={{ cursor: 'pointer' }}
                  >
                    <rect
                      x={c.x - hw} y={c.y - 6} width={hw * 2} height={12}
                      fill={C.door} opacity={0.85}
                      stroke={isSel ? 'white' : C.door} strokeWidth={isSel ? 2 : 1}
                      rx={2}
                    />
                    <text
                      x={c.x} y={c.y - 10}
                      textAnchor="middle" fontSize={8} fontWeight="600"
                      fill={C.door} stroke="rgba(0,0,0,0.7)" strokeWidth={2} paintOrder="stroke"
                      style={{ pointerEvents: 'none' }}
                    >{door.id}</text>
                    {/* Drag handle */}
                    {isSel && (
                      <circle cx={c.x} cy={c.y} r={HANDLE_R}
                        fill={C.handle} stroke="white" strokeWidth={2}
                        onMouseDown={e => { e.stopPropagation(); setDragState({ handle: 'door', id: door.id }); }}
                        style={{ cursor: 'grab' }}
                      />
                    )}
                  </g>
                );
              })}

              {/* ── Windows ────────────────────────────────────────────── */}
              {windows.map(win => {
                const c   = toSvg(win.center[0], win.center[1]);
                const hw  = Math.max((win.width / scale) / 2, 8);
                const isSel = selection?.id === win.id;
                return (
                  <g key={win.id}
                    onClick={e => { e.stopPropagation(); if (activeTool === 'select') setSelection({ type: 'window', id: win.id }); }}
                    style={{ cursor: 'pointer' }}
                  >
                    <rect
                      x={c.x - hw} y={c.y - 4} width={hw * 2} height={8}
                      fill="transparent"
                      stroke={isSel ? 'white' : C.window} strokeWidth={isSel ? 2.5 : 2}
                      rx={2}
                    />
                    <rect
                      x={c.x - hw + 2} y={c.y - 1} width={(hw - 2) * 2} height={2}
                      fill={C.window} opacity={0.6} style={{ pointerEvents: 'none' }}
                    />
                    <text
                      x={c.x} y={c.y - 8}
                      textAnchor="middle" fontSize={8} fontWeight="600"
                      fill={C.window} stroke="rgba(0,0,0,0.7)" strokeWidth={2} paintOrder="stroke"
                      style={{ pointerEvents: 'none' }}
                    >{win.id}</text>
                    {isSel && (
                      <circle cx={c.x} cy={c.y} r={HANDLE_R}
                        fill={C.handle} stroke="white" strokeWidth={2}
                        onMouseDown={e => { e.stopPropagation(); setDragState({ handle: 'window', id: win.id }); }}
                        style={{ cursor: 'grab' }}
                      />
                    )}
                  </g>
                );
              })}

              {/* ── Ghost line (add-wall tool) ──────────────────────────── */}
              {activeTool === 'add-wall' && wallStart && ghostPt && (() => {
                const p1 = toSvg(wallStart[0], wallStart[1]);
                const p2 = toSvg(ghostPt[0],   ghostPt[1]);
                const defThick = Math.max(0.20 / scale, MIN_WALL_PX);
                return (
                  <>
                    <line
                      x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                      stroke={C.ghost} strokeWidth={defThick}
                      strokeLinecap="square"
                      strokeDasharray="10 5"
                      style={{ pointerEvents: 'none' }}
                    />
                    <circle cx={p1.x} cy={p1.y} r={6}
                      fill={C.wall} opacity={0.8}
                      style={{ pointerEvents: 'none' }}
                    />
                    <circle cx={p2.x} cy={p2.y} r={4}
                      fill={C.wall} opacity={0.5}
                      style={{ pointerEvents: 'none' }}
                    />
                  </>
                );
              })()}

              {/* ── Crosshair dot when using placement tools ────────────── */}
              {activeTool !== 'select' && ghostPt && (() => {
                const g = toSvg(ghostPt[0], ghostPt[1]);
                return (
                  <circle cx={g.x} cy={g.y} r={3}
                    fill="white" opacity={0.6}
                    style={{ pointerEvents: 'none' }}
                  />
                );
              })()}
            </svg>
          </div>
        </main>

        {/* ── Right properties panel ────────────────────────────────────── */}
        <aside className="w-72 bg-gray-900 border-l border-gray-800 flex flex-col shrink-0 overflow-y-auto">
          <div className="p-4 border-b border-gray-800">
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">Properties</h2>
          </div>

          {!selection && (
            <div className="flex-1 flex items-center justify-center p-6 text-center">
              <div className="text-gray-600">
                <div className="text-3xl mb-3">↖</div>
                <p className="text-sm font-medium text-gray-500">Click an element to inspect or edit it</p>
                <p className="text-xs text-gray-600 mt-2">Use the toolbar on the left to add or draw new elements</p>
              </div>
            </div>
          )}

          {/* Wall properties */}
          {selWall && (
            <div className="p-4 space-y-4">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-sm bg-red-500" />
                <span className="text-sm font-semibold text-gray-200">Wall</span>
                <span className="text-xs text-gray-500 font-mono ml-auto">{selWall.id}</span>
              </div>
              <PropRow label="Length">
                <span className="text-gray-300 font-mono text-sm">{wallLength(selWall).toFixed(3)} m</span>
              </PropRow>
              <PropRow label="Thickness">
                <input
                  type="number" step={0.01} min={0.05} max={2.0}
                  value={selWall.thickness.toFixed(3)}
                  onChange={e => store.updateWall(selWall.id, { thickness: parseFloat(e.target.value) || 0.20 })}
                  className="w-24 bg-gray-800 text-gray-100 text-sm font-mono rounded px-2 py-1 border border-gray-700 focus:border-indigo-500 focus:outline-none"
                />
                <span className="text-gray-500 text-xs">m</span>
              </PropRow>
              <PropRow label="Start">
                <span className="text-gray-400 font-mono text-xs">
                  ({selWall.start[0].toFixed(2)}, {selWall.start[1].toFixed(2)})
                </span>
              </PropRow>
              <PropRow label="End">
                <span className="text-gray-400 font-mono text-xs">
                  ({selWall.end[0].toFixed(2)}, {selWall.end[1].toFixed(2)})
                </span>
              </PropRow>
              <p className="text-xs text-gray-600">Drag the orange endpoint handles to reposition</p>
              <DeleteBtn onClick={() => { store.deleteWall(selWall.id); setSelection(null); }} />
            </div>
          )}

          {/* Door properties */}
          {selDoor && (
            <div className="p-4 space-y-4">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-sm bg-blue-500" />
                <span className="text-sm font-semibold text-gray-200">Door</span>
                <span className="text-xs text-gray-500 font-mono ml-auto">{selDoor.id}</span>
              </div>
              <PropRow label="Width">
                <input
                  type="number" step={0.05} min={0.5} max={5.0}
                  value={selDoor.width.toFixed(3)}
                  onChange={e => store.updateDoor(selDoor.id, { width: parseFloat(e.target.value) || 0.8 })}
                  className="w-24 bg-gray-800 text-gray-100 text-sm font-mono rounded px-2 py-1 border border-gray-700 focus:border-indigo-500 focus:outline-none"
                />
                <span className="text-gray-500 text-xs">m</span>
              </PropRow>
              <PropRow label="Center">
                <span className="text-gray-400 font-mono text-xs">
                  ({selDoor.center[0].toFixed(2)}, {selDoor.center[1].toFixed(2)})
                </span>
              </PropRow>
              <DeleteBtn onClick={() => { store.deleteDoor(selDoor.id); setSelection(null); }} />
            </div>
          )}

          {/* Window properties */}
          {selWindow && (
            <div className="p-4 space-y-4">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-sm bg-cyan-500" />
                <span className="text-sm font-semibold text-gray-200">Window</span>
                <span className="text-xs text-gray-500 font-mono ml-auto">{selWindow.id}</span>
              </div>
              <PropRow label="Width">
                <input
                  type="number" step={0.05} min={0.3} max={5.0}
                  value={selWindow.width.toFixed(3)}
                  onChange={e => store.updateWindow(selWindow.id, { width: parseFloat(e.target.value) || 1.2 })}
                  className="w-24 bg-gray-800 text-gray-100 text-sm font-mono rounded px-2 py-1 border border-gray-700 focus:border-indigo-500 focus:outline-none"
                />
                <span className="text-gray-500 text-xs">m</span>
              </PropRow>
              <PropRow label="Center">
                <span className="text-gray-400 font-mono text-xs">
                  ({selWindow.center[0].toFixed(2)}, {selWindow.center[1].toFixed(2)})
                </span>
              </PropRow>
              <DeleteBtn onClick={() => { store.deleteWindow(selWindow.id); setSelection(null); }} />
            </div>
          )}

          {/* Room properties */}
          {selRoom && (
            <div className="p-4 space-y-4">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-sm bg-green-500" />
                <span className="text-sm font-semibold text-gray-200">Room</span>
                <span className="text-xs text-gray-500 font-mono ml-auto">{selRoom.id}</span>
              </div>
              <PropRow label="Label">
                <input
                  type="text"
                  value={selRoom.label || selRoom.type || ''}
                  placeholder="e.g. Bedroom"
                  onChange={e => store.updateRoom(selRoom.id, { label: e.target.value })}
                  className="flex-1 bg-gray-800 text-gray-100 text-sm rounded px-2 py-1 border border-gray-700 focus:border-indigo-500 focus:outline-none"
                />
              </PropRow>
              {selRoom.area != null && (
                <PropRow label="Area">
                  <span className="text-gray-300 font-mono text-sm">{selRoom.area.toFixed(2)} m²</span>
                </PropRow>
              )}
              <DeleteBtn onClick={() => { store.deleteRoom(selRoom.id); setSelection(null); }} />
            </div>
          )}

          {/* Keyboard shortcut hint */}
          <div className="mt-auto p-4 border-t border-gray-800">
            <p className="text-xs text-gray-600 font-medium mb-2">Shortcuts</p>
            <div className="space-y-1 text-xs text-gray-600">
              <div className="flex justify-between"><span>Select</span><kbd className="font-mono bg-gray-800 px-1 rounded">V</kbd></div>
              <div className="flex justify-between"><span>Draw Wall</span><kbd className="font-mono bg-gray-800 px-1 rounded">W</kbd></div>
              <div className="flex justify-between"><span>Add Door</span><kbd className="font-mono bg-gray-800 px-1 rounded">D</kbd></div>
              <div className="flex justify-between"><span>Add Window</span><kbd className="font-mono bg-gray-800 px-1 rounded">N</kbd></div>
              <div className="flex justify-between"><span>Delete selected</span><kbd className="font-mono bg-gray-800 px-1 rounded">Del</kbd></div>
              <div className="flex justify-between"><span>Undo / Redo</span><kbd className="font-mono bg-gray-800 px-1 rounded">Ctrl+Z/Y</kbd></div>
              <div className="flex justify-between"><span>Cancel draw</span><kbd className="font-mono bg-gray-800 px-1 rounded">Esc</kbd></div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Tiny reusable sub-components
// ─────────────────────────────────────────────────────────────────────────────

const PropRow: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div className="flex items-center justify-between gap-2">
    <span className="text-xs text-gray-500 shrink-0">{label}</span>
    <div className="flex items-center gap-1.5">{children}</div>
  </div>
);

const DeleteBtn: React.FC<{ onClick: () => void }> = ({ onClick }) => (
  <button
    onClick={onClick}
    className="w-full mt-2 py-2 px-3 rounded-lg bg-red-950 hover:bg-red-900
      text-red-400 hover:text-red-300 text-xs font-semibold transition-colors
      border border-red-900 hover:border-red-700"
  >
    🗑 Delete Element
  </button>
);
