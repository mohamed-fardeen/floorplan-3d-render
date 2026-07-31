import React, { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree, type ThreeEvent } from '@react-three/fiber';
import { OrbitControls, Grid, useGLTF, Html } from '@react-three/drei';
import * as THREE from 'three';
import { useEditorStore } from '../../store/editorStore';
import type { SceneGraph } from '../../types/schema';
import {
  buildHighlightGeometry,
  createSelectionFromFaces,
  faceRefFromIntersection,
  mergeFaceRefs,
  meshObjectName,
  raycastMeshes,
} from '../../lib/selectionGeometry';
import { isVisibleAt, renderDepthMask } from '../../lib/depthPick';
import { applyViewportVisuals } from '../../lib/viewportVisuals';
import type { FaceReference } from '../../types/selection';

const HIGHLIGHT_COLOR = '#4f46e5';

function safeRenderDepthMask(
  scene: THREE.Scene,
  camera: THREE.Camera,
  renderer: THREE.WebGLRenderer,
  width: number,
  height: number,
) {
  try {
    return renderDepthMask(scene, camera, width, height, renderer);
  } catch (err) {
    console.warn('[depthPick] depth mask unavailable, falling back to geometric', err);
    return null;
  }
}

interface BuildingModelProps {
  url: string;
  version: number;
  onSceneReady: (scene: THREE.Group) => void;
}

const BuildingModel: React.FC<BuildingModelProps> = ({ url, version, onSceneReady }) => {
  const cacheBustedUrl = `${url}${url.includes('?') ? '&' : '?'}v=${version}`;
  const { scene } = useGLTF(cacheBustedUrl);
  const cloned = useMemo(() => scene.clone(true), [scene]);
  const viewport = useEditorStore((s) => s.viewport);
  const getActiveSelection = useEditorStore((s) => s.getActiveSelection);
  const materialOptions = useEditorStore((s) => s.materialOptions);

  useEffect(() => {
    cloned.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        child.castShadow = true;
        child.receiveShadow = true;
      }
    });
    const sel = getActiveSelection();
    const color = (sel?.metadata?.color as string) || materialOptions.walls.color;
    const pattern = (sel?.metadata?.pattern as string) || materialOptions.walls.pattern;
    applyViewportVisuals(cloned, {
      pattern,
      baseColor: color,
      showPatterns: viewport.showPatterns,
    });
    onSceneReady(cloned);
  }, [cloned, onSceneReady, viewport.showPatterns, viewport.showDoorsAndWindows, getActiveSelection, materialOptions]);

  return <primitive object={cloned} />;
};

interface SelectionLayerProps {
  root: THREE.Group | null;
  faceRefs: FaceReference[];
}

const SelectionHighlight: React.FC<SelectionLayerProps> = ({ root, faceRefs }) => {
  const geometry = useMemo(() => {
    if (!root || faceRefs.length === 0) return null;
    return buildHighlightGeometry(root, faceRefs);
  }, [root, faceRefs]);

  const t = useRef(0);
  useFrame((_, delta) => {
    t.current = (t.current + delta) % 1;
    if (materialRef.current) {
      materialRef.current.opacity = 0.35 + 0.2 * Math.sin(t.current * Math.PI * 2);
    }
  });

  const materialRef = useRef<THREE.MeshBasicMaterial>(null);

  if (!geometry) return null;

  return (
    <mesh geometry={geometry} renderOrder={10}>
      <meshBasicMaterial
        ref={materialRef}
        color={HIGHLIGHT_COLOR}
        transparent
        opacity={0.45}
        depthTest
        side={THREE.DoubleSide}
      />
    </mesh>
  );
};

interface PickHandlerProps {
  root: THREE.Group | null;
  disabled: boolean;
}

