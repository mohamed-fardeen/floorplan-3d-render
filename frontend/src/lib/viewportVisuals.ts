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
import { buildCoiledWallGeometry } from './coilGeometry';

// Match any mesh whose name contains door/window/cutter/frame keywords (case-insensitive)
const isCutoutMesh = (name: string) =>
  /door|window|cutter|opening|frame/i.test(name) && !name.startsWith('Wall_');

const TRANSPARENT_MAT = new THREE.MeshStandardMaterial({
  color: 0x38bdf8,
  transparent: true,
  opacity: 0.25,
  roughness: 0.2,
  metalness: 0.1,
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
  _color: string,
): THREE.Texture | null {
  if (!patternId || patternId === 'none' || patternId === 'smooth') return null;
  const size = 256;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  const imgData = ctx.createImageData(size, size);
  const data = imgData.data;

  if (patternId === 'stacked_coils') {
    // 3D-printed concrete horizontal bead profile
    const period = 16;
    for (let y = 0; y < size; y++) {
      const phase = (y % period) / period;
      const angle = (phase - 0.5) * Math.PI * 2;
      const cosH  = Math.cos(angle);
      const dy    = cosH >= 0 ? -Math.sin(angle) * 0.8 : -Math.sin(angle) * 0.2;
      const nz    = cosH >= 0 ? Math.pow(cosH, 0.25) : 0.4;

      const r = 128;
      const g = Math.min(255, Math.max(0, Math.round(128 + dy * 110)));
      const b = Math.min(255, Math.max(0, Math.round(128 + nz * 127)));

      for (let x = 0; x < size; x++) {
        const idx = (y * size + x) * 4;
        data[idx] = r;
        data[idx + 1] = g;
        data[idx + 2] = b;
        data[idx + 3] = 255;
      }
    }
  } else if (patternId === 'woven_rope') {
    /**
     * Dense 3D-printed concrete oval bead normal map:
     *  - Each bead is a 2D oval dome: product of two clipped cosine bell curves
     *    (X and Y) → zero at all bead boundaries (deep grooves), peaked at centre
     *  - Tight 8px tall × 12px wide beads packed densely
     *  - Alternating row offset by half bead width (staggered bond)
     *  - Combined with high texture repeat [16,16] → visually matches reference
     */
    const beadH = 8;   // px per bead row (tight stacking)
    const beadW = 12;  // px per bead (slightly wider than tall)
    for (let y = 0; y < size; y++) {
      const rowIndex = Math.floor(y / beadH);
      const shiftX   = (rowIndex % 2) * (beadW * 0.5); // staggered bond offset
      const yPhase   = (y % beadH) / beadH;
      const yAngle   = (yPhase - 0.5) * Math.PI * 2;
      const yCos     = Math.cos(yAngle);
      // Vertical bell: clipped cosine — zero below midpoint → clean groove at row edges
      const yBell    = yCos > 0 ? Math.pow(yCos, 0.38) : 0.0;
      const dySlope  = yCos > 0 ? -Math.sin(yAngle) : 0.0;

      for (let x = 0; x < size; x++) {
        const xMod   = ((x + shiftX) % beadW + beadW) % beadW;
        const xPhase = xMod / beadW;
        const xAngle = (xPhase - 0.5) * Math.PI * 2;
        const xCos   = Math.cos(xAngle);
        // Horizontal bell: clipped cosine — zero at bead edges → groove between beads
        const xBell  = xCos > 0 ? Math.pow(xCos, 0.38) : 0.0;
        const dxSlope= xCos > 0 ? -Math.sin(xAngle) : 0.0;

        // 2D oval dome = product of both bells
        const h  = yBell * xBell;
        const nx = dxSlope * yBell * 0.95;
        const ny = dySlope * xBell * 0.95;
        const nz = Math.max(0.04, h);

        const idx = (y * size + x) * 4;
        data[idx]     = Math.min(255, Math.max(0, Math.round(128 + nx * 127)));
        data[idx + 1] = Math.min(255, Math.max(0, Math.round(128 + ny * 127)));
        data[idx + 2] = Math.min(255, Math.max(0, Math.round(128 + nz * 127)));
        data[idx + 3] = 255;
      }
    }
  } else if (patternId === 'ribbed') {
    // Cross-hatched weave pattern
    const scale = 16;
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const idx = (y * size + x) * 4;
        const cellX = Math.floor(x / scale) % 2;
        const cellY = Math.floor(y / scale) % 2;
        const isHoriz = (cellX ^ cellY) === 0;

        const pos = isHoriz ? (y % scale) / scale : (x % scale) / scale;
        const angle = (pos - 0.5) * Math.PI;
        const slope = -Math.sin(angle);
        const nz = Math.cos(angle);

        const r = isHoriz ? 128 : Math.round(128 + slope * 100);
        const g = isHoriz ? Math.round(128 + slope * 100) : 128;
        const b = Math.round(128 + nz * 127);

        data[idx] = r;
        data[idx + 1] = g;
        data[idx + 2] = b;
        data[idx + 3] = 255;
      }
    }
  } else if (patternId === 'ribbed') {
    // Vertical ribs (variations along U)
    const ribWidth = 12;
    for (let x = 0; x < size; x++) {
      const phase = (x % ribWidth) / ribWidth;
      const angle = (phase - 0.5) * Math.PI;
      const nx = -Math.sin(angle);
      const nz = Math.cos(angle);

      const r = Math.min(255, Math.max(0, Math.round(128 + nx * 110)));
      const g = 128;
      const b = Math.min(255, Math.max(0, Math.round(128 + nz * 127)));

      for (let y = 0; y < size; y++) {
        const idx = (y * size + x) * 4;
        data[idx] = r;
        data[idx + 1] = g;
        data[idx + 2] = b;
        data[idx + 3] = 255;
      }
    }
  } else if (patternId === 'wave') {
    // Sinusoidal horizontal wave layers
    for (let y = 0; y < size; y++) {
      const angle = (y / size) * Math.PI * 12;
      const ny = Math.cos(angle);
      const nz = Math.sin(angle) * 0.5 + 0.5;

      const r = 128;
      const g = Math.round(128 + ny * 90);
      const b = Math.round(180 + nz * 75);

      for (let x = 0; x < size; x++) {
        const idx = (y * size + x) * 4;
        data[idx] = r;
        data[idx + 1] = g;
        data[idx + 2] = b;
        data[idx + 3] = 255;
      }
    }
  } else {
    return null;
  }

  ctx.putImageData(imgData, 0, 0);

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.needsUpdate = true;
  return texture;
}

