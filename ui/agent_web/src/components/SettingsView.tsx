import { ArrowLeft, Edit3, Eye, EyeOff, Trash2 } from "lucide-react";
import { useState } from "react";
import type { IntentSender, ModelCatalog, SessionProjection } from "../types";

interface SettingsViewProps {
  session: SessionProjection;
  catalog: ModelCatalog;
  settingsState?: { provider?: string; protocol?: string; base_url?: string; model?: string; key_configured?: boolean; key_suffix?: string };
  onBack: () => void;
  onIntent: IntentSender;
}

const inputTiers = ["32K", "64K", "128K", "256K"];
const outputTiers = ["8K", "16K", "32K", "64K"];

export function SettingsView({ session, catalog, settingsState, onBack, onIntent }: SettingsViewProps) {
  const [draft, setDraft] = useState({ id: "", provider: "openai", protocol: "responses", base_url: "", api_key: "", model: "", tools: false, image_input: false, reasoning: false, input_context: "", output_context: "" });
  const [showKey, setShowKey] = useState(false);
  const editCustom = (item: ModelCatalog["custom"][number]) => setDraft({ id: item.id, provider: item.provider ?? "openai", protocol: item.protocol ?? "responses", base_url: String(item.base_url ?? ""), api_key: "", model: String(item.model ?? item.name), tools: item.capabilities?.includes("tools") ?? false, image_input: item.capabilities?.includes("image_input") ?? false, reasoning: item.capabilities?.includes("reasoning") ?? false, input_context: String(item.input_context ?? ""), output_context: String(item.output_context ?? "") });
  const updateThinking = (enabled: boolean, level: "Low" | "High" | "X-High" = session.thinking_level ?? "High") => onIntent({ protocol_version: 1, type: "set_thinking_preferences", request_id: crypto.randomUUID(), session_id: session.id, payload: { enabled, level } });
  const saveCustom = () => {
    if (!draft.id.trim() || !draft.base_url.trim() || !draft.model.trim()) return;
    onIntent({ protocol_version: 1, type: "save_custom_model", request_id: crypto.randomUUID(), session_id: session.id, payload: draft });
    setDraft({ id: "", provider: "openai", protocol: "responses", base_url: "", api_key: "", model: "", tools: false, image_input: false, reasoning: false, input_context: "", output_context: "" });
  };
  return <section className="secondary-view settings-view" aria-label="MathAgent settings">
    <div className="secondary-view-header"><button aria-label="Back to conversation" title="Back to conversation" onClick={onBack}><ArrowLeft size={15} /></button><h1>Settings</h1></div>
    <section className="settings-section"><h2>Agent / Model</h2>
      <label>思考模式 <input type="checkbox" checked={session.thinking_enabled ?? true} onChange={(event) => updateThinking(event.target.checked)} /></label>
      <div className="thinking-levels">{(["Low", "High", "X-High"] as const).map((level) => <button key={level} disabled={session.thinking_enabled === false} className={session.thinking_level === level ? "selected" : ""} onClick={() => updateThinking(true, level)}>{level}</button>)}</div>
      <p>Provider: {settingsState?.provider ?? "openai"} · {settingsState?.protocol ?? "responses"} · API Key {settingsState?.key_configured ? `已配置 (••••${settingsState.key_suffix ?? ""})` : "未配置"}</p>
    </section>
    <section className="settings-section"><h2>Skills</h2><p>Geometry、Calculus、Linear algebra 会由 MathAgent 自动选择。</p></section>
    <section className="settings-section"><h2>Memory</h2><p>学习水平、视觉偏好和最近主题保存在本地 `.math` 配置中。</p></section>
    <section className="settings-section"><h2>Rules</h2><p>Math Teacher instructions 由桌面设置对话框编辑并保存。</p></section>
    <section className="settings-section model-settings"><h2>内置模型</h2>
      <div className="settings-model-list">{catalog.builtin.map((item) => <div className={item.id === session.model ? "settings-model selected" : "settings-model"} key={item.id}><span>{item.name}</span><button aria-label={`Select ${item.name}`} onClick={() => onIntent({ protocol_version: 1, type: "set_selected_model", request_id: crypto.randomUUID(), session_id: session.id, payload: { model: item.id } })}>选择</button></div>)}
      {catalog.custom.map((item) => <div className="settings-model custom" key={item.id}><span>{item.name}</span><div><button aria-label={`Select ${item.name}`} onClick={() => onIntent({ protocol_version: 1, type: "set_selected_model", request_id: crypto.randomUUID(), session_id: session.id, payload: { model: item.id } })}>选择</button><button aria-label={`Edit ${item.name}`} onClick={() => editCustom(item)}><Edit3 size={13} /></button><button aria-label={`Delete ${item.name}`} onClick={() => onIntent({ protocol_version: 1, type: "delete_custom_model", request_id: crypto.randomUUID(), session_id: session.id, payload: { id: item.id } })}><Trash2 size={13} /></button></div></div>)}</div>
      <h3>+ 配置自定义模型</h3>
      <input aria-label="模型 ID" placeholder="模型 ID" value={draft.id} onChange={(event) => setDraft({ ...draft, id: event.target.value })} />
      <select aria-label="供应商" value={draft.provider} onChange={(event) => setDraft({ ...draft, provider: event.target.value })}><option value="openai">Custom</option><option value="deepseek">DeepSeek</option></select>
      <select aria-label="API protocol" value={draft.protocol} onChange={(event) => setDraft({ ...draft, protocol: event.target.value })}><option value="responses">OpenAI - Responses</option><option value="chat_completions">Chat Completions</option></select>
      <input aria-label="BASE URL" placeholder="https://api.example.com/v1" value={draft.base_url} onChange={(event) => setDraft({ ...draft, base_url: event.target.value })} />
      <div className="key-input"><input aria-label="API KEY" type={showKey ? "text" : "password"} placeholder="请输入 API Key" value={draft.api_key} onChange={(event) => setDraft({ ...draft, api_key: event.target.value })} /><button aria-label="Toggle API key visibility" onClick={() => setShowKey(!showKey)}>{showKey ? <EyeOff size={14} /> : <Eye size={14} />}</button></div>
      <input aria-label="模型名称" placeholder="输入模型 ID" value={draft.model} onChange={(event) => setDraft({ ...draft, model: event.target.value })} />
      <div className="settings-checks"><label><input type="checkbox" checked={draft.tools} onChange={(event) => setDraft({ ...draft, tools: event.target.checked })} />工具调用</label><label><input type="checkbox" checked={draft.image_input} onChange={(event) => setDraft({ ...draft, image_input: event.target.checked })} />图片输入</label><label><input type="checkbox" checked={draft.reasoning} onChange={(event) => setDraft({ ...draft, reasoning: event.target.checked })} />推理</label></div>
      <div className="settings-context-grid"><label>输入<select value={draft.input_context} onChange={(event) => setDraft({ ...draft, input_context: event.target.value })}><option value="">使用供应商默认值</option>{inputTiers.map((tier) => <option key={tier}>{tier}</option>)}</select></label><label>输出<select value={draft.output_context} onChange={(event) => setDraft({ ...draft, output_context: event.target.value })}><option value="">使用供应商默认值</option>{outputTiers.map((tier) => <option key={tier}>{tier}</option>)}</select></label></div>
      <div className="settings-form-actions"><button className="settings-test" disabled={!draft.base_url.trim() || !draft.model.trim()} onClick={() => onIntent({ protocol_version: 1, type: "test_model_provider", request_id: crypto.randomUUID(), session_id: session.id, payload: draft })}>测试连接</button><button className="settings-save" disabled={!draft.id.trim() || !draft.base_url.trim() || !draft.model.trim()} onClick={saveCustom}>保存</button></div>
    </section>
  </section>;
}
