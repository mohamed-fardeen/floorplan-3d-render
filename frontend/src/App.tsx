import { useState } from 'react';
import { Home } from './pages/Home';
import { Sidebar } from './components/ui/Sidebar';
import { ConstructionViewport } from './components/viewport/ConstructionViewport';
import { EditingPanel } from './components/editor/EditingPanel';
import { useEditorStore } from './store/editorStore';
import type { SceneGraph } from './types/schema';
import type { MaterialOptions } from './api/client';

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
  const { setSceneGraph, setGlbUrl, setMaterialOptions, setExportOptions } = useEditorStore();

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

  const handleBackToHome = () => {
    setView('home');
  };

  if (view === 'editor') {
    return (
      <div className="flex h-screen w-full overflow-hidden">
        <Sidebar onBackToHome={handleBackToHome} />
        <ConstructionViewport className="min-w-0 flex-1" />
        <EditingPanel />
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