const PATTERN_REPEAT = new Map<string, [number, number]>([
  ['stacked_coils', [8, 8]],
  ['woven_rope', [16, 16]],
  ['ribbed', [12, 2]],
  ['wave', [2, 8]],
]);

export interface ViewportVisualOptions {
  /** Default pattern for walls that are NOT in the active selection. */
  pattern: string;
  /** Default base color for walls that are NOT in the active selection. */
  baseColor: string;
  showPatterns: boolean;
}

/**
 * Optional per-selection overrides. When a wall mesh is referenced by the
 * active selection it picks up the selection's pattern/color; everything
 * else keeps `ViewportVisualOptions.baseColor` / `pattern` as the default.
 */
export interface SelectionOverrideOptions {
  /** Mesh names (`Wall_<id>` etc.) that belong to the active selection. */
  selectedObjectNames: ReadonlySet<string>;
  /** Selection-specific color (hex) — applied only to selected meshes. */
  selectedColor?: string;
  /** Selection-specific pattern — applied only to selected meshes. */
  selectedPattern?: string;
}

/**
 * Optional isolation directive. When set, every wall whose name is NOT
 * `isolatedWallName` is faded to `dimOpacity` and disabled (no shadow, no
 * picking). The isolated wall itself keeps full opacity.
 */
export interface IsolationOptions {
  isolatedWallName: string;
  dimOpacity: number;
}

/**
 * Per-wall material overrides keyed by mesh name (`Wall_<id>`). Built up
 * while the user is in isolation mode and persisted across wall switches
 * so a previously edited wall keeps its new colour even after the user
 * picks a different one.
 */
export type WallOverrideMap = ReadonlyMap<string, { color?: string; pattern?: string }>;

interface WallTreatment {
  color: string;
  pattern: string;
  label: string;
}

function resolveWallTreatment(
  meshName: string,
  base: WallTreatment,
  override: SelectionOverrideOptions | undefined,
  wallOverrides: WallOverrideMap | undefined,
): WallTreatment {
  // Per-wall override (persistent) wins over the per-active-selection
  // override so a wall's saved colour sticks even after the user picks
  // a different one.
  if (wallOverrides && wallOverrides.has(meshName)) {
    const w = wallOverrides.get(meshName)!;
    return {
      color: w.color ?? base.color,
      pattern: w.pattern ?? base.pattern,
      label: 'override',
    };
  }
  if (!override || override.selectedObjectNames.size === 0) {
    return base;
  }
  if (!override.selectedObjectNames.has(meshName)) {
    return base;
  }
  return {
    color: override.selectedColor ?? base.color,
    pattern: override.selectedPattern ?? base.pattern,
    label: 'selection',
  };
}

