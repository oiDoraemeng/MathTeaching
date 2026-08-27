import {
  EMPTY_CONTEXT,
  normalizeContextUsage,
  type AppState,
  type SessionProjection,
  type SnapshotProjection,
  type TimelineEvent,
} from "../types";

export type AppAction =
  | { type: "snapshot_loaded"; snapshot: SnapshotProjection }
  | { type: "event_received"; event: TimelineEvent }
  | { type: "hover_turn"; sessionId: string; turnId: string; hovered: boolean }
  | { type: "toggle_details"; sessionId: string; turnId: string }
  | { type: "switch_session"; sessionId: string }
  | { type: "update_session_preferences"; sessionId: string; mode?: SessionProjection["mode"]; model?: string; executionMode?: SessionProjection["executionMode"] }
  | { type: "update_thinking_preferences"; sessionId: string; enabled: boolean; level?: SessionProjection["thinking_level"] }
  | { type: "set_view"; view: AppState["view"] }
  | { type: "history_loaded"; visible: AppState["history"]["visible"]; hidden: AppState["history"]["hidden"] }
  | { type: "register_mutation"; key: string; requestId: string; sessionId: string; previous: string }
  | { type: "clear_session"; sessionId: string };

export const initialSession = (): SessionProjection => ({
  id: "local-session",
  title: "New Chat",
  mode: "Agent",
  executionMode: "continuous",
  model: "DeepSeek",
  turns: [],
});

export const initialState = (): AppState => ({
  sessions: [initialSession()],
  activeSessionId: "local-session",
  contextUsage: EMPTY_CONTEXT,
  modelStatus: { connected: false },
  settingsState: {},
  gapDetected: false,
  lastSequence: {},
  view: "conversation",
  history: { visible: [], hidden: [] },
  modelCatalog: { builtin: [], custom: [] },
  capabilityCatalog: { catalog_version: 1, capabilities: [] },
  pendingMutations: {},
});

function sessionWithEvent(session: SessionProjection, event: TimelineEvent): SessionProjection {
  let turnId = event.turn_id ?? `turn-${event.sequence ?? Date.now()}`;
  let turn = session.turns.find((item) => item.id === turnId);
  // Some QWebChannel/native builds omit turn_id on high-frequency deltas.
  // Keep those deltas on the latest open turn instead of creating one card
  // per token.
  if (!turn && event.type === "message_delta" && !event.turn_id) {
    const openTurn = [...session.turns].reverse().find((item) => item.status === "running");
    if (openTurn) {
      turn = openTurn;
      turnId = openTurn.id;
    }
  }
  const turns = [...session.turns];
  if (!turn) {
    turn = { id: turnId, userMessage: "", events: [], status: "running" };
    turns.push(turn);
  }
  const updatedTurn = { ...turn, events: [...turn.events], hovered: turn.hovered, technicalDetails: turn.technicalDetails };
  if (event.type === "user_message") {
    const text = event.payload.text ?? event.payload.content ?? "";
    updatedTurn.userMessage = typeof text === "string" ? text : updatedTurn.userMessage;
  } else if (event.type === "message_delta") {
    const previous = updatedTurn.events.find((item) => item.type === "explanation");
    const delta = event.payload.text ?? event.payload.content ?? event.payload.delta ?? "";
    const isReasoning = event.payload.kind === "reasoning";
    if (typeof delta === "string") {
      if (isReasoning) {
        // 思考过程（如 DeepSeek 的 reasoning_content）单独累计，不混入正式回答。
        const reasoning = previous ? String(previous.payload.reasoning ?? "") : "";
        const payload = { ...(previous ? previous.payload : event.payload), text: previous ? String(previous.payload.text ?? "") : "", reasoning: `${reasoning}${delta}` };
        if (previous) {
          previous.payload = payload;
        } else {
          updatedTurn.events.push({ ...event, type: "explanation", payload });
        }
      } else if (previous) {
        previous.payload = { ...previous.payload, text: `${String(previous.payload.text ?? "")}${delta}` };
      } else {
        updatedTurn.events.push({ ...event, type: "explanation", payload: { ...event.payload, text: delta } });
      }
    }
  } else {
    updatedTurn.events.push(event);
  }
  const status = event.type === "turn_finished" ? String(event.payload.status ?? "completed") : event.type === "error" ? "error" : event.type === "stopped" ? "stopped" : updatedTurn.status;
  updatedTurn.status = status;
  const index = turns.findIndex((item) => item.id === turnId);
  turns[index] = updatedTurn;
  return { ...session, turns };
}

