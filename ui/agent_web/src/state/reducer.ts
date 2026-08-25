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
  | { type: "clear_session"; sessionId: string };

export const initialSession = (): SessionProjection => ({
  id: "local-session",
  title: "New Chat",
  mode: "Agent",
  executionMode: "confirm",
  model: "DeepSeek",
  turns: [],
});

export const initialState = (): AppState => ({
  sessions: [initialSession()],
  activeSessionId: "local-session",
  contextUsage: EMPTY_CONTEXT,
  modelStatus: { connected: false },
  gapDetected: false,
  lastSequence: {},
});

function sessionWithEvent(session: SessionProjection, event: TimelineEvent): SessionProjection {
  const turnId = event.turn_id ?? `turn-${event.sequence ?? Date.now()}`;
  let turn = session.turns.find((item) => item.id === turnId);
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
    if (previous && typeof delta === "string") {
      previous.payload = { ...previous.payload, text: `${String(previous.payload.text ?? "")}${delta}` };
    } else {
      updatedTurn.events.push({ ...event, type: "explanation", payload: { ...event.payload, text: delta } });
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
      const sessions = action.snapshot.sessions.length ? action.snapshot.sessions : [initialSession()];
      const activeSessionId = action.snapshot.active_session_id ?? action.snapshot.activeSessionId ?? sessions[0].id;
      return {
        ...state,
        sessions,
        activeSessionId: sessions.some((session) => session.id === activeSessionId) ? activeSessionId : sessions[0].id,
        contextUsage: normalizeContextUsage(action.snapshot.context_usage ?? action.snapshot.contextUsage),
        modelStatus: action.snapshot.model_status ?? action.snapshot.modelStatus ?? state.modelStatus,
        gapDetected: false,
        lastSequence: {},
      };
    }
    case "event_received": {
      const { event } = action;
      const key = `${event.session_id}:${event.turn_id ?? "session"}`;
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
    case "clear_session":
      return { ...state, sessions: state.sessions.map((session) => session.id === action.sessionId ? { ...session, turns: [] } : session) };
    default:
      return state;
  }
}
