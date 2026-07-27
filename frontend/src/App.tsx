import React, { useState } from 'react';
import { Home } from './pages/Home';
import { Sidebar } from './components/ui/Sidebar';
import { EditorCanvas } from './components/editor/EditorCanvas';
import { Preview3D } from './components/preview/Preview3D';
import { PropertiesPanel } from './components/ui/PropertiesPanel';
import { useEditorStore } from './store/editorStore';
import type { SceneGraph } from './types/schema';

type View = 'home' | 'editor';

function App() {
  const [view, setView] = useState<View>('home');
  const { setSceneGraph } = useEditorStore();

  const handleOpenEditor = (sceneGraph: SceneGraph) => {
    setSceneGraph(sceneGraph);
    setView('editor');
  };

  const handleBackToHome = () => {
    setView('home');
  };

  if (view === 'editor') {
    return (
      <div className="flex h-screen w-full overflow-hidden">
        <Sidebar onBackToHome={handleBackToHome} />
        <EditorCanvas />
        <Preview3D />
        <PropertiesPanel />
      </div>
    );
  }

  return <Home onOpenEditor={handleOpenEditor} />;
}

export default App;
