import { useEffect, useRef, useState } from "react";
import type { IntentSender, ModelCatalog, ModelDescriptor } from "../types";

const fallbackCatalog: ModelCatalog = {
  builtin: [
    { id: "deepseek-v4-flash-high", name: "Deepseek-V4-Flash High", group: "builtin", capabilities: ["reasoning"] },
    { id: "deepseek-v4-pro-high", name: "Deepseek-V4-Pro High", group: "builtin", context_window: "1M", capabilities: ["image_input", "reasoning"] },
    { id: "deepseek-v4-flash-vision-exp", name: "deepseek-v4-flash-vision-exp", group: "builtin", capabilities: ["image_input", "reasoning"] },
  ],
  custom: [],
};

function detailTitle(item: ModelDescriptor): string {
  return item.id === "deepseek-v4-pro-high" ? "DeepSeek-V4-Pro" : item.name;
}

function ModelDetails({ item }: { item: ModelDescriptor }) {
  const capabilities = item.capabilities?.length ? item.capabilities.join("、") : "基础对话";
  return <div className="model-details" role="tooltip">
    <strong>{detailTitle(item)}</strong>
    <span>{item.context_window ? `上下文窗口：${item.context_window}` : "数学教学模型"}</span>
    <span>可用功能：{capabilities}</span>
    <span>思考模式：{item.thinking_enabled === false ? "关闭" : "开启"}</span>
    <span>思考强度：{item.thinking_levels?.join(" · ") ?? "Low · High · X-High"}</span>
  </div>;
}

function ModelRow({ item, selected, onSelect }: { item: ModelDescriptor; selected: boolean; onSelect: () => void }) {
  const [hovered, setHovered] = useState(false);
  return <div className="model-row" onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)} onFocus={() => setHovered(true)} onBlur={() => setHovered(false)}>
    <button role="menuitem" className={selected ? "selected" : ""} onClick={onSelect}>{item.name}</button>
    {hovered && <ModelDetails item={item} />}
  </div>;
}

export function ModelSelector({ model, sessionId, onIntent, catalog = fallbackCatalog }: { model: string; sessionId: string; onIntent: IntentSender; catalog?: ModelCatalog }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const closeOnOutside = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);
  const selected = [...catalog.builtin, ...catalog.custom].find((item) => item.id === model || item.name === model);
  const select = (item: ModelDescriptor) => { onIntent({ protocol_version: 1, type: "change_model", request_id: crypto.randomUUID(), session_id: sessionId, payload: { model: item.id } }); setOpen(false); };
  return <div ref={rootRef} className="model-selector model-picker">
    <button className="model-picker-button" aria-label="模型" title="模型" aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen(!open)}>{selected?.name ?? model}<span aria-hidden="true">▾</span></button>
    {open && <div className="model-popover" role="menu">
      <strong>内置模型</strong>
      {catalog.builtin.map((item) => <ModelRow key={item.id} item={item} selected={item.id === model || item.name === model} onSelect={() => select(item)} />)}
      <strong>自定义模型</strong>
      {catalog.custom.map((item) => <ModelRow key={item.id} item={item} selected={item.id === model} onSelect={() => select(item)} />)}
      <button role="menuitem" className="model-configure" onClick={() => onIntent({ protocol_version: 1, type: "open_settings", request_id: crypto.randomUUID(), session_id: sessionId, payload: { section: "models" } })}>+ 配置自定义模型</button>
    </div>}
  </div>;
}
