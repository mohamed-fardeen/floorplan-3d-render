import React from 'react';
import { useEditorStore } from '../../store/editorStore';
import type { SelectionTool } from '../../types/selection';

const TOOLS: { id: SelectionTool; label: string; hint: string }[] = [
  { id: 'click', label: 'Click', hint: 'Select faces under cursor' },
  { id: 'brush', label: 'Brush', hint: 'Paint-select region' },
  { id: 'box', label: 'Box', hint: 'Drag rectangle to select' },
];

export const SelectionToolbar: React.FC = () => {
  const {
    selectionTool,
    setSelectionTool,
    brushRadius,
    setBrushRadius,
    clearSelections,
    selections,
    activeSelectionId,
    setActiveSelection,
  } = useEditorStore();

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
            <span className="text-xs font-medium text-gray-600">Saved regions</span>
            <button
              type="button"
              onClick={clearSelections}
              className="text-xs text-red-600 hover:underline"
            >
              Clear all
            </button>
          </div>
          {selections.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setActiveSelection(s.id)}
              className={`w-full rounded px-2 py-1 text-left text-xs ${
                s.id === activeSelectionId ? 'bg-indigo-100 text-indigo-900' : 'bg-white text-gray-700'
              }`}
            >
              {s.faceRefs.length} faces · {s.meshRefs.map((m) => m.objectName).slice(0, 2).join(', ')}
            </button>
          ))}
        </div>
      )}

      <p className="text-[10px] leading-snug text-gray-500">
        Right-drag to orbit · Scroll to zoom · Middle-drag to pan
      </p>
    </div>
  );
};
