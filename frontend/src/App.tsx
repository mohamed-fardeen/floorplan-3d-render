import { useCallback, useEffect, useRef, useState } from 'react';
import { Home } from './pages/Home';
import { Sidebar } from './components/ui/Sidebar';
import { ConstructionViewport } from './components/viewport/ConstructionViewport';
import { EditingPanel } from './components/editor/EditingPanel';
import { useEditorStore } from './store/editorStore';
import type { SceneGraph } from './types/schema';
import type { MaterialOptions } from './api/client';
import { exportBlender } from './api/client';
import { useMcpConnection } from './api/useMcpConnection';
import * as THREE from 'three';

type View = 'home' | 'editor';

interface OpenEditorPayload {
  sceneGraph: SceneGraph;
  glbUrl?: string;
  materialOptions?: MaterialOptions;
  includeBase?: boolean;
  includeRoof?: boolean;
}

function App() {
  const [view, setView] = useState<View>('home');
  const [glbRoot, setGlbRoot] = useState<THREE.Group | null>(null);
  const screenshotRef = useRef<(() => string | null) | null>(null);
  const { setSceneGraph, setGlbUrl, setMaterialOptions, setExportOptions, transformActiveSelectionFaces,
    sceneGraph, syncStatus, setSyncStatus, includeBase, includeRoof, materialOptions, bumpGlbVersion } =
    useEditorStore();
  const transformRef = useRef(transformActiveSelectionFaces);
  transformRef.current = transformActiveSelectionFaces;

  const mcp = useMcpConnection(view === 'editor' ? 1500 : 5000);
  const autoSyncedRef = useRef(false);
  useEffect(() => {
    // Auto-trigger a sync once Blender MCP comes online and we have a scene.
    if (view !== 'editor') return;
    if (!mcp.available) return;
    if (autoSyncedRef.current) return;
    if (!sceneGraph) return;
    if (syncStatus === 'syncing') return;
    autoSyncedRef.current = true;
    (async () => {
      try {
        setSyncStatus('syncing');
        const res = await exportBlender(
          sceneGraph,
          includeBase,
          includeRoof,
          materialOptions,
          false,
        );
        const glb = (res.export_paths || []).find((p: string) => p.endsWith('.glb'));
        if (glb) {
          const filename = glb.split('\\').pop()?.split('/').pop();
          setGlbUrl(`http://localhost:8000/output/${filename}?t=${Date.now()}`);
          bumpGlbVersion();
        }
        setSyncStatus(res.status === 'success' ? 'synced' : 'error', res.detail);
      } catch (err) {
        setSyncStatus('error', err instanceof Error ? err.message : String(err));
      }
    })();
  }, [mcp.available, view, sceneGraph, syncStatus, includeBase, includeRoof, materialOptions,
    setSyncStatus, setGlbUrl, bumpGlbVersion]);

  const handleOpenEditor = ({
    sceneGraph,
    glbUrl,
    materialOptions,
    includeBase = true,
    includeRoof = false,
  }: OpenEditorPayload) => {
    setSceneGraph(sceneGraph);
    if (glbUrl) setGlbUrl(glbUrl);
    if (materialOptions) setMaterialOptions(materialOptions);
    setExportOptions(includeBase, includeRoof);
    setView('editor');
  };

  const handleBackToHome = () => setView('home');

  const onRoot = useCallback((g: THREE.Group | null) => setGlbRoot(g), []);
  const registerScreenshot = useCallback((fn: () => string | null) => {
    screenshotRef.current = fn;
  }, []);

  if (view === 'editor') {
    return (
      <div className="flex h-screen w-full overflow-hidden">
        <Sidebar
          onBackToHome={handleBackToHome}
          glbRoot={glbRoot}
          mcpAvailable={mcp.available}
          onSelectionTransform={(name) => {
            if (!glbRoot) return;
            if (name === 'grow') {
              import('./lib/selectionGeometry').then(({ growFaces }) => {
                transformRef.current((refs) => growFaces(glbRoot, refs, 1));
              });
            } else if (name === 'shrink') {
              import('./lib/selectionGeometry').then(({ shrinkFaces }) => {
                transformRef.current((refs) => shrinkFaces(glbRoot, refs, 1));
              });
            } else if (name === 'invert') {
              import('./lib/selectionGeometry').then(({ invertFaces }) => {
                transformRef.current((refs) => invertFaces(glbRoot, refs));
              });
            } else if (name === 'connected') {
              import('./lib/selectionGeometry').then(({ connectedFaces }) => {
                transformRef.current((refs) => connectedFaces(glbRoot, refs));
              });
            } else if (name === 'expandToMesh') {
              import('./lib/selectionGeometry').then(({ expandToMeshFaces }) => {
                transformRef.current((refs) => expandToMeshFaces(glbRoot, refs));
              });
            }
          }}
        />
        <ConstructionViewport className="min-w-0 flex-1" onRoot={onRoot} registerScreenshot={registerScreenshot} />
        <EditingPanel
          glbRoot={glbRoot}
          viewportScreenshot={() => screenshotRef.current?.() ?? null}
        />
      </div>
    );
  }

  return (
    <Home
      onOpenEditor={(sceneGraph, extras) =>
        handleOpenEditor({ sceneGraph, ...extras })
      }
    />
  );
}

export default App;