import React from 'react';

interface SceneSummaryProps {
  sceneGraph: any;
  parserConfidence: number;
  validationReport?: string[];
}

export const SceneSummary: React.FC<SceneSummaryProps> = ({ sceneGraph, parserConfidence, validationReport }) => {
  if (!sceneGraph) return null;

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-md mt-6">
      <h3 className="text-xl font-bold mb-4">Scene Graph Summary</h3>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-50 p-4 rounded-lg text-center border border-gray-200">
          <div className="text-3xl font-bold text-indigo-600">{sceneGraph.rooms?.length || 0}</div>
          <div className="text-sm text-gray-500 uppercase tracking-wide mt-1">Rooms</div>
        </div>
        <div className="bg-gray-50 p-4 rounded-lg text-center border border-gray-200">
          <div className="text-3xl font-bold text-indigo-600">{sceneGraph.walls?.length || 0}</div>
          <div className="text-sm text-gray-500 uppercase tracking-wide mt-1">Walls</div>
        </div>
        <div className="bg-gray-50 p-4 rounded-lg text-center border border-gray-200">
          <div className="text-3xl font-bold text-indigo-600">{sceneGraph.doors?.length || 0}</div>
          <div className="text-sm text-gray-500 uppercase tracking-wide mt-1">Doors</div>
        </div>
        <div className="bg-gray-50 p-4 rounded-lg text-center border border-gray-200">
          <div className="text-3xl font-bold text-indigo-600">{sceneGraph.windows?.length || 0}</div>
          <div className="text-sm text-gray-500 uppercase tracking-wide mt-1">Windows</div>
        </div>
      </div>

      <div className="mb-4">
        <h4 className="font-semibold text-gray-700">Parser Confidence</h4>
        <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
          <div 
            className={`h-2.5 rounded-full ${parserConfidence > 0.8 ? 'bg-green-500' : parserConfidence > 0.5 ? 'bg-yellow-500' : 'bg-red-500'}`} 
            style={{ width: `${(parserConfidence * 100).toFixed(0)}%` }}
          ></div>
        </div>
        <p className="text-xs text-gray-500 mt-1">{(parserConfidence * 100).toFixed(1)}%</p>
      </div>

      {validationReport && validationReport.length > 0 && (
        <div className="mt-4">
          <h4 className="font-semibold text-gray-700 mb-2">Validation Report</h4>
          <ul className="list-disc pl-5 text-sm text-gray-600 space-y-1">
            {validationReport.map((msg, idx) => (
              <li key={idx}>{msg}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
