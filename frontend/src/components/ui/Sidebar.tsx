import React, { useState } from 'react';
import { useEditorStore } from '../../store/editorStore';
import { validateGraph, exportBlender } from '../../api/client';
import { SelectionToolbar } from '../editor/SelectionToolbar';
import { AIEditPanel } from '../editor/AIEditPanel';
import { ArrowLeft } from 'lucide-react';

interface SidebarProps {
  onBackToHome: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onBackToHome }) => {
  const {
    undo,
    redo,
    historyIndex,
    history,
    sceneGraph,
    setSceneGraph,
    materialOptions,
    includeBase,
    includeRoof,
    setGlbUrl,
    bumpGlbVersion,
    setSyncStatus,
  } = useEditorStore();

  const [syncing, setSyncing] = useState(false);

  const handleValidate = async () => {
    if (!sceneGraph) return;
    try {
      const result = await validateGraph(sceneGraph);
      if (result.status === 'success') {
        setSceneGraph(result.scene_graph);
        alert('Validation complete. Graph updated.');
      }
    } catch (err) {
      console.error('Validation failed', err);
      alert('Validation failed.');
    }
  };

  const handleSync = async () => {
    if (!sceneGraph || syncing) return;
    setSyncing(true);
    setSyncStatus('syncing');
    try {
      const result = await exportBlender(sceneGraph, includeBase, includeRoof, materialOptions, false);
      if (result.status !== 'success') {
        throw new Error(result.detail || 'Export failed');
      }
      const glbPath = (result.export_paths || []).find((p: string) => p.endsWith('.glb'));
      if (glbPath) {
        const filename = glbPath.split('\\').pop()?.split('/').pop();
        setGlbUrl(`http://localhost:8000/output/${filename}?t=${Date.now()}`);
        bumpGlbVersion();
      }
      setSyncStatus('synced');
    } catch (err) {
      console.error('Sync failed', err);
      setSyncStatus('error', err instanceof Error ? err.message : String(err));
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="flex h-full w-64 flex-col overflow-y-auto border-r border-gray-300 bg-gray-100">
      <div className="border-b border-gray-300 p-3">
        <button
          type="button"
          onClick={onBackToHome}
          className="flex w-full items-center gap-2 rounded px-3 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-200 hover:text-gray-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Pipeline
        </button>
      </div>

      <div className="border-b border-gray-300 p-4">
        <h2 className="text-lg font-bold">Construction Editor</h2>
        {sceneGraph && (
          <p className="mt-1 text-xs text-gray-500">
            {sceneGraph.walls.length} walls · {sceneGraph.rooms.length} rooms
          </p>
        )}
      </div>

      <SelectionToolbar />

      <div className="flex justify-between border-b border-gray-300 p-4">
        <button
          type="button"
          onClick={undo}
          disabled={historyIndex <= 0}
          className="rounded bg-gray-300 px-3 py-1 disabled:opacity-50"
        >
          Undo
        </button>
        <button
          type="button"
          onClick={redo}
          disabled={historyIndex >= history.length - 1}
          className="rounded bg-gray-300 px-3 py-1 disabled:opacity-50"
        >
          Redo
        </button>
      </div>

      <AIEditPanel />

      <div className="mt-auto flex flex-col gap-2 p-4">
        <button
          type="button"
          onClick={handleValidate}
          disabled={!sceneGraph}
          className="w-full rounded bg-yellow-500 px-4 py-2 text-white hover:bg-yellow-600 disabled:opacity-50"
        >
          Validate Graph
        </button>
        <button
          type="button"
          onClick={handleSync}
          disabled={!sceneGraph || syncing}
          className="w-full rounded bg-green-600 px-4 py-2 text-white hover:bg-green-700 disabled:opacity-50"
        >
          {syncing ? 'Syncing…' : 'Sync to Blender'}
        </button>
      </div>
    </div>
  );
};
