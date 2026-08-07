/**
 * coilGeometry.ts
 *
 * Generates real 3D extruded coil-ridge geometry for walls, matching the
 * horizontal print-layer look of 3D-printed architectural concrete.
 *
 * Unlike a normal-map illusion, this geometry has actual displaced vertices
 * on the front and back faces so the ridges:
 *  - Cast and receive real shadows between layers
 *  - Show correct parallax as the camera orbits
 *  - Are clearly visible from oblique angles
 *
 * Coil profile (per period P, measured along wall height):
 *   phase  = (y mod P) / P            0 → 1
 *   angle  = (phase − 0.5) · 2π      −π → +π  (bead top = 0)
 *   cosH   = cos(angle)              −1 → +1
 *   shaped = cosH≥0 ? cosH^k : −(−cosH)^(2k)   wide bead / narrow groove
 *   disp   = shaped · amplitude
 */

import * as THREE from 'three';

// ─── Public API ────────────────────────────────────────────────────────────

export interface CoilGeometryOptions {
  /** Pattern style: 'stacked_coils' (horizontal courses) or 'woven_rope' (interlocking twisted weave). */
  patternType?: 'stacked_coils' | 'woven_rope';

  /**
   * Height of one coil layer in world-space metres.
   * Default 0.042 (42 mm) — very tight, ~24 courses per metre.
   */
  coilPeriod?: number;

  /**
   * Maximum outward protrusion of each ridge from the base wall face (metres).
   * Default 0.018 (18 mm).  Clamped to 35 % of wall thickness.
   */
  coilAmplitude?: number;

  /**
   * Power exponent that controls bead width.
   * < 1 → wider flat plateau, narrow pinched groove (matches ref image).
   * Default 0.28.
   */
  beadSharpness?: number;

  /**
   * Vertex subdivisions per coil period on the primary (front/back) faces.
   * Higher = smoother profile silhouette.  Default 8.
   */
  segmentsPerCoil?: number;

  /**
   * Subdivisions along the wall's horizontal length.
   * Doesn't affect coil appearance but keeps the mesh regular.  Default 12.
   */
  widthSegments?: number;
}

const DEFAULTS: Required<CoilGeometryOptions> = {
  patternType: 'stacked_coils',
  coilPeriod: 0.042,
  coilAmplitude: 0.018,
  beadSharpness: 0.28,
  segmentsPerCoil: 8,
  widthSegments: 12,
};

// ─── Profile helpers ────────────────────────────────────────────────────────

/**
 * Pseudo-random noise generator based on layer index and path position.
 * Returns deterministic float [-1, 1] to keep mesh generation pure and reproducible.
 */
function pseudoNoise(seedA: number, seedB: number): number {
  const sinVal = Math.sin(seedA * 12.9898 + seedB * 78.233) * 43758.5453;
  return (sinVal - Math.floor(sinVal)) * 2 - 1;
}

/**
 * Outward displacement at a given position within the wall (localY height & localU along length).
 * Implements real robotic concrete 3D printing physics:
 *  - Flattened capsule nozzle profile (width ~44mm, height ~19mm)
 *  - 5-10% vertical squish compression against layer below
 *  - Staggered layer bond offset (~20mm shift on alternate layers)
 *  - Shallow 2-4mm inter-layer grooves & bulged bead sides
 *  - Subtle robotic path wobble & layer height/width micro-variations
 */
