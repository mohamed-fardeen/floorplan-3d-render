import React from 'react';
import type { MaterialOptions } from '../api/client';

interface DesignOptionsProps {
  includeBase: boolean;
  includeRoof: boolean;
  materials: MaterialOptions;
  onIncludeBaseChange: (value: boolean) => void;
  onIncludeRoofChange: (value: boolean) => void;
  onMaterialsChange: (value: MaterialOptions) => void;
  onContinue: () => void;
  onBack: () => void;
}

const WALL_THEMES = [
  { id: 'warm_modern', name: 'Warm Modern', color: '#D8C8B8' },
  { id: 'painted_white', name: 'Clean White', color: '#F2F2F2' },
  { id: 'cool_modern', name: 'Cool Grey', color: '#B9C2C9' },
  { id: 'sage', name: 'Sage', color: '#AEB9A3' },
  { id: 'sand', name: 'Soft Sand', color: '#D9C7A7' },
  { id: 'navy', name: 'Deep Navy', color: '#34495E' },
  { id: 'clay', name: 'Clay', color: '#B86F52' },
  { id: 'blush', name: 'Soft Blush', color: '#D8B4B0' },
  { id: 'charcoal', name: 'Charcoal', color: '#4A4D50' },
  { id: 'olive', name: 'Olive', color: '#7D8260' },
  { id: 'sky', name: 'Sky Blue', color: '#A9C7D8' },
  { id: 'custom', name: 'Custom', color: null },
];

const FLOOR_DESIGNS = [
  { id: 'square_grid', name: 'Classic Tile', colors: ['#E8E3D9', '#B8B5AE'] },
  { id: 'checker', name: 'Checker', colors: ['#F1EEE8', '#424242'] },
  { id: 'terracotta', name: 'Terracotta', colors: ['#B86645', '#D9A17E'] },
  { id: 'marble', name: 'Marble', colors: ['#E8E8E4', '#9EA3A6'] },
  { id: 'slate', name: 'Slate', colors: ['#59636A', '#89939A'] },
  { id: 'wood', name: 'Wood', colors: ['#8B5E3C', '#C18B5D'] },
  { id: 'mosaic', name: 'Mosaic', colors: ['#4F8F8B', '#E5D5B5'] },
  { id: 'sandstone', name: 'Sandstone', colors: ['#C8AD82', '#E0CDAA'] },
  { id: 'granite', name: 'Granite', colors: ['#575757', '#A0A0A0'] },
  { id: 'solid', name: 'Solid', colors: ['#A77A50', '#A77A50'] },
  { id: 'custom', name: 'Custom', colors: null },
];

const WALL_PATTERNS = [
  { id: 'none', name: 'Smooth', preview: 'solid' },
  { id: 'stacked_coils', name: '3D printed', preview: 'stacked' },
];

/** Darken a #RRGGBB colour for ridge preview shading (same hue as the wall). */
function shadeHex(hex: string, factor: number): string {
  const raw = hex.replace('#', '');
  if (raw.length !== 6) return hex;
  const ch = (i: number) =>
    Math.max(0, Math.min(255, Math.round(parseInt(raw.slice(i, i + 2), 16) * factor)))
      .toString(16)
      .padStart(2, '0');
  return `#${ch(0)}${ch(2)}${ch(4)}`;
}

