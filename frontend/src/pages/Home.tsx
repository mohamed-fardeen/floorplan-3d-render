import React, { useEffect, useState } from 'react';
import { UploadArea } from '../components/UploadArea';
import { ProgressTracker } from '../components/ProgressTracker';
import type { PipelineStage } from '../components/ProgressTracker';
import { SceneSummary } from '../components/SceneSummary';
import { ConstructionViewport } from '../components/viewport/ConstructionViewport';
import { DownloadPanel } from '../components/DownloadPanel';
import { AnnotatedFloorplan } from '../components/AnnotatedFloorplan';
import { uploadAndParse, exportBlender } from '../api/client';
import type { MaterialOptions } from '../api/client';
import type { SceneGraph } from '../types/schema';
import { AnnotationPage } from './AnnotationPage';
import { DesignOptions } from '../components/DesignOptions';
import { useAnnotationStore } from '../store/annotationStore';

const HOME_STATE_KEY = 'floorplan-3d-home-state';

interface PersistedHomeState {
  stage: PipelineStage;
  sceneGraph: SceneGraph | null;
  parserConfidence: number;
  validationReport: string[];
  glbUrl?: string;
  imageUrl: string | null;
  selectedModel: string;
  includeBase: boolean;
  includeRoof: boolean;
  materialOptions: MaterialOptions;
}

function readPersistedState(): PersistedHomeState | null {
  try {
    const raw = localStorage.getItem(HOME_STATE_KEY);
    return raw ? JSON.parse(raw) as PersistedHomeState : null;
  } catch {
    return null;
  }
}

interface HomeProps {
  onOpenEditor: (
    sceneGraph: SceneGraph,
    extras?: {
      glbUrl?: string;
      materialOptions?: MaterialOptions;
      includeBase?: boolean;
      includeRoof?: boolean;
    },
  ) => void;
}

function outputUrl(path: string | undefined): string | undefined {
  if (!path) return undefined;
  const filename = path.split('\\').pop()?.split('/').pop();
  return filename ? `http://localhost:8000/output/${filename}` : undefined;
}

function defaultOutputUrls(sceneGraph: SceneGraph) {
  const project = (sceneGraph.metadata.project_name || 'building').replace(/\s+/g, '_');
  return {
    glbUrl: `http://localhost:8000/output/${project}.glb`,
    blendUrl: `http://localhost:8000/output/${project}.blend`,
  };
}

export const Home: React.FC<HomeProps> = ({ onOpenEditor }) => {
  const [stage, setStage] = useState<PipelineStage>('idle');
  const [error, setError] = useState<string | undefined>();
  const [sceneGraph, setSceneGraph] = useState<SceneGraph | null>(null);
  const [parserConfidence, setParserConfidence] = useState<number>(0);
  const [validationReport, setValidationReport] = useState<string[]>([]);
  const [glbUrl, setGlbUrl] = useState<string | undefined>();
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState('multi');

  const [includeBase, setIncludeBase] = useState(true);
  const [includeRoof, setIncludeRoof] = useState(false);
  const [materialOptions, setMaterialOptions] = useState<MaterialOptions>({
    walls: {
      theme: 'warm_modern',
      color: '#D8C8B8',
      pattern: 'none',
      pattern_color: '#D8C8B8',
    },
    floor: {
      design: 'square_grid',
      primary_color: '#E8E3D9',
      secondary_color: '#B8B5AE',
      grout_color: '#A8A49C',
      tile_size_m: 0.4,
    },
  });
  const { setAnnotationData } = useAnnotationStore();

  const startPipeline = async (file: File) => {
    setStage('parsing');
    setError(undefined);
    setSceneGraph(null);
    setGlbUrl(undefined);
    const objectUrl = URL.createObjectURL(file);
    setImageUrl(objectUrl);

    try {
      const uploadResult = await uploadAndParse(file, selectedModel);
      if (uploadResult.status !== 'success') {
        throw new Error(uploadResult.detail || 'Failed to upload and parse image.');
      }

      const graph = uploadResult.scene_graph;
      setSceneGraph(graph);
      setParserConfidence(uploadResult.parser_confidence || 0);
      setValidationReport(uploadResult.validation_report || []);

      setAnnotationData(graph, objectUrl);
      setStage('annotating');
    } catch (err: any) {
      console.error(err);
      setStage('error');
      setError(err.message || String(err));
    }
  };

  // After annotation review: export GLB (web-only, no Blender) then open the web editor.
  const handleApprove = async (editedGraph: SceneGraph) => {
    setStage('exporting');
    setSceneGraph(editedGraph);
    setError(undefined);
    try {
      // open_blender = false → backend only generates the GLB, never spawns Blender
      const exportResult = await exportBlender(editedGraph, includeBase, includeRoof, materialOptions, false);
      if (exportResult.status !== 'success') {
        throw new Error(exportResult.detail || 'Failed to export 3D model.');
      }
      const paths: string[] = exportResult.export_paths || [];
      const glbPath = paths.find(p => p.toLowerCase().endsWith('.glb'));
      const nextGlbUrl = outputUrl(glbPath) || defaultOutputUrls(editedGraph).glbUrl;
      setGlbUrl(nextGlbUrl);
      setStage('complete');
      onOpenEditor(editedGraph, { glbUrl: nextGlbUrl, materialOptions, includeBase, includeRoof });
    } catch (err: any) {
      console.error(err);
      setStage('error');
      setError(err.message || String(err));
    }
  };

  if (stage === 'designing') {
    return (
      <DesignOptions
        includeBase={includeBase}
        includeRoof={includeRoof}
        materials={materialOptions}
        onIncludeBaseChange={setIncludeBase}
        onIncludeRoofChange={setIncludeRoof}
        onMaterialsChange={setMaterialOptions}
        onContinue={continueToAnnotation}
        onBack={() => setStage('idle')}
      />
    );
  }

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

      <div className="max-w-4xl mx-auto mb-6 flex flex-wrap items-end justify-center gap-6 text-gray-700">
        <label className="flex flex-col items-start gap-2">
          <span className="font-medium">Perception model</span>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            disabled={stage !== 'idle' && stage !== 'complete' && stage !== 'error'}
            className="min-w-64 rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-100"
          >
            <option value="multi">CubiCasa + Architect YOLO</option>
            <option value="yytsi">Yytsi</option>
            <option value="cubicasa">CubiCasa</option>
            <option value="mask2former">Mask2Former</option>
            <option value="architect-yolo">Architect YOLO</option>
            <option value="deepfloorplan">DeepFloorplan</option>
            <option value="raster-to-vector">Raster to Vector</option>
            <option value="huggingface">Hugging Face</option>
          </select>
        </label>
      </div>

      <UploadArea
        onStartPipeline={startPipeline}
        disabled={stage !== 'idle' && stage !== 'complete' && stage !== 'error'}
      />

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

      {glbUrl && stage === 'complete' && sceneGraph && (
        <div className="mx-auto mt-6 h-[500px] max-w-4xl overflow-hidden rounded-lg shadow-inner">
          <ConstructionViewport className="h-full w-full" glbUrl={glbUrl} sceneGraph={sceneGraph} />
        </div>
      )}

      {sceneGraph && stage === 'complete' && (
        <DownloadPanel
          sceneGraph={sceneGraph}
          glbUrl={glbUrl}
        />
      )}
    </div>
  );
};