export function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "snapshot_loaded": {
      const projectedSessions = action.snapshot.sessions.filter((session) => !session.closed && !session.hidden);
      const sessions = projectedSessions.length ? projectedSessions : (action.snapshot.sessions.length ? [action.snapshot.sessions[0]] : [initialSession()]);
      const activeSessionId = action.snapshot.active_session_id ?? action.snapshot.activeSessionId ?? sessions[0].id;
      return {
        ...state,
        sessions,
        activeSessionId: sessions.some((session) => session.id === activeSessionId) ? activeSessionId : sessions[0].id,
        contextUsage: normalizeContextUsage(action.snapshot.context_usage ?? action.snapshot.contextUsage),
        modelStatus: action.snapshot.model_status ?? action.snapshot.modelStatus ?? state.modelStatus,
        settingsState: action.snapshot.settings_state ?? action.snapshot.settingsState ?? state.settingsState,
        history: {
          visible: action.snapshot.history?.visible ?? [],
          hidden: action.snapshot.history?.hidden ?? [],
        },
        modelCatalog: action.snapshot.model_catalog ?? action.snapshot.modelCatalog ?? state.modelCatalog,
        capabilityCatalog: action.snapshot.capability_catalog ?? action.snapshot.capabilityCatalog ?? state.capabilityCatalog,
        view: state.view,
        pendingMutations: {},
        gapDetected: false,
        lastSequence: {},
      };
    }
    case "event_received": {
      const { event } = action;
      if ((event.type === "mutation_succeeded" || event.type === "provider_test_result") && event.request_id) {
        const pendingMutations = { ...state.pendingMutations };
        for (const [key, value] of Object.entries(pendingMutations)) if (value.requestId === event.request_id && value.sessionId === event.session_id) delete pendingMutations[key];
        return { ...state, pendingMutations };
      }
      if (event.type === "error" && event.request_id) {
        const entry = Object.entries(state.pendingMutations).find(([, value]) => value.requestId === event.request_id && value.sessionId === event.session_id);
        if (!entry) return state;
        const [key, mutation] = entry;
        const [field] = key.split(":");
        const sessions = state.sessions.map((session) => session.id !== mutation.sessionId ? session : { ...session, ...(field === "model" ? { model: mutation.previous } : field === "mode" ? { mode: mutation.previous as SessionProjection["mode"] } : { executionMode: mutation.previous as SessionProjection["executionMode"] }) });
        const pendingMutations = { ...state.pendingMutations };
        delete pendingMutations[key];
        return { ...state, sessions, pendingMutations };
      }
      const key = event.session_id;
      const sequence = event.sequence;
      const previous = state.lastSequence[key] ?? 0;
      if (sequence !== undefined && sequence <= previous) return state;
      const gapDetected = sequence !== undefined && previous > 0 && sequence > previous + 1;
      const sessions = state.sessions.map((session) => session.id === event.session_id ? sessionWithEvent(session, event) : session);
      return { ...state, sessions, gapDetected: state.gapDetected || gapDetected, lastSequence: sequence === undefined ? state.lastSequence : { ...state.lastSequence, [key]: sequence } };
    }
    case "hover_turn":
      return { ...state, sessions: state.sessions.map((session) => session.id !== action.sessionId ? session : { ...session, turns: session.turns.map((turn) => turn.id === action.turnId ? { ...turn, hovered: action.hovered } : turn) }) };
    case "toggle_details":
      return { ...state, sessions: state.sessions.map((session) => session.id !== action.sessionId ? session : { ...session, turns: session.turns.map((turn) => turn.id === action.turnId ? { ...turn, technicalDetails: !turn.technicalDetails } : turn) }) };
    case "switch_session":
      return state.sessions.some((session) => session.id === action.sessionId) ? { ...state, activeSessionId: action.sessionId } : state;
    case "set_view":
      return { ...state, view: action.view };
    case "history_loaded":
      return { ...state, history: { visible: action.visible, hidden: action.hidden } };
    case "update_session_preferences":
      return {
        ...state,
        sessions: state.sessions.map((session) => session.id !== action.sessionId ? session : {
          ...session,
          mode: action.mode ?? session.mode,
          model: action.model ?? session.model,
          executionMode: action.executionMode ?? session.executionMode,
        }),
      };
    case "update_thinking_preferences":
      return {
        ...state,
        sessions: state.sessions.map((session) => session.id !== action.sessionId ? session : { ...session, thinking_enabled: action.enabled, thinking_level: action.level ?? session.thinking_level }),
      };
    case "register_mutation":
      return { ...state, pendingMutations: { ...state.pendingMutations, [action.key]: { requestId: action.requestId, sessionId: action.sessionId, previous: action.previous } } };
    case "clear_session":
      return { ...state, sessions: state.sessions.map((session) => session.id === action.sessionId ? { ...session, turns: [] } : session) };
    default:
      return state;
  }
}
