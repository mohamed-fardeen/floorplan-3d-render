/**
 * Printing metrics — surface area, concrete volume, print-path length,
 * material usage, and duration. Runs entirely in the browser using the
 * loaded GLB scene; future cost-estimation agents reuse these numbers.
 */

import * as THREE from 'three';
import type { FaceReference } from '../types/selection';

const PRINT_SPEED_M_PER_S = 0.025; // 25 mm/s — typical concrete printing nozzle
const MATERIAL_DENSITY_KG_PER_M3 = 2400; // printed concrete

export interface PrintingMetrics {
  surface_area_m2: number;
  volume_m3: number;
  print_path_length_m: number;
  material_usage_kg: number;
  estimated_duration_s: number;
  estimated_duration_human: string;
  face_count: number;
  mesh_count: number;
  bbox_min: [number, number, number];
  bbox_max: [number, number, number];
}

const _tmpMatrix = new THREE.Matrix4();

function faceWorldArea(
  mesh: THREE.Mesh,
  pos: THREE.BufferAttribute,
  idx: THREE.BufferAttribute | null,
  faceIndex: number,
): number {
  const i0 = idx ? idx.getX(faceIndex * 3) : faceIndex * 3;
  const i1 = idx ? idx.getX(faceIndex * 3 + 1) : faceIndex * 3 + 1;
  const i2 = idx ? idx.getX(faceIndex * 3 + 2) : faceIndex * 3 + 2;
  if (i0 >= pos.count || i1 >= pos.count || i2 >= pos.count) return 0;
  const a = new THREE.Vector3(pos.getX(i0), pos.getY(i0), pos.getZ(i0));
  const b = new THREE.Vector3(pos.getX(i1), pos.getY(i1), pos.getZ(i1));
  const c = new THREE.Vector3(pos.getX(i2), pos.getY(i2), pos.getZ(i2));
  _tmpMatrix.copy(mesh.matrixWorld);
  a.applyMatrix4(_tmpMatrix);
  b.applyMatrix4(_tmpMatrix);
  c.applyMatrix4(_tmpMatrix);
  return 0.5 * b.clone().sub(a).cross(c.clone().sub(a)).length();
}

function bboxOfFace(
  mesh: THREE.Mesh,
  pos: THREE.BufferAttribute,
  idx: THREE.BufferAttribute | null,
  faceIndex: number,
  bbox: THREE.Box3,
): void {
  const i0 = idx ? idx.getX(faceIndex * 3) : faceIndex * 3;
  const v = new THREE.Vector3(pos.getX(i0), pos.getY(i0), pos.getZ(i0));
  _tmpMatrix.copy(mesh.matrixWorld);
  v.applyMatrix4(_tmpMatrix);
  bbox.expandByPoint(v);
}

export function computePrintingMetrics(
  root: THREE.Object3D,
  refs: FaceReference[],
): PrintingMetrics {
  let area = 0;
  let pathLength = 0;
  const bbox = new THREE.Box3();
  const meshByKey = new Map<string, THREE.Mesh>();
  root.traverse((child) => {
    if ((child as THREE.Mesh).isMesh) {
      const mesh = child as THREE.Mesh;
      meshByKey.set(mesh.uuid, mesh);
      meshByKey.set(mesh.name, mesh);
    }
  });
  const uniqueMeshes = new Set<string>();

  for (const ref of refs) {
    const mesh = meshByKey.get(ref.meshRef.meshUuid ?? ref.meshRef.objectName);
    if (!mesh || !mesh.geometry) continue;
    const pos = mesh.geometry.getAttribute('position') as THREE.BufferAttribute | undefined;
    const idx = mesh.geometry.getIndex();
    if (!pos) continue;
    const faceIndex = ref.faceIndex;
    if (faceIndex < 0) continue;
    const faceCount = idx ? idx.count / 3 : pos.count / 3;
    if (faceIndex >= faceCount) continue;
    area += faceWorldArea(mesh, pos, idx, faceIndex);
    bboxOfFace(mesh, pos, idx, faceIndex, bbox);
    uniqueMeshes.add(mesh.uuid);
    pathLength += Math.sqrt(area);
  }

  const dim = bbox.getSize(new THREE.Vector3());
  const volume = Math.max(0, dim.x * dim.y * dim.z);
  const materialKg = volume * MATERIAL_DENSITY_KG_PER_M3;
  const durationS = pathLength > 0 ? pathLength / PRINT_SPEED_M_PER_S : 0;
  const hours = Math.floor(durationS / 3600);
  const minutes = Math.round((durationS % 3600) / 60);
  const durationHuman = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;

  return {
    surface_area_m2: Number(area.toFixed(3)),
    volume_m3: Number(volume.toFixed(3)),
    print_path_length_m: Number(pathLength.toFixed(2)),
    material_usage_kg: Number(materialKg.toFixed(1)),
    estimated_duration_s: Math.round(durationS),
    estimated_duration_human: durationHuman,
    face_count: refs.length,
    mesh_count: uniqueMeshes.size,
    bbox_min: bbox.min.toArray() as [number, number, number],
    bbox_max: bbox.max.toArray() as [number, number, number],
  };
}

export function emptyMetrics(): PrintingMetrics {
  return {
    surface_area_m2: 0,
    volume_m3: 0,
    print_path_length_m: 0,
    material_usage_kg: 0,
    estimated_duration_s: 0,
    estimated_duration_human: '0m',
    face_count: 0,
    mesh_count: 0,
    bbox_min: [0, 0, 0],
    bbox_max: [0, 0, 0],
  };
}