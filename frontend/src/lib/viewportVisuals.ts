/**
 * Apply browser-side visual treatment to the loaded GLB scene:
 *   - Doors / windows / cutter meshes render transparent so the building
 *     looks like a real architectural model.
 *   - Walls get a procedural pattern preview (normal map) when the active
 *     pattern is set in the editor store.
 *
 * The transformations are non-destructive — we replace materials on clones
 * but keep the original meshes intact for picking.
 */

import * as THREE from 'three';

const CUTOUT_NAME_RE = /^(Door|Window|Cutter)_/i;

const TRANSPARENT_MAT = new THREE.MeshStandardMaterial({
  color: 0x0f172a,
  transparent: true,
  opacity: 0.08,
  roughness: 0.4,
  metalness: 0.0,
  side: THREE.DoubleSide,
  depthWrite: false,
});

export interface PatternPreview {
  id: string;
  normalMap: THREE.Texture;
}

/** Generate a procedural normal map for a pattern id. Returns null if unsupported. */
export function buildPatternNormalMap(
  patternId: string | undefined,
  color: string,
): THREE.Texture | null {
  if (!patternId || patternId === 'none' || patternId === 'smooth') return null;
  const size = 256;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  // Base neutral normal (0.5, 0.5, 1.0) -> (128, 128, 255)
  ctx.fillStyle = 'rgb(128, 128, 255)';
  ctx.fillRect(0, 0, size, size);

  const base = color || '#D8C8B8';
  ctx.strokeStyle = 'rgb(80, 80, 255)'; // bumps towards -z
  ctx.lineWidth = 2;

  if (patternId === 'stacked_coils') {
    // Horizontal ridges (print-coil courses).
    for (let y = 0; y < size; y += 8) {
      ctx.fillStyle = (y / 8) % 2 === 0 ? 'rgb(80,80,255)' : 'rgb(180,180,255)';
      ctx.fillRect(0, y, size, 4);
    }
  } else if (patternId === 'woven_rope') {
    // Cross-hatched weave.
    for (let y = 0; y < size; y += 8) {
      ctx.fillStyle = (y / 8) % 2 === 0 ? 'rgb(60,60,255)' : 'rgb(180,180,255)';
      ctx.fillRect(0, y, size, 4);
    }
    for (let x = 0; x < size; x += 8) {
      ctx.fillStyle = (x / 8) % 2 === 0 ? 'rgb(180,180,255)' : 'rgb(80,80,255)';
      ctx.fillRect(x, 0, 4, size);
    }
  } else if (patternId === 'ribbed') {
    // Vertical ribs.
    for (let x = 0; x < size; x += 6) {
      ctx.fillStyle = (x / 6) % 2 === 0 ? 'rgb(60,60,255)' : 'rgb(180,180,255)';
      ctx.fillRect(x, 0, 3, size);
    }
  } else if (patternId === 'brick') {
    // Staggered brick courses.
    for (let y = 0; y < size; y += 12) {
      ctx.fillStyle = y % 24 === 0 ? 'rgb(50,50,255)' : 'rgb(180,180,255)';
      const offset = y % 24 === 0 ? 0 : 16;
      for (let x = -16; x < size; x += 32) {
        ctx.fillRect(x + offset, y, 30, 2);
        ctx.fillRect(x + offset + 30, y, 2, 12);
      }
    }
  } else if (patternId === 'wave') {
    // Sinusoidal bands.
    for (let y = 0; y < size; y += 1) {
      const phase = Math.sin((y / size) * Math.PI * 6) * 0.5 + 0.5;
      const v = Math.round(80 + phase * 95);
      ctx.fillStyle = `rgb(${v},${v},255)`;
      ctx.fillRect(0, y, size, 1);
    }
  } else if (patternId === 'honeycomb') {
    // Hex tile bumps.
    ctx.fillStyle = 'rgb(128,128,255)';
    ctx.fillRect(0, 0, size, size);
    for (let y = 0; y < size; y += 14) {
      for (let x = 0; x < size; x += 16) {
        const cx = x + (y / 14) % 2 === 0 ? 0 : 8;
        ctx.fillStyle = 'rgb(70,70,255)';
        ctx.beginPath();
        ctx.arc(cx, y, 5, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  } else {
    return null;
  }

  void base; // referenced for future tinting

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(8, 4);
  texture.needsUpdate = true;
  return texture;
}

const PATTERN_REPEAT = new Map<string, [number, number]>([
  ['stacked_coils', [6, 12]],
  ['woven_rope', [4, 4]],
  ['ribbed', [8, 2]],
  ['brick', [4, 6]],
  ['wave', [3, 6]],
  ['honeycomb', [2, 4]],
]);

export interface ViewportVisualOptions {
  pattern: string;
  baseColor: string;
  showPatterns: boolean;
}

/** Mutate materials on the cloned scene to apply cutouts + pattern previews. */
export function applyViewportVisuals(
  root: THREE.Object3D,
  options: ViewportVisualOptions,
) {
  const normalMap = options.showPatterns ? buildPatternNormalMap(options.pattern, options.baseColor) : null;
  if (normalMap) {
    const [rx, ry] = PATTERN_REPEAT.get(options.pattern) || [6, 6];
    normalMap.repeat.set(rx, ry);
    normalMap.needsUpdate = true;
  }

  root.traverse((child) => {
    if (!(child as THREE.Mesh).isMesh) return;
    const mesh = child as THREE.Mesh;
    const name = mesh.name || '';

    // Doors / windows / cutters → transparent + wireframe edge.
    if (CUTOUT_NAME_RE.test(name)) {
      mesh.material = TRANSPARENT_MAT.clone();
      mesh.castShadow = false;
      mesh.receiveShadow = false;
      // Drop the geometry draw — let the wireframe show where the cutout is.
      // (Keep the mesh so picking still works on the wall behind it.)
      mesh.visible = false;
      return;
    }

    // Walls → optional pattern overlay.
    if (name.startsWith('Wall_') && normalMap) {
      const existing = mesh.material as THREE.MeshStandardMaterial;
      const replacement = new THREE.MeshStandardMaterial({
        color: existing?.color?.clone() ?? new THREE.Color(0xd8c8b8),
        roughness: 0.85,
        metalness: 0.0,
        normalMap,
        normalScale: new THREE.Vector2(0.6, 0.6),
      });
      mesh.material = replacement;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
    }
  });
}

/** Reset materials to the original GLB state (best effort: clears our overrides). */
export function clearViewportVisuals(root: THREE.Object3D) {
  root.traverse((child) => {
    if (!(child as THREE.Mesh).isMesh) return;
    const mesh = child as THREE.Mesh;
    const name = mesh.name || '';
    if (CUTOUT_NAME_RE.test(name)) {
      mesh.visible = true;
    }
  });
}