/**
 * Geometry-agnostic selection helpers.
 *
 * The viewport builds Selection objects from raw Three.js intersections.
 * These helpers must work with arbitrary mesh topology — straight walls,
 * boolean-difference cut walls, curved printed walls, geometry-node meshes —
 * so we always reason in world-space face centres and triangle indices,
 * never wall IDs.
 */

import * as THREE from 'three';
import type {
  BoundingInfo,
  FaceReference,
  MeshReference,
  Selection,
  SelectionEditMetadata,
} from '../types/selection';

const _tmpVecA = new THREE.Vector3();
const _tmpVecB = new THREE.Vector3();
const _tmpVecC = new THREE.Vector3();
const _tmpNormal = new THREE.Vector3();
const _tmpMatrix = new THREE.Matrix4();

/** Resolve a Three.js object back to the canonical mesh reference. */
export function meshObjectName(object: THREE.Object3D): string {
  return object.name || object.uuid;
}

/** Build a stable MeshReference from any Three.js Object3D. */
export function meshReferenceFromObject(object: THREE.Object3D): MeshReference {
  return { objectName: meshObjectName(object), meshUuid: object.uuid };
}

/** Cast through a Three.js raycaster returning intersections with all mesh descendants. */
export function raycastMeshes(
  root: THREE.Object3D,
  raycaster: THREE.Raycaster,
): THREE.Intersection[] {
  const hits: THREE.Intersection[] = [];
  root.traverse((child) => {
    if ((child as THREE.Mesh).isMesh) {
      const mesh = child as THREE.Mesh;
      if (!mesh.geometry) return;
      const result = raycaster.intersectObject(mesh, false);
      for (const r of result) hits.push(r);
    }
  });
  hits.sort((a, b) => a.distance - b.distance);
  return hits;
}

/**
 * Convert a Three.js intersection into a FaceReference that survives
 * topology changes: we keep the world-space face centre + normal as a fallback
 * when Blender round-trip rewrites vertex indices.
 */
export function faceRefFromIntersection(intersection: THREE.Intersection): FaceReference | null {
  const mesh = intersection.object as THREE.Mesh | undefined;
  if (!mesh || !mesh.geometry) return null;

  const faceIndex =
    typeof intersection.faceIndex === 'number' ? intersection.faceIndex : null;
  if (faceIndex === null) return null;

  const pos = mesh.geometry.getAttribute('position') as THREE.BufferAttribute | undefined;
  const idx = mesh.geometry.getIndex();
  if (!pos) return null;

  const i0 = idx ? idx.getX(faceIndex * 3) : faceIndex * 3;
  const i1 = idx ? idx.getX(faceIndex * 3 + 1) : faceIndex * 3 + 1;
  const i2 = idx ? idx.getX(faceIndex * 3 + 2) : faceIndex * 3 + 2;

  _tmpMatrix.copy(mesh.matrixWorld);
  _tmpVecA.set(pos.getX(i0), pos.getY(i0), pos.getZ(i0)).applyMatrix4(_tmpMatrix);
  _tmpVecB.set(pos.getX(i1), pos.getY(i1), pos.getZ(i1)).applyMatrix4(_tmpMatrix);
  _tmpVecC.set(pos.getX(i2), pos.getY(i2), pos.getZ(i2)).applyMatrix4(_tmpMatrix);

  const ab = _tmpVecB.clone().sub(_tmpVecA);
  const ac = _tmpVecC.clone().sub(_tmpVecA);
  _tmpNormal.copy(ab).cross(ac).normalize();

  return {
    meshRef: meshReferenceFromObject(mesh),
    faceIndex,
    normal: [
      Number(_tmpNormal.x.toFixed(4)),
      Number(_tmpNormal.y.toFixed(4)),
      Number(_tmpNormal.z.toFixed(4)),
    ],
  };
}

/** Merge two FaceReference lists, deduplicating by mesh+face. */
export function mergeFaceRefs(
  a: FaceReference[],
  b: FaceReference[],
): FaceReference[] {
  const seen = new Set<string>();
  const out: FaceReference[] = [];
  const push = (ref: FaceReference) => {
    const key = `${ref.meshRef.meshUuid ?? ref.meshRef.objectName}::${ref.faceIndex}`;
    if (seen.has(key)) return;
    seen.add(key);
    out.push(ref);
  };
  for (const r of a) push(r);
  for (const r of b) push(r);
  return out;
}

