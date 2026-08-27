import { Send, Square } from "lucide-react";
import { useState } from "react";
import { AttachmentActions } from "./AttachmentActions";
import { ContextRing } from "./ContextRing";
import { ModeSelector, modeIntent } from "./ModeSelector";
import { ModelSelector } from "./ModelSelector";
import type { AgentMode, CapabilityCatalog, ContextUsage, IntentSender, ModelCatalog } from "../types";

interface ComposerProps {
  sessionId: string;
  mode: AgentMode;
  model: string;
  contextUsage: ContextUsage;
  catalog?: ModelCatalog;
  capabilityCatalog?: CapabilityCatalog;
  busy?: boolean;
  onIntent: IntentSender;
  onModeChange?: (mode: AgentMode) => void;
}

export function Composer({ sessionId, mode, model, contextUsage, catalog, capabilityCatalog, busy = false, onIntent, onModeChange }: ComposerProps) {
  const [prompt, setPrompt] = useState("");
  const submit = () => {
    const text = prompt.trim();
    if (!text || busy) return;
    onIntent({ protocol_version: 1, type: "send_message", request_id: crypto.randomUUID(), session_id: sessionId, payload: { text, mode } });
    setPrompt("");
  };
  const stop = () => onIntent({ protocol_version: 1, type: "stop_turn", request_id: crypto.randomUUID(), session_id: sessionId, payload: {} });
  return <section className="composer" aria-label="消息输入">
    <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); submit(); } }} placeholder={'提问或输入 "/"快捷命令'} aria-label="提问或输入" />
    <div className="composer-toolbar">
      <AttachmentActions sessionId={sessionId} capabilityCatalog={capabilityCatalog} onIntent={onIntent} onInsertPrompt={setPrompt} />
      <ModeSelector mode={mode} onChange={(value) => { onModeChange?.(value); onIntent(modeIntent(value, sessionId)); }} />
      <span className="toolbar-spacer" />
      <ModelSelector model={model} sessionId={sessionId} catalog={catalog} onIntent={onIntent} />
      <ContextRing percentage={contextUsage.percentage} />
      <button className="send-button" aria-label={busy ? "停止" : "发送"} title={busy ? "停止" : "发送"} disabled={!busy && !prompt.trim()} onClick={busy ? stop : submit}>{busy ? <Square size={15} /> : <Send size={15} />}</button>
    </div>
  </section>;
}
