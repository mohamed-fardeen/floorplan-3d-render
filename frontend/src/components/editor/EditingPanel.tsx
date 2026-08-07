import React, { useState } from 'react';
import { useEditorStore } from '../../store/editorStore';
import { EDITOR_PATTERN_OPTIONS, MATERIAL_PRESETS, shadeHex } from '../../lib/patterns';
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
    applyDesignPlanLocally,
  } = useEditorStore();
  const renameSelection = useEditorStore((s) => s.renameSelection);

  const selection = getActiveSelection();
  const setWallColorOverride = useEditorStore((s) => s.setWallColorOverride);
  const [tab, setTab] = useState<Tab>('design');
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(null);
  const [appliedPreset, setAppliedPreset] = useState(false);
  const [appliedColor, setAppliedColor] = useState(false);
  const [appliedPattern, setAppliedPattern] = useState(false);

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

  const applyLocal = (operations: Parameters<typeof applyDesignPlanLocally>[0]['operations']) => {
    if (!selection) return;
    applyDesignPlanLocally({ selection: selection.id, operations });
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
              onClick={() => {
                applyLocal([{ type: 'set_color', value: color }]);
                for (const meshRef of selection.meshRefs) {
                  if (meshRef.objectName && meshRef.objectName.startsWith('Wall_')) {
                    setWallColorOverride(meshRef.objectName, { color });
                  }
                }
                setAppliedColor(true);
                setTimeout(() => setAppliedColor(false), 2000);
              }}
              className={`mt-2 w-full rounded py-2 text-sm font-medium transition-colors ${
                appliedColor
                  ? 'bg-green-600 text-white'
                  : 'bg-indigo-600 text-white hover:bg-indigo-700'
              }`}
            >
              {appliedColor ? '✓ Applied!' : 'Apply'}
            </button>
            <p className="mt-1.5 text-[10px] text-gray-500">
              Saved to the current session only.
            </p>
          </section>
        )}

        {tab === 'preset' && (
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-600">
              Material preset
            </h3>
            <div className="grid grid-cols-1 gap-1">
              {MATERIAL_PRESETS.map((preset) => {
                const isSelected = (selectedPresetId ?? selection.metadata.materialPreset) === preset.id;
                return (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => setSelectedPresetId(preset.id)}
                    className={`flex w-full items-center gap-2 rounded border px-2 py-1.5 text-left transition ${
                      isSelected
                        ? 'border-indigo-500 bg-indigo-50/50 ring-1 ring-indigo-500'
                        : 'border-gray-200 bg-white hover:border-indigo-300'
                    }`}
                  >
                    <span
                      className="h-5 w-5 shrink-0 rounded border border-black/10"
                      style={{ backgroundColor: preset.color }}
                    />
                    <span className="flex-1 text-xs text-gray-800">{preset.name}</span>
                    <span className="text-[10px] uppercase text-gray-400">{preset.pattern}</span>
                  </button>
                );
              })}
            </div>
            <button
              type="button"
              onClick={() => {
                const chosenId = selectedPresetId ?? selection.metadata.materialPreset ?? 'warm_modern';
                const preset = MATERIAL_PRESETS.find((p) => p.id === chosenId) ?? MATERIAL_PRESETS[0];
                
                updateSelectionMetadata(selection.id, {
                  materialPreset: preset.id,
                  color: preset.color,
                  pattern: preset.pattern,
                });

                applyLocal([
                  { type: 'set_material_preset', preset: preset.id },
                  { type: 'set_color', value: preset.color },
                  { type: 'apply_pattern', pattern: preset.pattern },
                ]);

                // Also update wallColorOverrides for all meshes in selection
                for (const meshRef of selection.meshRefs) {
                  if (meshRef.objectName && meshRef.objectName.startsWith('Wall_')) {
                    setWallColorOverride(meshRef.objectName, {
                      color: preset.color,
                      pattern: preset.pattern,
                    });
                  }
                }

                setAppliedPreset(true);
                setTimeout(() => setAppliedPreset(false), 2000);
              }}
              className={`mt-2 w-full rounded py-2 text-sm font-medium transition-colors ${
                appliedPreset
                  ? 'bg-green-600 text-white'
                  : 'bg-indigo-600 text-white hover:bg-indigo-700'
              }`}
            >
              {appliedPreset ? '✓ Applied!' : 'Apply preset'}
            </button>
            <p className="mt-1.5 text-[10px] text-gray-500">
              Saved to the current session only.
            </p>
          </section>
        )}

        {tab === 'pattern' && (
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-600">
              Pattern
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {EDITOR_PATTERN_OPTIONS.map((p) => (
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
              onClick={() => {
                applyLocal([{ type: 'apply_pattern', pattern }]);
                for (const meshRef of selection.meshRefs) {
                  if (meshRef.objectName && meshRef.objectName.startsWith('Wall_')) {
                    setWallColorOverride(meshRef.objectName, { pattern });
                  }
                }
                setAppliedPattern(true);
                setTimeout(() => setAppliedPattern(false), 2000);
              }}
              className={`mt-2 w-full rounded py-2 text-sm font-medium transition-colors ${
                appliedPattern
                  ? 'bg-green-600 text-white'
                  : 'bg-indigo-600 text-white hover:bg-indigo-700'
              }`}
            >
              {appliedPattern ? '✓ Applied!' : 'Apply pattern'}
            </button>
            <p className="mt-1.5 text-[10px] text-gray-500">
              Saved to the current session only.
            </p>
            <p className="mt-2 text-[10px] leading-snug text-gray-500">
              Pattern preview shows on the 3D viewport as a normal-map overlay.
              Browser-only patterns (ribbed, brick, wave, honeycomb) use the
              normal-map shader directly — no backend sync required.
            </p>
          </section>
        )}

        {tab === 'ai' && (
          <section>
            <AIEditPanel glbRoot={glbRoot} viewportScreenshot={viewportScreenshot} />
          </section>
        )}
      </div>
    </div>
  );
};
