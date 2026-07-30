/**
 * Depth-aware picking helpers.
 *
 * For box/lasso screen-space selection we want to ignore faces hidden behind
 * closer geometry. We render the scene to an off-screen WebGLRenderTarget
 * once per selection, read back the depth buffer, then compare each polygon
 * centre's depth against the rendered depth. If the polygon's depth is
 * further than the rendered depth at the same pixel, it is occluded.
 *
 * This is intentionally lightweight: we only need a depth target, not a full
 * color buffer. The render uses the existing scene's camera and traversal.
 */

import * as THREE from 'three';

const _ndc = new THREE.Vector3();

export interface DepthMaskResult {
  /** Pixel width / height of the depth buffer. */
  width: number;
  height: number;
  /** Depth values per pixel (row-major, single channel float32, 0..1 NDC depth). */
  data: Float32Array;
}

/** Render the scene's depth into a buffer at the supplied pixel resolution. */
export function renderDepthMask(
  scene: THREE.Scene,
  camera: THREE.Camera,
  width: number,
  height: number,
  renderer: THREE.WebGLRenderer,
): DepthMaskResult {
  const dpr = renderer.getPixelRatio();
  const w = Math.max(1, Math.floor(width * dpr));
  const h = Math.max(1, Math.floor(height * dpr));

  const target = new THREE.WebGLRenderTarget(w, h, {
    depthBuffer: true,
    stencilBuffer: false,
    type: THREE.FloatType,
    format: THREE.RGBAFormat,
    minFilter: THREE.NearestFilter,
    magFilter: THREE.NearestFilter,
  });

  const prevTarget = renderer.getRenderTarget();
  const prevAutoClear = renderer.autoClear;
  const prevClearColor = new THREE.Color();
  const prevClearAlpha = renderer.getClearAlpha();
  renderer.getClearColor(prevClearColor);

  renderer.setRenderTarget(target);
  renderer.autoClear = true;
  renderer.setClearColor(0x000000, 0);
  renderer.clear();
  renderer.render(scene, camera);

  const pixels = new Float32Array(w * h * 4);
  renderer.readRenderTargetPixels(target, 0, 0, w, h, pixels);

  renderer.setRenderTarget(prevTarget);
  renderer.autoClear = prevAutoClear;
  renderer.setClearColor(prevClearColor, prevClearAlpha);

  const depth = new Float32Array(w * h);
  for (let i = 0; i < w * h; i++) {
    depth[i] = pixels[i * 4];
  }
  target.dispose();

  return { width: w, height: h, data: depth };
}

/** Linearise an NDC depth value (already 0..1 after read-back) into view-space Z. */
export function linearizeDepth(ndcDepth: number, camera: THREE.Camera): number {
  const near = (camera as THREE.PerspectiveCamera).near ?? 0.1;
  const far = (camera as THREE.PerspectiveCamera).far ?? 1000;
  const z = ndcDepth * 2 - 1;
  return (2 * near * far) / (far + near - z * (far - near));
}

/**
 * Test whether a world-space point would be occluded by the depth buffer at
 * its projected pixel. Returns true when the point is visible.
 */
export function isVisibleAt(
  world: THREE.Vector3,
  camera: THREE.Camera,
  mask: DepthMaskResult,
  tolerance: number = 0.005,
): boolean {
  _ndc.copy(world).project(camera);
  if (_ndc.z < -1 || _ndc.z > 1) return false;
  const x = Math.floor(((_ndc.x + 1) / 2) * (mask.width - 1));
  const y = Math.floor(((-_ndc.y + 1) / 2) * (mask.height - 1));
  if (x < 0 || y < 0 || x >= mask.width || y >= mask.height) return false;
  const idx = y * mask.width + x;
  const bufferDepth = mask.data[idx];
  if (bufferDepth === 0) return true; // sky / no geometry — visible
  // NDC z is in front of bufferDepth within tolerance → visible.
  return Math.abs(_ndc.z - bufferDepth) < tolerance || _ndc.z < bufferDepth;
}