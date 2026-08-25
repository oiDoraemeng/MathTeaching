import { FileText, Image, Menu, Paperclip, Wrench } from "lucide-react";
import type { IntentSender } from "../types";
export function AttachmentActions({ sessionId, onIntent }: { sessionId: string; onIntent: IntentSender }) {
  const send = (kind: string) => onIntent({ protocol_version: 1, type: "attach_files", request_id: crypto.randomUUID(), session_id: sessionId, payload: { kind } });
  return <div className="attachment-actions" aria-label="输入工具"><button aria-label="附件" title="添加附件" onClick={() => send("file")}><Paperclip size={15} /></button><button aria-label="图片" title="添加图片" onClick={() => send("image")}><Image size={15} /></button><button aria-label="文档" title="添加文档" onClick={() => send("document")}><FileText size={15} /></button><button aria-label="菜单" title="快捷菜单" onClick={() => send("menu")}><Menu size={15} /></button><button aria-label="工具" title="工具" onClick={() => send("tool")}><Wrench size={15} /></button></div>;
}
