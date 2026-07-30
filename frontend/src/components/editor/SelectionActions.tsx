import React, { useState } from 'react';
import { useEditorStore } from '../../store/editorStore';

interface SelectionActionsProps {
  onGrow: () => void;
  onShrink: () => void;
  onInvert: () => void;
  onConnected: () => void;
  onExpandToMesh: () => void;
}

export const SelectionActions: React.FC<SelectionActionsProps> = ({
  onGrow,
  onShrink,
  onInvert,
  onConnected,
  onExpandToMesh,
}) => {
  const { getActiveSelection, saveSelectionAsNamed, recallNamedSelection, namedSelections } =
    useEditorStore();
  const active = getActiveSelection();
  const [name, setName] = useState('');

  return (
    <div className="border-b border-gray-300 p-4">
      <h3 className="text-sm font-semibold text-gray-800">Selection actions</h3>
      <p className="mb-2 text-[11px] text-gray-500">
        Geometry-agnostic transforms on the active region.
      </p>
      <div className="grid grid-cols-2 gap-1">
        <button
          type="button"
          disabled={!active}
          onClick={onGrow}
          className="rounded bg-gray-200 px-2 py-1 text-xs hover:bg-gray-300 disabled:opacity-40"
        >
          Grow
        </button>
        <button
          type="button"
          disabled={!active}
          onClick={onShrink}
          className="rounded bg-gray-200 px-2 py-1 text-xs hover:bg-gray-300 disabled:opacity-40"
        >
          Shrink
        </button>
        <button
          type="button"
          disabled={!active}
          onClick={onConnected}
          className="rounded bg-gray-200 px-2 py-1 text-xs hover:bg-gray-300 disabled:opacity-40"
        >
          Connected
        </button>
        <button
          type="button"
          disabled={!active}
          onClick={onInvert}
          className="rounded bg-gray-200 px-2 py-1 text-xs hover:bg-gray-300 disabled:opacity-40"
        >
          Invert
        </button>
        <button
          type="button"
          disabled={!active}
          onClick={onExpandToMesh}
          className="col-span-2 rounded bg-gray-200 px-2 py-1 text-xs hover:bg-gray-300 disabled:opacity-40"
        >
          Expand to mesh faces
        </button>
      </div>

      <div className="mt-3 flex gap-1">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Selection name"
          className="flex-1 rounded border border-gray-300 px-2 py-1 text-xs"
        />
        <button
          type="button"
          disabled={!active || !name.trim()}
          onClick={() => {
            if (!active) return;
            saveSelectionAsNamed(active.id, name.trim());
            setName('');
          }}
          className="rounded bg-indigo-600 px-2 py-1 text-xs text-white hover:bg-indigo-700 disabled:opacity-40"
        >
          Save
        </button>
      </div>

      {Object.keys(namedSelections).length > 0 && (
        <div className="mt-2 space-y-1">
          <span className="text-[10px] font-medium uppercase tracking-wide text-gray-500">
            Named selections
          </span>
          {Object.entries(namedSelections).map(([n]) => (
            <button
              key={n}
              type="button"
              onClick={() => recallNamedSelection(n)}
              className="flex w-full items-center justify-between rounded border border-gray-200 bg-white px-2 py-1 text-xs hover:border-indigo-300"
            >
              <span>{n}</span>
              <span className="text-[10px] text-gray-400">recall</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};