function ridgeDisplace(
  localY: number,
  period: number,
  amplitude: number,
  sharpness: number,
  patternType: 'stacked_coils' | 'woven_rope' = 'stacked_coils',
  localU: number = 0,
): number {
  if (patternType === 'woven_rope') {
    /**
     * Woven rope 3D-printed concrete bead extrusion physics:
     *  - Flattened capsule-shaped nozzle profile (flattened top, bulged sides)
     *  - 8% vertical compression squish against the layer below
     *  - Alternating row staggered bond offset (half-bead width shift per layer)
     *  - Shallow 2-4 mm inter-layer grooves
     *  - Subtle 1-3 mm deterministic robotic path wobble & ±2% dimension variation
     *  - Woven braided strand modulation across path length (u)
     */
    const squishFactor = 0.92; // 8% vertical squish compression
    const compressedPeriod = period * squishFactor;
    const layerIndex = Math.floor(localY / compressedPeriod);

    // Staggered bond offset: alternate rows shift horizontally by ~20 mm (half bead width)
    const weaveLength = period * 2.4;
    const staggerOffset = (layerIndex % 2) * (weaveLength * 0.5);

    // Subtle robotic extrusion path wobble (1-3 mm) and ±2% bead height/width variation
    const noiseWobble = pseudoNoise(layerIndex, Math.floor((localU + staggerOffset) * 10)) * 0.002;
    const layerVar = 1 + pseudoNoise(layerIndex, 88) * 0.02;

    // Vertical bead shape: flattened capsule profile with flat top & bulged sides
    const yPhase = (((localY % compressedPeriod) + compressedPeriod) % compressedPeriod) / compressedPeriod; // 0 -> 1
    const yAngle = (yPhase - 0.5) * Math.PI * 2;
    const yCos   = Math.cos(yAngle);

    // Flattened top with bulged sides & shallow 2-4mm inter-layer groove
    const yCapsule = yCos >= 0
      ? Math.pow(yCos, 0.24) * layerVar
      : -Math.pow(-yCos, 0.6) * 0.22;

    // Horizontal braided strand weave modulation along path length (u)
    const uPhase = (((localU + staggerOffset + noiseWobble) % weaveLength) + weaveLength) % weaveLength / weaveLength;
    const uCos   = Math.cos((uPhase - 0.5) * Math.PI * 2);
    const uWeave = uCos * 0.40 + 0.60;

    return yCapsule * uWeave * amplitude + noiseWobble;
  }

  // Layer indexing & vertical compression (5-10% squish against layer below)
  const squishFactor = 0.92; // 8% vertical compression
  const compressedPeriod = period * squishFactor;
  const layerIndex = Math.floor(localY / compressedPeriod);

  // Staggered bond offset: alternate layers shifted horizontally by ~20mm (half bead width)
  const staggerOffset = (layerIndex % 2) * 0.020;

  // Subtle robotic path wobble (1-3mm) & ±2% layer height/width variation
  const noiseWobble = pseudoNoise(layerIndex, Math.floor((localU + staggerOffset) * 10)) * 0.002;
  const layerVar = 1 + pseudoNoise(layerIndex, 42) * 0.02;

  // Flattened capsule-shaped nozzle profile with bulged sides & flat top
  const effectiveU = localU + staggerOffset + noiseWobble;
  const yPhase = (((localY % compressedPeriod) + compressedPeriod) % compressedPeriod) / compressedPeriod; // 0 -> 1
  const angle  = (yPhase - 0.5) * Math.PI * 2; // -π -> +π

  // Capsule profile: flat top (exponent < 0.30), bulged sides, shallow 3mm groove
  const cosH = Math.cos(angle);
  const capsuleProfile = cosH >= 0
    ? Math.pow(cosH, 0.22) * layerVar // Flat top with wide bulged sides
    : -Math.pow(-cosH, 0.6) * 0.25;  // Shallow 2-4mm groove between compressed layers

  return capsuleProfile * amplitude + noiseWobble;
}

/**
 * First derivative dDisp/dLocalY via central finite differences.
 * Used to compute analytically-correct surface normals on the displaced face.
 */
function ridgeSlope(
  localY: number,
  period: number,
  amplitude: number,
  sharpness: number,
  patternType: 'stacked_coils' | 'woven_rope' = 'stacked_coils',
  localU: number = 0,
): number {
  const e = period * 0.01;
  return (
    ridgeDisplace(localY + e, period, amplitude, sharpness, patternType, localU) -
    ridgeDisplace(localY - e, period, amplitude, sharpness, patternType, localU)
  ) / (2 * e);
}

