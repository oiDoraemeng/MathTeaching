import {
  EMPTY_CONTEXT,
  normalizeContextUsage,
  type AppState,
  type SessionProjection,
  type SnapshotProjection,
  type TimelineEvent,
  type CaseProjection,
  type TurnProjection,
} from "../types";

const HIDDEN_TIMELINE_EVENTS = new Set(["session_started", "capability_fallback", "execution_started", "execution_finished", "execution", "turn_finished", "approval_required"]);

export type AppAction =
  | { type: "snapshot_loaded"; snapshot: SnapshotProjection }
  | { type: "event_received"; event: TimelineEvent }
  | { type: "hover_turn"; sessionId: string; turnId: string; hovered: boolean }
  | { type: "toggle_details"; sessionId: string; turnId: string }
  | { type: "toggle_thinking"; sessionId: string; turnId: string }
  | { type: "toggle_plan"; sessionId: string; turnId: string }
  | { type: "switch_session"; sessionId: string }
  | { type: "update_session_preferences"; sessionId: string; mode?: SessionProjection["mode"]; model?: string; executionMode?: SessionProjection["executionMode"] }
  | { type: "update_thinking_preferences"; sessionId: string; enabled: boolean; level?: SessionProjection["thinking_level"] }
  | { type: "set_view"; view: AppState["view"] }
  | { type: "history_loaded"; visible: AppState["history"]["visible"]; hidden: AppState["history"]["hidden"] }
  | { type: "register_mutation"; key: string; requestId: string; sessionId: string; previous: string }
  | { type: "clear_session"; sessionId: string }
  | { type: "select_case"; caseId: string }
  | { type: "select_case_pane"; caseId: string; paneId: string }
  | { type: "close_case"; caseId: string };

function applyTheme(mode: unknown): "light" | "dark" | null {
  if (mode !== "light" && mode !== "dark") return null;
  document.documentElement.dataset.theme = mode;
  return mode;
}

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
  activeTab: "session:local-session",
  cases: [],
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
  theme: undefined,
});

function hydrateTurn(turn: SessionProjection["turns"][number]): SessionProjection["turns"][number] {
  const persistedStatus = turn.status;
  let next: TurnProjection = { ...turn, events: [], reasoningText: turn.reasoningText ?? "", assistantText: turn.assistantText ?? "", progressLogs: [], thinkingExpanded: turn.thinkingExpanded ?? (turn.status === "running"), planExpanded: turn.planExpanded ?? false, drawState: turn.drawState ?? "unavailable" };
  for (const event of turn.events ?? []) next = sessionWithEvent({ id: "hydrate", title: "", mode: "Agent", executionMode: "continuous", model: "", turns: [next] }, event).turns[0];
  next.events = (turn.events ?? []).filter((event) => event.type === "explanation");
  next.status = persistedStatus;
  if (persistedStatus === "undone") next.drawState = "undone";
  else if (next.commandPlan) next.drawState = persistedStatus === "completed" || persistedStatus === "success" ? "drawn" : "available";
  if (persistedStatus !== "running") next.thinkingExpanded = false;
  return next;
}

