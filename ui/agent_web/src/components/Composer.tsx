import { Send, Square, Plus } from "lucide-react";
import { useState } from "react";
import { AttachmentActions } from "./AttachmentActions";
import { ContextRing } from "./ContextRing";
import { ModeSelector, modeIntent } from "./ModeSelector";
import { ModelSelector } from "./ModelSelector";
import type { AgentMode, ContextUsage, ExecutionMode, IntentSender } from "../types";

interface ComposerProps {
  sessionId: string;
  mode: AgentMode;
  executionMode: ExecutionMode;
  model: string;
  contextUsage: ContextUsage;
  busy?: boolean;
  onIntent: IntentSender;
  onModeChange?: (mode: AgentMode) => void;
}

export function Composer({ sessionId, mode, executionMode, model, contextUsage, busy = false, onIntent, onModeChange }: ComposerProps) {
  const [prompt, setPrompt] = useState("");
  const submit = () => { const text = prompt.trim(); if (!text || busy) return; onIntent({ protocol_version: 1, type: "send_message", request_id: crypto.randomUUID(), session_id: sessionId, payload: { text, mode } }); setPrompt(""); };
  const stop = () => onIntent({ protocol_version: 1, type: "stop_turn", request_id: crypto.randomUUID(), session_id: sessionId, payload: {} });
  return <section className="composer" aria-label="消息输入"><textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); submit(); } }} placeholder={'提问或输入 "/"快捷命令'} aria-label="提问或输入" /><div className="composer-toolbar"><AttachmentActions sessionId={sessionId} onIntent={onIntent} /><span className="toolbar-spacer" /><button className="composer-icon" aria-label="添加附件" title="添加附件" onClick={() => onIntent({ protocol_version: 1, type: "attach_files", request_id: crypto.randomUUID(), session_id: sessionId, payload: {} })}><Plus size={15} /></button><ModeSelector mode={mode} onChange={(value) => { onModeChange?.(value); onIntent(modeIntent(value, sessionId)); }} /><label className="execution-selector"><span className="sr-only">执行方式</span><select value={executionMode} onChange={(event) => onIntent({ protocol_version: 1, type: "change_execution_mode", request_id: crypto.randomUUID(), session_id: sessionId, payload: { execution_mode: event.target.value } })} aria-label="执行方式"><option value="confirm">确认执行</option><option value="continuous">连续执行</option></select></label><span className="toolbar-spacer" /><ModelSelector model={model} sessionId={sessionId} onIntent={onIntent} /><ContextRing percentage={contextUsage.percentage} /><button className="send-button" aria-label={busy ? "停止" : "发送"} title={busy ? "停止" : "发送"} disabled={!busy && !prompt.trim()} onClick={busy ? stop : submit}>{busy ? <Square size={15} /> : <Send size={15} />}</button></div></section>;
}
