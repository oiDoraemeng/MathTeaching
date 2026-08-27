import { FilePlus, Paperclip, Wrench } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { CapabilityCatalog, CapabilityDescriptor, IntentSender } from "../types";

const categoryLabels: Record<CapabilityDescriptor["category"], string> = {
  scene_read: "场景读取",
  scene_edit: "场景编辑",
  math: "数学分析",
  view: "视图",
  result: "结果",
  teaching: "教学说明",
};

function starter(capability: CapabilityDescriptor): string {
  return `请${capability.description.replace(/\.$/, "")}。`;
}

export function AttachmentActions({ sessionId, capabilityCatalog, onIntent, onInsertPrompt }: { sessionId: string; capabilityCatalog?: CapabilityCatalog; onIntent: IntentSender; onInsertPrompt: (value: string) => void }) {
  const [open, setOpen] = useState<"skills" | "attachments" | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const closeOnOutside = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(null);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(null);
    };
    document.addEventListener("mousedown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);

  const sendAttachment = (kind: "image" | "file") => {
    onIntent({
      protocol_version: 1,
      type: "attach_files",
      request_id: crypto.randomUUID(),
      session_id: sessionId,
      payload: { kind },
    });
    setOpen(null);
  };

  return <div ref={rootRef} className="attachment-actions" aria-label="Composer tools">
    <button aria-label="Tools" title="Tools" aria-expanded={open === "skills"} onClick={() => {
      setOpen(open === "skills" ? null : "skills");
      onIntent({ protocol_version: 1, type: "open_skills", request_id: crypto.randomUUID(), session_id: sessionId, payload: {} });
    }}><Wrench size={15} /></button>
    <button aria-label="Add attachment" title="Add attachment" aria-expanded={open === "attachments"} onClick={() => setOpen(open === "attachments" ? null : "attachments")}><Paperclip size={15} /></button>
    {open === "skills" && <div className="composer-popover skills-popover" role="menu"><strong>可用能力</strong>{Object.entries(categoryLabels).map(([category, label]) => {
      const items = capabilityCatalog?.capabilities.filter((item) => item.category === category) ?? [];
      return items.length ? <section className="capability-group" key={category}><span>{label}</span>{items.map((item) => <button key={item.name} role="menuitem" title={item.description} onClick={() => { onInsertPrompt(starter(item)); setOpen(null); }}><b>{item.name}</b><small>{item.description}</small></button>)}</section> : null;
    })}</div>}
    {open === "attachments" && <div className="composer-popover attachment-popover" role="menu"><button role="menuitem" onClick={() => sendAttachment("image")}><FilePlus size={14} />Add image</button><button role="menuitem" onClick={() => sendAttachment("file")}><FilePlus size={14} />Add file</button></div>}
  </div>;
}
