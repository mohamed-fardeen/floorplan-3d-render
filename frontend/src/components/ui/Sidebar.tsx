import React from 'react';
import { useEditorStore } from '../../store/editorStore';
import { validateGraph, exportBlender } from '../../api/client';
import { ArrowLeft } from 'lucide-react';

interface SidebarProps {
  onBackToHome: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onBackToHome }) => {
  const { undo, redo, historyIndex, history, sceneGraph, setSceneGraph } = useEditorStore();

  const handleValidate = async () => {
    if (!sceneGraph) return;
    try {
      const result = await validateGraph(sceneGraph);
      if (result.status === 'success') {
        setSceneGraph(result.scene_graph);
        alert('Validation complete. Graph updated.');
      }
    } catch (err) {
      console.error('Validation failed', err);
      alert('Validation failed.');
    }
  };

  const handleExport = async () => {
    if (!sceneGraph) return;
    try {
      const result = await exportBlender(sceneGraph);
      if (result.status === 'success') {
        alert(`Export complete! Paths: \n${result.export_paths.join('\n')}`);
      }
    } catch (err) {
      console.error('Export failed', err);
      alert('Export failed.');
    }
  };

  return (
    <div className="w-64 bg-gray-100 border-r border-gray-300 flex flex-col h-full overflow-y-auto">
      {/* Back button */}
      <div className="p-3 border-b border-gray-300">
        <button
          onClick={onBackToHome}
          className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-200 w-full px-3 py-2 rounded transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Pipeline
        </button>
      </div>

      <div className="p-4 border-b border-gray-300">
        <h2 className="text-lg font-bold">Floor Plan Editor</h2>
        {sceneGraph && (
          <p className="text-xs text-gray-500 mt-1">
            {sceneGraph.walls.length} walls · {sceneGraph.rooms.length} rooms
          </p>
        )}
      </div>

      <div className="p-4 border-b border-gray-300">
        <h3 className="text-md font-semibold mb-2">Tools</h3>
        <div className="flex flex-col gap-2">
          <button className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">Add Wall</button>
          <button className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">Add Room</button>
          <button className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">Add Door</button>
          <button className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">Add Window</button>
        </div>
      </div>

      <div className="p-4 border-b border-gray-300 flex justify-between">
        <button
          onClick={undo}
          disabled={historyIndex <= 0}
          className="bg-gray-300 px-3 py-1 rounded disabled:opacity-50"
        >Undo</button>
        <button
          onClick={redo}
          disabled={historyIndex >= history.length - 1}
          className="bg-gray-300 px-3 py-1 rounded disabled:opacity-50"
        >Redo</button>
      </div>

      <div className="p-4 flex flex-col gap-2 mt-auto">
        <button
          onClick={handleValidate}
          disabled={!sceneGraph}
          className="w-full bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600 disabled:opacity-50"
        >
          Validate Graph
        </button>
        <button
          onClick={handleExport}
          disabled={!sceneGraph}
          className="w-full bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 disabled:opacity-50"
        >
          Export to Blender
        </button>
      </div>
    </div>
  );
};
