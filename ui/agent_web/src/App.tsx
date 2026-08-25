import { useEffect, useMemo, useReducer, useState } from "react";
import { AgentHeader } from "./components/AgentHeader";
import { Composer } from "./components/Composer";
import { EmptyState } from "./components/EmptyState";
import { SessionTabs } from "./components/SessionTabs";
import { Timeline } from "./components/Timeline";
import { createQtBridge } from "./bridge/qtBridge";
import { appReducer, initialSession, initialState } from "./state/reducer";
import type { ClientIntent } from "./types";
import "./styles/theme.css";
import "./styles/layout.css";

export function App() {
  const [state, dispatch] = useReducer(appReducer, undefined, initialState);
  const [busy, setBusy] = useState(false);
  const bridge = useMemo(() => createQtBridge(), []);
  const session = state.sessions.find((item) => item.id === state.activeSessionId) ?? state.sessions[0];
  useEffect(() => { bridge.attach(dispatch); bridge.requestSnapshot(session.id); return () => bridge.detach(); }, [bridge, session.id]);
  useEffect(() => { const latest = session.turns.at(-1); setBusy(Boolean(latest && latest.status === "running")); }, [session.turns]);
  const sendIntent = (intent: ClientIntent) => {
    if (intent.type === "stop_turn") setBusy(false);
    if (intent.type === "change_mode") dispatch({ type: "update_session_preferences", sessionId: intent.session_id, mode: String(intent.payload.mode) as "Agent" | "Ask" | "Plan" });
    if (intent.type === "change_execution_mode") dispatch({ type: "update_session_preferences", sessionId: intent.session_id, executionMode: String(intent.payload.execution_mode) as "confirm" | "continuous" });
    if (intent.type === "change_model") dispatch({ type: "update_session_preferences", sessionId: intent.session_id, model: String(intent.payload.model) });
    bridge.send(intent);
  };
  const newChat = () => {
    const id = `session-${crypto.randomUUID()}`;
    dispatch({ type: "snapshot_loaded", snapshot: { sessions: [...state.sessions, { ...initialSession(), id }], active_session_id: id } });
    bridge.send({ protocol_version: 1, type: "create_session", request_id: crypto.randomUUID(), session_id: id, payload: { title: "New Chat", mode: "Agent", execution_mode: "confirm", model: "DeepSeek" } });
  };
  const closeChat = (id: string) => { if (state.sessions.length <= 1) return; const remaining = state.sessions.filter((item) => item.id !== id); dispatch({ type: "snapshot_loaded", snapshot: { sessions: remaining, active_session_id: id === state.activeSessionId ? remaining[0].id : state.activeSessionId } }); bridge.send({ protocol_version: 1, type: "close_session", request_id: crypto.randomUUID(), session_id: id, payload: {} }); };
  const starter = (prompt: string) => sendIntent({ protocol_version: 1, type: "send_message", request_id: crypto.randomUUID(), session_id: session.id, payload: { text: prompt, mode: session.mode } });
  return <main className="agent-app">
    <AgentHeader onNewChat={newChat} onHistory={() => sendIntent({ protocol_version: 1, type: "request_snapshot", request_id: crypto.randomUUID(), session_id: session.id, payload: { view: "history" } })} onSettings={() => sendIntent({ protocol_version: 1, type: "request_snapshot", request_id: crypto.randomUUID(), session_id: session.id, payload: { view: "settings" } })} />
    <SessionTabs sessions={state.sessions} activeSessionId={state.activeSessionId} onSelect={(id) => { dispatch({ type: "switch_session", sessionId: id }); bridge.requestSnapshot(id); }} onClose={closeChat} />
    {session.turns.length === 0 ? <section className="timeline" aria-label="对话时间线"><EmptyState onStarter={starter} /></section> : <Timeline session={session} onIntent={sendIntent} onHover={(turnId, hovered) => dispatch({ type: "hover_turn", sessionId: session.id, turnId, hovered })} onToggleDetails={(turnId) => dispatch({ type: "toggle_details", sessionId: session.id, turnId })} />}
    <Composer sessionId={session.id} mode={session.mode} executionMode={session.executionMode} model={session.model} contextUsage={session.contextUsage ?? state.contextUsage} busy={busy} onIntent={sendIntent} />
  </main>;
}
