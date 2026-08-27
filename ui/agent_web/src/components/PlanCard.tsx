import { CheckCircle2, ChevronDown, ClipboardList } from "lucide-react";
import { useState } from "react";
import type { IntentSender, TimelineEvent } from "../types";

export function PlanCard({ event, sessionId, onIntent }: { event: TimelineEvent; sessionId: string; onIntent: IntentSender }) {
  const [details, setDetails] = useState(false);
  const payload = event.payload;
  const nestedPlan = payload.plan && typeof payload.plan === "object" && !Array.isArray(payload.plan)
    ? payload.plan as Record<string, unknown>
    : payload;
  const operations = Array.isArray(nestedPlan.operations) ? nestedPlan.operations : [];
  const summary = typeof nestedPlan.summary === "string" ? nestedPlan.summary : "MathAgent 已生成场景计划";
  const validation = typeof payload.validation === "string" ? payload.validation : "待校验";
  const approve = () => onIntent({ protocol_version: 1, type: "approve_plan", request_id: crypto.randomUUID(), session_id: sessionId, turn_id: event.turn_id, payload: {} });
  return <article className="event-card plan-card"><header><ClipboardList size={16} /><strong>CommandPlan</strong><span className="event-status">{validation}</span></header><p>{summary}</p><div className="plan-meta">{operations.length || Number(payload.operation_count) || 0} 个操作</div><button className="details-toggle" onClick={() => setDetails((value) => !value)} aria-expanded={details}><ChevronDown size={14} />技术细节</button>{details && <pre className="technical-details">{JSON.stringify(payload, null, 2)}</pre>}<button className="plan-approve" onClick={approve}><CheckCircle2 size={15} />确认执行</button></article>;
}