const PickHandler: React.FC<PickHandlerProps> = ({ root, disabled }) => {
  const { camera, gl } = useThree();
  const {
    selectionTool,
    brushRadius,
    addSelection,
    activeSelectionId,
    selections,
    getActiveSelection,
  } = useEditorStore();

  const painting = useRef(false);
  const [brushPreview, setBrushPreview] = useState<FaceReference[]>([]);
  const raycaster = useMemo(() => new THREE.Raycaster(), []);
  const pointer = useMemo(() => new THREE.Vector2(), []);

  const pickAt = useCallback(
    (clientX: number, clientY: number, append: boolean) => {
      if (!root || disabled) return;
      const rect = gl.domElement.getBoundingClientRect();
      pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);

      if (selectionTool === 'brush') {
        raycaster.params.Mesh = { threshold: brushRadius };
      }

      const hits = raycastMeshes(root, raycaster);
      if (hits.length === 0) return;

      const newRefs: FaceReference[] = [];
      for (const hit of hits.slice(0, selectionTool === 'brush' ? 8 : 1)) {
        const ref = faceRefFromIntersection(hit);
        if (ref) newRefs.push(ref);
      }
      if (newRefs.length === 0) return;

      if (selectionTool === 'brush' && append) {
        setBrushPreview((prev) => mergeFaceRefs(prev, newRefs));
        return;
      }

      const active = getActiveSelection();
      const faceRefs =
        selectionTool === 'brush' && append && active
          ? mergeFaceRefs(active.faceRefs, newRefs)
          : newRefs;

      const selection = createSelectionFromFaces(root, faceRefs, active?.metadata ?? {});
      addSelection(selection);
    },
    [
      root,
      disabled,
      gl.domElement,
      camera,
      raycaster,
      pointer,
      selectionTool,
      brushRadius,
      addSelection,
      getActiveSelection,
    ],
  );

  const finishBrush = useCallback(() => {
    if (!root || brushPreview.length === 0) {
      setBrushPreview([]);
      return;
    }
    const active = getActiveSelection();
    const faceRefs = active ? mergeFaceRefs(active.faceRefs, brushPreview) : brushPreview;
    const selection = createSelectionFromFaces(root, faceRefs, active?.metadata ?? {});
    addSelection(selection);
    setBrushPreview([]);
  }, [root, brushPreview, addSelection, getActiveSelection]);

  useEffect(() => {
    const el = gl.domElement;

    const onPointerDown = (e: PointerEvent) => {
      if (disabled || e.button !== 0) return;
      if (selectionTool === 'box') return;
      painting.current = true;
      setBrushPreview([]);
      pickAt(e.clientX, e.clientY, false);
    };

    const onPointerMove = (e: PointerEvent) => {
      if (!painting.current || selectionTool !== 'brush') return;
      pickAt(e.clientX, e.clientY, true);
    };

    const onPointerUp = () => {
      if (selectionTool === 'brush' && painting.current) finishBrush();
      painting.current = false;
    };

    el.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    return () => {
      el.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
    };
  }, [gl.domElement, disabled, selectionTool, pickAt, finishBrush]);

  const activeFaces = useMemo(() => {
    const active = selections.find((s) => s.id === activeSelectionId);
    if (active) return active.faceRefs;
    if (selectionTool === 'brush' && brushPreview.length) return brushPreview;
    return [];
  }, [selections, activeSelectionId, selectionTool, brushPreview]);

  return (
    <>
      <SelectionHighlight root={root} faceRefs={activeFaces} />
      {selectionTool === 'box' && root && (
        <BoxSelectOverlay root={root} disabled={disabled} />
      )}
      {selectionTool === 'lasso' && root && (
        <LassoOverlay root={root} disabled={disabled} />
      )}
    </>
  );
};

interface BoxSelectOverlayProps {
  root: THREE.Group;
  disabled: boolean;
}

