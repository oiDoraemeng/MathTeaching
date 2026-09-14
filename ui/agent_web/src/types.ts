export type AgentMode = "Agent" | "Ask" | "Plan";
export type ExecutionMode = "confirm" | "continuous";
export type ViewName = "conversation" | "history" | "settings";

export type TimelineEventType =
  | "user_message"
  | "message_delta"
  | "explanation"
  | "scene_context"
  | "calculation"
  | "plan_ready"
  | "validation"
  | "preview"
  | "execution"
  | "stopped"
  | "error"
  | "theme_state"
  | "turn_finished"
  | string;

export interface TimelineEvent {
  type: TimelineEventType;
  session_id: string;
  turn_id?: string;
  sequence?: number;
  request_id?: string;
  payload: Record<string, unknown>;
}

export interface ProgressLog {
  id: string;
  kind: "tool" | "validation" | "status" | "error";
  label: string;
  detail?: string;
  status?: string;
}

export interface CommandOperation {
  name: string;
  summary: string;
  status?: string;
  validation?: string;
}

export interface ContextUsage {
  usedTokens: number;
  maxTokens: number;
  percentage: number;
}

export interface ModelStatus {
  provider?: string;
  model?: string;
  connected?: boolean;
  streaming?: boolean;
  error?: string;
}

export interface SettingsState {
  provider?: string;
  protocol?: string;
  base_url?: string;
  model?: string;
  key_configured?: boolean;
  key_suffix?: string;
}

export interface TurnProjection {
  id: string;
  userMessage: string;
  events: TimelineEvent[];
  status: string;
  hovered?: boolean;
  technicalDetails?: boolean;
  reasoningText?: string;
  assistantText?: string;
  progressLogs?: ProgressLog[];
  commandPlan?: { summary: string; operations: CommandOperation[] };
  thinkingExpanded?: boolean;
  planExpanded?: boolean;
  drawState?: "available" | "pending" | "drawn" | "undone" | "unavailable";
}

export interface SessionProjection {
  id: string;
  title: string;
  mode: AgentMode;
  executionMode: ExecutionMode;
  model: string;
  thinking_enabled?: boolean;
  thinking_level?: "Low" | "High" | "X-High";
  closed?: boolean;
  hidden?: boolean;
  turns: TurnProjection[];
  contextUsage?: ContextUsage;
  attachments?: Array<{ id: string; turn_id?: string; path: string; mime_type: string; byte_size: number; sha256: string }>;
}

export interface CaseProjection {
  id: string;
  topicId?: string;
  category: string;
  name: string;
  formula: string;
  steps: string[];
  conclusion: string;
  summary?: string;
  /** Lecture-grounded prose kept with the artifact for the continuous note view. */
  sourceExcerpt?: string;
  sceneMode?: "2d" | "3d";
  artifactRevision?: number | null;
  revision?: number | null;
  sourceHash?: string | null;
  source?: CaseSourceProjection;
  sourceDiagnostic?: SourceDiagnosticProjection | null;
  definition?: string;
  derivation?: string[];
  intuition?: string;
  geometricMeaning?: string;
  pitfalls?: string[];
  invariants?: string[];
  connections?: string[];
  analogyBoundary?: string;
  transferNote?: string;
  readGuide?: string[];
  workedExamples?: WorkedExampleProjection[];
  claims?: ClaimProjection[];
  symbolRoles?: Record<string, string>;
  symbolPalette?: Record<string, string>;
  palette?: Record<string, string>;
  storyboard?: StoryboardStageProjection[];
  planDigest?: string | null;
  compilerVersion?: string | null;
  caseLayout?: CaseLayoutProjection;
  activeCaseId?: string;
  sections?: CaseSectionProjection[];
}

export interface CaseSectionProjection {
  id: string;
  title: string;
}

export interface CaseSourceProjection {
  sourcePath: string[];
  headingPath: string[];
  headingLevel?: number | null;
  occurrence?: number | null;
  sourceHash?: string | null;
}

export interface SourceDiagnosticProjection {
  code: string;
  publishedHash: string;
  currentHash: string;
}

export interface CaseLayoutProjection {
  defaultPaneCount: 1 | 2 | 3 | 4;
  cases: Array<{ id: string; topicId: string; exampleRef: string; claimRefs: string[]; stageRefs: string[]; purpose: string }>;
}

export interface WorkedExampleProjection {
  id?: string;
  title?: string;
  kind?: string;
  given?: unknown;
  calculation?: string[];
  result?: unknown;
  checks?: Array<{ name: string; expected: unknown; tolerance?: number }>;
  claimRefs?: string[];
}