function sessionWithEvent(session: SessionProjection, event: TimelineEvent): SessionProjection {
  let turnId = event.turn_id ?? `turn-${event.sequence ?? Date.now()}`;
  let turn = session.turns.find((item) => item.id === turnId);
  const hidden = event.payload.ui_hidden === true || HIDDEN_TIMELINE_EVENTS.has(event.type);
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
  if (!turn && hidden) return session;
  if (!turn) {
    turn = { id: turnId, userMessage: "", events: [], status: "running" };
    turns.push(turn);
  }
  const updatedTurn = {
    ...turn,
    events: [...turn.events],
    hovered: turn.hovered,
    technicalDetails: turn.technicalDetails,
    reasoningText: turn.reasoningText ?? "",
    assistantText: turn.assistantText ?? "",
    progressLogs: [...(turn.progressLogs ?? [])],
    thinkingExpanded: turn.thinkingExpanded ?? true,
    planExpanded: turn.planExpanded ?? false,
    drawState: turn.drawState ?? "unavailable",
  };
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
        updatedTurn.reasoningText = `${updatedTurn.reasoningText ?? ""}${delta}`;
      } else if (previous) {
        previous.payload = { ...previous.payload, text: `${String(previous.payload.text ?? "")}${delta}` };
        updatedTurn.assistantText = `${updatedTurn.assistantText ?? ""}${delta}`;
      } else {
        updatedTurn.events.push({ ...event, type: "explanation", payload: { ...event.payload, text: delta } });
        updatedTurn.assistantText = `${updatedTurn.assistantText ?? ""}${delta}`;
      }
    }
  } else if (event.type === "plan_ready") {
    updatedTurn.events.push(event);
    const raw = event.payload.plan && typeof event.payload.plan === "object" && !Array.isArray(event.payload.plan) ? event.payload.plan as Record<string, unknown> : event.payload;
    const rawOperations = Array.isArray(raw.operations) ? raw.operations : [];
    updatedTurn.commandPlan = {
      summary: typeof raw.summary === "string" ? raw.summary : "已生成绘图指令",
      operations: rawOperations.map((operation, index) => {
        const item = operation && typeof operation === "object" ? operation as Record<string, unknown> : {};
        const name = String(item.op ?? item.name ?? item.type ?? `操作 ${index + 1}`);
        const params = Object.entries(item).filter(([key]) => !["op", "name", "type"].includes(key)).map(([key, value]) => `${key}=${typeof value === "string" ? value : JSON.stringify(value)}`).join(", ");
        return { name, summary: params || name, status: "待执行", validation: "待校验" };
      }),
    };
    updatedTurn.drawState = updatedTurn.status === "completed" || updatedTurn.status === "success" ? "drawn" : "available";
  } else if (event.type === "tool_started" || event.type === "tool_finished" || event.type === "validation" || event.type === "calculation" || event.type === "plan_composed" || event.type === "scene_conflict" || event.type === "error" || event.type === "stopped") {
    const payload = event.payload ?? {};
    const label = typeof payload.name === "string" ? payload.name : event.type === "validation" ? "计划校验" : event.type === "tool_started" ? "能力调用" : event.type === "tool_finished" ? "能力结果" : event.type === "scene_conflict" ? "场景冲突" : event.type === "error" ? "执行错误" : event.type === "stopped" ? "已停止" : event.type === "plan_composed" ? "绘图方案" : event.type === "calculation" ? "数学计算" : "状态更新";
    const detail = typeof payload.summary === "string" ? payload.summary : typeof payload.arguments_summary === "string" ? payload.arguments_summary : typeof payload.message === "string" ? payload.message : typeof payload.text === "string" ? payload.text : "";
    const statusValue = typeof payload.status === "string" ? payload.status : typeof payload.result_kind === "string" ? payload.result_kind : undefined;
    updatedTurn.progressLogs?.push({ id: `${event.type}-${event.sequence ?? updatedTurn.progressLogs.length}`, kind: event.type === "error" || event.type === "scene_conflict" ? "error" : event.type === "validation" ? "validation" : event.type.startsWith("tool_") ? "tool" : "status", label, detail, status: statusValue });
    if (event.type === "validation" && updatedTurn.commandPlan) {
      const validation = payload.valid === true ? "已通过" : payload.valid === false ? "未通过" : "已完成";
      updatedTurn.commandPlan = { ...updatedTurn.commandPlan, operations: updatedTurn.commandPlan.operations.map((operation) => ({ ...operation, validation })) };
    }
    if (event.type === "scene_conflict" && updatedTurn.commandPlan) {
      updatedTurn.commandPlan = { ...updatedTurn.commandPlan, operations: updatedTurn.commandPlan.operations.map((operation) => ({ ...operation, status: "已阻止", validation: "场景冲突" })) };
    }
  } else if (!hidden) {
    updatedTurn.events.push(event);
  }
  const status = event.type === "turn_finished" ? String(event.payload.status ?? "completed") : event.type === "error" ? "error" : event.type === "stopped" ? "stopped" : updatedTurn.status;
  updatedTurn.status = status;
  if (event.type === "turn_finished") {
    updatedTurn.thinkingExpanded = false;
    if (updatedTurn.commandPlan) {
      updatedTurn.drawState = status === "completed" || status === "success" ? "drawn" : "available";
      if (status === "completed" || status === "success") updatedTurn.commandPlan = { ...updatedTurn.commandPlan, operations: updatedTurn.commandPlan.operations.map((operation) => ({ ...operation, status: "已执行" })) };
    }
  }
  if (event.type === "execution" && updatedTurn.commandPlan) {
    const executionStatus = String(event.payload.status ?? "");
    if (executionStatus === "started") updatedTurn.commandPlan = { ...updatedTurn.commandPlan, operations: updatedTurn.commandPlan.operations.map((operation) => ({ ...operation, status: "执行中" })) };
    if (executionStatus === "undone") {
      updatedTurn.drawState = "undone";
      updatedTurn.status = "undone";
      updatedTurn.commandPlan = { ...updatedTurn.commandPlan, operations: updatedTurn.commandPlan.operations.map((operation) => ({ ...operation, status: "已撤销" })) };
    }
  }
  const index = turns.findIndex((item) => item.id === turnId);
  turns[index] = updatedTurn;
  return { ...session, turns };
}

