export type AgentMode = "Agent" | "Ask" | "Plan";
export type ExecutionMode = "confirm" | "continuous";

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

export interface TurnProjection {
  id: string;
  userMessage: string;
  events: TimelineEvent[];
  status: string;
  hovered?: boolean;
  technicalDetails?: boolean;
}

export interface SessionProjection {
  id: string;
  title: string;
  mode: AgentMode;
  executionMode: ExecutionMode;
  model: string;
  turns: TurnProjection[];
  contextUsage?: ContextUsage;
  attachments?: Array<{ id: string; turn_id?: string; path: string; mime_type: string; byte_size: number; sha256: string }>;
}

export interface SnapshotProjection {
  sessions: SessionProjection[];
  active_session_id?: string;
  activeSessionId?: string;
  context_usage?: ContextUsage;
  contextUsage?: ContextUsage;
  model_status?: ModelStatus;
  modelStatus?: ModelStatus;
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
  | "change_execution_mode";

export interface ClientIntent extends Omit<BridgeEnvelope, "type"> {
  type: IntentType;
}

export type IntentSender = (intent: ClientIntent) => void;

export interface AppState {
  sessions: SessionProjection[];
  activeSessionId: string;
  contextUsage: ContextUsage;
  modelStatus: ModelStatus;
  gapDetected: boolean;
  lastSequence: Record<string, number>;
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