export interface ClaimProjection {
  id: string;
  statement: string;
  formula?: string | null;
  formulaSymbols?: string[];
  entityRefs?: string[];
  relationRefs?: string[];
  stageRefs?: string[];
}

export interface StoryboardStageProjection {
  id: string;
  title: string;
  caption: string;
  layout: "sequence" | "side_by_side" | "overlay" | string;
  visibleRefs: string[];
  visibleAliases: string[];
  anchor: number[];
}

export interface SnapshotProjection {
  sessions: SessionProjection[];
  active_session_id?: string;
  activeSessionId?: string;
  context_usage?: ContextUsage;
  contextUsage?: ContextUsage;
  model_status?: ModelStatus;
  modelStatus?: ModelStatus;
  settings_state?: SettingsState;
  settingsState?: SettingsState;
  history?: { visible?: HistoryItem[]; hidden?: HistoryItem[] };
  model_catalog?: ModelCatalog;
  modelCatalog?: ModelCatalog;
  capability_catalog?: CapabilityCatalog;
  capabilityCatalog?: CapabilityCatalog;
}

export interface CapabilityDescriptor {
  name: string;
  category: "scene_read" | "scene_edit" | "math" | "view" | "result" | "teaching";
  description: string;
  input_schema: Record<string, unknown>;
  result_kind: string;
  scene_scope: "2d" | "3d" | "both";
  mutating: boolean;
}

export interface CapabilityCatalog {
  catalog_version: number;
  capabilities: CapabilityDescriptor[];
}

export interface ModelDescriptor {
  id: string;
  name: string;
  group: string;
  provider?: string;
  protocol?: string;
  capabilities?: string[];
  context_window?: string;
  base_url?: string;
  model?: string;
  input_context?: string;
  output_context?: string;
  thinking_enabled?: boolean;
  thinking_levels?: Array<"Low" | "High" | "X-High">;
}

export interface ModelCatalog {
  builtin: ModelDescriptor[];
  custom: ModelDescriptor[];
}

export interface HistoryItem {
  id: string;
  title: string;
  updated_at?: string;
  last_opened_at?: string;
  turn_count: number;
  hidden: boolean;
  closed: boolean;
}

export interface BridgeEnvelope {
  protocol_version: 1;
  type: string;
  request_id: string;
  session_id: string;
  turn_id?: string;
  sequence?: number;
  payload: Record<string, unknown>;
}

export type IntentType =
  | "create_session"
  | "close_session"
  | "reopen_session"
  | "send_message"
  | "approve_plan"
  | "stop_turn"
  | "restore_turn"
  | "undo_turn"
  | "branch_turn"
  | "request_snapshot"
  | "attach_files"
  | "change_mode"
  | "change_model"
  | "change_execution_mode"
  | "open_history"
  | "open_settings"
  | "restore_session_view"
  | "rename_session"
  | "hide_session"
  | "restore_hidden_session"
  | "save_model_provider"
  | "test_model_provider"
  | "save_custom_model"
  | "update_custom_model"
  | "delete_custom_model"
  | "set_selected_model"
  | "set_thinking_preferences"
  | "open_skills"
  | "select_math_stage"
  | "select_math_case_pane"
  | "set_math_case_pane_count";

export interface ClientIntent extends Omit<BridgeEnvelope, "type"> {
  type: IntentType;
}

export type IntentSender = (intent: ClientIntent) => void;

export interface AppState {
  sessions: SessionProjection[];
  activeSessionId: string;
  activeTab: string;
  cases: CaseProjection[];
  contextUsage: ContextUsage;
  modelStatus: ModelStatus;
  settingsState: SettingsState;
  gapDetected: boolean;
  lastSequence: Record<string, number>;
  view: ViewName;
  history: { visible: HistoryItem[]; hidden: HistoryItem[] };
  modelCatalog: ModelCatalog;
  capabilityCatalog: CapabilityCatalog;
  pendingMutations: Record<string, { requestId: string; sessionId: string; previous: string }>;
  theme?: "light" | "dark";
}

export const EMPTY_CONTEXT: ContextUsage = {
  usedTokens: 0,
  maxTokens: 16_000,
  percentage: 0,
};

export function normalizeContextUsage(value?: ContextUsage): ContextUsage {
  if (!value) return EMPTY_CONTEXT;
  const percentage = Math.max(0, Math.min(100, Number(value.percentage) || 0));
  return { ...value, percentage };
}

export function eventText(event: TimelineEvent): string {
  const payload = event.payload ?? {};
  const candidate = payload.text ?? payload.content ?? payload.delta ?? payload.message;
  return typeof candidate === "string" ? candidate : "";
}
