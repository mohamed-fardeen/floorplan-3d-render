import React, { useState } from 'react';
import { useEditorStore } from '../../store/editorStore';
import type { SelectionTool } from '../../types/selection';

const TOOLS: { id: SelectionTool; label: string; hint: string }[] = [
  { id: 'click', label: 'Click', hint: 'Select faces under cursor' },
  { id: 'brush', label: 'Brush', hint: 'Paint-select region' },
  { id: 'box', label: 'Box', hint: 'Drag rectangle to select' },
  { id: 'lasso', label: 'Lasso', hint: 'Free-form polygon selection' },
];

export const SelectionToolbar: React.FC = () => {
  const {
    selectionTool,
    setSelectionTool,
    brushRadius,
    setBrushRadius,
    clearSelections,
    removeSelection,
    renameSelection,
    selections,
    activeSelectionId,
    setActiveSelection,
  } = useEditorStore();
  const [renamingId, setRenamingId] = useState<string | null>(null);

  return (
    <div className="flex flex-col gap-3 border-b border-gray-300 p-4">
      <h3 className="text-sm font-semibold text-gray-800">Selection</h3>
      <div className="flex gap-1">
        {TOOLS.map((tool) => (
          <button
            key={tool.id}
            type="button"
            title={tool.hint}
            onClick={() => setSelectionTool(tool.id)}
            className={`flex-1 rounded px-2 py-1.5 text-xs font-medium ${
              selectionTool === tool.id
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {tool.label}
          </button>
        ))}
      </div>

      {selectionTool === 'brush' && (
        <label className="text-xs text-gray-600">
          Brush radius ({brushRadius.toFixed(2)} m)
          <input
            type="range"
            min={0.05}
            max={0.5}
            step={0.01}
            value={brushRadius}
            onChange={(e) => setBrushRadius(parseFloat(e.target.value))}
            className="mt-1 w-full"
          />
        </label>
      )}

      {selections.length > 0 && (
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-600">Saved regions ({selections.length})</span>
            <button
              type="button"
              onClick={clearSelections}
              className="text-xs text-red-600 hover:underline"
            >
              Clear all
            </button>
          </div>
          {selections.map((s) => {
            const isActive = s.id === activeSelectionId;
            const label = s.name ?? `Region ${s.id.slice(-5)}`;
            return (
              <div
                key={s.id}
                className={`flex items-center gap-1 rounded border px-1.5 py-1 ${
                  isActive ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 bg-white'
                }`}
              >
                {renamingId === s.id ? (
                  <input
                    autoFocus
                    defaultValue={label}
                    onBlur={(e) => {
                      renameSelection(s.id, e.target.value);
                      setRenamingId(null);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        renameSelection(s.id, (e.target as HTMLInputElement).value);
                        setRenamingId(null);
                      }
                      if (e.key === 'Escape') setRenamingId(null);
                    }}
                    className="flex-1 rounded border border-indigo-300 px-1 py-0.5 text-xs"
                  />
                ) : (
                  <button
                    type="button"
                    onClick={() => setActiveSelection(s.id)}
                    onDoubleClick={() => setRenamingId(s.id)}
                    className={`flex-1 truncate text-left text-xs ${
                      isActive ? 'text-indigo-900' : 'text-gray-700'
                    }`}
                    title="Double-click to rename"
                  >
                    {label} · {s.faceRefs.length}f · {s.meshRefs.length}m
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => removeSelection(s.id)}
                  className="text-xs text-gray-400 hover:text-red-600"
                  title="Remove selection"
                >
                  ✕
                </button>
              </div>
            );
          })}
        </div>
      )}

      <p className="text-[10px] leading-snug text-gray-500">
        Right-drag to orbit · Scroll to zoom · Middle-drag to pan
      </p>
    </div>
  );
};