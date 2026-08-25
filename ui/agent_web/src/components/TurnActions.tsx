import { GitBranch, RotateCcw, Undo2 } from "lucide-react";
import type { IntentSender, TurnProjection } from "../types";

interface TurnActionsProps { sessionId: string; turn: TurnProjection; onIntent: IntentSender; }
export function TurnActions({ sessionId, turn, onIntent }: TurnActionsProps) {
  const enabled = turn.status === "completed" || turn.status === "success";
  if (!enabled) return null;
  const send = (type: "restore_turn" | "undo_turn" | "branch_turn") => onIntent({ protocol_version: 1, type, request_id: crypto.randomUUID(), session_id: sessionId, turn_id: turn.id, payload: {} });
  return <div className={`turn-actions ${turn.hovered ? "visible" : ""}`} aria-hidden={!turn.hovered}>
    <button onClick={() => send("restore_turn")} aria-label="恢复场景" title="恢复场景"><RotateCcw size={14} />恢复场景</button>
    <button onClick={() => send("undo_turn")} aria-label="撤销绘图" title="撤销绘图"><Undo2 size={14} />撤销绘图</button>
    <button onClick={() => send("branch_turn")} aria-label="分支到新聊天记录" title="分支到新聊天记录"><GitBranch size={14} />分支</button>
  </div>;
}
