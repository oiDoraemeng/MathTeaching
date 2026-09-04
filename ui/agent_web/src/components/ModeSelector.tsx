import type { AgentMode, IntentSender } from "../types";
export function ModeSelector({ mode, onChange }: { mode: AgentMode; onChange: (mode: AgentMode) => void }) {
  return <label className="mode-selector"><span className="sr-only">助手模式</span><select value={mode} onChange={(event) => onChange(event.target.value as AgentMode)} aria-label="助手模式"><option value="Agent">代理</option><option value="Ask">问答</option><option value="Plan">计划</option></select></label>;
}
export function modeIntent(mode: AgentMode, sessionId: string): Parameters<IntentSender>[0] { return { protocol_version: 1, type: "change_mode", request_id: crypto.randomUUID(), session_id: sessionId, payload: { mode } }; }