/** Mutate materials/geometries on the cloned scene to apply cutouts + pattern previews. */
export function applyViewportVisuals(
  root: THREE.Object3D,
  options: ViewportVisualOptions,
  selectionOverride?: SelectionOverrideOptions,
  isolation?: IsolationOptions,
  wallOverrides?: WallOverrideMap,
) {
  // eslint-disable-next-line no-console
  const log = isolation
    ? (msg: string, ...args: unknown[]) =>
        console.log(`[viewportVisuals] ${msg}`, ...args)
    : () => undefined;

  log('applyViewportVisuals start', {
    isolation: isolation?.isolatedWallName,
    dimOpacity: isolation?.dimOpacity,
    hasRoot: !!root,
    rootChildren: root.children.length,
  });

  const baseTreatment: WallTreatment = {
    color: options.baseColor,
    pattern: options.pattern,
    label: 'default',
  };

  // Per-treatment normal maps (we cache one texture per pattern id so
  // selecting a wall doesn't cause every other wall to re-build its map).
  const normalMaps = new Map<string, THREE.Texture | null>();
  const getNormalMap = (patternId: string, color: string): THREE.Texture | null => {
    if (!options.showPatterns) return null;
    const key = `${patternId}::${color}`;
    if (!normalMaps.has(key)) {
      normalMaps.set(key, buildPatternNormalMap(patternId, color));
      const tex = normalMaps.get(key);
      if (tex) {
        const [rx, ry] = PATTERN_REPEAT.get(patternId) || [6, 6];
        tex.repeat.set(rx, ry);
        tex.needsUpdate = true;
      }
    }
    return normalMaps.get(key) ?? null;
  };

  root.traverse((child) => {
    if (!(child as THREE.Mesh).isMesh) return;
    const mesh = child as THREE.Mesh;
    const name = mesh.name || '';

    // Doors / windows / cutters → hide cutter objects completely to leave an empty hole opening.
    if (isCutoutMesh(name)) {
      mesh.visible = false;
      mesh.castShadow = false;
      mesh.receiveShadow = false;
      return;
    }

    // Corner posts (WallPost_<id>) are structural fillers that sit inside
    // the wall volume. They are not part of the wall surface and should
    // never receive the wall's pattern / colour / isolation treatment.
    // In isolation mode we hide them entirely — the post is the same
    // colour as the wall and sits right where the camera flies to,
    // so leaving it visible would render the post cube over the
    // isolated wall and produce a blank screen.
    if (name.startsWith('WallPost_')) {
      if (isolation) {
        const before = mesh.visible;
        mesh.visible = false;
        log(`post ${name}: hidden (was visible=${before})`);
      }
      return;
    }

    // Walls → per-mesh treatment. Default walls use the project defaults,
    // walls inside the active selection use the selection's overrides.
    if (name.startsWith('Wall_')) {
      const isIsolated = !!isolation && name === isolation.isolatedWallName;
      const isDimmed = !!isolation && !isIsolated;
      log(`wall ${name}: isIsolated=${isIsolated}, isDimmed=${isDimmed}, visible=${mesh.visible}`);

      // In isolation mode non-isolated walls fade to `dimOpacity` (but stay
      // in the scene, just translucent). They lose shadow casting/receiving
      // so they don't pollute the isolated wall's lighting. Picking is
      // separately disabled by the PickHandler / Box / Lasso overlays
      // (they scope hits to `Wall_<isolatedId>`).
      if (isDimmed) {
        // Swap in a dedicated transparent material so the 5% dim is
        // actually rendered. Mutating `transparent` on the previously
        // opaque MeshStandardMaterial alone doesn't trigger a shader
        // recompile, so the wall kept rendering fully opaque until the
        // material was force-replaced. Stash the original material so
        // `clearViewportVisuals` can put it back when isolation ends.
        const mat = mesh.material as THREE.MeshStandardMaterial | undefined;
        if (mat) {
          const ud = (mat as any).userData ?? {};
          if (!ud.__dimmedMaterial) {
            ud.__originalMaterial = mat;
            ud.__dimmedMaterial = true;
            (mat as any).userData = ud;
            const dimmedMat = new THREE.MeshStandardMaterial({
              color: mat.color ? mat.color.clone() : new THREE.Color(0x9ca3af),
              roughness: mat.roughness ?? 0.85,
              metalness: mat.metalness ?? 0.0,
              normalMap: (mat as any).normalMap ?? undefined,
              normalScale: (mat as any).normalScale
                ? (mat as any).normalScale.clone()
                : new THREE.Vector2(1, 1),
              transparent: true,
              opacity: isolation!.dimOpacity,
              depthWrite: false,
            });
            (dimmedMat as any).userData = ud;
            mesh.material = dimmedMat;
          } else {
            mat.opacity = isolation!.dimOpacity;
          }
        }
        mesh.castShadow = false;
        mesh.receiveShadow = false;
        return;
      }
      if (isolation && isIsolated) {
        const mat = mesh.material as THREE.MeshStandardMaterial | undefined;
        log(`isolated wall ${name}: material before`, {
          hasMaterial: !!mat,
          materialName: mat ? (mat as any).name : 'none',
          opacity: mat?.opacity,
          transparent: mat?.transparent,
          visible: mat?.visible,
          meshVisible: mesh.visible,
        });
        if (mat) {
          // If we swapped in a dimmed material earlier, restore the
          // original opaque material so the isolated wall renders fully
          // solid again.
          const original = (mat as any)?.userData?.__originalMaterial as
            | THREE.MeshStandardMaterial
            | undefined;
          if (original) {
            (original as any).userData = {
              ...((original as any).userData ?? {}),
            };
            delete (original as any).userData.__dimmedMaterial;
            mesh.material = original;
          } else {
            mat.transparent = false;
            mat.opacity = 1;
            mat.depthWrite = true;
            mat.needsUpdate = true;
          }
        }
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        mesh.visible = true;
        log(`isolated wall ${name}: after restore, mesh.visible=${mesh.visible}, mat.opacity=${mesh.material?.opacity}`);
      }

      const treatment = resolveWallTreatment(name, baseTreatment, selectionOverride, wallOverrides);
      const isWovenRope = options.showPatterns && treatment.pattern === 'woven_rope';

      if (isWovenRope) {
        if (!mesh.geometry.boundingBox) {
          mesh.geometry.computeBoundingBox();
        }
        if (mesh.geometry.boundingBox) {
          if (!mesh.userData.originalGeometry) {
            mesh.userData.originalGeometry = mesh.geometry;
          }
          const coiledGeo = buildCoiledWallGeometry(mesh.geometry.boundingBox, {
            patternType: 'woven_rope',
            coilPeriod: 0.019,
            coilAmplitude: 0.022,
            beadSharpness: 0.22,
            segmentsPerCoil: 8,
            widthSegments: 16,
          });
          if (coiledGeo.getAttribute('position')) {
            mesh.geometry = coiledGeo;
          }
        }

        mesh.material = new THREE.MeshStandardMaterial({
          color: new THREE.Color(treatment.color || '#d8c8b8'),
          roughness: 0.88,
          metalness: 0.0,
        });
      } else {
        if (mesh.userData.originalGeometry) {
          mesh.geometry = mesh.userData.originalGeometry;
        }

        const normalMap = getNormalMap(treatment.pattern, treatment.color);
        const replacement = new THREE.MeshStandardMaterial({
          color: new THREE.Color(treatment.color || '#d8c8b8'),
          roughness: 0.85,
          metalness: 0.0,
          normalMap: normalMap || undefined,
          normalScale: new THREE.Vector2(1.1, 1.1),
        });
        mesh.material = replacement;
      }

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
    if (isCutoutMesh(name)) {
      mesh.visible = true;
      return;
    }
    // Restore any wall mesh whose material was swapped for the dimmed
    // isolation overlay. Without this the walls stay at 5% opacity
    // forever after the user exits isolation mode.
    if (name.startsWith('Wall_')) {
      const mat = mesh.material as THREE.MeshStandardMaterial | undefined;
      const original = (mat as any)?.userData?.__originalMaterial as
        | THREE.MeshStandardMaterial
        | undefined;
      if (original) {
        mesh.material = original;
      } else {
        if (mat) {
          mat.opacity = 1;
          mat.transparent = false;
          mat.depthWrite = true;
          mat.needsUpdate = true;
        }
      }
    }
  });
}