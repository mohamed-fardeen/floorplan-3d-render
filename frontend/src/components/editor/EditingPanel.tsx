import React, { useEffect, useState } from 'react';
import { useEditorStore } from '../../store/editorStore';
import { PATTERN_LIBRARY, MATERIAL_PRESETS, shadeHex } from '../../lib/patterns';
import { applyDesignActions, exportBlender, openDesignStream } from '../../api/client';
import { MetricsPanel } from './MetricsPanel';
import { AIEditPanel } from './AIEditPanel';
import { CollapsibleSection } from '../ui/CollapsibleSection';
import * as THREE from 'three';

interface EditingPanelProps {
  glbRoot?: THREE.Group | null;
  viewportScreenshot?: () => string | null;
}

type Tab = 'design' | 'preset' | 'pattern' | 'ai';

export const EditingPanel: React.FC<EditingPanelProps> = ({ glbRoot = null, viewportScreenshot }) => {
  const {
    getActiveSelection,
    updateSelectionMetadata,
    materialOptions,
    setMaterialOptions,
    sceneGraph,
    includeBase,
    includeRoof,
    setSyncStatus,
    setSyncStage,
    bumpGlbVersion,
    setGlbUrl,
    applyDesignPlanLocally,
  } = useEditorStore();
  const renameSelection = useEditorStore((s) => s.renameSelection);

  useEffect(() => {
    const { close } = openDesignStream((event) => {
      setSyncStage(event.stage ?? null, event.message ?? null);
      if (event.stage === 'done' || event.stage === 'error') {
        setSyncStage(null, null);
      }
    });
    return close;
  }, [setSyncStage]);

  const selection = getActiveSelection();
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('design');

  if (!selection) {
    return (
      <div className="flex h-full w-80 flex-col border-l border-gray-200 bg-white">
        <div className="border-b border-gray-200 px-4 py-3">
          <h2 className="text-base font-semibold text-gray-900">Region Editor</h2>
          <p className="mt-0.5 text-xs text-gray-500">
            No selection — pick a region in the 3D viewport.
          </p>
        </div>
        <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-gray-500">
          Use the tools in the left sidebar (Click / Brush / Box / Lasso) to
          pick faces, then come back here to edit materials.
        </div>
        <CollapsibleSection title="AI Assistant" defaultOpen>
          <AIEditPanel glbRoot={glbRoot} viewportScreenshot={viewportScreenshot} />
        </CollapsibleSection>
      </div>
    );
  }

  const color = selection.metadata.color ?? materialOptions.walls.color;
  const pattern = selection.metadata.pattern ?? materialOptions.walls.pattern;
  const ridge = shadeHex(color, 0.72);

  const syncEdit = async (operations: Parameters<typeof applyDesignActions>[0]['operations']) => {
    if (!sceneGraph) return;
    setApplying(true);
    setError(null);
    setSyncStatus('syncing');

    const plan = { selection: selection.id, operations };
    applyDesignPlanLocally(plan);

    const collectGlb = async (paths: string[] | undefined) => {
      const glbPath = (paths || []).find((p) => p.endsWith('.glb'));
      if (!glbPath) return false;
      const filename = glbPath.split('\\').pop()?.split('/').pop();
      setGlbUrl(`http://localhost:8000/output/${filename}?t=${Date.now()}`);
      bumpGlbVersion();
      return true;
    };

    try {
      const controller = new AbortController();
      const timer = window.setTimeout(() => controller.abort(), 120_000);
      let result: Awaited<ReturnType<typeof applyDesignActions>>;
      try {
        result = await applyDesignActions({
          scene_graph: sceneGraph,
          selection: {
            ...selection,
            metadata: (selection.metadata ?? {}) as never,
          },
          operations,
          material_options: useEditorStore.getState().materialOptions,
          include_base: includeBase,
          include_roof: includeRoof,
        });
      } finally {
        window.clearTimeout(timer);
      }

      if (result.status !== 'success') {
        throw new Error(result.detail || 'Sync failed');
      }

      let gotGlb = await collectGlb(result.export_paths);

      // Fallback: if design/apply didn't return a GLB (e.g. the backend
      // couldn't find Blender), run the full export pipeline so the
      // browser at least hot-reloads.
      if (!gotGlb) {
        const fallback = await exportBlender(
          sceneGraph,
          includeBase,
          includeRoof,
          useEditorStore.getState().materialOptions,
          false,
        );
        if (fallback.status === 'success') {
          gotGlb = await collectGlb(fallback.export_paths);
        }
      }

      setSyncStatus(gotGlb ? 'synced' : 'error', gotGlb ? undefined : 'No GLB produced');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      setSyncStatus('error', msg);
    } finally {
      setApplying(false);
    }
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: 'design', label: 'Color' },
    { id: 'preset', label: 'Preset' },
    { id: 'pattern', label: 'Pattern' },
    { id: 'ai', label: 'AI' },
  ];

  return (
    <div className="flex h-full w-80 flex-col border-l border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">Region Editor</h2>
          <span className="rounded bg-indigo-100 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700">
            active
          </span>
        </div>
        <input
          type="text"
          value={selection.name ?? ''}
          placeholder={`Region ${selection.id.slice(-5)}`}
          onChange={(e) => renameSelection(selection.id, e.target.value)}
          className="mt-2 w-full rounded border border-gray-200 bg-white px-2 py-1 text-xs"
        />
        <div className="mt-1.5 flex items-center gap-2 text-[10px] text-gray-500">
          <span>{selection.faceRefs.length} faces</span>
          <span>·</span>
          <span>{selection.meshRefs.length} meshes</span>
        </div>
      </div>

      <CollapsibleSection title="Metrics">
        <MetricsPanel glbRoot={glbRoot} />
      </CollapsibleSection>

      <div className="border-b border-gray-200 px-4 py-2">
        <div className="flex gap-1 rounded bg-gray-100 p-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`flex-1 rounded px-2 py-1 text-xs font-medium ${
                tab === t.id
                  ? 'bg-white text-indigo-700 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-3">
        {tab === 'design' && (
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-600">
              Color
            </h3>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={color}
                onChange={(e) => updateSelectionMetadata(selection.id, { color: e.target.value })}
                className="h-9 w-12 cursor-pointer rounded border border-gray-200"
              />
              <input
                type="text"
                value={color.toUpperCase()}
                onChange={(e) => updateSelectionMetadata(selection.id, { color: e.target.value })}
                className="flex-1 rounded border border-gray-200 px-2 py-1.5 font-mono text-sm"
              />
            </div>
            <button
              type="button"
              disabled={applying}
              onClick={() => syncEdit([{ type: 'set_color', value: color }])}
              className="mt-2 w-full rounded bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-40"
            >
              {applying ? 'Syncing…' : 'Apply color'}
            </button>
          </section>
        )}

        {tab === 'preset' && (
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-600">
              Material preset
            </h3>
            <div className="grid grid-cols-1 gap-1">
              {MATERIAL_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => {
                    updateSelectionMetadata(selection.id, {
                      materialPreset: preset.id,
                      color: preset.color,
                      pattern: preset.pattern,
                    });
                    setMaterialOptions({
                      ...materialOptions,
                      walls: {
                        ...materialOptions.walls,
                        theme: preset.id,
                        color: preset.color,
                        pattern: preset.pattern,
                      },
                    });
                  }}
                  className="flex w-full items-center gap-2 rounded border border-gray-200 bg-white px-2 py-1.5 text-left hover:border-indigo-300"
                >
                  <span
                    className="h-5 w-5 shrink-0 rounded border border-black/10"
                    style={{ backgroundColor: preset.color }}
                  />
                  <span className="flex-1 text-xs text-gray-800">{preset.name}</span>
                  <span className="text-[10px] uppercase text-gray-400">{preset.pattern}</span>
                </button>
              ))}
            </div>
            <button
              type="button"
              disabled={applying}
              onClick={() =>
                syncEdit([
                  { type: 'set_material_preset', preset: selection.metadata.materialPreset ?? 'warm_modern' },
                  { type: 'set_color', value: color },
                  { type: 'apply_pattern', pattern },
                ])
              }
              className="mt-2 w-full rounded bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-40"
            >
              {applying ? 'Syncing…' : 'Apply preset & sync'}
            </button>
          </section>
        )}

        {tab === 'pattern' && (
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-600">
              Pattern
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {PATTERN_LIBRARY.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => updateSelectionMetadata(selection.id, { pattern: p.id })}
                  className={`overflow-hidden rounded-lg border p-1.5 text-left transition ${
                    pattern === p.id
                      ? 'border-indigo-500 ring-2 ring-indigo-100'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div
                    className="mb-1 h-10 rounded border border-black/10"
                    style={p.previewStyle(color, ridge)}
                  />
                  <span className="text-[11px] font-medium text-gray-800">{p.name}</span>
                </button>
              ))}
            </div>
            <button
              type="button"
              disabled={applying}
              onClick={() => syncEdit([{ type: 'apply_pattern', pattern }])}
              className="mt-2 w-full rounded bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-40"
            >
              {applying ? 'Syncing…' : 'Apply pattern'}
            </button>
            <p className="mt-2 text-[10px] leading-snug text-gray-500">
              Pattern preview shows on the 3D viewport as a normal-map overlay.
              The Blender export uses the real shader (stacked_coils /
              woven_rope). Browser-only patterns (ribbed, brick, wave, honeycomb)
              fall back to stacked_coils in Blender.
            </p>
          </section>
        )}

        {tab === 'ai' && (
          <section>
            <AIEditPanel glbRoot={glbRoot} viewportScreenshot={viewportScreenshot} />
          </section>
        )}

        {error && <p className="text-xs text-red-600">{error}</p>}
      </div>
    </div>
  );
};