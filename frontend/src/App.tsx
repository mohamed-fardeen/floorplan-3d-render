import { useCallback, useRef, useState } from 'react';
import { Home } from './pages/Home';
import { Sidebar } from './components/ui/Sidebar';
import { ConstructionViewport } from './components/viewport/ConstructionViewport';
import { EditingPanel } from './components/editor/EditingPanel';
import { useEditorStore } from './store/editorStore';
import type { SceneGraph } from './types/schema';
import type { MaterialOptions } from './api/client';
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
  const { setSceneGraph, setGlbUrl, setMaterialOptions, setExportOptions, transformActiveSelectionFaces } =
    useEditorStore();
  const transformRef = useRef(transformActiveSelectionFaces);
  transformRef.current = transformActiveSelectionFaces;

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

  if (view === 'editor') {
    return (
      <div className="flex h-screen w-full overflow-hidden">
        <Sidebar
          onBackToHome={handleBackToHome}
          glbRoot={glbRoot}
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
        <ConstructionViewport className="min-w-0 flex-1" onRoot={onRoot} />
        <EditingPanel glbRoot={glbRoot} />
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