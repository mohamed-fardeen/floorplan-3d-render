import React from 'react';
import { useEditorStore } from '../../store/editorStore';

export const PropertiesPanel: React.FC = () => {
  const { selectedObjectId, selectedObjectType, sceneGraph } = useEditorStore();

  if (!selectedObjectId || !sceneGraph) {
    return (
      <div className="w-80 bg-gray-100 border-l border-gray-300 p-4 h-full">
        <p className="text-gray-500 text-sm">Select an object to edit its properties.</p>
      </div>
    );
  }

  return (
    <div className="w-80 bg-gray-100 border-l border-gray-300 flex flex-col h-full">
      <div className="p-4 border-b border-gray-300">
        <h2 className="text-lg font-bold capitalize">{selectedObjectType} Properties</h2>
      </div>
      <div className="p-4 flex-grow overflow-y-auto">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700">ID</label>
          <input type="text" readOnly value={selectedObjectId} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm bg-gray-50 p-2 text-sm" />
        </div>
        {/* Further properties based on type will go here */}
      </div>
    </div>
  );
};
