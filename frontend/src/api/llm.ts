const API_BASE_URL = 'http://localhost:8000/api';

export interface LlmProviderStatus {
  name: string;
  available: boolean;
}

export async function fetchLlmProviders(): Promise<LlmProviderStatus[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/agent/providers`);
    const data = await response.json();
    return data.providers || [];
  } catch {
    return [];
  }
}