const BoxSelectOverlay: React.FC<BoxSelectOverlayProps> = ({ root, disabled }) => {
  const { camera, gl, scene } = useThree();
  const { addSelection } = useEditorStore();
  const [drag, setDrag] = useState<{ x0: number; y0: number; x1: number; y1: number } | null>(null);

  const onPointerDown = (e: ThreeEvent<PointerEvent>) => {
    if (disabled || e.button !== 0) return;
    e.stopPropagation();
    setDrag({ x0: e.clientX, y0: e.clientY, x1: e.clientX, y1: e.clientY });
  };

  const onPointerMove = (e: ThreeEvent<PointerEvent>) => {
    if (!drag) return;
    setDrag({ ...drag, x1: e.clientX, y1: e.clientY });
  };

  const onPointerUp = () => {
    if (!drag) return;
    const rect = gl.domElement.getBoundingClientRect();
    const minX = Math.min(drag.x0, drag.x1) - rect.left;
    const maxX = Math.max(drag.x0, drag.x1) - rect.left;
    const minY = Math.min(drag.y0, drag.y1) - rect.top;
    const maxY = Math.max(drag.y0, drag.y1) - rect.top;

    const depthMask = safeRenderDepthMask(scene, camera, gl, rect.width, rect.height);

    const faceRefs: FaceReference[] = [];
    root.traverse((child) => {
      if (!(child as THREE.Mesh).isMesh) return;
      const mesh = child as THREE.Mesh;
      if (!mesh.geometry) return;
      const pos = mesh.geometry.getAttribute('position');
      const idx = mesh.geometry.getIndex();
      const faceCount = idx ? idx.count / 3 : pos.count / 3;

      for (let fi = 0; fi < faceCount; fi++) {
        const a = idx ? idx.getX(fi * 3) : fi * 3;
        const cx = (pos.getX(a) + pos.getX(idx ? idx.getX(fi * 3 + 1) : fi * 3 + 1) + pos.getX(idx ? idx.getX(fi * 3 + 2) : fi * 3 + 2)) / 3;
        const cy = (pos.getY(a) + pos.getY(idx ? idx.getY(fi * 3 + 1) : fi * 3 + 1) + pos.getY(idx ? idx.getY(fi * 3 + 2) : fi * 3 + 2)) / 3;
        const cz = (pos.getZ(a) + pos.getZ(idx ? idx.getZ(fi * 3 + 1) : fi * 3 + 1) + pos.getZ(idx ? idx.getZ(fi * 3 + 2) : fi * 3 + 2)) / 3;
        const world = new THREE.Vector3(cx, cy, cz).applyMatrix4(mesh.matrixWorld);
        const projected = world.clone().project(camera);
        const sx = ((projected.x + 1) / 2) * rect.width;
        const sy = ((-projected.y + 1) / 2) * rect.height;
        if (sx >= minX && sx <= maxX && sy >= minY && sy <= maxY) {
          if (depthMask && !isVisibleAt(world, camera, depthMask)) continue;
          faceRefs.push({
            meshRef: { objectName: meshObjectName(mesh), meshUuid: mesh.uuid },
            faceIndex: fi,
          });
        }
      }
    });

    if (faceRefs.length > 0) {
      addSelection(createSelectionFromFaces(root, faceRefs));
    }
    setDrag(null);
  };

  if (!drag) {
    return (
      <mesh visible={false} onPointerDown={onPointerDown}>
        <planeGeometry args={[1000, 1000]} />
        <meshBasicMaterial transparent opacity={0} />
      </mesh>
    );
  }

  const left = Math.min(drag.x0, drag.x1);
  const top = Math.min(drag.y0, drag.y1);
  const width = Math.abs(drag.x1 - drag.x0);
  const height = Math.abs(drag.y1 - drag.y0);

  return (
    <Html fullscreen style={{ pointerEvents: 'none' }}>
      <div
        style={{
          position: 'absolute',
          left,
          top,
          width,
          height,
          border: '2px solid #4f46e5',
          background: 'rgba(79,70,229,0.12)',
          pointerEvents: 'none',
        }}
      />
      <div
        style={{ position: 'fixed', inset: 0, pointerEvents: 'auto', cursor: 'crosshair' }}
        onPointerMove={(e) => onPointerMove(e as unknown as ThreeEvent<PointerEvent>)}
        onPointerUp={onPointerUp}
      />
    </Html>
  );
};

interface LassoOverlayProps {
  root: THREE.Group;
  disabled: boolean;
}

function pointInPolygon(point: [number, number], polygon: [number, number][]): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];
    const intersect =
      yi > point[1] !== yj > point[1] &&
      point[0] < ((xj - xi) * (point[1] - yi)) / (yj - yi || 1e-9) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