/** Compute the bounding info for a list of face references. */
export function boundingFromFaceRefs(
  root: THREE.Object3D,
  refs: FaceReference[],
): BoundingInfo {
  const min = new THREE.Vector3(+Infinity, +Infinity, +Infinity);
  const max = new THREE.Vector3(-Infinity, -Infinity, -Infinity);

  const meshByName = new Map<string, THREE.Mesh>();
  root.traverse((child) => {
    if ((child as THREE.Mesh).isMesh) {
      const mesh = child as THREE.Mesh;
      meshByName.set(mesh.uuid, mesh);
      meshByName.set(mesh.name, mesh);
    }
  });

  for (const ref of refs) {
    const mesh = meshByName.get(ref.meshRef.meshUuid ?? '') ?? meshByName.get(ref.meshRef.objectName);
    if (!mesh || !mesh.geometry) continue;
    const pos = mesh.geometry.getAttribute('position') as THREE.BufferAttribute | undefined;
    const idx = mesh.geometry.getIndex();
    if (!pos) continue;
    const i0 = idx ? idx.getX(ref.faceIndex * 3) : ref.faceIndex * 3;
    _tmpMatrix.copy(mesh.matrixWorld);
    _tmpVecA.set(pos.getX(i0), pos.getY(i0), pos.getZ(i0)).applyMatrix4(_tmpMatrix);
    min.min(_tmpVecA);
    max.max(_tmpVecA);
  }

  if (!Number.isFinite(min.x)) {
    return { min: [0, 0, 0], max: [0, 0, 0], center: [0, 0, 0] };
  }

  return {
    min: [min.x, min.y, min.z],
    max: [max.x, max.y, max.z],
    center: [(min.x + max.x) / 2, (min.y + max.y) / 2, (min.z + max.z) / 2],
  };
}

/** Distinct mesh references contained in a list of face refs. */
export function uniqueMeshRefs(refs: FaceReference[]): MeshReference[] {
  const seen = new Set<string>();
  const out: MeshReference[] = [];
  for (const ref of refs) {
    const key = ref.meshRef.meshUuid ?? ref.meshRef.objectName;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(ref.meshRef);
  }
  return out;
}

/**
 * Build a geometry consisting of the triangles in `refs`, transformed into
 * world space. Works for both indexed and non-indexed BufferGeometry,
 * including curved / geometry-node generated meshes.
 *
 * Uses the canonical object name as the primary key so the highlight survives
 * GLB hot-reload (UUIDs change on clone but names don't).
 */
export function buildHighlightGeometry(
  root: THREE.Object3D,
  refs: FaceReference[],
): THREE.BufferGeometry | null {
  if (refs.length === 0) return null;

  const positions: number[] = [];
  const meshByKey = new Map<string, THREE.Mesh>();
  root.traverse((child) => {
    if ((child as THREE.Mesh).isMesh) {
      const mesh = child as THREE.Mesh;
      meshByKey.set(mesh.uuid, mesh);
      meshByKey.set(mesh.name, mesh);
    }
  });

  for (const ref of refs) {
    const key = ref.meshRef.meshUuid ?? ref.meshRef.objectName;
    const mesh = meshByKey.get(key);
    if (!mesh || !mesh.geometry) continue;
    const pos = mesh.geometry.getAttribute('position') as THREE.BufferAttribute | undefined;
    const idx = mesh.geometry.getIndex();
    if (!pos) continue;

    const faceIndex = ref.faceIndex;
    if (faceIndex < 0) continue;

    const faceCount = idx ? idx.count / 3 : pos.count / 3;
    if (faceIndex >= faceCount) continue;

    const i0 = idx ? idx.getX(faceIndex * 3) : faceIndex * 3;
    const i1 = idx ? idx.getX(faceIndex * 3 + 1) : faceIndex * 3 + 1;
    const i2 = idx ? idx.getX(faceIndex * 3 + 2) : faceIndex * 3 + 2;

    if (i0 >= pos.count || i1 >= pos.count || i2 >= pos.count) continue;

    _tmpMatrix.copy(mesh.matrixWorld);
    _tmpVecA.set(pos.getX(i0), pos.getY(i0), pos.getZ(i0)).applyMatrix4(_tmpMatrix);
    _tmpVecB.set(pos.getX(i1), pos.getY(i1), pos.getZ(i1)).applyMatrix4(_tmpMatrix);
    _tmpVecC.set(pos.getX(i2), pos.getY(i2), pos.getZ(i2)).applyMatrix4(_tmpMatrix);

    positions.push(_tmpVecA.x, _tmpVecA.y, _tmpVecA.z);
    positions.push(_tmpVecB.x, _tmpVecB.y, _tmpVecB.z);
    positions.push(_tmpVecC.x, _tmpVecC.y, _tmpVecC.z);
  }

  if (positions.length === 0) return null;
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    'position',
    new THREE.Float32BufferAttribute(positions, 3),
  );
  geometry.computeBoundingSphere();
  return geometry;
}

/** Build a Selection object from the given face refs. */
export function createSelectionFromFaces(
  root: THREE.Object3D,
  refs: FaceReference[],
  metadata: SelectionEditMetadata = {},
  name?: string,
): Selection {
  const id = `sel_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
  return {
    id,
    name,
    meshRefs: uniqueMeshRefs(refs),
    faceRefs: refs,
    bounding: boundingFromFaceRefs(root, refs),
    metadata,
    createdAt: Date.now(),
  };
}

/** Discard highlight geometries to avoid GPU leaks. */
export function disposeHighlightGeometry(geometry: THREE.BufferGeometry | null) {
  if (geometry) geometry.dispose();
}