function caseFromEvent(event: TimelineEvent): CaseProjection | null {
  const payload = event.payload ?? {};
  const id = typeof payload.case_id === "string" ? payload.case_id.trim() : "";
  const name = typeof payload.name === "string" ? payload.name.trim() : "";
  const formula = typeof payload.formula === "string" ? payload.formula : "";
  const conclusion = typeof payload.conclusion === "string" ? payload.conclusion : "";
  const steps = Array.isArray(payload.steps) ? payload.steps.filter((value): value is string => typeof value === "string").slice(0, 12) : [];
  // The case id is the only required identity.  Lecture sections such as
  // 1.3.1（内积的两种定义）and 1.4.1（投影的定义）write the formulas inside the
  // definition prose and artifact sections, so an empty standalone formula
  // must not drop the whole case.  Derivation steps and conclusion are
  // optional as well; the view omits those blocks when empty.
  if (!id) return null;
  const list = (key: string, limit = 16) => Array.isArray(payload[key]) ? payload[key].filter((value): value is string => typeof value === "string").slice(0, limit) : undefined;
  const object = (key: string) => payload[key] && typeof payload[key] === "object" && !Array.isArray(payload[key]) ? payload[key] as Record<string, string> : undefined;
  const claims = Array.isArray(payload.claims) ? payload.claims.filter((value): value is Record<string, unknown> => Boolean(value) && typeof value === "object" && !Array.isArray(value)).slice(0, 24).map((claim) => ({
    id: typeof claim.id === "string" ? claim.id : "",
    statement: typeof claim.statement === "string" ? claim.statement : "",
    formula: typeof claim.formula === "string" ? claim.formula : null,
    formulaSymbols: Array.isArray(claim.formula_symbols) ? claim.formula_symbols.filter((value): value is string => typeof value === "string").slice(0, 32) : [],
    entityRefs: Array.isArray(claim.entity_refs) ? claim.entity_refs.filter((value): value is string => typeof value === "string").slice(0, 32) : [],
    relationRefs: Array.isArray(claim.relation_refs) ? claim.relation_refs.filter((value): value is string => typeof value === "string").slice(0, 32) : [],
    stageRefs: Array.isArray(claim.stage_refs) ? claim.stage_refs.filter((value): value is string => typeof value === "string").slice(0, 32) : [],
  })) : undefined;
  const storyboard = Array.isArray(payload.storyboard) ? payload.storyboard.filter((value): value is Record<string, unknown> => Boolean(value) && typeof value === "object" && !Array.isArray(value)).slice(0, 24).map((stage) => ({
    id: typeof stage.id === "string" ? stage.id : "",
    title: typeof stage.title === "string" ? stage.title : "",
    caption: typeof stage.caption === "string" ? stage.caption : "",
    layout: typeof stage.layout === "string" ? stage.layout : "sequence",
    visibleRefs: Array.isArray(stage.visible_refs) ? stage.visible_refs.filter((value): value is string => typeof value === "string") : [],
    visibleAliases: Array.isArray(stage.visible_aliases) ? stage.visible_aliases.filter((value): value is string => typeof value === "string") : [],
    anchor: Array.isArray(stage.anchor) ? stage.anchor.filter((value): value is number => typeof value === "number") : [],
  })) : undefined;
  const examples = Array.isArray(payload.worked_examples) ? payload.worked_examples.filter((value): value is Record<string, unknown> => Boolean(value) && typeof value === "object" && !Array.isArray(value)).slice(0, 8).map((example) => ({
    id: typeof example.id === "string" ? example.id : "",
    title: typeof example.title === "string" ? example.title : "",
    kind: typeof example.kind === "string" ? example.kind : "",
    given: example.given,
    calculation: Array.isArray(example.calculation) ? example.calculation.filter((value): value is string => typeof value === "string") : [],
    result: example.result,
    checks: Array.isArray(example.checks) ? example.checks.filter((value): value is { name: string; expected: unknown; tolerance?: number } => Boolean(value) && typeof value === "object" && typeof (value as Record<string, unknown>).name === "string").map((check) => ({ name: check.name, expected: check.expected, tolerance: typeof check.tolerance === "number" ? check.tolerance : undefined })) : [],
    claimRefs: Array.isArray(example.claim_refs) ? example.claim_refs.filter((value): value is string => typeof value === "string") : [],
  })) : undefined;
  const rawSource = payload.source;
  const source = rawSource && typeof rawSource === "object" && !Array.isArray(rawSource)
    ? (() => {
        const value = rawSource as Record<string, unknown>;
        const diagnosticValue = value.diagnostic;
        return {
          sourcePath: Array.isArray(value.source_path) ? value.source_path.filter((item): item is string => typeof item === "string") : [],
          headingPath: Array.isArray(value.heading_path) ? value.heading_path.filter((item): item is string => typeof item === "string") : [],
          headingLevel: typeof value.heading_level === "number" ? value.heading_level : null,
          occurrence: typeof value.occurrence === "number" ? value.occurrence : null,
          sourceHash: typeof value.source_hash === "string" ? value.source_hash : null,
          diagnostic: diagnosticValue && typeof diagnosticValue === "object" && !Array.isArray(diagnosticValue) ? diagnosticValue as Record<string, unknown> : null,
        };
      })()
    : undefined;
  const sourceDiagnosticValue = source?.diagnostic;
  const sourceDiagnostic = sourceDiagnosticValue && typeof sourceDiagnosticValue.code === "string"
    && typeof sourceDiagnosticValue.published_hash === "string"
    && typeof sourceDiagnosticValue.current_hash === "string"
    ? { code: sourceDiagnosticValue.code, publishedHash: sourceDiagnosticValue.published_hash, currentHash: sourceDiagnosticValue.current_hash }
    : null;
  const rawLayout = payload.case_layout;
  const caseLayout = rawLayout && typeof rawLayout === "object" && !Array.isArray(rawLayout)
    ? (() => {
        const value = rawLayout as Record<string, unknown>;
        const count = value.default_pane_count;
        const defaultPaneCount = count === 1 || count === 2 || count === 3 || count === 4 ? count : 1;
        const entries = Array.isArray(value.cases) ? value.cases.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object" && !Array.isArray(item)).slice(0, 4).map((item) => ({
          id: typeof item.id === "string" ? item.id : "",
          topicId: typeof item.topic_id === "string" ? item.topic_id : "",
          exampleRef: typeof item.example_ref === "string" ? item.example_ref : "",
          claimRefs: Array.isArray(item.claim_refs) ? item.claim_refs.filter((v): v is string => typeof v === "string") : [],
          stageRefs: Array.isArray(item.stage_refs) ? item.stage_refs.filter((v): v is string => typeof v === "string") : [],
          purpose: typeof item.purpose === "string" ? item.purpose : "",
        })) : [];
        return { defaultPaneCount: defaultPaneCount as 1 | 2 | 3 | 4, cases: entries };
      })()
    : undefined;
  return {
    id,
    topicId: typeof payload.topic_id === "string" ? payload.topic_id : id,
    category: typeof payload.category === "string" ? payload.category : "向量",
    name,
    formula,
    steps,
    conclusion,
    summary: typeof payload.summary === "string" ? payload.summary : "",
    sourceExcerpt: typeof payload.source_excerpt === "string" ? payload.source_excerpt : "",
    sceneMode: payload.scene_mode === "3d" ? "3d" : "2d",
    artifactRevision: typeof payload.artifact_revision === "number" ? payload.artifact_revision : null,
    revision: typeof payload.revision === "number" ? payload.revision : (typeof payload.artifact_revision === "number" ? payload.artifact_revision : null),
    sourceHash: typeof payload.source_hash === "string" ? payload.source_hash : null,
    source: source ? { sourcePath: source.sourcePath, headingPath: source.headingPath, headingLevel: source.headingLevel, occurrence: source.occurrence, sourceHash: source.sourceHash } : undefined,
    sourceDiagnostic,
    definition: typeof payload.definition === "string" ? payload.definition : "",
    derivation: list("derivation"),
    intuition: typeof payload.intuition === "string" ? payload.intuition : "",
    geometricMeaning: typeof payload.geometric_meaning === "string" ? payload.geometric_meaning : "",
    pitfalls: list("pitfalls", 12),
    invariants: list("invariants", 12),
    connections: list("connections", 12),
    analogyBoundary: typeof payload.analogy_boundary === "string" ? payload.analogy_boundary : "",
    transferNote: typeof payload.transfer_note === "string" ? payload.transfer_note : "",
    readGuide: list("read_guide", 12),
    workedExamples: examples,
    sections: Array.isArray(payload.sections)
      ? payload.sections.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object" && !Array.isArray(item)).slice(0, 12).map((item) => ({
          id: typeof item.id === "string" ? item.id : "",
          title: typeof item.title === "string" ? item.title : "",
        }))
      : [],
    claims,
    symbolRoles: object("symbol_roles"),
    symbolPalette: object("symbol_palette"),
    palette: object("palette"),
    storyboard,
    planDigest: typeof payload.plan_digest === "string" ? payload.plan_digest : null,
    compilerVersion: typeof payload.compiler_version === "string" ? payload.compiler_version : null,
    caseLayout,
    activeCaseId: typeof payload.active_case_id === "string" ? payload.active_case_id : caseLayout?.cases[0]?.id,
  };
}

