import { describe, expect, it } from "vitest";
import { appReducer, initialState } from "./reducer";
import type { TimelineEvent } from "../types";

const event = (type: string, sequence: number, payload: Record<string, unknown> = {}): TimelineEvent => ({ type, sequence, session_id: "local-session", turn_id: "turn-1", payload });

describe("MathAgent reducer", () => {
  it("places the submitted user message in the same turn immediately", () => {
    const state = appReducer(initialState(), { type: "event_received", event: event("user_message", 1, { text: "生成向量加法的几何教学图" }) });
    expect(state.sessions[0].turns).toHaveLength(1);
    expect(state.sessions[0].turns[0].userMessage).toBe("生成向量加法的几何教学图");
  });
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
  it("separates streamed answer from plan state", () => {
    let state = initialState();
    state = appReducer(state, { type: "event_received", event: event("message_delta", 1, { text: "面积可以" }) });
    state = appReducer(state, { type: "event_received", event: event("message_delta", 2, { text: "这样理解。" }) });
    state = appReducer(state, { type: "event_received", event: event("plan_ready", 3, { operations: [{ type: "create_curve" }] }) });
    const turn = state.sessions[0].turns[0];
    expect(turn.events).toHaveLength(2);
    expect(turn.events[0].payload.text).toBe("面积可以这样理解。");
    expect(turn.events[1].type).toBe("plan_ready");
    expect(turn.assistantText).toBe("面积可以这样理解。");
    expect(turn.commandPlan?.operations).toHaveLength(1);
  });
  it("keeps reasoning deltas visible separately from the streamed answer", () => {
    let state = initialState();
    state = appReducer(state, { type: "event_received", event: event("message_delta", 1, { text: "analyzing", kind: "reasoning" }) });
    state = appReducer(state, { type: "event_received", event: event("message_delta", 2, { text: "The sum is (3,4)." }) });
    const explanation = state.sessions[0].turns[0].events[0];
    expect(explanation.type).toBe("explanation");
    expect(explanation.payload.reasoning).toBe("analyzing");
    expect(explanation.payload.text).toBe("The sum is (3,4).");
    expect(state.sessions[0].turns[0].reasoningText).toBe("analyzing");
    expect(state.sessions[0].turns[0].assistantText).toBe("The sum is (3,4).");
  });
  it("hides lifecycle events while keeping safe operation summaries", () => {
    let state = initialState();
    state = appReducer(state, { type: "event_received", event: event("message_delta", 1, { text: "答案" }) });
    state = appReducer(state, { type: "event_received", event: event("plan_composed", 2, { summary: "创建图形", operation_count: 1 }) });
    state = appReducer(state, { type: "event_received", event: event("session_started", 3) });
    state = appReducer(state, { type: "event_received", event: event("execution_finished", 4, { status: "completed" }) });
    state = appReducer(state, { type: "event_received", event: event("turn_finished", 5, { ui_hidden: true, status: "completed" }) });
    const turn = state.sessions[0].turns[0];
    expect(turn.events.map((item) => item.type)).toEqual(["explanation"]);
    expect(turn.progressLogs?.at(-1)?.label).toBe("绘图方案");
    expect(turn.progressLogs?.some((log) => log.label.includes("execution_finished"))).toBe(false);
    expect(turn.thinkingExpanded).toBe(false);
  });
  it("updates command operation validation and execution states", () => {
    let state = initialState();
    state = appReducer(state, { type: "event_received", event: event("plan_ready", 1, { operations: [{ op: "point.upsert", alias: "P" }] }) });
    state = appReducer(state, { type: "event_received", event: event("validation", 2, { valid: true }) });
    state = appReducer(state, { type: "event_received", event: event("execution", 3, { status: "started", ui_hidden: true }) });
    state = appReducer(state, { type: "event_received", event: event("turn_finished", 4, { status: "completed", ui_hidden: true }) });
    const operation = state.sessions[0].turns[0].commandPlan?.operations[0];
    expect(operation?.validation).toBe("已通过");
    expect(operation?.status).toBe("已执行");
  });
  it("shows bounded tool argument summaries without creating a lifecycle-only turn", () => {
    let state = initialState();
    state = appReducer(state, { type: "event_received", event: event("message_delta", 1, { text: "答案" }) });
    state = appReducer(state, { type: "event_received", event: event("tool_started", 2, { name: "scene.edit", arguments_summary: "alias=P, coordinates=[1,2]" }) });
    expect(state.sessions[0].turns).toHaveLength(1);
    expect(state.sessions[0].turns[0].progressLogs?.at(-1)?.detail).toBe("alias=P, coordinates=[1,2]");
    const unchanged = appReducer(state, { type: "event_received", event: event("session_started", 3, { mode: "Agent" }) });
    expect(unchanged.sessions[0].turns).toHaveLength(1);
  });
  it("restores an undone plan state from a persisted snapshot", () => {
    const state = appReducer(initialState(), { type: "snapshot_loaded", snapshot: {
      active_session_id: "s1",
      sessions: [{ id: "s1", title: "Chat", mode: "Agent", executionMode: "continuous", model: "DeepSeek", turns: [{
        id: "t1", userMessage: "画点", status: "undone", assistantText: "已完成", events: [
          { type: "plan_ready", session_id: "s1", turn_id: "t1", payload: { operations: [{ op: "point.upsert", alias: "P" }] } },
          { type: "validation", session_id: "s1", turn_id: "t1", payload: { valid: true } },
        ],
      }] }],
    } });
    expect(state.sessions[0].turns[0].drawState).toBe("undone");
    expect(state.sessions[0].turns[0].status).toBe("undone");
    expect(state.sessions[0].turns[0].commandPlan?.operations[0].validation).toBe("已通过");
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
  it("creates one reusable case tab and activates it", () => {
    const caseEvent: TimelineEvent = { type: "math_case", session_id: "", payload: {
      case_id: "vector-subtraction", category: "向量", name: "向量减法", formula: "a-b=(1,-1)",
      steps: ["加上相反向量"], conclusion: "减法等价于加法。", summary: "向量减法",
    } };
    let state = appReducer(initialState(), { type: "event_received", event: caseEvent });
    state = appReducer(state, { type: "event_received", event: { ...caseEvent, payload: { ...caseEvent.payload, summary: "更新后的解释" } } });
    expect(state.cases).toHaveLength(1);
    expect(state.cases[0].summary).toBe("更新后的解释");
    expect(state.activeTab).toBe("case:vector-subtraction");
  });
  it("keeps a case whose formulas live inside the definition prose", () => {
    const caseEvent: TimelineEvent = { type: "math_case", session_id: "", payload: {
      case_id: "ch01.inner.definitions", category: "内积", name: "1.3.1 内积的两种定义", formula: "",
      definition: "定义 1.10（内积）：设 $\\boldsymbol a$ 与 $\\boldsymbol b$ 为两个向量。",
      invariants: ["性质 1.1（对称性）"],
      sections: [{ id: "definition", title: "定义" }, { id: "invariants", title: "内积的基本性质" }],
    } };
    const state = appReducer(initialState(), { type: "event_received", event: caseEvent });
    expect(state.activeTab).toBe("case:ch01.inner.definitions");
    expect(state.cases[0].definition).toContain("定义 1.10");
    expect(state.cases[0].invariants).toEqual(["性质 1.1（对称性）"]);
    expect(state.cases[0].sections).toEqual([{ id: "definition", title: "定义" }, { id: "invariants", title: "内积的基本性质" }]);
  });
  it("closes a case tab and returns to the active session", () => {
    const caseEvent: TimelineEvent = { type: "math_case", session_id: "", payload: {
      case_id: "vector-addition", category: "向量", name: "向量加法", formula: "a+b", steps: ["step"], conclusion: "sum",
    } };
    const withCase = appReducer(initialState(), { type: "event_received", event: caseEvent });
    const closed = appReducer(withCase, { type: "close_case", caseId: "vector-addition" });
    expect(closed.cases).toHaveLength(0);
    expect(closed.activeTab).toBe("session:local-session");
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
