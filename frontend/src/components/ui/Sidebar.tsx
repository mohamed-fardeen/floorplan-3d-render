import React, { useEffect, useState } from 'react';
import { useEditorStore } from '../../store/editorStore';
import {
  validateGraph,
  exportBlender,
  getBlenderMcpInfo,
  getBlenderMcpLog,
  launchBlenderMcp,
} from '../../api/client';
import { SelectionToolbar } from '../editor/SelectionToolbar';
import { SelectionActions } from '../editor/SelectionActions';
import { MetricsPanel } from '../editor/MetricsPanel';
import { AIEditPanel } from '../editor/AIEditPanel';
import { CollapsibleSection } from './CollapsibleSection';
import { ArrowLeft, Cpu, Save, RefreshCw, Sparkles } from 'lucide-react';
import * as THREE from 'three';

interface SidebarProps {
  onBackToHome: () => void;
  glbRoot: THREE.Group | null;
  mcpAvailable: boolean;
  onSelectionTransform: (name: 'grow' | 'shrink' | 'invert' | 'connected' | 'expandToMesh') => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onBackToHome, glbRoot, mcpAvailable, onSelectionTransform }) => {
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
  const [launchingMcp, setLaunchingMcp] = useState(false);
  const [mcpError, setMcpError] = useState<string | null>(null);
  const [mcpLog, setMcpLog] = useState<string>('');
  const [blenderPath, setBlenderPath] = useState<string | null>(null);
  const [showLog, setShowLog] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const probe = async () => {
      try {
        const [info, log] = await Promise.all([
          getBlenderMcpInfo(),
          getBlenderMcpLog(),
        ]);
        if (cancelled) return;
        setBlenderPath(info.blender_executable);
        setMcpLog(log);
      } catch {
        /* ignore */
      }
    };
    probe();
    const handle = window.setInterval(probe, 4000);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, []);

  const handleLaunchMcp = async () => {
    setLaunchingMcp(true);
    setMcpError(null);
    try {
      const res = await launchBlenderMcp();
      if (res.status === 'error') {
        setMcpError(res.detail || 'Unknown launch error');
      } else if (res.log) {
        setMcpLog(res.log);
      }
    } catch (err) {
      setMcpError(err instanceof Error ? err.message : String(err));
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
      }
    } catch (err) {
      console.error('Validation failed', err);
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

      <CollapsibleSection title="Selection" badge={`${useEditorStore.getState().selections.length} regions`}>
        <SelectionToolbar />
        <div className="mt-3">
          <SelectionActions
            onGrow={() => onSelectionTransform('grow')}
            onShrink={() => onSelectionTransform('shrink')}
            onInvert={() => onSelectionTransform('invert')}
            onConnected={() => onSelectionTransform('connected')}
            onExpandToMesh={() => onSelectionTransform('expandToMesh')}
          />
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="History" badge={`${history.length}/${selectionHistory.length}`}>
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
          <button
            type="button"
            onClick={undoSelection}
            disabled={selectionHistoryIndex <= 0}
            className="rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-40"
          >
            Undo sel
          </button>
          <button
            type="button"
            onClick={redoSelection}
            disabled={selectionHistoryIndex >= selectionHistory.length - 1}
            className="rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-40"
          >
            Redo sel
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
        <div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={handleValidate}
            disabled={!sceneGraph}
            className="flex w-full items-center justify-center gap-1.5 rounded bg-amber-500 px-3 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-40"
          >
            <Sparkles className="h-4 w-4" /> Validate Graph
          </button>
          <button
            type="button"
            onClick={handleSync}
            disabled={!sceneGraph || syncing}
            className="flex w-full items-center justify-center gap-1.5 rounded bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-40"
          >
            <RefreshCw className={`h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? 'Syncing…' : 'Sync to Blender'}
          </button>
        </div>

        <div className="mt-3 rounded-lg border border-gray-200 bg-gray-50 p-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 font-medium text-gray-700">
              <Cpu className="h-3 w-3" /> Live MCP
            </span>
            <span
              className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] ${
                mcpAvailable ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-200 text-gray-600'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  mcpAvailable ? 'bg-emerald-500' : 'bg-gray-400'
                }`}
              />
              {mcpAvailable ? 'connected' : 'offline'}
            </span>
          </div>
          <p className="mt-1 truncate text-[10px] text-gray-500" title={blenderPath ?? ''}>
            {blenderPath ? `Blender: ${blenderPath}` : 'Blender executable not detected'}
          </p>
          {!mcpAvailable && (
            <>
              <button
                type="button"
                onClick={handleLaunchMcp}
                disabled={launchingMcp || !blenderPath}
                className="mt-2 w-full rounded bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-40"
              >
                {launchingMcp ? 'Launching Blender…' : 'Launch Blender with MCP'}
              </button>
              {!blenderPath && (
                <p className="mt-2 text-[10px] text-red-600">
                  Blender executable not found on PATH or under C:\Program Files\Blender Foundation.
                  Install Blender 4.0+ and restart the backend.
                </p>
              )}
              <button
                type="button"
                onClick={() => setShowLog((v) => !v)}
                className="mt-1 text-[10px] text-gray-500 hover:text-gray-700"
              >
                {showLog ? 'Hide' : 'Show'} launch log
              </button>
              {showLog && (
                <pre className="mt-1 max-h-32 overflow-y-auto whitespace-pre-wrap break-all rounded bg-white p-1.5 font-mono text-[9px] text-gray-700">
                  {mcpLog || '(no log yet)'}
                </pre>
              )}
              {mcpError && (
                <p className="mt-1 text-[10px] text-red-600">{mcpError}</p>
              )}
              <p className="mt-2 text-[10px] leading-snug text-gray-500">
                If the button is greyed out, install Blender 4.0+. Otherwise the
                backend launches Blender with the addon preloaded and the socket
                listens on <code className="rounded bg-gray-200 px-1">:9876</code>.
              </p>
            </>
          )}
          {mcpAvailable && (
            <p className="mt-2 text-[10px] leading-snug text-emerald-700">
              Blender MCP socket is reachable. Region edits dispatch live.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};