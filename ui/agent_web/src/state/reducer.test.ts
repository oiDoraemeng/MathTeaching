import { describe, expect, it } from "vitest";
import { appReducer, initialState } from "./reducer";
import type { TimelineEvent } from "../types";

const event = (type: string, sequence: number, payload: Record<string, unknown> = {}): TimelineEvent => ({ type, sequence, session_id: "local-session", turn_id: "turn-1", payload });

describe("MathAgent reducer", () => {
  it("replaces state with a session snapshot", () => {
    const state = appReducer(initialState(), { type: "snapshot_loaded", snapshot: { active_session_id: "s1", sessions: [{ id: "s1", title: "探索", mode: "Ask", executionMode: "confirm", model: "DeepSeek", turns: [] }] } });
    expect(state.activeSessionId).toBe("s1");
    expect(state.sessions[0].mode).toBe("Ask");
  });
  it("keeps closed records out of the live tab state", () => {
    const state = appReducer(initialState(), { type: "snapshot_loaded", snapshot: {
      active_session_id: "open",
      sessions: [
        { id: "closed", title: "Closed", mode: "Agent", executionMode: "continuous", model: "DeepSeek", turns: [], closed: true },
        { id: "open", title: "Open", mode: "Agent", executionMode: "continuous", model: "DeepSeek", turns: [] },
      ],
    } });
    expect(state.sessions.map((session) => session.id)).toEqual(["open"]);
  });
  it("merges deltas into one explanation and appends a plan", () => {
    let state = initialState();
    state = appReducer(state, { type: "event_received", event: event("message_delta", 1, { text: "面积可以" }) });
    state = appReducer(state, { type: "event_received", event: event("message_delta", 2, { text: "这样理解。" }) });
    state = appReducer(state, { type: "event_received", event: event("plan_ready", 3, { operations: [{ type: "create_curve" }] }) });
    const turn = state.sessions[0].turns[0];
    expect(turn.events).toHaveLength(2);
    expect(turn.events[0].payload.text).toBe("面积可以这样理解。");
    expect(turn.events[1].type).toBe("plan_ready");
  });
  it("keeps reasoning deltas visible separately from the streamed answer", () => {
    let state = initialState();
    state = appReducer(state, { type: "event_received", event: event("message_delta", 1, { text: "analyzing", kind: "reasoning" }) });
    state = appReducer(state, { type: "event_received", event: event("message_delta", 2, { text: "The sum is (3,4)." }) });
    const explanation = state.sessions[0].turns[0].events[0];
    expect(explanation.type).toBe("explanation");
    expect(explanation.payload.reasoning).toBe("analyzing");
    expect(explanation.payload.text).toBe("The sum is (3,4).");
  });
  it("coalesces streamed deltas when the bridge omits turn_id", () => {
    let state = initialState();
    const first: TimelineEvent = { type: "message_delta", sequence: 1, session_id: "local-session", payload: { text: "The " } };
    const second: TimelineEvent = { type: "message_delta", sequence: 2, session_id: "local-session", payload: { text: "answer" } };
    state = appReducer(state, { type: "event_received", event: first });
    state = appReducer(state, { type: "event_received", event: second });
    expect(state.sessions[0].turns).toHaveLength(1);
    expect(state.sessions[0].turns[0].events[0].payload.text).toBe("The answer");
  });
  it("suppresses duplicate sequence and records a gap", () => {
    let state = initialState();
    state = appReducer(state, { type: "event_received", event: event("message_delta", 1, { text: "a" }) });
    const duplicate = appReducer(state, { type: "event_received", event: event("message_delta", 1, { text: "b" }) });
    expect(duplicate.sessions[0].turns[0].events[0].payload.text).toBe("a");
    const gap = appReducer(state, { type: "event_received", event: event("execution", 3, { text: "done" }) });
    expect(gap.gapDetected).toBe(true);
  });
  it("rolls back only the matching optimistic mutation", () => {
    let state = initialState();
    state = appReducer(state, { type: "register_mutation", key: "model:local-session", requestId: "r1", sessionId: "local-session", previous: "old" });
    state = appReducer(state, { type: "update_session_preferences", sessionId: "local-session", model: "new" });
    const unrelated = appReducer(state, { type: "event_received", event: { type: "error", request_id: "other", session_id: "local-session", payload: { code: "bad" } } });
    expect(unrelated.sessions[0].model).toBe("new");
    const rolledBack = appReducer(state, { type: "event_received", event: { type: "error", request_id: "r1", session_id: "local-session", payload: { code: "bad" } } });
    expect(rolledBack.sessions[0].model).toBe("old");
  });
});
