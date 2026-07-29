import React, { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useThree, type ThreeEvent } from '@react-three/fiber';
import { OrbitControls, Grid, useGLTF, Html } from '@react-three/drei';
import * as THREE from 'three';
import { useEditorStore } from '../../store/editorStore';
import {
  buildHighlightGeometry,
  createSelectionFromFaces,
  faceRefFromIntersection,
  mergeFaceRefs,
  meshObjectName,
  raycastMeshes,
} from '../../lib/selectionGeometry';
import type { FaceReference } from '../../types/selection';

const HIGHLIGHT_COLOR = '#4f46e5';

interface BuildingModelProps {
  url: string;
  version: number;
  onSceneReady: (scene: THREE.Group) => void;
}

const BuildingModel: React.FC<BuildingModelProps> = ({ url, version, onSceneReady }) => {
  const cacheBustedUrl = `${url}${url.includes('?') ? '&' : '?'}v=${version}`;
  const { scene } = useGLTF(cacheBustedUrl);
  const cloned = useMemo(() => scene.clone(true), [scene]);

  useEffect(() => {
    cloned.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        child.castShadow = true;
        child.receiveShadow = true;
      }
    });
    onSceneReady(cloned);
  }, [cloned, onSceneReady]);

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

  if (!geometry) return null;

  return (
    <mesh geometry={geometry} renderOrder={10}>
      <meshBasicMaterial
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
    </>
  );
};

interface BoxSelectOverlayProps {
  root: THREE.Group;
  disabled: boolean;
}

const BoxSelectOverlay: React.FC<BoxSelectOverlayProps> = ({ root, disabled }) => {
  const { camera, gl } = useThree();
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

interface SceneContentProps {
  glbUrl: string;
  version: number;
}

const SceneContent: React.FC<SceneContentProps> = ({ glbUrl, version }) => {
  const [root, setRoot] = useState<THREE.Group | null>(null);

  return (
    <>
      <ambientLight intensity={0.55} />
      <directionalLight position={[8, 14, 6]} intensity={1.1} castShadow shadow-mapSize={[2048, 2048]} />
      <directionalLight position={[-6, 8, -4]} intensity={0.35} />

      <Grid
        infiniteGrid
        cellSize={0.5}
        sectionSize={2}
        fadeDistance={40}
        fadeStrength={1}
        cellColor="#6b7280"
        sectionColor="#374151"
      />

      {import.meta.env.DEV && <axesHelper args={[2]} />}

      <Suspense fallback={null}>
        <BuildingModel url={glbUrl} version={version} onSceneReady={setRoot} />
      </Suspense>

      <PickHandler root={root} disabled={false} />

      <OrbitControls
        makeDefault
        enablePan
        enableZoom
        enableRotate
        mouseButtons={{
          LEFT: undefined as unknown as THREE.MOUSE,
          MIDDLE: THREE.MOUSE.PAN,
          RIGHT: THREE.MOUSE.ROTATE,
        }}
      />
    </>
  );
};

import type { SceneGraph } from '../../types/schema';

interface ConstructionViewportProps {
  className?: string;
  glbUrl?: string | null;
  sceneGraph?: SceneGraph | null;
}

export const ConstructionViewport: React.FC<ConstructionViewportProps> = ({
  className = '',
  glbUrl: glbUrlProp,
  sceneGraph: sceneGraphProp,
}) => {
  const store = useEditorStore();
  const glbUrl = glbUrlProp ?? store.glbUrl;
  const sceneGraph = sceneGraphProp ?? store.sceneGraph;
  const glbVersion = store.glbVersion;
  const syncStatus = store.syncStatus;

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
          <span className="rounded bg-amber-500/90 px-2 py-1 text-xs text-white">Syncing…</span>
        )}
        {syncStatus === 'synced' && (
          <span className="rounded bg-emerald-600/90 px-2 py-1 text-xs text-white">Synced</span>
        )}
        {syncStatus === 'error' && (
          <span className="rounded bg-red-600/90 px-2 py-1 text-xs text-white">Sync failed</span>
        )}
      </div>

      <div className="absolute top-3 right-3 z-10 flex gap-2">
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
        onCreated={({ camera }) => {
          camera.lookAt(0, 1.5, 0);
        }}
      >
        <SceneContent glbUrl={glbUrl} version={glbVersion} />
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