export const DesignOptions: React.FC<DesignOptionsProps> = ({
  includeBase,
  includeRoof,
  materials,
  onIncludeBaseChange,
  onIncludeRoofChange,
  onMaterialsChange,
  onContinue,
  onBack,
}) => {
  const ridgeShade = shadeHex(materials.walls.color, 0.72);

  const setWallTheme = (theme: string, color: string | null) => {
    onMaterialsChange({
      ...materials,
      walls: { ...materials.walls, theme, ...(color ? { color } : {}) },
    });
  };

  const setFloorDesign = (design: string, colors: string[] | null) => {
    onMaterialsChange({
      ...materials,
      floor: {
        ...materials.floor,
        design,
        ...(colors ? { primary_color: colors[0], secondary_color: colors[1] } : {}),
      },
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-10 font-sans">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">Choose Your 3D Design</h1>
          <p className="mt-2 text-gray-500">These finishes will be applied to the Blender model.</p>
        </div>

        <div className="space-y-6 rounded-2xl bg-white p-6 shadow-lg sm:p-8">
          <section>
            <h2 className="mb-4 text-xl font-semibold text-gray-900">Structure</h2>
            <div className="flex flex-wrap gap-6">
              <label className="flex cursor-pointer items-center gap-2">
                <input type="checkbox" checked={includeBase} onChange={(e) => onIncludeBaseChange(e.target.checked)} className="h-4 w-4 accent-indigo-600" />
                <span className="font-medium">Floor</span>
              </label>
              <label className="flex cursor-pointer items-center gap-2">
                <input type="checkbox" checked={includeRoof} onChange={(e) => onIncludeRoofChange(e.target.checked)} className="h-4 w-4 accent-indigo-600" />
                <span className="font-medium">Ceiling</span>
              </label>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-xl font-semibold text-gray-900">Wall colour</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-6">
              {WALL_THEMES.map((theme) => (
                <button key={theme.id} type="button" onClick={() => setWallTheme(theme.id, theme.color)} className={`rounded-xl border-2 p-3 text-left transition ${materials.walls.theme === theme.id ? 'border-indigo-600 ring-2 ring-indigo-100' : 'border-gray-200 hover:border-gray-300'}`}>
                  <div className="mb-2 h-14 rounded-lg border border-black/10" style={{ backgroundColor: theme.color || materials.walls.color }} />
                  <span className="text-sm font-medium text-gray-800">{theme.name}</span>
                </button>
              ))}
            </div>
            {materials.walls.theme === 'custom' && (
              <label className="mt-4 flex items-center gap-3 text-sm font-medium text-gray-700">
                Custom wall colour
                <input type="color" value={materials.walls.color} onChange={(e) => onMaterialsChange({ ...materials, walls: { ...materials.walls, color: e.target.value } })} className="h-10 w-16 cursor-pointer rounded border border-gray-300" />
                <span className="font-mono">{materials.walls.color.toUpperCase()}</span>
              </label>
            )}
            <div className="mt-6">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-700">Wall texture</h3>
              <div className="grid grid-cols-3 gap-3">
                {WALL_PATTERNS.map((pattern) => (
                  <button key={pattern.id} type="button" onClick={() => onMaterialsChange({ ...materials, walls: { ...materials.walls, pattern: pattern.id } })} className={`overflow-hidden rounded-xl border-2 p-2 text-left transition ${materials.walls.pattern === pattern.id ? 'border-indigo-600 ring-2 ring-indigo-100' : 'border-gray-200 hover:border-gray-300'}`}>
                    <div className="mb-2 h-16 rounded-lg border border-black/10" style={{
                      backgroundColor: materials.walls.color,
                      backgroundImage: pattern.preview === 'stacked'
                        ? `repeating-linear-gradient(0deg, ${ridgeShade} 0 5px, ${materials.walls.color} 5px 11px)`
                        : pattern.preview === 'woven'
                          ? `repeating-linear-gradient(0deg, ${ridgeShade} 0 5px, ${materials.walls.color} 5px 11px), repeating-linear-gradient(90deg, transparent 0 11px, ${ridgeShade} 11px 13px)`
                          : 'none',
                    }} />
                    <span className="text-sm font-medium text-gray-800">{pattern.name}</span>
                  </button>
                ))}
              </div>
              {materials.walls.pattern !== 'none' && (
                <p className="mt-3 text-sm text-gray-500">
                  Ridges use the same colour as the wall — applied as a Blender shader (Material Preview / Rendered view).
                </p>
              )}
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-xl font-semibold text-gray-900">Floor tile design</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-6">
              {FLOOR_DESIGNS.map((design) => {
                const colors = design.colors || [materials.floor.primary_color, materials.floor.secondary_color];
                return (
                  <button key={design.id} type="button" onClick={() => setFloorDesign(design.id, design.colors)} className={`rounded-xl border-2 p-3 text-left transition ${materials.floor.design === design.id ? 'border-indigo-600 ring-2 ring-indigo-100' : 'border-gray-200 hover:border-gray-300'}`}>
                    <div className="mb-2 h-14 rounded-lg border border-black/10" style={{ background: `conic-gradient(${colors[0]} 25%, ${colors[1]} 0 50%, ${colors[0]} 0 75%, ${colors[1]} 0) 0 0 / 22px 22px` }} />
                    <span className="text-sm font-medium text-gray-800">{design.name}</span>
                  </button>
                );
              })}
            </div>
            {materials.floor.design === 'custom' && (
              <div className="mt-4 flex flex-wrap gap-6">
                <label className="flex items-center gap-3 text-sm font-medium text-gray-700">Tile colour <input type="color" value={materials.floor.primary_color} onChange={(e) => onMaterialsChange({ ...materials, floor: { ...materials.floor, primary_color: e.target.value } })} className="h-10 w-16 cursor-pointer rounded border border-gray-300" /></label>
                <label className="flex items-center gap-3 text-sm font-medium text-gray-700">Accent colour <input type="color" value={materials.floor.secondary_color} onChange={(e) => onMaterialsChange({ ...materials, floor: { ...materials.floor, secondary_color: e.target.value } })} className="h-10 w-16 cursor-pointer rounded border border-gray-300" /></label>
              </div>
            )}
          </section>

          <div className="flex justify-between border-t border-gray-200 pt-6">
            <button type="button" onClick={onBack} className="rounded-lg border border-gray-300 px-5 py-2.5 font-medium text-gray-700 hover:bg-gray-50">Back</button>
            <button type="button" onClick={onContinue} className="rounded-lg bg-indigo-600 px-6 py-2.5 font-semibold text-white hover:bg-indigo-700">Continue to Annotation</button>
          </div>
        </div>
      </div>
    </div>
  );
};
