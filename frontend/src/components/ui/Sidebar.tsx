import React from 'react';
import { useEditorStore } from '../../store/editorStore';
import { validateGraph } from '../../api/client';
import { MetricsPanel } from '../editor/MetricsPanel';
import { AIEditPanel } from '../editor/AIEditPanel';
import { CollapsibleSection } from './CollapsibleSection';
import { ArrowLeft, Save, Sparkles, MousePointerClick } from 'lucide-react';
import * as THREE from 'three';

interface SidebarProps {
  onBackToHome: () => void;
  glbRoot: THREE.Group | null;
  onSelectionTransform: (name: 'grow' | 'shrink' | 'invert' | 'connected' | 'expandToMesh') => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onBackToHome, glbRoot, onSelectionTransform: _onSelectionTransform }) => {
  const {
    undo,
    redo,
    historyIndex,
    history,
    sceneGraph,
    setSceneGraph,
    persistProject,
  } = useEditorStore();

  const handleValidate = async () => {
    if (!sceneGraph) return;
    try {
      const result = await validateGraph(sceneGraph);
      if (result.status === 'success') {
        setSceneGraph(result.scene_graph);
      }
    } catch (err) {
      console.error('Validation failed', err);
    }
  };

  return (
    <div className="flex h-full w-72 flex-col overflow-y-auto border-r border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-3 py-2">
        <button
          type="button"
          onClick={onBackToHome}
          className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Pipeline
        </button>
      </div>

      <div className="border-b border-gray-200 px-4 py-3">
        <h2 className="text-base font-semibold text-gray-900">Construction Editor</h2>
        {sceneGraph && (
          <p className="mt-0.5 text-xs text-gray-500">
            {sceneGraph.walls.length} walls · {sceneGraph.rooms.length} rooms · {sceneGraph.doors.length} doors · {sceneGraph.windows.length} windows
          </p>
        )}
      </div>

      {/* Selection tools now live inside the IsolationPanel (right side).
          Outside isolation mode the user just orbits the camera and clicks
          a wall to enter isolation. */}
      <div className="border-b border-gray-200 px-4 py-3">
        <div className="flex items-start gap-2 rounded-md bg-indigo-50 px-2 py-1.5 text-[11px] text-indigo-900">
          <MousePointerClick className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>
            Click any wall in the 3D view to <strong>isolate</strong> it. All
            pattern / colour / geometry / selection tools then appear inside
            the isolation panel.
          </span>
        </div>
      </div>

      <CollapsibleSection title="History" badge={`${history.length}`}>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={undo}
            disabled={historyIndex <= 0}
            className="rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-40"
          >
            Undo graph
          </button>
          <button
            type="button"
            onClick={redo}
            disabled={historyIndex >= history.length - 1}
            className="rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-40"
          >
            Redo graph
          </button>
        </div>
        <button
          type="button"
          onClick={() => persistProject()}
          disabled={!sceneGraph}
          className="mt-2 flex w-full items-center justify-center gap-1 rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-40"
        >
          <Save className="h-3 w-3" /> Save session
        </button>
      </CollapsibleSection>

      <CollapsibleSection title="Metrics">
        <MetricsPanel glbRoot={glbRoot} />
      </CollapsibleSection>

      <CollapsibleSection title="AI Agent" badge="LLM" defaultOpen={false}>
        <AIEditPanel />
      </CollapsibleSection>

      <div className="mt-auto border-t border-gray-200 p-3">
        <button
          type="button"
          onClick={handleValidate}
          disabled={!sceneGraph}
          className="flex w-full items-center justify-center gap-1.5 rounded bg-amber-500 px-3 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-40"
        >
          <Sparkles className="h-4 w-4" /> Validate Graph
        </button>
      </div>
    </div>
  );
};
