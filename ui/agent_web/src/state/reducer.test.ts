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
  it("suppresses duplicate sequence and records a gap", () => {
    let state = initialState();
    state = appReducer(state, { type: "event_received", event: event("message_delta", 1, { text: "a" }) });
    const duplicate = appReducer(state, { type: "event_received", event: event("message_delta", 1, { text: "b" }) });
    expect(duplicate.sessions[0].turns[0].events[0].payload.text).toBe("a");
    const gap = appReducer(state, { type: "event_received", event: event("execution", 3, { text: "done" }) });
    expect(gap.gapDetected).toBe(true);
  });
});
