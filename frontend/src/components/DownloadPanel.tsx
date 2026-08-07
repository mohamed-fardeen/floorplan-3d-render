import React from 'react';
import { FileText, Box } from 'lucide-react';

interface DownloadPanelProps {
  sceneGraph: any;
  glbUrl?: string;
}

export const DownloadPanel: React.FC<DownloadPanelProps> = ({ sceneGraph, glbUrl }) => {
  const downloadJson = () => {
    if (!sceneGraph) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(sceneGraph, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", "scene_graph.json");
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-md mt-6 mb-12">
      <h3 className="text-xl font-bold mb-4">Downloads</h3>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <button 
          onClick={downloadJson}
          className="flex items-center justify-center gap-2 bg-gray-100 hover:bg-gray-200 text-gray-800 font-semibold py-3 px-4 rounded border border-gray-300 transition-colors"
        >
          <FileText className="w-5 h-5" />
          <span>Scene Graph JSON</span>
        </button>
        
        <a 
          href={glbUrl}
          download
          className={`flex items-center justify-center gap-2 font-semibold py-3 px-4 rounded border transition-colors ${glbUrl ? 'bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border-indigo-200' : 'bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed pointer-events-none'}`}
        >
          <Box className="w-5 h-5" />
          <span>GLB Model</span>
        </a>
      </div>
    </div>
  );
};