/**
 * Construct capsule cross-section profile points for 3D concrete bead extrusion.
 *  - Flattened top
 *  - Bulged sides
 */
function createCapsuleProfile(width: number, height: number): THREE.Vector2[] {
  const pts: THREE.Vector2[] = [];
  const numPts = 24;
  for (let i = 0; i <= numPts; i++) {
    const t = i / numPts;
    const angle = Math.PI * t; // 0 to π (half cylinder top profile)

    let rx = Math.cos(angle) * width * 0.5;
    let ry = Math.sin(angle) * height;

    // Flatten top at 70% height
    if (ry > height * 0.7) {
      ry = height * 0.7;
    }
    // Bulge sides outward by 12%
    rx *= 1.12;

    pts.push(new THREE.Vector2(rx, ry));
  }
  return pts;
}

/**
 * Extrude capsule concrete bead layer by layer for woven_rope pattern.
 * Stacked deposited concrete filaments with 5-10% vertical squish, staggered row offsets, and subtle 1-3mm path wobble.
 */
function buildBeadWall(
  bbox: THREE.Box3,
  opts: CoilGeometryOptions,
): THREE.BufferGeometry {
  const size = new THREE.Vector3();
  bbox.getSize(size);
  const ctr = new THREE.Vector3();
  bbox.getCenter(ctr);

  if (size.x < 0.005 || size.y < 0.005 || size.z < 0.005) {
    return new THREE.BufferGeometry();
  }

  const wallH = size.y;
  const lengthIsX = size.x >= size.z;
  const wallLen   = lengthIsX ? size.x : size.z;
  const wallThick = lengthIsX ? size.z : size.x;

  const BEAD_WIDTH    = Math.min(0.044, wallThick * 0.45);
  const BEAD_HEIGHT   = 0.019;
  const LAYER_SPACING = 0.018; // 8% vertical compression squish

  const numLayers = Math.max(1, Math.floor(wallH / LAYER_SPACING));
  const uOrig  = lengthIsX ? ctr.x - wallLen / 2  : ctr.z - wallLen / 2;
  const wFront = lengthIsX ? ctr.z + wallThick / 2 : ctr.x + wallThick / 2;
  const wBack  = lengthIsX ? ctr.z - wallThick / 2 : ctr.x - wallThick / 2;
  const yBot   = ctr.y - wallH / 2;

  const positions: number[] = [];
  const normals:   number[] = [];
  const uvs:       number[] = [];
  const indices:   number[] = [];
  let vi = 0;

  for (let layer = 0; layer < numLayers; layer++) {
    const y = yBot + layer * LAYER_SPACING;
    const xOffset = (layer % 2) * (BEAD_WIDTH * 0.5);

    const layerNoiseWobble = pseudoNoise(layer, 17) * 0.002;
    const width  = BEAD_WIDTH  * (1 + pseudoNoise(layer, 12) * 0.02);
    const height = BEAD_HEIGHT * (1 + pseudoNoise(layer, 50) * 0.02);

    const profile = createCapsuleProfile(width, height);

    // Continuous toolpath extrusion along wall path length
    const uSteps = Math.max(24, Math.ceil(wallLen / 0.05));
    const baseIndexFront = vi;
    const waveLength = 0.12; // 12cm weave period along toolpath

    for (let uIdx = 0; uIdx <= uSteps; uIdx++) {
      const uFrac = uIdx / uSteps;
      const uPos = uFrac * wallLen;
      const uVal = uOrig + uPos;

      // Diagonal weaving phase shift along toolpath
      const weavePhase = (uPos / waveLength + (layer % 2) * 0.5) % 1.0;
      const weaveAngle = (weavePhase - 0.5) * Math.PI * 2;
      const weaveDisplace = Math.cos(weaveAngle) * 0.008;

      for (let pIdx = 0; pIdx < profile.length; pIdx++) {
        const pt = profile[pIdx];
        const px = uVal;
        const py = y + pt.y;
        const pz = wFront + pt.x + weaveDisplace + layerNoiseWobble;

        const pos: [number, number, number] = lengthIsX ? [px, py, pz] : [pz, py, px];
        const norm: [number, number, number] = lengthIsX ? [0, 0, 1] : [1, 0, 0];

        positions.push(pos[0], pos[1], pos[2]);
        normals.push(norm[0], norm[1], norm[2]);
        uvs.push(uFrac, pIdx / profile.length);
        vi++;
      }
    }

    for (let uIdx = 0; uIdx < uSteps; uIdx++) {
      for (let pIdx = 0; pIdx < profile.length - 1; pIdx++) {
        const a = baseIndexFront + uIdx * profile.length + pIdx;
        const b = baseIndexFront + (uIdx + 1) * profile.length + pIdx;
        const c = baseIndexFront + uIdx * profile.length + (pIdx + 1);
        const d = baseIndexFront + (uIdx + 1) * profile.length + (pIdx + 1);
        indices.push(a, b, c, b, d, c);
      }
    }

    // Back face toolpath extrusion
    const baseIndexBack = vi;
    for (let uIdx = 0; uIdx <= uSteps; uIdx++) {
      const uFrac = uIdx / uSteps;
      const uPos = uFrac * wallLen;
      const uVal = uOrig + uPos;

      const weavePhase = (uPos / waveLength + (layer % 2) * 0.5) % 1.0;
      const weaveAngle = (weavePhase - 0.5) * Math.PI * 2;
      const weaveDisplace = Math.cos(weaveAngle) * 0.008;

      for (let pIdx = 0; pIdx < profile.length; pIdx++) {
        const pt = profile[pIdx];
        const px = uVal;
        const py = y + pt.y;
        const pz = wBack - pt.x - weaveDisplace - layerNoiseWobble;

        const pos: [number, number, number] = lengthIsX ? [px, py, pz] : [pz, py, px];
        const norm: [number, number, number] = lengthIsX ? [0, 0, -1] : [-1, 0, 0];

        positions.push(pos[0], pos[1], pos[2]);
        normals.push(norm[0], norm[1], norm[2]);
        uvs.push(uFrac, pIdx / profile.length);
        vi++;
      }
    }

    for (let uIdx = 0; uIdx < uSteps; uIdx++) {
      for (let pIdx = 0; pIdx < profile.length - 1; pIdx++) {
        const a = baseIndexBack + uIdx * profile.length + pIdx;
        const b = baseIndexBack + (uIdx + 1) * profile.length + pIdx;
        const c = baseIndexBack + uIdx * profile.length + (pIdx + 1);
        const d = baseIndexBack + (uIdx + 1) * profile.length + (pIdx + 1);
        indices.push(a, c, b, b, c, d);
      }
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute('normal',   new THREE.Float32BufferAttribute(normals,   3));
  geo.setAttribute('uv',       new THREE.Float32BufferAttribute(uvs,       2));
  geo.setIndex(indices);
  geo.computeVertexNormals();

  return geo;
}

// ─── Geometry builder ───────────────────────────────────────────────────────

/**
 * Build a coiled-wall BufferGeometry with real extruded horizontal ridges.
 *
 * The bounding box should be the GEOMETRY's own bbox (local mesh space),
 * obtained via `mesh.geometry.computeBoundingBox(); mesh.geometry.boundingBox`.
 *
 * Wall orientation is auto-detected:
 *   - Y is always height (standing wall).
 *   - The thinner of X / Z is the wall thickness (displacement direction).
 *   - The longer of X / Z is the wall length.
 *
 * The returned geometry is in the same local coordinate space as the original.
 */
export function buildCoiledWallGeometry(
  bbox: THREE.Box3,
  opts: CoilGeometryOptions = {},
): THREE.BufferGeometry {
  const cfg = { ...DEFAULTS, ...opts };

  if (cfg.patternType === 'woven_rope') {
    return buildBeadWall(bbox, cfg);
  }

  const { coilPeriod, beadSharpness, segmentsPerCoil, widthSegments } = cfg;

  // ── Measure the wall ─────────────────────────────────────────────────────
  const size = new THREE.Vector3();
  bbox.getSize(size);
  const ctr = new THREE.Vector3();
  bbox.getCenter(ctr);

  if (size.x < 0.005 || size.y < 0.005 || size.z < 0.005) {
    return new THREE.BufferGeometry(); // degenerate – skip
  }

  // Walls always stand upright; Y = height.
  const wallH = size.y;

  // The thinner horizontal axis = thickness (where coils protrude).
  // The longer horizontal axis = length (where coils run).
  const lengthIsX = size.x >= size.z;
  const wallLen   = lengthIsX ? size.x : size.z;
  const wallThick = lengthIsX ? size.z : size.x;

  // Clamp amplitude so ridges don't exceed 55 % of wall thickness.
  const amp = Math.min(cfg.coilAmplitude, wallThick * 0.55);

  // ── Segment counts ────────────────────────────────────────────────────────
  const hSegs = Math.max(2, Math.ceil(wallH / coilPeriod)) * segmentsPerCoil;

  // For woven_rope: auto-compute wSegs so each blob column gets ≥6 vertices.
  // blobPeriodU = period * 1.7 (matches the constant in ridgeDisplace).
  let wSegs: number;
  if (cfg.patternType === 'woven_rope') {
    const blobPeriodU = coilPeriod * 1.7;
    wSegs = Math.max(16, Math.ceil(wallLen / blobPeriodU) * 6);
  } else {
    wSegs = Math.max(4, widthSegments);
  }

  // ── Coordinate helpers ───────────────────────────────────────────────────
  // Absolute positions in local space.
  const uOrig  = lengthIsX ? ctr.x - wallLen / 2   : ctr.z - wallLen / 2;
  const wFront = lengthIsX ? ctr.z + wallThick / 2  : ctr.x + wallThick / 2;
  const wBack  = lengthIsX ? ctr.z - wallThick / 2  : ctr.x - wallThick / 2;
  const yBot   = ctr.y - wallH / 2;

  /** World-space position on the front (+w) face. */
  function fPos(uFrac: number, vFrac: number, disp: number): [number, number, number] {
    const u = uOrig + uFrac * wallLen;
    const y = yBot  + vFrac * wallH;
    const w = wFront + disp;
    return lengthIsX ? [u, y, w] : [w, y, u];
  }

  /** World-space position on the back (−w) face. */
  function bPos(uFrac: number, vFrac: number, disp: number): [number, number, number] {
    const u = uOrig + uFrac * wallLen;
    const y = yBot  + vFrac * wallH;
    const w = wBack - disp;
    return lengthIsX ? [u, y, w] : [w, y, u];
  }

  /**
   * Surface normal for the front (+w) or back (−w) face.
   * wSign = +1 for front, −1 for back.
   * slope = dDisp/dLocalY at this vertex.
   */
  function faceNormal(wSign: 1 | -1, slope: number): [number, number, number] {
    // Tangent vectors on the face:
    //   T_u = (1, 0, 0)          (no displacement along u)
    //   T_v = (0, 1, wSign·slope) (displacement varies with v)
    // Normal = T_u × T_v = (0·wSign·slope − 0·1, 0·0 − 1·wSign·slope, 1·1 − 0·0)
    //        = (0, −wSign·slope, 1)  →  normalise
    const nLen = Math.hypot(1, slope);
    const nv = (-wSign * slope) / nLen;
    const nw = wSign / nLen;
    return lengthIsX ? [0, nv, nw] : [nw, nv, 0];
  }

  /** Normal for the −u end cap. */
  function leftNorm(): [number, number, number] {
    return lengthIsX ? [-1, 0, 0] : [0, 0, -1];
  }

  /** Normal for the +u end cap. */
  function rightNorm(): [number, number, number] {
    return lengthIsX ? [1, 0, 0] : [0, 0, 1];
  }

  // ── Buffer arrays ─────────────────────────────────────────────────────────
  const positions: number[] = [];
  const normals_:  number[] = [];
  const uvs:       number[] = [];
  const indices:   number[] = [];
  let vi = 0;

  function push3(arr: number[], a: number, b: number, c: number) {
    arr.push(a, b, c);
  }

  function addVertex(
    pos:  [number, number, number],
    norm: [number, number, number],
    u: number,
    v: number,
  ) {
    push3(positions, pos[0],  pos[1],  pos[2]);
    push3(normals_,  norm[0], norm[1], norm[2]);
    uvs.push(u, v);
    vi++;
  }

  // ── Front face (+w, facing outward) ──────────────────────────────────────
  const frontBase = vi;
  for (let j = 0; j <= hSegs; j++) {
    const vf     = j / hSegs;
    const localY = vf * wallH;

    for (let i = 0; i <= wSegs; i++) {
      const uf     = i / wSegs;
      const localU = uf * wallLen;
      const disp   = ridgeDisplace(localY, coilPeriod, amp, beadSharpness, cfg.patternType, localU);
      const slope  = ridgeSlope   (localY, coilPeriod, amp, beadSharpness, cfg.patternType, localU);
      const norm   = faceNormal(+1, slope);
      addVertex(fPos(uf, vf, disp), norm, uf, vf);
    }
  }
  for (let j = 0; j < hSegs; j++) {
    for (let i = 0; i < wSegs; i++) {
      const a = frontBase + j * (wSegs + 1) + i;
      const b = frontBase + j * (wSegs + 1) + i + 1;
      const c = frontBase + (j + 1) * (wSegs + 1) + i;
      const d = frontBase + (j + 1) * (wSegs + 1) + i + 1;
      // CCW from outside (+w side): BL BR TL / BR TR TL
      indices.push(a, b, c, b, d, c);
    }
  }

  // ── Back face (−w, reversed u for correct winding from outside) ───────────
  const backBase = vi;
  for (let j = 0; j <= hSegs; j++) {
    const vf     = j / hSegs;
    const localY = vf * wallH;

    for (let i = 0; i <= wSegs; i++) {
      const uf     = 1 - i / wSegs;
      const localU = uf * wallLen;
      const disp   = ridgeDisplace(localY, coilPeriod, amp, beadSharpness, cfg.patternType, localU);
      const slope  = ridgeSlope   (localY, coilPeriod, amp, beadSharpness, cfg.patternType, localU);
      const norm   = faceNormal(-1, slope);
      addVertex(bPos(uf, vf, disp), norm, i / wSegs, vf);
    }
  }
  for (let j = 0; j < hSegs; j++) {
    for (let i = 0; i < wSegs; i++) {
      const a = backBase + j * (wSegs + 1) + i;
      const b = backBase + j * (wSegs + 1) + i + 1;
      const c = backBase + (j + 1) * (wSegs + 1) + i;
      const d = backBase + (j + 1) * (wSegs + 1) + i + 1;
      indices.push(a, b, c, b, d, c);
    }
  }

  // ── Left end cap (u = 0, facing −u direction) ─────────────────────────────
  // Smoothly curves around from front (+w) to back (−w) with a solid blunt rounded end
  const capSegs = 8;
  const leftBase = vi;
  for (let j = 0; j <= hSegs; j++) {
    const vf     = j / hSegs;
    const localY = vf * wallH;
    const disp   = ridgeDisplace(localY, coilPeriod, amp, beadSharpness, cfg.patternType, 0);
    const r      = (wallThick / 2) + disp;
    for (let c = 0; c <= capSegs; c++) {
      const angle = (c / capSegs) * Math.PI; // 0 (front +w) -> Math.PI (back -w)
      const cosA  = Math.cos(angle);
      const sinA  = Math.sin(angle);
      const u     = uOrig - sinA * r;
      const w     = ctr.z + cosA * r;
      const y     = yBot + vf * wallH;
      const pos: [number, number, number] = lengthIsX ? [u, y, w] : [w, y, u];
      const norm: [number, number, number] = lengthIsX ? [-sinA, 0, cosA] : [cosA, 0, -sinA];
      addVertex(pos, norm, c / capSegs, vf);
    }
  }
  for (let j = 0; j < hSegs; j++) {
    for (let c = 0; c < capSegs; c++) {
      const a = leftBase + j * (capSegs + 1) + c;
      const b = leftBase + j * (capSegs + 1) + c + 1;
      const d = leftBase + (j + 1) * (capSegs + 1) + c;
      const e = leftBase + (j + 1) * (capSegs + 1) + c + 1;
      indices.push(a, b, d, b, e, d);
    }
  }

  // ── Right end cap (u = 1, facing +u direction) ────────────────────────────
  const rightBase = vi;
  for (let j = 0; j <= hSegs; j++) {
    const vf     = j / hSegs;
    const localY = vf * wallH;
    const disp   = ridgeDisplace(localY, coilPeriod, amp, beadSharpness, cfg.patternType, wallLen);
    const r      = (wallThick / 2) + disp;
    for (let c = 0; c <= capSegs; c++) {
      const angle = (c / capSegs) * Math.PI; // 0 (back -w) -> Math.PI (front +w)
      const cosA  = Math.cos(angle);
      const sinA  = Math.sin(angle);
      const u     = uOrig + wallLen + sinA * r;
      const w     = ctr.z - cosA * r;
      const y     = yBot + vf * wallH;
      const pos: [number, number, number] = lengthIsX ? [u, y, w] : [w, y, u];
      const norm: [number, number, number] = lengthIsX ? [sinA, 0, -cosA] : [-cosA, 0, sinA];
      addVertex(pos, norm, c / capSegs, vf);
    }
  }
  for (let j = 0; j < hSegs; j++) {
    for (let c = 0; c < capSegs; c++) {
      const a = rightBase + j * (capSegs + 1) + c;
      const b = rightBase + j * (capSegs + 1) + c + 1;
      const d = rightBase + (j + 1) * (capSegs + 1) + c;
      const e = rightBase + (j + 1) * (capSegs + 1) + c + 1;
      indices.push(a, b, d, b, e, d);
    }
  }

  // ── Top cap (+Y) ──────────────────────────────────────────────────────────
  // Continuous solid top cover connecting outer wall faces and rounded corners
  const dispTop = ridgeDisplace(wallH, coilPeriod, amp, beadSharpness);
  const topN: [number, number, number] = [0, 1, 0];
  const topBase = vi;
  addVertex(fPos(0, 1, dispTop), topN, 0, 0);
  addVertex(fPos(1, 1, dispTop), topN, 1, 0);
  addVertex(bPos(0, 1, dispTop), topN, 0, 1);
  addVertex(bPos(1, 1, dispTop), topN, 1, 1);
  indices.push(topBase, topBase + 1, topBase + 2, topBase + 1, topBase + 3, topBase + 2);

  // ── Bottom cap (−Y) ───────────────────────────────────────────────────────
  const dispBot = ridgeDisplace(0, coilPeriod, amp, beadSharpness);
  const botN: [number, number, number] = [0, -1, 0];
  const botBase = vi;
  addVertex(bPos(0, 0, dispBot), botN, 0, 0);
  addVertex(bPos(1, 0, dispBot), botN, 1, 0);
  addVertex(fPos(0, 0, dispBot), botN, 0, 1);
  addVertex(fPos(1, 0, dispBot), botN, 1, 1);
  indices.push(botBase, botBase + 1, botBase + 2, botBase + 1, botBase + 3, botBase + 2);

  // ── Assemble ──────────────────────────────────────────────────────────────
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute('normal',   new THREE.Float32BufferAttribute(normals_,  3));
  geo.setAttribute('uv',       new THREE.Float32BufferAttribute(uvs,       2));
  geo.setIndex(indices);

  return geo;
}
