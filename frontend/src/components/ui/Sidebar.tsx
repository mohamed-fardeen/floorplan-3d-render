import React, { useEffect, useState } from 'react';
import { useEditorStore } from '../../store/editorStore';
import {
  validateGraph,
  exportBlender,
  getBlenderMcpStatus,
  launchBlenderMcp,
} from '../../api/client';
import { SelectionToolbar } from '../editor/SelectionToolbar';
import { SelectionActions } from '../editor/SelectionActions';
import { MetricsPanel } from '../editor/MetricsPanel';
import { AIEditPanel } from '../editor/AIEditPanel';
import { ArrowLeft } from 'lucide-react';
import * as THREE from 'three';

interface SidebarProps {
  onBackToHome: () => void;
  glbRoot: THREE.Group | null;
  onSelectionTransform: (name: 'grow' | 'shrink' | 'invert' | 'connected' | 'expandToMesh') => void;
}

interface SidebarProps {
  onBackToHome: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onBackToHome, glbRoot, onSelectionTransform }) => {
  const {
    undo,
    redo,
    undoSelection,
    redoSelection,
    historyIndex,
    history,
    selectionHistoryIndex,
    selectionHistory,
    sceneGraph,
    setSceneGraph,
    materialOptions,
    includeBase,
    includeRoof,
    setGlbUrl,
    bumpGlbVersion,
    setSyncStatus,
    persistProject,
  } = useEditorStore();

  const [syncing, setSyncing] = useState(false);
  const [mcpAvailable, setMcpAvailable] = useState(false);
  const [launchingMcp, setLaunchingMcp] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const probe = async () => {
      const status = await getBlenderMcpStatus();
      if (!cancelled) setMcpAvailable(status.available);
    };
    probe();
    const handle = window.setInterval(probe, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, []);

  const handleLaunchMcp = async () => {
    setLaunchingMcp(true);
    try {
      await launchBlenderMcp();
      const status = await getBlenderMcpStatus();
      setMcpAvailable(status.available);
    } finally {
      setLaunchingMcp(false);
    }
  };

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

      <SelectionActions
        onGrow={() => onSelectionTransform('grow')}
        onShrink={() => onSelectionTransform('shrink')}
        onInvert={() => onSelectionTransform('invert')}
        onConnected={() => onSelectionTransform('connected')}
        onExpandToMesh={() => onSelectionTransform('expandToMesh')}
      />

      <MetricsPanel glbRoot={glbRoot} />

      <div className="grid grid-cols-2 gap-2 border-b border-gray-300 p-4">
        <button
          type="button"
          onClick={undo}
          disabled={historyIndex <= 0}
          className="rounded bg-gray-300 px-2 py-1 text-xs disabled:opacity-50"
        >
          Undo graph
        </button>
        <button
          type="button"
          onClick={redo}
          disabled={historyIndex >= history.length - 1}
          className="rounded bg-gray-300 px-2 py-1 text-xs disabled:opacity-50"
        >
          Redo graph
        </button>
        <button
          type="button"
          onClick={undoSelection}
          disabled={selectionHistoryIndex <= 0}
          className="rounded bg-gray-300 px-2 py-1 text-xs disabled:opacity-50"
        >
          Undo selection
        </button>
        <button
          type="button"
          onClick={redoSelection}
          disabled={selectionHistoryIndex >= selectionHistory.length - 1}
          className="rounded bg-gray-300 px-2 py-1 text-xs disabled:opacity-50"
        >
          Redo selection
        </button>
      </div>
      <div className="border-b border-gray-300 px-4 py-2">
        <button
          type="button"
          onClick={() => persistProject()}
          disabled={!sceneGraph}
          className="w-full rounded bg-slate-200 px-2 py-1 text-xs text-slate-800 hover:bg-slate-300 disabled:opacity-50"
        >
          Save session to browser
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
        <div className="mt-2 flex items-center gap-2 rounded border border-gray-200 bg-white px-2 py-1.5 text-xs">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              mcpAvailable ? 'bg-emerald-500' : 'bg-gray-400'
            }`}
          />
          <span className="text-gray-700">
            Live MCP {mcpAvailable ? 'connected' : 'offline'}
          </span>
          {!mcpAvailable && (
            <button
              type="button"
              onClick={handleLaunchMcp}
              disabled={launchingMcp}
              className="ml-auto rounded bg-indigo-600 px-2 py-0.5 text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {launchingMcp ? 'Launching…' : 'Launch'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
