import axios from 'axios';
import type { DesignOperation, Selection } from '../types/selection';

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

export interface DesignApplyRequest {
  scene_graph: unknown;
  selection: Selection;
  operations: DesignOperation[];
  material_options: MaterialOptions;
  include_base?: boolean;
  include_roof?: boolean;
}

export const applyDesignActions = async (
  req: DesignApplyRequest,
  opts: { signal?: AbortSignal } = {},
): Promise<any> => {
  try {
    const response = await fetch(`${API_BASE_URL}/design/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scene_graph: req.scene_graph,
        selection: req.selection,
        operations: req.operations,
        material_options: req.material_options,
        include_base: req.include_base ?? true,
        include_roof: req.include_roof ?? false,
      }),
      signal: opts.signal,
    });
    return await response.json();
  } catch (error) {
    // AbortError is the caller's signal firing — let it propagate so they
    // can distinguish a user-initiated cancel from a network/parse failure.
    if ((error as { name?: string })?.name === 'AbortError') {
      throw error;
    }
    console.error('API Error (applyDesignActions):', error);
    return { status: 'error', detail: String(error) };
  }
};

export const planDesignFromPrompt = async (req: {
  prompt: string;
  selection_summary?: Record<string, unknown>;
}): Promise<any> => {
  try {
    const response = await fetch(`${API_BASE_URL}/design/ai-plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return await response.json();
  } catch (error) {
    console.error('API Error (planDesignFromPrompt):', error);
    return { status: 'error', detail: String(error) };
  }
};

export interface DesignProgressEvent {
  stage: string;
  message: string;
  ts?: number;
  [key: string]: unknown;
}

/**
 * Open an EventSource for design progress. Returns the EventSource and a
 * cleanup function. The caller subscribes to `onEvent` for each payload.
 */
export function openDesignStream(
  onEvent: (event: DesignProgressEvent) => void,
  onError?: (err: Event) => void,
): { source: EventSource; close: () => void } {
  const source = new EventSource(`${API_BASE_URL}/design/stream`);
  const handler = (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data) as DesignProgressEvent;
      onEvent(data);
    } catch (err) {
      console.warn('[stream] failed to parse event', err);
    }
  };
  source.addEventListener('data' as never, handler as never);
  source.onerror = (e) => {
    if (onError) onError(e);
  };
  return {
    source,
    close: () => {
      source.removeEventListener('data' as never, handler as never);
      source.close();
    },
  };
}

export async function launchBlenderMcp(
  blendPath?: string,
): Promise<{ status: string; pid?: number; log?: string; detail?: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/mcp/launch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(blendPath ? { blend_path: blendPath } : {}),
    });
    if (!response.ok) {
      const errBody = await response.json().catch(() => ({ detail: response.statusText }));
      return { status: 'error', detail: errBody.detail || response.statusText };
    }
    return await response.json();
  } catch (error) {
    console.error('API Error (launchBlenderMcp):', error);
    return { status: 'error', detail: String(error) };
  }
}

export async function getBlenderMcpStatus(): Promise<{ available: boolean; info?: unknown }> {
  try {
    const response = await fetch(`${API_BASE_URL}/mcp/status`);
    return await response.json();
  } catch (error) {
    console.error('API Error (getBlenderMcpStatus):', error);
    return { available: false };
  }
}

export async function getBlenderMcpLog(): Promise<string> {
  try {
    const response = await fetch(`${API_BASE_URL}/mcp/log?limit=4000`);
    const data = await response.json();
    return data.log || '';
  } catch {
    return '';
  }
}

export async function getBlenderMcpInfo(): Promise<{
  blender_executable: string | null;
  blender_on_path: boolean;
  addon_module: string;
  socket_port: number;
}> {
  try {
    const response = await fetch(`${API_BASE_URL}/mcp/info`);
    return await response.json();
  } catch {
    return { blender_executable: null, blender_on_path: false, addon_module: 'floorplan_mcp_addon', socket_port: 6789 };
  }
}
