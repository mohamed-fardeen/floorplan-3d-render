import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

export const uploadAndParse = async (file: File, model: string = 'multi') => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('model', model);
  
  const response = await apiClient.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const validateGraph = async (sceneGraph: any) => {
  const response = await apiClient.post('/validate', { scene_graph: sceneGraph });
  return response.data;
};

export interface MaterialOptions {
  walls: {
    theme: string;
    color: string;
    pattern: string;
    pattern_color: string;
  };
  floor: {
    design: string;
    primary_color: string;
    secondary_color: string;
    grout_color: string;
    tile_size_m: number;
  };
}

export const exportBlender = async (
  sceneGraph: any, 
  includeBase: boolean = true, 
  includeRoof: boolean = false,
  materialOptions?: MaterialOptions,
  openBlender: boolean = false,
): Promise<any> => {
  try {
    const response = await fetch(`${API_BASE_URL}/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        scene_graph: sceneGraph,
        include_base: includeBase,
        include_roof: includeRoof,
        material_options: materialOptions,
        open_blender: openBlender,
      }),
    });
    return await response.json();
  } catch (error) {
    console.error('API Error (exportBlender):', error);
    return { status: 'error', detail: String(error) };
  }
};
