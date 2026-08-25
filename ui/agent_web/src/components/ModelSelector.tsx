import type { IntentSender } from "../types";
export function ModelSelector({ model, sessionId, onIntent }: { model: string; sessionId: string; onIntent: IntentSender }) {
  return <label className="model-selector"><span className="sr-only">模型</span><select value={model} onChange={(event) => onIntent({ protocol_version: 1, type: "change_model", request_id: crypto.randomUUID(), session_id: sessionId, payload: { model: event.target.value } })} aria-label="模型"><option>DeepSeek</option><option>OpenAI</option><option>Local</option></select></label>;
}
