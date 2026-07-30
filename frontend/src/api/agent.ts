/** Client types for the multi-agent orchestrator. */

export interface AgentChatSelection {
  id?: string;
  meshRefs?: Array<{ objectName?: string; meshUuid?: string }>;
  faceRefs?: Array<{ meshRef?: { objectName?: string }; faceIndex?: number }>;
  metadata?: Record<string, unknown>;
}

export interface AgentChatRequest {
  prompt: string;
  selection: AgentChatSelection;
  project_id?: string;
  conversation?: Array<Record<string, unknown>>;
  available_patterns?: string[];
  available_materials?: string[];
}

export interface AgentInvocation {
  tool: string;
  arguments: Record<string, unknown>;
  operation_id?: string;
}

export interface AgentChatResponse {
  intent: 'design' | 'geometry' | 'mixed' | 'clarify' | 'reject' | string;
  invoked_agents: string[];
  design_operations: Array<Record<string, unknown>>;
  geometry_tool_calls: Array<Record<string, unknown>>;
  execution_invocations: AgentInvocation[];
  fallback_to_script: boolean;
  clarification?: string | null;
  error?: string | null;
  notes: string[];
  trace_ids: string[];
  runner?: {
    applied: AgentInvocation[];
    deferred: AgentInvocation[];
    warnings: string[];
    fallback_to_script: boolean;
    export_paths: string[];
  } | null;
}

export interface AgentLogEntry {
  id: string;
  ts: number;
  step: string;
  project_id?: string;
  [key: string]: unknown;
}

const API_BASE_URL = 'http://localhost:8000/api';

export async function postAgentChat(req: AgentChatRequest): Promise<AgentChatResponse> {
  const response = await fetch(`${API_BASE_URL}/agent/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  return response.json();
}

export async function fetchAgentLog(
  projectId?: string,
  limit = 50,
): Promise<{ items: AgentLogEntry[] }> {
  const qs = new URLSearchParams();
  if (projectId) qs.set('project_id', projectId);
  qs.set('limit', String(limit));
  const response = await fetch(`${API_BASE_URL}/agent/log?${qs.toString()}`);
  return response.json();
}