import { AlertCircle, Calculator, CheckCircle2, Eye, Info, LoaderCircle, MessageCircle, ScanLine, Square } from "lucide-react";
import { MarkdownContent } from "./MarkdownContent";
import { PlanCard } from "./PlanCard";
import type { IntentSender, TimelineEvent } from "../types";

const labels: Record<string, string> = { explanation: "数学解释", scene_context: "场景上下文", calculation: "数学计算", preview: "渲染预览", execution: "执行结果", stopped: "已停止", error: "执行错误", validation: "计划校验", turn_finished: "回合完成" };
export function EventCard({ event, sessionId, onIntent, technicalDetails, onToggleDetails }: { event: TimelineEvent; sessionId: string; onIntent: IntentSender; technicalDetails?: boolean; onToggleDetails?: () => void }) {
  if (event.type === "plan_ready") return <PlanCard event={event} sessionId={sessionId} onIntent={onIntent} />;
  const text = typeof event.payload.text === "string" ? event.payload.text : typeof event.payload.content === "string" ? event.payload.content : typeof event.payload.message === "string" ? event.payload.message : "";
  const Icon = event.type === "calculation" ? Calculator : event.type === "preview" ? Eye : event.type === "execution" || event.type === "turn_finished" ? CheckCircle2 : event.type === "error" ? AlertCircle : event.type === "stopped" ? Square : event.type === "scene_context" ? ScanLine : event.type === "validation" ? LoaderCircle : event.type === "explanation" ? MessageCircle : Info;
  return <article className={`event-card event-${event.type}`}><header><Icon size={15} /><strong>{labels[event.type] ?? event.type}</strong>{event.type === "validation" && <span className="event-status">进行中</span>}</header>{text && (event.type === "explanation" ? <MarkdownContent>{text}</MarkdownContent> : <p>{text}</p>)}{(technicalDetails || event.type === "error") && <pre className="technical-details">{JSON.stringify(event.payload, null, 2)}</pre>}{onToggleDetails && event.type !== "error" && <button className="details-toggle" onClick={onToggleDetails} aria-expanded={technicalDetails}>技术细节</button>}</article>;
}
