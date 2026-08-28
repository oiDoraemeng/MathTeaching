import { useEffect, useRef } from "react";
import { ChevronDown, Copy, GitBranch, Redo2, Undo2 } from "lucide-react";
import { MarkdownContent } from "./MarkdownContent";
import type { IntentSender, SessionProjection, TurnProjection } from "../types";

function sendTurnIntent(onIntent: IntentSender, sessionId: string, turnId: string, type: "undo_turn" | "approve_plan" | "branch_turn") {
  onIntent({ protocol_version: 1, type, request_id: crypto.randomUUID(), session_id: sessionId, turn_id: turnId, payload: {} });
}

function PlanStatusBar({ sessionId, turn, onIntent, onToggle }: { sessionId: string; turn: TurnProjection; onIntent: IntentSender; onToggle: () => void }) {
  const plan = turn.commandPlan;
  if (!plan) return null;
  const canUndo = turn.drawState === "drawn";
  const canDraw = turn.drawState === "available" || turn.drawState === "undone" || turn.status === "approval_required" || turn.status === "plan_pending";
  return <section className="plan-status-bar" aria-label="绘图指令">
    <button className="plan-status-toggle" onClick={onToggle} aria-expanded={turn.planExpanded}><ChevronDown size={14} className={turn.planExpanded ? "rotated" : ""} /><span>已生成 绘图指令</span><small>{plan.operations.length} 个操作</small></button>
    <div className="plan-status-spacer" />
    <button className="plan-action" disabled={!canUndo} onClick={() => sendTurnIntent(onIntent, sessionId, turn.id, "undo_turn")} aria-label="撤销" title="撤销"><Undo2 size={14} />撤销</button>
    <button className="plan-action plan-action-primary" disabled={!canDraw} onClick={() => sendTurnIntent(onIntent, sessionId, turn.id, "approve_plan")} aria-label="绘制" title="绘制"><Redo2 size={14} />绘制</button>
    {turn.planExpanded && <div className="plan-details" role="region" aria-label="绘图指令详情">{plan.operations.map((operation, index) => <div className="plan-operation" key={`${operation.name}-${index}`}><span className="plan-operation-index">{index + 1}</span><div><strong>{operation.name}</strong><p>{operation.summary}</p></div><div className="plan-operation-statuses"><small>执行: {operation.status ?? "待执行"}</small><small>校验: {operation.validation ?? "待校验"}</small></div></div>)}</div>}
  </section>;
}

function TurnView({ sessionId, turn, onIntent, onToggleThinking, onTogglePlan }: { sessionId: string; turn: TurnProjection; onIntent: IntentSender; onToggleThinking: () => void; onTogglePlan: () => void }) {
  const logs = turn.progressLogs ?? [];
  const reasoning = turn.reasoningText ?? "";
  const answer = turn.assistantText ?? "";
  return <div className="turn-block">
    <div className="user-message" role="article" aria-label="User message"><span className="sr-only">User</span><p>{turn.userMessage}</p></div>
    {(reasoning || logs.length > 0) && <section className="thinking-section"><button className="thinking-toggle" onClick={onToggleThinking} aria-expanded={turn.thinkingExpanded}><ChevronDown size={14} className={turn.thinkingExpanded ? "rotated" : ""} /><span>思考过程</span><small>{turn.status === "running" ? "进行中" : "已完成"}</small></button>{turn.thinkingExpanded && <div className="thinking-content">{reasoning && <div className="reasoning-text"><MarkdownContent>{reasoning}</MarkdownContent></div>}{logs.map((log) => <div className={`progress-log progress-${log.kind}`} key={log.id}><span className="progress-dot" /><strong>{log.label}</strong>{log.detail && <span>{log.detail}</span>}{log.status && <small>{log.status}</small>}</div>)}</div>}</section>}
    {answer && <div className="assistant-content"><MarkdownContent>{answer}</MarkdownContent></div>}
    <PlanStatusBar sessionId={sessionId} turn={turn} onIntent={onIntent} onToggle={onTogglePlan} />
    <div className={`turn-actions ${turn.hovered ? "visible" : ""}`} aria-hidden={!turn.hovered}><button onClick={() => void navigator.clipboard?.writeText(answer)} aria-label="复制" title="复制"><Copy size={14} /></button><button onClick={() => sendTurnIntent(onIntent, sessionId, turn.id, "branch_turn")} aria-label="创建分支" title="创建分支"><GitBranch size={14} /></button></div>
  </div>;
}

export function Timeline({ session, onIntent, onHover, onToggleDetails, onTogglePlan }: { session: SessionProjection; onIntent: IntentSender; onHover: (turnId: string, hovered: boolean) => void; onToggleDetails: (turnId: string) => void; onTogglePlan?: (turnId: string) => void }) {
  const endRef = useRef<HTMLDivElement>(null);
  const latest = session.turns.at(-1);
  useEffect(() => { endRef.current?.scrollIntoView?.({ block: "nearest" }); }, [session.turns.length, latest?.events.length, latest?.assistantText, latest?.reasoningText, latest?.progressLogs?.length]);
  return <section className="timeline" aria-label="Conversation timeline">{session.turns.length === 0 ? <div className="timeline-empty" /> : session.turns.map((turn) => <div key={turn.id} onMouseEnter={() => onHover(turn.id, true)} onMouseLeave={() => onHover(turn.id, false)}><TurnView sessionId={session.id} turn={turn} onIntent={onIntent} onToggleThinking={() => onToggleDetails(turn.id)} onTogglePlan={() => onTogglePlan?.(turn.id)} /></div>)}<div ref={endRef} /></section>;
}
