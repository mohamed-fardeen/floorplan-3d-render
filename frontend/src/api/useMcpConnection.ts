import { useEffect, useState } from 'react';
import { getBlenderMcpStatus } from './client';

export interface McpConnectionState {
  available: boolean;
  attempts: number;
  error: string | null;
}

/**
 * Polls /api/mcp/status every second while the editor is open. Used by the
 * Sidebar MCP card to surface "Live MCP" status and by EditingPanel to know
 * when it's safe to dispatch live commands.
 */
export function useMcpConnection(intervalMs = 1500): McpConnectionState {
  const [state, setState] = useState<McpConnectionState>({
    available: false,
    attempts: 0,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    let attempts = 0;
    const tick = async () => {
      try {
        const status = await getBlenderMcpStatus();
        if (cancelled) return;
        attempts += 1;
        setState({
          available: status.available,
          attempts,
          error: status.available ? null : null,
        });
      } catch (err) {
        if (cancelled) return;
        attempts += 1;
        setState({
          available: false,
          attempts,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    };
    tick();
    const handle = window.setInterval(tick, intervalMs);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, [intervalMs]);

  return state;
}