export function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "snapshot_loaded": {
      const projectedSessions = action.snapshot.sessions.filter((session) => !session.closed && !session.hidden);
      const sessions = (projectedSessions.length ? projectedSessions : (action.snapshot.sessions.length ? [action.snapshot.sessions[0]] : [initialSession()])).map((session) => ({ ...session, turns: session.turns.map(hydrateTurn) }));
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
      if (event.type === "theme_state") {
        const theme = applyTheme(event.payload?.mode);
        return theme ? { ...state, theme } : state;
      }
      if (event.type === "math_case") {
        const nextCase = caseFromEvent(event);
        if (!nextCase) return state;
        return { ...state, cases: [nextCase], activeTab: `case:${nextCase.id}` };
      }
      if (event.type === "math_case_focus") {
        const caseId = typeof event.payload.case_id === "string" ? event.payload.case_id : "";
        const paneId = typeof event.payload.pane_id === "string" ? event.payload.pane_id : "";
        if (!caseId || !paneId) return state;
        return {
          ...state,
          cases: state.cases.map((item) => item.id === caseId ? { ...item, activeCaseId: paneId } : item),
        };
      }
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
    case "toggle_thinking":
      return { ...state, sessions: state.sessions.map((session) => session.id !== action.sessionId ? session : { ...session, turns: session.turns.map((turn) => turn.id === action.turnId ? { ...turn, thinkingExpanded: !turn.thinkingExpanded } : turn) }) };
    case "toggle_plan":
      return { ...state, sessions: state.sessions.map((session) => session.id !== action.sessionId ? session : { ...session, turns: session.turns.map((turn) => turn.id === action.turnId ? { ...turn, planExpanded: !turn.planExpanded } : turn) }) };
    case "switch_session":
      return state.sessions.some((session) => session.id === action.sessionId) ? { ...state, activeSessionId: action.sessionId, activeTab: `session:${action.sessionId}` } : state;
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
    case "select_case":
      return state.cases.some((item) => item.id === action.caseId) ? { ...state, activeTab: `case:${action.caseId}` } : state;
    case "select_case_pane":
      return state.cases.some((item) => item.id === action.caseId)
        ? { ...state, cases: state.cases.map((item) => item.id === action.caseId ? { ...item, activeCaseId: action.paneId } : item) }
        : state;
    case "close_case": {
      const cases = state.cases.filter((item) => item.id !== action.caseId);
      return { ...state, cases, activeTab: state.activeTab === `case:${action.caseId}` ? `session:${state.activeSessionId}` : state.activeTab };
    }
    default:
      return state;
  }
}
