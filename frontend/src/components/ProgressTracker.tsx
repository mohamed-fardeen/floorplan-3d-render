import React from 'react';
import { CircleCheck, Circle, Loader } from 'lucide-react';

export type PipelineStage = 
  | 'idle' 
  | 'uploading' 
  | 'parsing' 
  | 'validating' 
  | 'ocr' 
  | 'scene_graph' 
  | 'annotating'
  | 'blender' 
  | 'complete' 
  | 'error';

interface ProgressTrackerProps {
  currentStage: PipelineStage;
  error?: string;
}

const STAGES = [
  { id: 'uploading', label: 'Upload Complete' },
  { id: 'parsing', label: 'Parser' },
  { id: 'validating', label: 'Geometry Validation' },
  { id: 'ocr', label: 'OCR' },
  { id: 'scene_graph', label: 'Scene Graph' },
  { id: 'annotating', label: 'Manual Review' },
  { id: 'blender', label: 'Blender Generation' },
  { id: 'complete', label: 'Export Complete' }
];

export const ProgressTracker: React.FC<ProgressTrackerProps> = ({ currentStage, error }) => {
  const getStageIndex = (stage: PipelineStage) => {
    if (stage === 'idle') return -1;
    if (stage === 'error') return STAGES.length; // Don't use index for error logic directly
    
    // In our synchronous backend:
    // When "blender" is running, all previous steps are done.
    // When "parsing" is running, it's actually doing parsing, validation, ocr, scene_graph simultaneously from the frontend's perspective.
    
    if (stage === 'uploading' || stage === 'parsing' || stage === 'validating' || stage === 'ocr' || stage === 'scene_graph') {
      // Simulate progress visually if we just know it's in the first phase
      return STAGES.findIndex(s => s.id === 'scene_graph');
    }
    
    if (stage === 'annotating') return STAGES.findIndex(s => s.id === 'annotating');
    if (stage === 'blender') return STAGES.findIndex(s => s.id === 'blender');
    if (stage === 'complete') return STAGES.length;
    return -1;
  };

  const currentIndex = getStageIndex(currentStage);

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-md mt-6">
      <h3 className="text-xl font-bold mb-6">Pipeline Progress</h3>
      
      <div className="space-y-4">
        {STAGES.map((stage, idx) => {
          let status: 'waiting' | 'loading' | 'done' = 'waiting';
          
          if (currentStage === 'error') {
            status = 'waiting'; // We'll show error separately
          } else if (currentStage === 'parsing' && idx <= STAGES.findIndex(s => s.id === 'scene_graph')) {
            // First phase is running
            status = 'loading'; 
          } else if (currentStage === 'annotating') {
            if (idx < STAGES.findIndex(s => s.id === 'annotating')) status = 'done';
            else if (idx === STAGES.findIndex(s => s.id === 'annotating')) status = 'loading';
          } else if (currentStage === 'blender') {
            if (idx < STAGES.findIndex(s => s.id === 'blender')) status = 'done';
            else if (idx === STAGES.findIndex(s => s.id === 'blender')) status = 'loading';
          } else if (currentStage === 'complete') {
            status = 'done';
          }

          return (
            <div key={stage.id} className="flex items-center gap-3">
              {status === 'done' ? (
                <CircleCheck className="w-6 h-6 text-green-500" />
              ) : status === 'loading' ? (
                <Loader className="w-6 h-6 text-blue-500 animate-spin" />
              ) : (
                <Circle className="w-6 h-6 text-gray-300" />
              )}
              <span className={`font-medium ${status === 'done' ? 'text-gray-900' : status === 'loading' ? 'text-blue-600' : 'text-gray-400'}`}>
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>

      {currentStage === 'error' && error && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-md">
          <h4 className="text-red-800 font-bold mb-2">Pipeline Failed</h4>
          <pre className="text-sm text-red-600 whitespace-pre-wrap font-mono overflow-x-auto">
            {error}
          </pre>
        </div>
      )}
    </div>
  );
};
