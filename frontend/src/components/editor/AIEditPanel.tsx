import React, { useState } from 'react';
import { useEditorStore } from '../../store/editorStore';
import { planDesignFromPrompt, applyDesignActions } from '../../api/client';

export const AIEditPanel: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [lastPlan, setLastPlan] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const {
    getActiveSelection,
    sceneGraph,
    includeBase,
    includeRoof,
    applyDesignPlanLocally,
    setSyncStatus,
    bumpGlbVersion,
    setGlbUrl,
  } = useEditorStore();

  const runAIEdit = async () => {
    const selection = getActiveSelection();
    if (!sceneGraph || !selection || !prompt.trim()) return;

    setLoading(true);
    setError(null);
    setSyncStatus('syncing');

    try {
      const planResult = await planDesignFromPrompt({
        prompt: prompt.trim(),
        selection_summary: {
          face_count: selection.faceRefs.length,
          mesh_names: selection.meshRefs.map((m) => m.objectName),
          current_metadata: selection.metadata,
        },
      });

      if (planResult.status !== 'success' || !planResult.plan) {
        throw new Error(planResult.detail || 'AI planning failed');
      }

      setLastPlan(JSON.stringify(planResult.plan, null, 2));
      applyDesignPlanLocally(planResult.plan);

      const applyResult = await applyDesignActions({
        scene_graph: sceneGraph,
        selection,
        operations: planResult.plan.operations,
        material_options: useEditorStore.getState().materialOptions,
        include_base: includeBase,
        include_roof: includeRoof,
      });

      if (applyResult.status !== 'success') {
        throw new Error(applyResult.detail || 'Blender sync failed');
      }

      const glbPath = (applyResult.export_paths || []).find((p: string) => p.endsWith('.glb'));
      if (glbPath) {
        const filename = glbPath.split('\\').pop()?.split('/').pop();
        setGlbUrl(`http://localhost:8000/output/${filename}?t=${Date.now()}`);
        bumpGlbVersion();
      }
      setSyncStatus('synced');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      setSyncStatus('error', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="border-t border-gray-300 bg-white p-4">
      <h3 className="mb-2 text-sm font-semibold text-gray-800">AI Design Assistant</h3>
      <p className="mb-2 text-xs text-gray-500">
        Describes changes as structured actions — never raw Blender Python.
      </p>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder='e.g. "Make this region white with stacked coils"'
        rows={3}
        className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
      />
      <button
        type="button"
        onClick={runAIEdit}
        disabled={loading || !getActiveSelection()}
        className="mt-2 w-full rounded bg-violet-600 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50"
      >
        {loading ? 'Planning & syncing…' : 'Apply AI edit'}
      </button>
      {!getActiveSelection() && (
        <p className="mt-2 text-xs text-amber-600">Select a region first.</p>
      )}
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
      {lastPlan && (
        <pre className="mt-3 max-h-32 overflow-auto rounded bg-gray-100 p-2 text-[10px] text-gray-700">
          {lastPlan}
        </pre>
      )}
    </div>
  );
};
