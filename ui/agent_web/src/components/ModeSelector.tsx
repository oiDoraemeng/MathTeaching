import type { AgentMode, IntentSender } from "../types";
export function ModeSelector({ mode, onChange }: { mode: AgentMode; onChange: (mode: AgentMode) => void }) {
  return <label className="mode-selector"><span className="sr-only">Agent 模式</span><select value={mode} onChange={(event) => onChange(event.target.value as AgentMode)} aria-label="Agent 模式"><option value="Agent">Agent</option><option value="Ask">Ask</option><option value="Plan">Plan</option></select></label>;
}
export function modeIntent(mode: AgentMode, sessionId: string): Parameters<IntentSender>[0] { return { protocol_version: 1, type: "change_mode", request_id: crypto.randomUUID(), session_id: sessionId, payload: { mode } }; }
