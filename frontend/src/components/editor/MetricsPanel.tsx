import React, { useEffect, useState } from 'react';
import { useEditorStore } from '../../store/editorStore';
import { computePrintingMetrics, emptyMetrics, type PrintingMetrics } from '../../lib/metrics';

interface MetricsPanelProps {
  glbRoot: THREE.Object3D | null;
}

import * as THREE from 'three';

export const MetricsPanel: React.FC<MetricsPanelProps> = ({ glbRoot }) => {
  const { getActiveSelection } = useEditorStore();
  const selection = getActiveSelection();
  const [metrics, setMetrics] = useState<PrintingMetrics>(emptyMetrics());

  useEffect(() => {
    if (!glbRoot || !selection) {
      setMetrics(emptyMetrics());
      return;
    }
    try {
      const next = computePrintingMetrics(glbRoot, selection.faceRefs);
      setMetrics(next);
    } catch (err) {
      console.warn('[metrics] compute failed', err);
      setMetrics(emptyMetrics());
    }
  }, [glbRoot, selection]);

  return (
    <div className="border-b border-gray-300 p-4">
      <h3 className="text-sm font-semibold text-gray-800">Printing metrics</h3>
      <p className="mb-2 text-[11px] text-gray-500">
        Derived from the active selection's geometry. Reused by future cost-estimation agents.
      </p>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
        <dt className="text-gray-500">Surface area</dt>
        <dd className="text-right font-mono">{metrics.surface_area_m2.toFixed(3)} m²</dd>
        <dt className="text-gray-500">Volume (bbox)</dt>
        <dd className="text-right font-mono">{metrics.volume_m3.toFixed(3)} m³</dd>
        <dt className="text-gray-500">Print path</dt>
        <dd className="text-right font-mono">{metrics.print_path_length_m.toFixed(2)} m</dd>
        <dt className="text-gray-500">Material usage</dt>
        <dd className="text-right font-mono">{metrics.material_usage_kg.toFixed(1)} kg</dd>
        <dt className="text-gray-500">Duration est.</dt>
        <dd className="text-right font-mono">{metrics.estimated_duration_human}</dd>
        <dt className="text-gray-500">Faces</dt>
        <dd className="text-right font-mono">{metrics.face_count}</dd>
      </dl>
    </div>
  );
};