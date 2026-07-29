/**
 * Lightweight browser-side material pattern previews.
 *
 * Blender remains the single source of truth for shaders; the browser only
 * renders CSS previews so the editing panel can show what a region will look
 * like without shipping the entire geometry-nodes tree.
 *
 * Pattern IDs mirror the backend `WallMaterialOptions.pattern` enum so the AI
 * planner and the panel stay in lock-step.
 */

export type PatternId =
  | 'none'
  | 'smooth'
  | 'stacked_coils'
  | 'woven_rope'
  | 'ribbed'
  | 'brick'
  | 'wave';

export interface PatternDefinition {
  id: PatternId;
  name: string;
  description: string;
  /** Mirrors backend `WallMaterialOptions.pattern`. */
  blenderPattern: 'none' | 'stacked_coils' | 'woven_rope';
  /** CSS background for the UI swatch preview. */
  previewStyle: (baseColor: string, ridgeShade: string) => React.CSSProperties;
}

export interface MaterialPreset {
  id: string;
  name: string;
  color: string;
  pattern: PatternId;
}

export const PATTERN_LIBRARY: PatternDefinition[] = [
  {
    id: 'smooth',
    name: 'Smooth',
    description: 'Flat painted finish. No surface relief.',
    blenderPattern: 'none',
    previewStyle: (base) => ({
      background: base,
    }),
  },
  {
    id: 'none',
    name: 'Default',
    description: 'Use project default wall finish.',
    blenderPattern: 'none',
    previewStyle: (base, ridge) => ({
      background: `repeating-linear-gradient(45deg, ${base} 0 6px, ${ridge} 6px 7px)`,
    }),
  },
  {
    id: 'stacked_coils',
    name: 'Stacked coils',
    description: 'Horizontal print-coil ridges.',
    blenderPattern: 'stacked_coils',
    previewStyle: (base, ridge) => ({
      background: `repeating-linear-gradient(
        to bottom,
        ${base} 0 6px,
        ${ridge} 6px 8px,
        ${base} 8px 14px
      )`,
    }),
  },
  {
    id: 'woven_rope',
    name: 'Woven rope',
    description: 'Cross-hatched extruded filament pattern.',
    blenderPattern: 'woven_rope',
    previewStyle: (base, ridge) => ({
      background: `repeating-linear-gradient(
        to right,
        ${base} 0 5px,
        ${ridge} 5px 7px
      ), repeating-linear-gradient(
        to bottom,
        ${base} 0 5px,
        ${ridge} 5px 7px
      )`,
      backgroundBlendMode: 'multiply',
    }),
  },
  {
    id: 'ribbed',
    name: 'Ribbed',
    description: 'Tall vertical ribs (browser preview only).',
    blenderPattern: 'stacked_coils',
    previewStyle: (base, ridge) => ({
      background: `repeating-linear-gradient(
        to right,
        ${base} 0 4px,
        ${ridge} 4px 6px
      )`,
    }),
  },
  {
    id: 'brick',
    name: 'Brick',
    description: 'Stacked brick courses (browser preview only).',
    blenderPattern: 'stacked_coils',
    previewStyle: (base, ridge) => ({
      background: `repeating-linear-gradient(
        to bottom,
        ${base} 0 8px,
        ${ridge} 8px 9px
      )`,
      backgroundSize: '100% 16px',
    }),
  },
  {
    id: 'wave',
    name: 'Wave',
    description: 'Sinusoidal print ridges (browser preview only).',
    blenderPattern: 'stacked_coils',
    previewStyle: (base, ridge) => ({
      background: `radial-gradient(circle at 50% 50%, ${ridge} 0 1.5px, ${base} 1.5px 4px)`,
      backgroundSize: '10px 10px',
    }),
  },
];

export const MATERIAL_PRESETS: MaterialPreset[] = [
  { id: 'warm_modern', name: 'Warm modern', color: '#D8C8B8', pattern: 'smooth' },
  { id: 'painted_white', name: 'Painted white', color: '#F5F5F0', pattern: 'smooth' },
  { id: 'cool_modern', name: 'Cool modern', color: '#C8D0D8', pattern: 'ribbed' },
  { id: 'sage', name: 'Sage', color: '#9CAF88', pattern: 'stacked_coils' },
  { id: 'sand', name: 'Sand', color: '#D4C4A8', pattern: 'brick' },
  { id: 'navy', name: 'Navy', color: '#34495E', pattern: 'ribbed' },
  { id: 'clay', name: 'Clay', color: '#7A2915', pattern: 'stacked_coils' },
  { id: 'blush', name: 'Blush', color: '#AF756E', pattern: 'smooth' },
  { id: 'charcoal', name: 'Charcoal', color: '#3D3D3D', pattern: 'woven_rope' },
  { id: 'olive', name: 'Olive', color: '#34391E', pattern: 'stacked_coils' },
  { id: 'sky', name: 'Sky', color: '#6592AF', pattern: 'wave' },
  { id: 'stacked_coils_white', name: 'Stacked coils — white', color: '#F0F0F0', pattern: 'stacked_coils' },
  { id: 'woven_rope_natural', name: 'Woven rope — natural', color: '#C4A882', pattern: 'woven_rope' },
  { id: 'custom', name: 'Custom', color: '#9CA3AF', pattern: 'smooth' },
];

/** Blend a hex colour towards black (factor < 1) or white (factor > 1). */
export function shadeHex(hex: string, factor: number): string {
  if (!/^#[0-9a-f]{6}$/i.test(hex)) return hex;
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const blend = (c: number) => {
    const target = factor < 1 ? 0 : 255;
    const t = Math.min(1, Math.abs(factor - (factor < 1 ? 0 : 1)));
    return Math.round(c + (target - c) * t);
  };
  const out = (n: number) => n.toString(16).padStart(2, '0');
  return `#${out(blend(r))}${out(blend(g))}${out(blend(b))}`;
}

export function findPattern(id: string | undefined): PatternDefinition | undefined {
  return PATTERN_LIBRARY.find((p) => p.id === id);
}

export function findPreset(id: string | undefined): MaterialPreset | undefined {
  return MATERIAL_PRESETS.find((p) => p.id === id);
}