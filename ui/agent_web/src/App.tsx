import { useEffect, useMemo, useReducer, useState } from "react";
import { AgentHeader } from "./components/AgentHeader";
import { Composer } from "./components/Composer";
import { EmptyState } from "./components/EmptyState";
import { SessionTabs } from "./components/SessionTabs";
import { Timeline } from "./components/Timeline";
import { HistoryView } from "./components/HistoryView";
import { SettingsView } from "./components/SettingsView";
import { MathCaseView } from "./components/MathCaseView";
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
  const activeCase = state.activeTab.startsWith("case:") ? state.cases.find((item) => `case:${item.id}` === state.activeTab) : undefined;
  useEffect(() => { bridge.attach(dispatch); bridge.requestSnapshot(session.id); return () => bridge.detach(); }, [bridge, session.id]);
  useEffect(() => { const latest = session.turns.at(-1); setBusy(Boolean(latest && latest.status === "running")); }, [session.turns]);
  const sendIntent = (intent: ClientIntent) => {
    if (intent.type === "stop_turn") setBusy(false);
    const target = state.sessions.find((item) => item.id === intent.session_id);
    if (intent.type === "change_mode" && target) { dispatch({ type: "register_mutation", key: `mode:${intent.session_id}`, requestId: intent.request_id, sessionId: intent.session_id, previous: target.mode }); dispatch({ type: "update_session_preferences", sessionId: intent.session_id, mode: String(intent.payload.mode) as "Agent" | "Ask" | "Plan" }); }
    if (intent.type === "change_execution_mode" && target) { dispatch({ type: "register_mutation", key: `executionMode:${intent.session_id}`, requestId: intent.request_id, sessionId: intent.session_id, previous: target.executionMode }); dispatch({ type: "update_session_preferences", sessionId: intent.session_id, executionMode: String(intent.payload.execution_mode) as "confirm" | "continuous" }); }
    if ((intent.type === "change_model" || intent.type === "set_selected_model") && target) { dispatch({ type: "register_mutation", key: `model:${intent.session_id}`, requestId: intent.request_id, sessionId: intent.session_id, previous: target.model }); dispatch({ type: "update_session_preferences", sessionId: intent.session_id, model: String(intent.payload.model) }); }
    if (intent.type === "set_thinking_preferences") dispatch({ type: "update_thinking_preferences", sessionId: intent.session_id, enabled: Boolean(intent.payload.enabled), level: String(intent.payload.level ?? "High") as "Low" | "High" | "X-High" });
    bridge.send(intent);
  };
  const newChat = () => {
    const id = `session-${crypto.randomUUID()}`;
    dispatch({ type: "snapshot_loaded", snapshot: { sessions: [...state.sessions, { ...initialSession(), id }], active_session_id: id } });
    bridge.send({ protocol_version: 1, type: "create_session", request_id: crypto.randomUUID(), session_id: id, payload: { title: "New Chat", mode: "Agent", execution_mode: "continuous", model: "DeepSeek" } });
  };
  const closeChat = (id: string) => { if (state.sessions.length <= 1) return; const remaining = state.sessions.filter((item) => item.id !== id); dispatch({ type: "snapshot_loaded", snapshot: { sessions: remaining, active_session_id: id === state.activeSessionId ? remaining[0].id : state.activeSessionId } }); bridge.send({ protocol_version: 1, type: "close_session", request_id: crypto.randomUUID(), session_id: id, payload: {} }); };
  const closeTab = (id: string) => { if (id.startsWith("case:")) { dispatch({ type: "close_case", caseId: id.slice("case:".length) }); return; } closeChat(id); };
  const starter = (prompt: string) => sendIntent({ protocol_version: 1, type: "send_message", request_id: crypto.randomUUID(), session_id: session.id, payload: { text: prompt, mode: session.mode } });
  return <main className="agent-app">
    <AgentHeader onNewChat={newChat} onHistory={() => { dispatch({ type: "set_view", view: "history" }); sendIntent({ protocol_version: 1, type: "open_history", request_id: crypto.randomUUID(), session_id: session.id, payload: {} }); }} onSettings={() => { dispatch({ type: "set_view", view: "settings" }); sendIntent({ protocol_version: 1, type: "open_settings", request_id: crypto.randomUUID(), session_id: session.id, payload: {} }); }} />
    {state.view === "conversation" && <><SessionTabs sessions={state.sessions} cases={state.cases} activeSessionId={state.activeSessionId} activeTab={state.activeTab} onSelect={(id) => { dispatch({ type: "switch_session", sessionId: id }); bridge.requestSnapshot(id); }} onSelectCase={(id) => dispatch({ type: "select_case", caseId: id })} onClose={closeTab} />
      {activeCase ? <MathCaseView caseData={activeCase} /> : <>{session.turns.length === 0 ? <section className="timeline" aria-label="对话时间线"><EmptyState onStarter={starter} /></section> : <Timeline session={session} onIntent={sendIntent} onHover={(turnId, hovered) => dispatch({ type: "hover_turn", sessionId: session.id, turnId, hovered })} onToggleDetails={(turnId) => dispatch({ type: "toggle_thinking", sessionId: session.id, turnId })} onTogglePlan={(turnId) => dispatch({ type: "toggle_plan", sessionId: session.id, turnId })} />}
      <Composer sessionId={session.id} mode={session.mode} model={session.model} contextUsage={session.contextUsage ?? state.contextUsage} catalog={state.modelCatalog} capabilityCatalog={state.capabilityCatalog} busy={busy} onIntent={sendIntent} /></>}
    </>}
    {state.view === "history" && <HistoryView visible={state.history.visible} hidden={state.history.hidden} onSelect={(item) => { dispatch({ type: "set_view", view: "conversation" }); if (item.closed) { sendIntent({ protocol_version: 1, type: "reopen_session", request_id: crypto.randomUUID(), session_id: item.id, payload: {} }); } else { dispatch({ type: "switch_session", sessionId: item.id }); bridge.requestSnapshot(item.id); } }} onBack={() => { dispatch({ type: "set_view", view: "conversation" }); sendIntent({ protocol_version: 1, type: "restore_session_view", request_id: crypto.randomUUID(), session_id: session.id, payload: {} }); }} onIntent={sendIntent} />}
    {state.view === "settings" && <SettingsView session={session} catalog={state.modelCatalog} settingsState={state.settingsState} onIntent={sendIntent} onBack={() => { dispatch({ type: "set_view", view: "conversation" }); sendIntent({ protocol_version: 1, type: "restore_session_view", request_id: crypto.randomUUID(), session_id: session.id, payload: {} }); }} />}
  </main>;
}
