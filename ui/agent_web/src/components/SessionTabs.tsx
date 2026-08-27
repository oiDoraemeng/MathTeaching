import { X } from "lucide-react";
import type { SessionProjection } from "../types";

interface SessionTabsProps {
  sessions: SessionProjection[];
  activeSessionId: string;
  onSelect: (id: string) => void;
  onClose: (id: string) => void;
}

export function SessionTabs({ sessions, activeSessionId, onSelect, onClose }: SessionTabsProps) {
  const openSessions = sessions.filter((session) => !session.closed && !session.hidden);
  return <nav className="session-tabs" aria-label="会话">
    {openSessions.map((session) => <div key={session.id} className={`session-tab ${session.id === activeSessionId ? "active" : ""}`}>
      <button className="session-tab-select" onClick={() => onSelect(session.id)} aria-current={session.id === activeSessionId ? "page" : undefined}>{session.title || "New Chat"}</button>
      {openSessions.length > 1 && <button className="session-tab-close" aria-label={`关闭 ${session.title || "New Chat"}`} title="关闭会话" onClick={() => onClose(session.id)}><X size={13} /></button>}
    </div>)}
  </nav>;
}
