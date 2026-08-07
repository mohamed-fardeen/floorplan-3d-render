import React, { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree, type ThreeEvent } from '@react-three/fiber';
import { OrbitControls, Grid, useGLTF, Html } from '@react-three/drei';
import * as THREE from 'three';
import { useEditorStore } from '../../store/editorStore';
import type { SceneGraph } from '../../types/schema';
import {
  allFacesOfMesh,
  buildHighlightGeometry,
  createSelectionFromFaces,
  faceRefFromIntersection,
  findWallMesh,
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

  // eslint-disable-next-line no-console
  useEffect(() => {
    if (!cloned) return;
    let wallCount = 0;
    let postCount = 0;
    let otherCount = 0;
    cloned.traverse((c) => {
      const m = c as THREE.Mesh;
      if (!m.isMesh) return;
      const n = m.name || '';
      if (n.startsWith('Wall_')) wallCount++;
      else if (n.startsWith('WallPost_')) postCount++;
      else otherCount++;
    });
    // eslint-disable-next-line no-console
    console.log('[BuildingModel] GLB loaded', {
      cacheBustedUrl,
      wallCount,
      postCount,
      otherCount,
    });
  }, [cloned]);
  const viewport = useEditorStore((s) => s.viewport);
  const selections = useEditorStore((s) => s.selections);
  const activeSelectionId = useEditorStore((s) => s.activeSelectionId);
  const materialOptions = useEditorStore((s) => s.materialOptions);
  const isolatedWallId = useEditorStore((s) => s.isolatedWallId);
  const wallColorOverrides = useEditorStore((s) => s.wallColorOverrides);

  const activeSel = useMemo(() => {
    return selections.find((s) => s.id === activeSelectionId);
  }, [selections, activeSelectionId]);

  const wallOverridesMap = useMemo(
    () => new Map(Object.entries(wallColorOverrides)),
    [wallColorOverrides],
  );

  useEffect(() => {
    cloned.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        child.castShadow = true;
        child.receiveShadow = true;
      }
    });

    // eslint-disable-next-line no-console
    console.log('[BuildingModel] useEffect running', {
      isolatedWallId,
      activeSelectionId: activeSel?.id,
      wallOverridesCount: Object.keys(wallColorOverrides).length,
      materialPattern: materialOptions.walls.pattern,
    });

    // Collect the mesh names covered by the active selection so the visual
    // pass can apply selection-specific color/pattern to exactly those walls
    // (and keep the project defaults on everything else).
    const selectedObjectNames = new Set<string>(
      (activeSel?.meshRefs ?? []).map((m) => m.objectName).filter(Boolean),
    );

    applyViewportVisuals(
      cloned,
      {
        pattern: materialOptions.walls.pattern,
        baseColor: materialOptions.walls.color,
        showPatterns: viewport.showPatterns,
      },
      activeSel && selectedObjectNames.size > 0
        ? {
            selectedObjectNames,
            selectedColor: activeSel.metadata?.color as string | undefined,
            selectedPattern: activeSel.metadata?.pattern as string | undefined,
          }
        : undefined,
      isolatedWallId
        ? { isolatedWallName: `Wall_${isolatedWallId}`, dimOpacity: 0.05 }
        : undefined,
      wallOverridesMap,
    );
    onSceneReady(cloned);
  }, [
    cloned,
    onSceneReady,
    viewport.showPatterns,
    viewport.showDoorsAndWindows,
    activeSel,
    materialOptions,
    isolatedWallId,
    wallOverridesMap,
  ]);

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
    isolatedWallId,
    enterWallIsolation,
  } = useEditorStore();

  const painting = useRef(false);
  const [brushPreview, setBrushPreview] = useState<FaceReference[]>([]);
  const raycaster = useMemo(() => new THREE.Raycaster(), []);
  const pointer = useMemo(() => new THREE.Vector2(), []);

  /** Restrict the scene to the isolated wall mesh, or leave it unchanged. */
  const scopeRoot = useCallback(
    (rawHits: THREE.Intersection[]): THREE.Intersection[] => {
      if (!isolatedWallId) return rawHits;
      const targetName = `Wall_${isolatedWallId}`;
      return rawHits.filter((h) => (h.object as THREE.Mesh).name === targetName);
    },
    [isolatedWallId],
  );

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

      const hits = scopeRoot(raycastMeshes(root, raycaster));
      // eslint-disable-next-line no-console
      console.log('[PickHandler] hits:', hits.map((h) => ({
        name: (h.object as THREE.Mesh).name,
        distance: h.distance?.toFixed(3),
        visible: (h.object as THREE.Mesh).visible,
      })));
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

      // Outside isolation, a wall click enters isolation with the entire
      // wall pre-selected so the IsolationPanel can immediately take over.
      // Corner posts share the `Wall_` prefix but are skipped here so a
      // click near the corner of two walls lands on the wall itself.
      if (!isolatedWallId) {
        const hitObjName = hits[0]?.object?.name || '';
        console.log('[PickHandler] hit object:', hitObjName, 'isolatedWallId:', isolatedWallId);
        if (
          hitObjName.startsWith('Wall_') &&
          !hitObjName.startsWith('WallPost_')
        ) {
          const wallId = hitObjName.replace('Wall_', '');
          const wallMesh = findWallMesh(root, wallId);
          console.log('[PickHandler] entering isolation for wall', wallId, 'mesh found:', !!wallMesh);
          if (wallMesh) {
            const allFaces = allFacesOfMesh(wallMesh);
            const fullWallSel = createSelectionFromFaces(
              root,
              allFaces,
              {},
              wallId,
            );
            addSelection(fullWallSel);
            enterWallIsolation(wallId, fullWallSel.id);
            return;
          }
        }
      }
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
      isolatedWallId,
      enterWallIsolation,
      scopeRoot,
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
      {/* Skip the blue selection highlight while isolation is active —
          the wall is already the only thing on screen and the indigo
          overlay obscures the actual material colour. */}
      {!isolatedWallId && (
        <SelectionHighlight root={root} faceRefs={activeFaces} />
      )}
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
  const isolatedWallId = useEditorStore((s) => s.isolatedWallId);
  const [drag, setDrag] = useState<{ x0: number; y0: number; x1: number; y1: number } | null>(null);

  const onPointerDown = (e: ThreeEvent<PointerEvent>) => {
    if (disabled || e.button !== 0) return;
    e.stopPropagation();
    const rect = gl.domElement.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setDrag({ x0: x, y0: y, x1: x, y1: y });
  };

  const onPointerMove = (e: MouseEvent) => {
    if (!drag) return;
    const rect = gl.domElement.getBoundingClientRect();
    setDrag({ ...drag, x1: e.clientX - rect.left, y1: e.clientY - rect.top });
  };

  const onPointerUp = () => {
    if (!drag) return;
    const rect = gl.domElement.getBoundingClientRect();
    const minX = Math.min(drag.x0, drag.x1);
    const maxX = Math.max(drag.x0, drag.x1);
    const minY = Math.min(drag.y0, drag.y1);
    const maxY = Math.max(drag.y0, drag.y1);

    const depthMask = safeRenderDepthMask(scene, camera, gl, rect.width, rect.height);

    const faceRefs: FaceReference[] = [];
    root.traverse((child) => {
      if (!(child as THREE.Mesh).isMesh) return;
      const mesh = child as THREE.Mesh;
      if (!mesh.geometry) return;
      // While isolation is active, only the isolated wall is selectable.
      if (isolatedWallId && mesh.name !== `Wall_${isolatedWallId}`) return;
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

  useEffect(() => {
    if (!drag) return;
    const moveHandler = (e: MouseEvent) => onPointerMove(e);
    const upHandler = () => onPointerUp();
    window.addEventListener('mousemove', moveHandler);
    window.addEventListener('mouseup', upHandler);
    return () => {
      window.removeEventListener('mousemove', moveHandler);
      window.removeEventListener('mouseup', upHandler);
    };
  }, [drag, gl, camera, scene, root, addSelection, isolatedWallId]);

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
  const isolatedWallId = useEditorStore((s) => s.isolatedWallId);
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
        if (isolatedWallId && mesh.name !== `Wall_${isolatedWallId}`) return;
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
  }, [root, gl.domElement, gl, scene, camera, addSelection, disabled, isolatedWallId]);

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

      <IsolationCamera root={root} />

      <OrbitControls
        makeDefault
        enablePan
        enableZoom
        enableRotate
        enableDamping
        dampingFactor={0.08}
        rotateSpeed={0.6}
        minDistance={0.5}
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
  const isolatedWallId = useEditorStore((s) => s.isolatedWallId);
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
        <p className="text-sm text-slate-500">Export from the pipeline to load a scene.</p>
      </div>
    );
  }

  return (
    <div className={`relative flex flex-col bg-slate-900 ${className}`} data-construction-viewport>
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
        {isolatedWallId && (
          <button
            type="button"
            onClick={store.exitWallIsolation}
            className="flex items-center gap-1.5 rounded-md bg-indigo-600 px-2.5 py-1.5 text-xs font-semibold text-white shadow-lg shadow-indigo-900/40 transition-colors hover:bg-indigo-500"
            title="Back — exit wall isolation and return to orbit view"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M19 12H5" />
              <path d="M12 19l-7-7 7-7" />
            </svg>
            Back to scene
          </button>
        )}
        <span className="rounded bg-black/50 px-2 py-1 text-xs font-medium text-white">
          3D Construction Editor
        </span>
        {isolatedWallId && (
          <span className="rounded bg-indigo-500/30 px-2 py-1 text-xs font-medium text-indigo-100 ring-1 ring-indigo-400/50">
            Isolating wall <span className="font-mono">{isolatedWallId}</span> — esc or Back to exit
          </span>
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
      <IsolationOverlay sceneGraph={sceneGraph} />
    </div>
  );
};

/**
 * Outer wrapper that renders the IsolationPanel when isolation mode is
 * active. Kept as a separate component so the panel can sit above the
 * canvas (z-50) without being part of the R3F tree.
 */
const IsolationOverlay: React.FC<{ sceneGraph: SceneGraph }> = ({ sceneGraph }) => {
  const isolatedWallId = useEditorStore((s) => s.isolatedWallId);
  const exitWallIsolation = useEditorStore((s) => s.exitWallIsolation);

  if (!isolatedWallId) return null;
  const wall = sceneGraph.walls.find((w) => w.id === isolatedWallId);
  if (!wall) return null;

  return <IsolationPanel wall={wall} onExit={exitWallIsolation} />;
};

/**
 * Camera animation that flies the orbit camera to the isolated wall when
 * isolation is entered and back to the home position when it is exited.
 * Smoothed with exponential lerp so it works regardless of frame rate.
 */
const ISOLATION_HOME_POS = new THREE.Vector3(6, 5, 8);
const ISOLATION_HOME_TARGET = new THREE.Vector3(0, 1.5, 0);

const IsolationCamera: React.FC<{ root: THREE.Group | null }> = ({ root }) => {
  const { camera, controls } = useThree() as ReturnType<typeof useThree> & {
    controls: { target: THREE.Vector3; update: () => void } | null;
  };
  const isolatedWallId = useEditorStore((s) => s.isolatedWallId);
  const exitWallIsolation = useEditorStore((s) => s.exitWallIsolation);

  const fromRef = useRef({
    pos: camera.position.clone(),
    target: controls?.target?.clone() ?? ISOLATION_HOME_TARGET.clone(),
  });
  const toRef = useRef({
    pos: ISOLATION_HOME_POS.clone(),
    target: ISOLATION_HOME_TARGET.clone(),
  });
  const activeRef = useRef(false);
  const lastWallId = useRef<string | null>(null);

  useEffect(() => {
    if (!root) return;
    if (isolatedWallId === lastWallId.current) return;
    lastWallId.current = isolatedWallId;

    fromRef.current = {
      pos: camera.position.clone(),
      target: controls?.target?.clone() ?? ISOLATION_HOME_TARGET.clone(),
    };

    if (isolatedWallId) {
      // eslint-disable-next-line no-console
      console.log('[CameraFly] isolated wall', isolatedWallId, 'position before', camera.position.toArray());
      const wallMesh = findWallMesh(root, isolatedWallId);
      if (wallMesh) {
        wallMesh.geometry.computeBoundingBox();
        const box = wallMesh.geometry.boundingBox;
        const center = new THREE.Vector3();
        const size = new THREE.Vector3();
        if (box) {
          // Dump the LOCAL box first so we can see the raw geometry extents.
          const localCenter = box.getCenter(new THREE.Vector3());
          const localSize = box.getSize(new THREE.Vector3());
          // eslint-disable-next-line no-console
          console.log('[CameraFly] wall local bbox', {
            min: box.min.toArray(),
            max: box.max.toArray(),
            localCenter: localCenter.toArray(),
            localSize: localSize.toArray(),
            matrixWorld_elements: [
              wallMesh.matrixWorld.elements[0],
              wallMesh.matrixWorld.elements[5],
              wallMesh.matrixWorld.elements[10],
              wallMesh.matrixWorld.elements[12],
              wallMesh.matrixWorld.elements[13],
              wallMesh.matrixWorld.elements[14],
            ],
            meshVisible: wallMesh.visible,
            meshScale: wallMesh.scale.toArray(),
          });
          // Center: convert LOCAL box center to WORLD space (apply matrix).
          box.getCenter(center).applyMatrix4(wallMesh.matrixWorld);
          // Size: keep it LOCAL. `applyMatrix4` would add the wall's
          // translation, inflating the longest dimension to e.g. ~9m for a
          // 4m wall and pushing the camera to its 8m cap — at the wrong
          // angle so the wall falls outside the view, producing a white
          // screen. Local size is rotation-invariant for our distance calc.
          box.getSize(size);
        } else {
          wallMesh.getWorldPosition(center);
        }

        const longest = Math.max(
          Math.abs(size.x),
          Math.abs(size.y),
          Math.abs(size.z),
          0.5,
        );
        const camDistance = Math.min(Math.max(longest * 1.6, 1.5), 6);

        // Camera sits slightly off-axis from the wall's normal so the user
        // sees the front face, not an edge-on view.
        const normal = new THREE.Vector3(0, 0, 1)
          .applyQuaternion(wallMesh.getWorldQuaternion(new THREE.Quaternion()));
        const offset = normal.clone().multiplyScalar(camDistance);
        offset.y += camDistance * 0.4;

        toRef.current = {
          pos: center.clone().add(offset),
          target: center.clone(),
        };

        if (!Number.isFinite(toRef.current.pos.x) || !Number.isFinite(toRef.current.pos.y) || !Number.isFinite(toRef.current.pos.z)) {
          toRef.current = {
            pos: ISOLATION_HOME_POS.clone(),
            target: ISOLATION_HOME_TARGET.clone(),
          };
        }
        // eslint-disable-next-line no-console
        console.log(
          '[CameraFly] wall mesh found',
          isolatedWallId,
          'center', center.toArray(),
          'normal', normal.toArray(),
          'camDistance', camDistance,
          'wall size', size.toArray(),
          'final cam pos', toRef.current.pos.toArray(),
        );
      } else {
        // eslint-disable-next-line no-console
        console.warn('[CameraFly] wall mesh NOT found for', isolatedWallId);
        // Wall mesh wasn't found — keep the camera where it is rather than
        // snapping it to the home position. Otherwise the user sees the
        // building fly away.
        toRef.current = {
          pos: camera.position.clone(),
          target: controls?.target?.clone() ?? ISOLATION_HOME_TARGET.clone(),
        };
      }
    } else {
      toRef.current = {
        pos: ISOLATION_HOME_POS.clone(),
        target: ISOLATION_HOME_TARGET.clone(),
      };
    }
    activeRef.current = true;
  }, [isolatedWallId, root, camera, controls]);

  useFrame((_, delta) => {
    if (!activeRef.current) return;
    const t = 1 - Math.exp(-delta * 6); // smoothing factor per frame
    camera.position.lerp(toRef.current.pos, t);
    if (controls?.target) {
      controls.target.lerp(toRef.current.target, t);
      controls.update();
    } else {
      camera.lookAt(toRef.current.target);
    }
    if (camera.position.distanceTo(toRef.current.pos) < 0.01) {
      activeRef.current = false;
    }
  });

  // Also reset to home on the reset-camera event.
  useEffect(() => {
    const handler = () => {
      if (isolatedWallId) exitWallIsolation();
      toRef.current = {
        pos: ISOLATION_HOME_POS.clone(),
        target: ISOLATION_HOME_TARGET.clone(),
      };
      activeRef.current = true;
    };
    window.addEventListener('construction-viewport-reset', handler);
    return () => window.removeEventListener('construction-viewport-reset', handler);
  }, [isolatedWallId, exitWallIsolation]);

  return null;
};

interface WallLike {
  id: string;
  start: [number, number];
  end: [number, number];
  thickness: number;
}

/**
 * IsolationPanel — the entire control surface for working with a single wall.
 *
 * Sections (top → bottom):
 *  • Header with back-arrow button (← Back) to leave isolation
 *  • Geometry preview (SVG) + length / thickness / angle handles
 *  • Numeric fields for length, thickness, angle
 *  • Colour picker + pattern (Smooth / 3D Printed)
 *  • Sub-selection tools (Click / Brush / Box / Lasso) for editing regions of the wall
 *  • "Apply & Exit" button
 *
 * Changes are saved directly to the per-wall override map (`wallColorOverrides`)
 * in the store. The previous Blender round-trip is gone — it was hanging
 * the web-only flow because Blender isn't running in this environment.
 * Per-wall overrides make the change survive exiting isolation and picking
 * a different wall.
 */
const IsolationPanel: React.FC<{ wall: WallLike; onExit: () => void }> = ({ wall, onExit }) => {
  const store = useEditorStore();
  const {
    selectionTool,
    setSelectionTool,
    brushRadius,
    setBrushRadius,
    selections,
    activeSelectionId,
    setActiveSelection,
    removeSelection,
    clearSelections,
    materialOptions,
    setWallColorOverride,
  } = store;
  const sceneGraph = useEditorStore((s) => s.sceneGraph);
  const wallOverrides = useEditorStore((s) => s.wallColorOverrides);
  const wallMeshName = `Wall_${wall.id}`;
  const existingOverride = wallOverrides[wallMeshName];

  const [length, setLength] = React.useState(() => wallLen(wall?.start, wall?.end));
  const [thickness, setThickness] = React.useState(wall?.thickness ?? 0.2);
  const [angleDeg, setAngleDeg] = React.useState(() => wallAngleDeg(wall));
  const [color, setColor] = React.useState<string>(
    () => existingOverride?.color ?? materialOptions.walls.color,
  );
  const [pattern, setPattern] = React.useState<string>(
    () => existingOverride?.pattern ?? materialOptions.walls.pattern ?? 'smooth',
  );

  const svgRef = React.useRef<SVGSVGElement>(null);
  const [dragging, setDragging] = React.useState<'left' | 'right' | 'rot' | null>(null);

  const MW = 560;
  const MH = 300;
  const CX = MW / 2;
  const CY = MH / 2 - 10;

  const displayScale = React.useMemo(
    () => Math.min(Math.max((MW * 0.65) / Math.max(length, 0.3), 50), 200),
    [length],
  );
  const halfLenPx = (length / 2) * displayScale;
  const thickPx = Math.max(thickness * displayScale, 6);
  const ROT_R = Math.min(halfLenPx + 50, CX - 20);

  const getModalPt = React.useCallback((e: MouseEvent | React.MouseEvent) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const r = svg.getBoundingClientRect();
    return {
      x: (e.clientX - r.left) * (MW / r.width),
      y: (e.clientY - r.top) * (MH / r.height),
    };
  }, []);

  React.useEffect(() => {
    if (!dragging) return;
    const onMove = (e: MouseEvent) => {
      const pt = getModalPt(e);
      if (dragging === 'left') {
        const arm = Math.max(CX - pt.x, 10);
        setLength((arm + halfLenPx) / displayScale);
      } else if (dragging === 'right') {
        const arm = Math.max(pt.x - CX, 10);
        setLength((halfLenPx + arm) / displayScale);
      } else if (dragging === 'rot') {
        const a = Math.atan2(pt.y - CY, pt.x - CX) * (180 / Math.PI);
        setAngleDeg(a);
      }
    };
    const onUp = () => setDragging(null);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [dragging, getModalPt, CX, CY, halfLenPx, displayScale]);

  const handleApplyGeometry = () => {
    const rad = (angleDeg * Math.PI) / 180;
    const ccx = (wall.start[0] + wall.end[0]) / 2;
    const ccy = (wall.start[1] + wall.end[1]) / 2;
    const halfL = length / 2;
    store.updateWall(wall.id, {
      start: [ccx - Math.cos(rad) * halfL, ccy - Math.sin(rad) * halfL],
      end: [ccx + Math.cos(rad) * halfL, ccy + Math.sin(rad) * halfL],
      thickness,
    });
  };

  // Back button = exit isolation without committing changes.
  const handleBack = () => {
    onExit();
  };

  // Save & Exit button: commit geometry and per-wall color/pattern override to the store
  const handleApplyAndExit = () => {
    handleApplyGeometry();
    setWallColorOverride(wallMeshName, { color, pattern });
    onExit();
  };

  // Esc to close the panel (no modifier checks needed — it's just one
  // shortcut and there are no input/keyboard conflicts because the only
  // form fields are the colour/number inputs which Esc wouldn't normally
  // consume on their own).
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tgt = e.target as HTMLElement | null;
      if (tgt?.tagName === 'INPUT' || tgt?.tagName === 'TEXTAREA' || tgt?.isContentEditable) return;
      if (e.key === 'Escape') {
        e.preventDefault();
        onExit();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onExit]);

  const rotRad = ((angleDeg - 90) * Math.PI) / 180;
  const rotHx = CX + ROT_R * Math.cos(rotRad);
  const rotHy = CY + ROT_R * Math.sin(rotRad);

  // Named regions of this wall (namedSelections are still global; we filter
  // the ones that touch the isolated wall's mesh).
  const localNamedSelections = useEditorStore.getState().namedSelections;

  return (
    <div className="pointer-events-none fixed inset-0 z-50">
      <div
        className="pointer-events-auto absolute right-4 top-16 bottom-4 flex w-[460px] flex-col overflow-hidden rounded-2xl border border-indigo-500/40 shadow-2xl"
        style={{
          background: 'linear-gradient(135deg,#0f172a,#111827)',
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-3"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
        >
          <div className="flex items-center gap-2">
            {/* Back arrow — leaves isolation and returns to orbit mode so
                the user can pick another wall. Edits to colour/pattern are
                already auto-saved via setWallColorOverride. */}
            <button
              type="button"
              onClick={handleBack}
              className="flex items-center gap-1 rounded-md bg-slate-800 px-2 py-1 text-xs font-medium text-slate-200 transition-colors hover:bg-slate-700 hover:text-white"
              title="Back — leave this wall and pick another"
            >
              <span className="text-base leading-none">←</span>
              <span>Back</span>
            </button>
            <div className="ml-1 h-2.5 w-2.5 rounded-sm bg-orange-500" />
            <span className="text-sm font-semibold text-slate-100">Wall Isolation</span>
            <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[11px] text-slate-400">
              {wall.id}
            </span>
            <span className="text-[11px] text-slate-500">— edits apply only to this wall</span>
          </div>
        </div>

        {/* Geometry preview */}
        <div className="flex justify-center px-5 pt-3">
          <svg
            ref={svgRef}
            width={MW}
            height={MH}
            viewBox={`0 0 ${MW} ${MH}`}
            style={{
              borderRadius: 12,
              background: 'radial-gradient(ellipse at center, rgba(30,30,50,0.9) 0%, rgba(10,10,20,0.95) 100%)',
              cursor: dragging === 'rot' ? 'crosshair' : dragging ? 'ew-resize' : 'default',
              display: 'block',
            }}
          >
            <defs>
              <pattern
                id="wall-iso-grid"
                width={displayScale}
                height={displayScale}
                patternUnits="userSpaceOnUse"
                x={CX % displayScale}
                y={CY % displayScale}
              >
                <path
                  d={`M ${displayScale} 0 L 0 0 0 ${displayScale}`}
                  fill="none"
                  stroke="rgba(255,255,255,0.04)"
                  strokeWidth={1}
                />
              </pattern>
            </defs>
            <rect width={MW} height={MH} fill="url(#wall-iso-grid)" />

            <circle
              cx={CX}
              cy={CY}
              r={ROT_R}
              fill="none"
              stroke="rgba(99,102,241,0.25)"
              strokeWidth={1.5}
              strokeDasharray="5 5"
              style={{ pointerEvents: 'none' }}
            />
            <text
              x={CX}
              y={CY - ROT_R - 10}
              textAnchor="middle"
              fontSize={10}
              fill="rgba(99,102,241,0.6)"
              style={{ pointerEvents: 'none' }}
            >
              drag to rotate
            </text>
            <circle
              cx={rotHx}
              cy={rotHy}
              r={11}
              fill="#4f46e5"
              stroke="rgba(255,255,255,0.6)"
              strokeWidth={2}
              onMouseDown={(e) => {
                e.stopPropagation();
                setDragging('rot');
              }}
              style={{ cursor: 'grab' }}
            />
            <text
              x={rotHx}
              y={rotHy}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="white"
              fontSize={11}
              style={{ pointerEvents: 'none' }}
            >
              ↺
            </text>

            <text
              x={CX}
              y={20}
              textAnchor="middle"
              fontSize={11}
              fontWeight={600}
              fill="rgba(99,102,241,0.85)"
              style={{ pointerEvents: 'none' }}
            >
              {angleDeg.toFixed(1)}°
            </text>

            <rect
              x={CX - halfLenPx}
              y={CY - thickPx / 2}
              width={halfLenPx * 2}
              height={thickPx}
              fill={color}
              opacity={0.9}
              rx={3}
              style={{ pointerEvents: 'none' }}
            />
            {/* Pattern overlay */}
            {pattern === 'stacked_coils' && (
              <rect
                x={CX - halfLenPx}
                y={CY - thickPx / 2}
                width={halfLenPx * 2}
                height={thickPx}
                fill={`repeating-linear-gradient(0deg, ${color} 0 4px, rgba(0,0,0,0.18) 4px 6px)`}
                rx={3}
                style={{ pointerEvents: 'none' }}
              />
            )}

            <circle
              cx={CX - halfLenPx}
              cy={CY}
              r={HANDLE_R}
              fill="#f97316"
              stroke="white"
              strokeWidth={2}
              onMouseDown={(e) => {
                e.stopPropagation();
                setDragging('left');
              }}
              style={{ cursor: 'ew-resize' }}
            />
            <circle
              cx={CX + halfLenPx}
              cy={CY}
              r={HANDLE_R}
              fill="#f97316"
              stroke="white"
              strokeWidth={2}
              onMouseDown={(e) => {
                e.stopPropagation();
                setDragging('right');
              }}
              style={{ cursor: 'ew-resize' }}
            />

            <text
              x={CX - halfLenPx}
              y={CY - HANDLE_R - 6}
              textAnchor="middle"
              fontSize={9}
              fill="rgba(249,115,22,0.8)"
              style={{ pointerEvents: 'none' }}
            >
              start
            </text>
            <text
              x={CX + halfLenPx}
              y={CY - HANDLE_R - 6}
              textAnchor="middle"
              fontSize={9}
              fill="rgba(249,115,22,0.8)"
              style={{ pointerEvents: 'none' }}
            >
              end
            </text>

            <text
              x={CX}
              y={CY + thickPx / 2 + 18}
              textAnchor="middle"
              fontSize={10}
              fill="rgba(255,255,255,0.55)"
              style={{ pointerEvents: 'none' }}
            >
              {length.toFixed(2)} m
            </text>
            <text
              x={CX + halfLenPx + 26}
              y={CY}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize={9}
              fill="rgba(255,255,255,0.45)"
              style={{ pointerEvents: 'none' }}
            >
              {thickness.toFixed(2)} m
            </text>
          </svg>
        </div>

        {/* Body — scrollable */}
        <div className="flex-1 space-y-3 overflow-y-auto px-5 py-3">
          {/* Geometry controls */}
          <div className="grid grid-cols-3 gap-2">
            <NumericField
              label="Length (m)"
              value={length}
              step={0.05}
              min={0.1}
              max={100}
              onChange={(v) => setLength(v || 0.5)}
            />
            <NumericField
              label="Thickness (m)"
              value={thickness}
              step={0.01}
              min={0.05}
              max={2.0}
              onChange={(v) => setThickness(v || 0.15)}
            />
            <NumericField
              label="Angle (°)"
              value={angleDeg}
              step={1}
              min={-180}
              max={180}
              onChange={(v) => setAngleDeg(v)}
            />
          </div>

          <button
            type="button"
            onClick={handleApplyGeometry}
            className="w-full rounded-md px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:bg-slate-700"
            style={{ border: '1px solid rgba(255,255,255,0.08)' }}
          >
            Update geometry
          </button>

          {/* Colour + pattern */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-slate-400">
                Colour
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  className="h-8 w-12 cursor-pointer rounded border border-slate-700 bg-transparent"
                />
                <input
                  type="text"
                  value={color.toUpperCase()}
                  onChange={(e) => setColor(e.target.value)}
                  className="flex-1 rounded-md px-2 py-1 font-mono text-xs text-slate-100 focus:outline-none"
                  style={{
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                  }}
                />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-slate-400">
                Pattern
              </label>
              <div className="flex gap-1">
                {([
                  { id: 'smooth', label: 'Smooth', preview: 'solid' },
                  { id: 'stacked_coils', label: '3D printed', preview: 'stacked' },
                ] as const).map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setPattern(p.id)}
                    className={`flex-1 overflow-hidden rounded-md border p-1 text-left text-xs transition-colors ${
                      pattern === p.id
                        ? 'border-indigo-400 ring-2 ring-indigo-500/40'
                        : 'border-slate-700 hover:border-slate-500'
                    }`}
                  >
                    <div
                      className="mb-1 h-8 rounded"
                      style={{
                        backgroundColor: color,
                        backgroundImage:
                          p.preview === 'stacked'
                            ? `repeating-linear-gradient(0deg, rgba(0,0,0,0.25) 0 4px, transparent 4px 8px)`
                            : 'none',
                      }}
                    />
                    <span className="text-slate-200">{p.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={handleApplyAndExit}
            className="w-full rounded-md px-3 py-2 text-xs font-semibold text-white shadow transition-colors hover:bg-indigo-500"
            style={{
              background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
              boxShadow: '0 4px 14px rgba(79,70,229,0.35)',
            }}
            title="Save changes to this wall and return to viewport"
          >
            ✓ Save & Pick Another Wall
          </button>

          <p className="text-[10px] leading-snug text-slate-500">
            Click <span className="mx-1 inline-block rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-slate-300">✓ Save &amp; Pick Another Wall</span> to commit changes to this wall. Click
            <span className="mx-1 inline-block rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-slate-300">← Back</span>
            (or press Esc) to cancel without saving.
          </p>

          {/* Sub-selection tools */}
          <div
            className="rounded-lg p-3"
            style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-300">
                Sub-select within this wall
              </span>
              <button
                type="button"
                onClick={clearSelections}
                className="text-[10px] text-slate-400 hover:text-rose-300"
                title="Clear all selections"
              >
                clear all
              </button>
            </div>
            <div className="flex gap-1">
              {(['click', 'brush', 'box', 'lasso'] as const).map((tool) => (
                <button
                  key={tool}
                  type="button"
                  onClick={() => setSelectionTool(tool)}
                  className={`flex-1 rounded px-2 py-1 text-xs font-medium capitalize transition-colors ${
                    selectionTool === tool
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {tool}
                </button>
              ))}
            </div>
            {selectionTool === 'brush' && (
              <label className="mt-2 block text-[10px] text-slate-400">
                Brush radius ({brushRadius.toFixed(2)} m)
                <input
                  type="range"
                  min={0.05}
                  max={0.5}
                  step={0.01}
                  value={brushRadius}
                  onChange={(e) => setBrushRadius(parseFloat(e.target.value))}
                  className="mt-1 w-full"
                />
              </label>
            )}

            {selections.length > 0 && (
              <div className="mt-2 space-y-1">
                {selections
                  .filter((s) =>
                    s.meshRefs.some((m) => m.objectName === wallMeshName),
                  )
                  .map((s) => {
                    const isActive = s.id === activeSelectionId;
                    const label = s.name ?? `Region ${s.id.slice(-5)}`;
                    return (
                      <div
                        key={s.id}
                        className={`flex items-center gap-1 rounded border px-1.5 py-1 ${
                          isActive ? 'border-indigo-400 bg-indigo-500/10' : 'border-slate-700 bg-slate-800/60'
                        }`}
                      >
                        <button
                          type="button"
                          onClick={() => setActiveSelection(s.id)}
                          className="flex-1 truncate text-left text-[11px] text-slate-200"
                          title={`${s.faceRefs.length} faces, ${s.meshRefs.length} meshes`}
                        >
                          {label} · {s.faceRefs.length}f
                        </button>
                        <button
                          type="button"
                          onClick={() => removeSelection(s.id)}
                          className="text-[11px] text-slate-500 hover:text-rose-300"
                        >
                          ✕
                        </button>
                      </div>
                    );
                  })}
              </div>
            )}

            {Object.keys(localNamedSelections).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {Object.keys(localNamedSelections).map((n) => (
                  <span
                    key={n}
                    className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400"
                  >
                    {n}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

function wallLen(start?: [number, number], end?: [number, number]): number {
  if (!start || !end || !Array.isArray(start) || !Array.isArray(end)) return 0;
  const dx = (end[0] ?? 0) - (start[0] ?? 0);
  const dy = (end[1] ?? 0) - (start[1] ?? 0);
  return Math.sqrt(dx * dx + dy * dy);
}

function wallAngleDeg(wall?: WallLike): number {
  if (!wall || !wall.start || !wall.end) return 0;
  const dx = (wall.end[0] ?? 0) - (wall.start[0] ?? 0);
  const dy = (wall.end[1] ?? 0) - (wall.start[1] ?? 0);
  return (Math.atan2(dy, dx) * 180) / Math.PI;
}

interface NumericFieldProps {
  label: string;
  value: number;
  step: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}

const NumericField: React.FC<NumericFieldProps> = ({ label, value, step, min, max, onChange }) => (
  <div>
    <label className="mb-1 block text-[10px] uppercase tracking-wide text-slate-400">
      {label}
    </label>
    <input
      type="number"
      step={step}
      min={min}
      max={max}
      value={Number.isFinite(value) ? value.toFixed(step < 1 ? 3 : 1) : ''}
      onChange={(e) => onChange(parseFloat(e.target.value))}
      className="w-full rounded-md px-2 py-1.5 font-mono text-xs text-slate-100 transition-colors focus:outline-none"
      style={{
        background: 'rgba(255,255,255,0.05)',
        border: '1px solid rgba(255,255,255,0.1)',
      }}
      onFocus={(e) => (e.target.style.borderColor = 'rgba(99,102,241,0.7)')}
      onBlur={(e) => (e.target.style.borderColor = 'rgba(255,255,255,0.1)')}
    />
  </div>
);

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
  const hint =
    viewport.interactionMode === 'orbit'
      ? '🖱 Left-drag: rotate · Right-drag: pan · Scroll: zoom'
      : '🖱 Left-click: pick · Right-drag: rotate · Scroll: zoom';
  return <span className="rounded bg-black/40 px-2 py-1 text-[10px] text-white/80">{hint}</span>;
};

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
