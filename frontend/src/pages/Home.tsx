import React, { useState } from 'react';
import { UploadArea } from '../components/UploadArea';
import { ProgressTracker } from '../components/ProgressTracker';
import type { PipelineStage } from '../components/ProgressTracker';
import { SceneSummary } from '../components/SceneSummary';
import { ModelViewer } from '../components/ModelViewer';
import { DownloadPanel } from '../components/DownloadPanel';
import { AnnotatedFloorplan } from '../components/AnnotatedFloorplan';
import { uploadAndParse, exportBlender } from '../api/client';
import type { SceneGraph } from '../types/schema';
import { AnnotationPage } from './AnnotationPage';
import { useAnnotationStore } from '../store/annotationStore';

interface HomeProps {
  onOpenEditor: (sceneGraph: SceneGraph) => void;
}

export const Home: React.FC<HomeProps> = ({ onOpenEditor }) => {
  const [stage, setStage] = useState<PipelineStage>('idle');
  const [error, setError] = useState<string | undefined>();
  const [sceneGraph, setSceneGraph] = useState<any>(null);
  const [parserConfidence, setParserConfidence] = useState<number>(0);
  const [validationReport, setValidationReport] = useState<string[]>([]);
  const [glbUrl, setGlbUrl] = useState<string | undefined>();
  const [blendUrl, setBlendUrl] = useState<string | undefined>();
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  
  const [includeBase, setIncludeBase] = useState(true);
  const [includeRoof, setIncludeRoof] = useState(false);
  const { setAnnotationData } = useAnnotationStore();

  const startPipeline = async (file: File) => {
    setStage('parsing'); // Since backend upload handles parse, val, ocr, SG synchronously
    setError(undefined);
    setSceneGraph(null);
    setGlbUrl(undefined);
    setBlendUrl(undefined);
    const objectUrl = URL.createObjectURL(file);
    setImageUrl(objectUrl);

    try {
      // 1. Upload & Parse
      const uploadResult = await uploadAndParse(file);
      if (uploadResult.status !== 'success') {
        throw new Error(uploadResult.detail || 'Failed to upload and parse image.');
      }

      const graph = uploadResult.scene_graph;
      setSceneGraph(graph);
      setParserConfidence(uploadResult.parser_confidence || 0);
      setValidationReport(uploadResult.validation_report || []);

      // Go to annotation review
      setAnnotationData(graph, objectUrl);
      setStage('annotating');

    } catch (err: any) {
      console.error(err);
      setStage('error');
      setError(err.message || String(err));
    }
  };

  const handleApprove = async (editedGraph: SceneGraph) => {
    setStage('blender');
    setSceneGraph(editedGraph);
    try {
      const exportResult = await exportBlender(editedGraph, includeBase, includeRoof);
      
      if (exportResult.status !== 'success') {
        throw new Error(exportResult.detail || 'Failed to export 3D model.');
      }

      const paths: string[] = exportResult.export_paths || [];
      const glbPath = paths.find(p => p.endsWith('.glb'));
      const blendPath = paths.find(p => p.endsWith('.blend'));

      if (glbPath) {
        const filename = glbPath.split('\\').pop()?.split('/').pop();
        setGlbUrl(`http://localhost:8000/output/${filename}`);
      }
      
      if (blendPath) {
        const filename = blendPath.split('\\').pop()?.split('/').pop();
        setBlendUrl(`http://localhost:8000/output/${filename}`);
      }

      setStage('complete');
    } catch (err: any) {
      console.error(err);
      setStage('error');
      setError(err.message || String(err));
    }
  };

  if (stage === 'annotating') {
    return (
      <AnnotationPage 
        onApprove={handleApprove}
        onBack={() => setStage('idle')}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-4xl mx-auto mb-10 text-center">
        <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight sm:text-5xl">
          Floor Plan to 3D Pipeline
        </h1>
        <p className="mt-4 max-w-2xl text-xl text-gray-500 mx-auto">
          Upload a 2D floor plan to test the end-to-end AI workflow generating a full 3D model.
        </p>
      </div>

      <div className="max-w-4xl mx-auto mb-6 flex justify-center gap-6 text-gray-700">
        <label className="flex items-center gap-2 cursor-pointer">
          <input 
            type="checkbox" 
            checked={includeBase} 
            onChange={(e) => setIncludeBase(e.target.checked)} 
            className="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500"
          />
          <span className="font-medium">Floor</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input 
            type="checkbox" 
            checked={includeRoof} 
            onChange={(e) => setIncludeRoof(e.target.checked)} 
            className="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500"
          />
          <span className="font-medium">Ceiling</span>
        </label>
      </div>

      <UploadArea onStartPipeline={startPipeline} disabled={stage !== 'idle' && stage !== 'complete' && stage !== 'error'} />
      
      {stage !== 'idle' && <ProgressTracker currentStage={stage} error={error} />}

      {sceneGraph && (
        <>
          <SceneSummary 
            sceneGraph={sceneGraph} 
            parserConfidence={parserConfidence} 
            validationReport={validationReport}
          />
          {imageUrl && <AnnotatedFloorplan imageUrl={imageUrl} sceneGraph={sceneGraph} />}
        </>
      )}

      {glbUrl && stage === 'complete' && <ModelViewer glbUrl={glbUrl} />}

      {sceneGraph && stage === 'complete' && (
        <div className="w-full max-w-2xl mx-auto mt-4 flex flex-col gap-3">
          <button
            onClick={() => onOpenEditor(sceneGraph)}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white text-lg font-semibold py-3 px-6 rounded-lg shadow-md transition-colors flex items-center justify-center gap-2"
          >
            Open in Floor Plan Editor →
          </button>
          
          <button
            onClick={() => exportBlender(sceneGraph, includeBase, includeRoof)}
            className="w-full bg-orange-500 hover:bg-orange-600 text-white text-lg font-semibold py-3 px-6 rounded-lg shadow-md transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
            Open in Blender
          </button>
        </div>
      )}

      {sceneGraph && stage === 'complete' && (
        <DownloadPanel 
          sceneGraph={sceneGraph} 
          glbUrl={glbUrl} 
          blendUrl={blendUrl} 
        />
      )}
    </div>
  );
};
