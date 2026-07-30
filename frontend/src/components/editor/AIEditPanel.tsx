import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useEditorStore } from '../../store/editorStore';
import { MATERIAL_PRESETS, PATTERN_LIBRARY } from '../../lib/patterns';
import {
  fetchAgentLog,
  postAgentChat,
} from '../../api/agent';
import type {
  AgentChatResponse,
  AgentLogEntry,
  AgentChatRequest,
} from '../../api/agent';
import { fetchLlmProviders } from '../../api/llm';
import { applyDesignActions } from '../../api/client';

interface ChatTurn {
  role: 'user' | 'agent';
  text: string;
  response?: AgentChatResponse;
  ts: number;
}

const formatTrace = (entry: AgentLogEntry): string => {
  const meta = Object.entries(entry)
    .filter(([k, v]) => k !== 'id' && k !== 'ts' && v !== undefined && v !== null)
    .map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
    .slice(0, 3)
    .join(' ');
  return `[${entry.step}] ${meta}`;
};

import * as THREE from 'three';

interface AIEditPanelProps {
  viewportScreenshot?: () => string | null;
  glbRoot?: THREE.Group | null;
}

export const AIEditPanel: React.FC<AIEditPanelProps> = ({ viewportScreenshot }) => {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<ChatTurn[]>([]);
  const [trace, setTrace] = useState<AgentLogEntry[]>([]);
  const [provider, setProvider] = useState<string>('');
  const [providers, setProviders] = useState<{ name: string; available: boolean }[]>([]);
  const [includeImage, setIncludeImage] = useState(true);
  const conversationRef = useRef<Array<Record<string, unknown>>>([]);

  const {
    getActiveSelection,
    sceneGraph,
    includeBase,
    includeRoof,
    applyDesignPlanLocally,
    setSyncStatus,
    setSyncStage,
    bumpGlbVersion,
    setGlbUrl,
  } = useEditorStore();

  const selection = getActiveSelection();
  const projectId = useMemo(() => {
    const meta = sceneGraph?.metadata as { project_name?: string } | undefined;
    return (meta?.project_name ?? 'unsaved').replace(/\s+/g, '_').toLowerCase();
  }, [sceneGraph]);

  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      try {
        const [log, prov] = await Promise.all([fetchAgentLog(projectId, 30), fetchLlmProviders()]);
        if (cancelled) return;
        setTrace(log.items);
        setProviders(prov);
        if (!provider && prov.find((p) => p.available)?.name) {
          setProvider('');
        }
      } catch {
        // network may be down in dev; fail silently
      }
    };
    refresh();
    const handle = window.setInterval(refresh, 4000);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, [projectId, loading]);

  const sendPrompt = async () => {
    if (!sceneGraph || !selection || !prompt.trim()) return;
    setLoading(true);
    setError(null);
    setSyncStatus('syncing');
    setSyncStage('orchestrator', 'Routing prompt');

    let viewportImage: string | undefined;
    if (includeImage && viewportScreenshot) {
      try {
        const data = viewportScreenshot();
        if (data) viewportImage = data.startsWith('data:') ? data.split(',')[1] : data;
      } catch {
        // ignore — image is optional
      }
    }

    const req: AgentChatRequest = {
      prompt: prompt.trim(),
      selection: {
        id: selection.id,
        meshRefs: selection.meshRefs,
        faceRefs: selection.faceRefs,
        metadata: selection.metadata as Record<string, unknown>,
      },
      project_id: projectId,
      conversation: conversationRef.current,
      available_patterns: PATTERN_LIBRARY.map((p) => p.id),
      available_materials: MATERIAL_PRESETS.map((p) => p.id),
      viewport_image: viewportImage,
      llm_provider: provider || undefined,
    };

    try {
      const result = await postAgentChat(req);
      conversationRef.current = [
        ...conversationRef.current,
        { role: 'user', content: req.prompt },
        { role: 'agent', intent: result.intent, invoked: result.invoked_agents },
      ];

      if (result.intent === 'clarify') {
        setHistory((h) => [
          ...h,
          { role: 'agent', text: result.clarification ?? 'Could you clarify?', response: result, ts: Date.now() },
        ]);
        setSyncStatus('idle');
        setSyncStage(null, null);
        return;
      }

      if (result.error) {
        setError(result.error);
        setSyncStatus('error', result.error);
        return;
      }

      if (result.design_operations.length) {
        applyDesignPlanLocally({
          selection: 'current',
          operations: result.design_operations as never,
        });
      }

      const noteLines = [...result.notes];
      if (result.recommendations?.length) {
        noteLines.push('Suggestions: ' + result.recommendations.join(' · '));
      }
      setHistory((h) => [
        ...h,
        {
          role: 'agent',
          text: noteLines.join(' • ') || `${result.invoked_agents.join(' → ')} complete`,
          response: result,
          ts: Date.now(),
        },
      ]);

      if (result.execution_invocations.length) {
        setSyncStage('execution', `Running ${result.execution_invocations.length} tool(s)`);
        const apply = await applyDesignActions({
          scene_graph: sceneGraph,
          selection: {
            ...selection,
            metadata: (selection.metadata ?? {}) as never,
          },
          operations: result.design_operations as never,
          material_options: useEditorStore.getState().materialOptions,
          include_base: includeBase,
          include_roof: includeRoof,
        });
        const paths: string[] = apply.export_paths || [];
        const glb = paths.find((p) => p.endsWith('.glb'));
        if (glb) {
          const filename = glb.split('\\').pop()?.split('/').pop();
          setGlbUrl(`http://localhost:8000/output/${filename}?t=${Date.now()}`);
          bumpGlbVersion();
        }
        setSyncStatus(apply.status === 'success' ? 'synced' : 'error', apply.detail);
        setSyncStage(null, null);
      } else {
        setSyncStatus('idle');
        setSyncStage(null, null);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      setSyncStatus('error', msg);
    } finally {
      setLoading(false);
    }
  };

  const activeProvider = providers.find((p) => p.available);

  return (
    <div className="flex flex-col gap-3 border-t border-gray-300 bg-white p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-800">Multi-Agent Design</h3>
        <span className="text-[10px] uppercase tracking-wide text-gray-500">
          orchestrator · design · geometry · execution
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-[10px] text-gray-600">
        <label className="flex items-center gap-1">
          <input
            type="checkbox"
            checked={includeImage}
            onChange={(e) => setIncludeImage(e.target.checked)}
          />
          include viewport image
        </label>
        <label className="flex items-center gap-1">
          provider
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="rounded border border-gray-300 bg-white px-1 py-0.5 text-[10px]"
          >
            <option value="">{activeProvider ? `auto (${activeProvider.name})` : 'auto (rules only)'}</option>
            {providers.map((p) => (
              <option key={p.name} value={p.name} disabled={!p.available}>
                {p.name}{p.available ? '' : ' (no key)'}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="max-h-40 space-y-1 overflow-y-auto rounded border border-gray-200 bg-gray-50 p-2 text-xs">
        {history.length === 0 && (
          <p className="text-gray-500">No conversation yet. Try: "Make this wall sage with stacked coils."</p>
        )}
        {history.map((turn, idx) => (
          <div
            key={idx}
            className={`rounded px-2 py-1 ${
              turn.role === 'user' ? 'bg-indigo-100 text-indigo-900' : 'bg-white text-gray-800'
            }`}
          >
            <div className="text-[10px] uppercase opacity-70">{turn.role}</div>
            <div>{turn.text}</div>
            {turn.response && (
              <details className="mt-1 text-[10px] text-gray-500">
                <summary className="cursor-pointer">Why?</summary>
                <div className="mt-1 space-y-1">
                  <div>intent: <code>{turn.response.explain?.intent}</code></div>
                  <div>agents: {turn.response.invoked_agents.join(' → ')}</div>
                  <div>expected: {turn.response.explain?.expected_result}</div>
                  {turn.response.recommendations?.length ? (
                    <div>suggestions: {turn.response.recommendations.join(' · ')}</div>
                  ) : null}
                  {turn.response.rule_report?.violations?.length ? (
                    <div>
                      rule warnings: {turn.response.rule_report.violations.length}
                    </div>
                  ) : null}
                </div>
              </details>
            )}
          </div>
        ))}
      </div>

      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder='e.g. "Curve this entrance by 0.5m and apply sage stacked coils"'
        rows={2}
        className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
        disabled={!selection}
      />
      <button
        type="button"
        onClick={sendPrompt}
        disabled={loading || !selection || !prompt.trim()}
        className="w-full rounded bg-violet-600 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50"
      >
        {loading ? 'Orchestrating…' : 'Send to agents'}
      </button>
      {!selection && <p className="text-xs text-amber-600">Select a region first.</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}

      {trace.length > 0 && (
        <details className="rounded border border-gray-200 bg-gray-50 px-2 py-1 text-[10px] text-gray-700">
          <summary className="cursor-pointer text-[11px] font-medium text-gray-700">
            Recent agent trace ({trace.length})
          </summary>
          <div className="mt-1 max-h-32 overflow-y-auto space-y-0.5 font-mono">
            {trace.slice(-12).map((entry) => (
              <div key={entry.id}>{formatTrace(entry)}</div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
};