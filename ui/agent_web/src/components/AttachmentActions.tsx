import { FilePlus, Paperclip, Wrench } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { IntentSender } from "../types";

export function AttachmentActions({ sessionId, onIntent }: { sessionId: string; onIntent: IntentSender }) {
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
    {open === "skills" && <div className="composer-popover skills-popover" role="menu"><strong>Math skills</strong><span>Geometry</span><span>Calculus</span><span>Linear algebra</span></div>}
    {open === "attachments" && <div className="composer-popover attachment-popover" role="menu"><button role="menuitem" onClick={() => sendAttachment("image")}><FilePlus size={14} />Add image</button><button role="menuitem" onClick={() => sendAttachment("file")}><FilePlus size={14} />Add file</button></div>}
  </div>;
}
