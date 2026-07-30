import React, { useEffect, useState } from 'react';
import { useEditorStore } from '../../store/editorStore';
import { PATTERN_LIBRARY, MATERIAL_PRESETS, shadeHex } from '../../lib/patterns';
import { applyDesignActions, openDesignStream } from '../../api/client';

export const EditingPanel: React.FC = () => {
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

  if (!selection) {
    return (
      <div className="flex h-full w-80 flex-col border-l border-gray-300 bg-gray-50">
        <div className="border-b border-gray-300 p-4">
          <h2 className="text-lg font-bold text-gray-900">Region Editor</h2>
        </div>
        <div className="flex flex-1 items-center justify-center p-6">
          <p className="text-center text-sm text-gray-500">
            Click, brush, box- or lasso-select geometry in the 3D viewport to edit materials.
          </p>
        </div>
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

    try {
      const result = await applyDesignActions({
        scene_graph: sceneGraph,
        selection,
        operations,
        material_options: useEditorStore.getState().materialOptions,
        include_base: includeBase,
        include_roof: includeRoof,
      });

      if (result.status !== 'success') {
        throw new Error(result.detail || 'Sync failed');
      }

      const paths: string[] = result.export_paths || [];
      const glbPath = paths.find((p) => p.endsWith('.glb'));
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
      setApplying(false);
    }
  };

  return (
    <div className="flex h-full w-80 flex-col border-l border-gray-300 bg-gray-50">
      <div className="border-b border-gray-300 p-4">
        <h2 className="text-lg font-bold text-gray-900">Region Editor</h2>
        <input
          type="text"
          value={selection.name ?? ''}
          placeholder={`Region ${selection.id.slice(-5)}`}
          onChange={(e) => renameSelection(selection.id, e.target.value)}
          className="mt-2 w-full rounded border border-gray-300 px-2 py-1 text-xs"
        />
        <p className="mt-1 text-xs text-gray-500">
          {selection.faceRefs.length} faces · {selection.meshRefs.length} meshes
        </p>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto p-4">
        <section>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-700">Color</h3>
          <div className="flex items-center gap-3">
            <input
              type="color"
              value={color}
              onChange={(e) => {
                updateSelectionMetadata(selection.id, { color: e.target.value });
              }}
              className="h-10 w-14 cursor-pointer rounded border border-gray-300"
            />
            <input
              type="text"
              value={color.toUpperCase()}
              onChange={(e) => updateSelectionMetadata(selection.id, { color: e.target.value })}
              className="flex-1 rounded border border-gray-300 px-2 py-1.5 font-mono text-sm"
            />
          </div>
          <button
            type="button"
            disabled={applying}
            onClick={() => syncEdit([{ type: 'set_color', value: color }])}
            className="mt-2 w-full rounded bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            Apply color
          </button>
        </section>

        <section>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-700">Pattern</h3>
          <div className="grid grid-cols-2 gap-2">
            {PATTERN_LIBRARY.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => updateSelectionMetadata(selection.id, { pattern: p.id })}
                className={`overflow-hidden rounded-lg border-2 p-2 text-left transition ${
                  pattern === p.id ? 'border-indigo-600 ring-2 ring-indigo-100' : 'border-gray-200'
                }`}
              >
                <div
                  className="mb-1 h-12 rounded border border-black/10"
                  style={p.previewStyle(color, ridge)}
                />
                <span className="text-xs font-medium text-gray-800">{p.name}</span>
              </button>
            ))}
          </div>
          <button
            type="button"
            disabled={applying}
            onClick={() => syncEdit([{ type: 'apply_pattern', pattern }])}
            className="mt-2 w-full rounded bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            Apply pattern
          </button>
        </section>

        <section>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-700">Material preset</h3>
          <div className="space-y-1">
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
                className="flex w-full items-center gap-2 rounded border border-gray-200 bg-white px-2 py-2 text-left hover:border-indigo-300"
              >
                <span
                  className="h-6 w-6 shrink-0 rounded border border-black/10"
                  style={{ backgroundColor: preset.color }}
                />
                <span className="text-sm text-gray-800">{preset.name}</span>
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
            className="mt-2 w-full rounded bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            Apply preset & sync
          </button>
        </section>

        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </div>
  );
};