const LassoOverlay: React.FC<LassoOverlayProps> = ({ root, disabled }) => {
  const { camera, gl, scene } = useThree();
  const { addSelection } = useEditorStore();
  const [path, setPath] = useState<[number, number][]>([]);
  const drawingRef = useRef(false);

  useEffect(() => {
    const el = gl.domElement;
    const rect = () => el.getBoundingClientRect();

    const onDown = (e: PointerEvent) => {
      if (disabled || e.button !== 0) return;
      drawingRef.current = true;
      const r = rect();
      setPath([[e.clientX - r.left, e.clientY - r.top]]);
    };

    const onMove = (e: PointerEvent) => {
      if (!drawingRef.current) return;
      const r = rect();
      setPath((prev) => {
        const last = prev[prev.length - 1];
        if (!last) return [[e.clientX - r.left, e.clientY - r.top]];
        const dx = e.clientX - r.left - last[0];
        const dy = e.clientY - r.top - last[1];
        if (dx * dx + dy * dy < 9) return prev;
        return [...prev, [e.clientX - r.left, e.clientY - r.top]];
      });
    };

    const onUp = () => {
      if (!drawingRef.current) return;
      drawingRef.current = false;
      const polygon = pathRef.current;
      setPath([]);
      if (polygon.length < 3) return;
      const r = rect();
      const minX = 0;
      const maxX = r.width;
      const minY = 0;
      const maxY = r.height;
      const depthMask = safeRenderDepthMask(scene, camera, gl, r.width, r.height);

      const faceRefs: FaceReference[] = [];
      root.traverse((child) => {
        if (!(child as THREE.Mesh).isMesh) return;
        const mesh = child as THREE.Mesh;
        if (!mesh.geometry) return;
        const pos = mesh.geometry.getAttribute('position');
        const idx = mesh.geometry.getIndex();
        if (!pos) return;
        const faceCount = idx ? idx.count / 3 : pos.count / 3;
        for (let fi = 0; fi < faceCount; fi++) {
          const a = idx ? idx.getX(fi * 3) : fi * 3;
          const b = idx ? idx.getX(fi * 3 + 1) : fi * 3 + 1;
          const c = idx ? idx.getX(fi * 3 + 2) : fi * 3 + 2;
          const cx = (pos.getX(a) + pos.getX(b) + pos.getX(c)) / 3;
          const cy = (pos.getY(a) + pos.getY(b) + pos.getY(c)) / 3;
          const cz = (pos.getZ(a) + pos.getZ(b) + pos.getZ(c)) / 3;
          const world = new THREE.Vector3(cx, cy, cz).applyMatrix4(mesh.matrixWorld);
          const projected = world.clone().project(camera);
          const sx = ((projected.x + 1) / 2) * r.width;
          const sy = ((-projected.y + 1) / 2) * r.height;
          if (sx < minX || sx > maxX || sy < minY || sy > maxY) continue;
          if (depthMask && !isVisibleAt(world, camera, depthMask)) continue;
          if (pointInPolygon([sx, sy], polygon)) {
            faceRefs.push({
              meshRef: { objectName: meshObjectName(mesh), meshUuid: mesh.uuid },
              faceIndex: fi,
            });
          }
        }
      });

      if (faceRefs.length > 0) {
        addSelection(createSelectionFromFaces(root, faceRefs));
      }
    };

    el.addEventListener('pointerdown', onDown);
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      el.removeEventListener('pointerdown', onDown);
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  }, [root, gl.domElement, gl, scene, camera, addSelection, disabled]);

  const pathRef = useRef(path);
  useEffect(() => {
    pathRef.current = path;
  }, [path]);

  if (path.length === 0) return null;

  const d = path
    .map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`)
    .join(' ');

  return (
    <Html fullscreen style={{ pointerEvents: 'none' }}>
      <svg className="absolute inset-0 h-full w-full" style={{ pointerEvents: 'none' }}>
        <path d={d} fill="rgba(79,70,229,0.18)" stroke="#4f46e5" strokeWidth={1.5} />
      </svg>
    </Html>
  );
};

interface SceneContentProps {
  glbUrl: string;
  version: number;
  onRoot?: (g: THREE.Group) => void;
}

const SceneContent: React.FC<SceneContentProps> = ({ glbUrl, version, onRoot }) => {
  const [root, setRoot] = useState<THREE.Group | null>(null);
  const { viewport } = useEditorStore();

  const handleRoot = useCallback(
    (g: THREE.Group) => {
      setRoot(g);
      onRoot?.(g);
    },
    [onRoot],
  );

  return (
    <>
      <ambientLight intensity={0.55} />
      <directionalLight position={[8, 14, 6]} intensity={1.1} castShadow shadow-mapSize={[2048, 2048]} />
      <directionalLight position={[-6, 8, -4]} intensity={0.35} />

      {viewport.showGrid && (
        <Grid
          infiniteGrid
          cellSize={0.5}
          sectionSize={2}
          fadeDistance={40}
          fadeStrength={1}
          cellColor="#6b7280"
          sectionColor="#374151"
        />
      )}

      {viewport.showAxes && (import.meta.env.DEV || true) && <axesHelper args={[2]} />}

      <Suspense fallback={null}>
        <BuildingModel url={glbUrl} version={version} onSceneReady={handleRoot} />
      </Suspense>

      <PickHandler root={root} disabled={false} />

      <OrbitControls
        makeDefault
        enablePan
        enableZoom
        enableRotate
        enableDamping
        dampingFactor={0.08}
        rotateSpeed={0.6}
        minDistance={2}
        maxDistance={60}
        mouseButtons={
          viewport.interactionMode === 'orbit'
            ? {
                LEFT: THREE.MOUSE.ROTATE,
                MIDDLE: THREE.MOUSE.DOLLY,
                RIGHT: THREE.MOUSE.PAN,
              }
            : {
                LEFT: undefined as unknown as THREE.MOUSE,
                MIDDLE: THREE.MOUSE.PAN,
                RIGHT: THREE.MOUSE.ROTATE,
              }
        }
      />
    </>
  );
};

interface ConstructionViewportProps {
  className?: string;
  glbUrl?: string | null;
  sceneGraph?: SceneGraph | null;
  onRoot?: (g: THREE.Group | null) => void;
  registerScreenshot?: (fn: () => string | null) => void;
}

export const ConstructionViewport: React.FC<ConstructionViewportProps> = ({
  className = '',
  glbUrl: glbUrlProp,
  sceneGraph: sceneGraphProp,
  onRoot,
  registerScreenshot,
}) => {
  const store = useEditorStore();
  const glbUrl = glbUrlProp ?? store.glbUrl;
  const sceneGraph = sceneGraphProp ?? store.sceneGraph;
  const glbVersion = store.glbVersion;
  const syncStatus = store.syncStatus;
  const syncStage = store.syncStage;
  const syncMessage = store.syncMessage;
  const lastVersionRef = React.useRef(glbVersion);

  React.useEffect(() => {
    if (lastVersionRef.current !== glbVersion) {
      lastVersionRef.current = glbVersion;
      store.invalidateMeshUuids();
    }
  }, [glbVersion, store]);

  const resetCamera = () => {
    const canvas = document.querySelector('[data-construction-viewport] canvas');
    if (!canvas) return;
    // OrbitControls reset via dispatch — fallback: reload camera position
    window.dispatchEvent(new CustomEvent('construction-viewport-reset'));
  };

  if (!sceneGraph) {
    return (
      <div className={`flex items-center justify-center bg-slate-900 text-slate-400 ${className}`}>
        Load a scene graph to begin 3D editing.
      </div>
    );
  }

  if (!glbUrl) {
    return (
      <div className={`flex flex-col items-center justify-center gap-3 bg-slate-900 text-slate-300 ${className}`}>
        <p>No GLB loaded yet.</p>
        <p className="text-sm text-slate-500">Export from the pipeline or use Sync in the sidebar.</p>
      </div>
    );
  }

  return (
    <div className={`relative flex flex-col bg-slate-900 ${className}`} data-construction-viewport>
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
        <span className="rounded bg-black/50 px-2 py-1 text-xs font-medium text-white">
          3D Construction Editor
        </span>
        {syncStatus === 'syncing' && (
          <span className="rounded bg-amber-500/90 px-2 py-1 text-xs text-white">
            {syncStage ? `${syncStage}: ${syncMessage ?? ''}` : 'Syncing…'}
          </span>
        )}
        {syncStatus === 'synced' && (
          <span className="rounded bg-emerald-600/90 px-2 py-1 text-xs text-white">Synced</span>
        )}
        {syncStatus === 'error' && (
          <span className="rounded bg-red-600/90 px-2 py-1 text-xs text-white">Sync failed</span>
        )}
        <ViewportHint />
      </div>

      <div className="absolute top-3 right-3 z-10 flex flex-col items-end gap-2">
        <ViewportMenu />
        <button
          type="button"
          onClick={resetCamera}
          className="rounded bg-white/10 px-3 py-1.5 text-xs font-medium text-white backdrop-blur hover:bg-white/20"
        >
          Reset camera
        </button>
      </div>

      <Canvas
        shadows
        camera={{ position: [6, 5, 8], fov: 45, near: 0.1, far: 200 }}
        className="flex-1"
        onCreated={({ gl, camera }) => {
          camera.lookAt(0, 1.5, 0);
          if (registerScreenshot) {
            registerScreenshot(() => {
              try {
                return gl.domElement.toDataURL('image/png');
              } catch {
                return null;
              }
            });
          }
        }}
      >
        <SceneContent glbUrl={glbUrl} version={glbVersion} onRoot={onRoot} />
        <CameraResetListener />
      </Canvas>
    </div>
  );
};

const CameraResetListener: React.FC = () => {
  const { camera } = useThree();
  useEffect(() => {
    const handler = () => {
      camera.position.set(6, 5, 8);
      camera.lookAt(0, 1.5, 0);
    };
    window.addEventListener('construction-viewport-reset', handler);
    return () => window.removeEventListener('construction-viewport-reset', handler);
  }, [camera]);
  return null;
};

const ViewportHint: React.FC = () => {
  const { viewport } = useEditorStore();
  const mcpAvailable = useMcpConnectionSafe();
  const interactionHint =
    viewport.interactionMode === 'orbit'
      ? '🖱 Left-drag: rotate · Right-drag: pan · Scroll: zoom'
      : '🖱 Left-click: pick · Right-drag: rotate · Scroll: zoom';
  return (
    <div className="flex flex-wrap items-center gap-1">
      <span className="rounded bg-black/40 px-2 py-1 text-[10px] text-white/80">
        {interactionHint}
      </span>
      <span
        className={`rounded px-2 py-1 text-[10px] ${
          mcpAvailable
            ? 'bg-emerald-600/80 text-white'
            : 'bg-amber-500/80 text-white'
        }`}
        title={mcpAvailable ? 'Live MCP is connected' : 'Waiting for Blender MCP socket'}
      >
        {mcpAvailable ? '● MCP live' : '○ MCP auto-connecting…'}
      </span>
    </div>
  );
};

function useMcpConnectionSafe() {
  // Inline mini-hook to avoid circular imports.
  // The App-level hook is the authoritative one; this just reads
  // /api/mcp/status directly for the HUD.
  const [available, setAvailable] = React.useState(false);
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/mcp/status');
        const data = await res.json();
        if (!cancelled) setAvailable(Boolean(data?.available));
      } catch {
        /* ignore */
      }
    };
    tick();
    const handle = window.setInterval(tick, 1500);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, []);
  return available;
}

const ViewportMenu: React.FC = () => {
  const { viewport, setViewportOptions } = useEditorStore();
  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-1 rounded bg-white/10 p-1 backdrop-blur">
        <button
          type="button"
          onClick={() =>
            setViewportOptions({
              interactionMode: viewport.interactionMode === 'select' ? 'orbit' : 'select',
            })
          }
          className={`rounded px-2 py-1 text-xs ${
            viewport.interactionMode === 'orbit' ? 'bg-amber-500/90 text-white' : 'bg-white/30 text-white'
          }`}
          title="Toggle between Select and Orbit modes"
        >
          {viewport.interactionMode === 'orbit' ? 'Orbit (left-drag)' : 'Select'}
        </button>
      </div>
      <div className="flex flex-wrap gap-1 rounded bg-white/10 p-1 backdrop-blur">
        <button
          type="button"
          onClick={() => setViewportOptions({ showGrid: !viewport.showGrid })}
          className={`rounded px-2 py-1 text-xs ${
            viewport.showGrid ? 'bg-white/30 text-white' : 'text-white/70 hover:bg-white/20'
          }`}
          title="Toggle grid"
        >
          Grid
        </button>
        <button
          type="button"
          onClick={() => setViewportOptions({ showAxes: !viewport.showAxes })}
          className={`rounded px-2 py-1 text-xs ${
            viewport.showAxes ? 'bg-white/30 text-white' : 'text-white/70 hover:bg-white/20'
          }`}
          title="Toggle axes"
        >
          Axes
        </button>
        <button
          type="button"
          onClick={() => setViewportOptions({ showPatterns: !viewport.showPatterns })}
          className={`rounded px-2 py-1 text-xs ${
            viewport.showPatterns ? 'bg-white/30 text-white' : 'text-white/70 hover:bg-white/20'
          }`}
          title="Toggle pattern preview on walls"
        >
          Pattern
        </button>
        <button
          type="button"
          onClick={() =>
            setViewportOptions({ showDoorsAndWindows: !viewport.showDoorsAndWindows })
          }
          className={`rounded px-2 py-1 text-xs ${
            viewport.showDoorsAndWindows
              ? 'bg-white/30 text-white'
              : 'text-white/70 hover:bg-white/20'
          }`}
          title="Show doors & windows (solid)"
        >
          Cutouts
        </button>
      </div>
    </div>
  );
};
