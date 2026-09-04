import { ArrowLeft, EyeOff, Pencil, RotateCcw } from "lucide-react";
import { useRef, useState } from "react";
import type { HistoryItem, IntentSender } from "../types";

interface HistoryViewProps {
  visible: HistoryItem[];
  hidden: HistoryItem[];
  onBack: () => void;
  onIntent: IntentSender;
  onSelect: (item: HistoryItem) => void;
}

function HistoryRow({ item, hidden, onIntent, onSelect }: { item: HistoryItem; hidden?: boolean; onIntent: IntentSender; onSelect: (item: HistoryItem) => void }) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(item.title);
  const cancelledRef = useRef(false);
  const save = () => {
    if (cancelledRef.current) return;
    const value = title.trim();
    if (value && value !== item.title) onIntent({ protocol_version: 1, type: "rename_session", request_id: crypto.randomUUID(), session_id: item.id, payload: { title: value } });
    setEditing(false);
  };
  return <article className="history-row" onDoubleClick={() => onSelect(item)}>
    <button className="history-row-main history-row-open" onClick={() => onSelect(item)}>
      {editing ? <input aria-label={`重命名 ${item.title}`} value={title} onChange={(event) => setTitle(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") save(); if (event.key === "Escape") { cancelledRef.current = true; setTitle(item.title); setEditing(false); event.preventDefault(); } }} onBlur={save} autoFocus /> : <strong>{item.title}</strong>}
      <span>{item.turn_count} 轮</span>
    </button>
    <div className="history-row-actions">
      {hidden ? <button aria-label={`恢复 ${item.title}`} title={`恢复 ${item.title}`} onClick={() => onIntent({ protocol_version: 1, type: "restore_hidden_session", request_id: crypto.randomUUID(), session_id: item.id, payload: {} })}><RotateCcw size={14} /></button> : <button aria-label={`隐藏 ${item.title}`} title={`隐藏 ${item.title}`} onClick={() => onIntent({ protocol_version: 1, type: "hide_session", request_id: crypto.randomUUID(), session_id: item.id, payload: {} })}><EyeOff size={14} /></button>}
      {!hidden && !editing && <button aria-label={`重命名 ${item.title}`} title={`重命名 ${item.title}`} onClick={() => { cancelledRef.current = false; setTitle(item.title); setEditing(true); }}><Pencil size={14} /></button>}
    </div>
  </article>;
}

export function HistoryView({ visible, hidden, onBack, onIntent, onSelect }: HistoryViewProps) {
  return <section className="secondary-view history-view" aria-label="对话历史">
    <div className="secondary-view-header"><button aria-label="返回当前对话" title="返回当前对话" onClick={onBack}><ArrowLeft size={15} /></button><h1>历史记录</h1></div>
    <div className="history-list">{visible.length ? visible.map((item) => <HistoryRow key={item.id} item={item} onIntent={onIntent} onSelect={onSelect} />) : <p className="secondary-empty">暂无会话</p>}</div>
    {hidden.length > 0 && <><h2>已隐藏</h2><div className="history-list">{hidden.map((item) => <HistoryRow key={item.id} item={item} hidden onIntent={onIntent} onSelect={onSelect} />)}</div></>}
  </section>;
}
