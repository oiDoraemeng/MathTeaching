import { useRef, type WheelEvent } from "react";
import { BookOpen, X } from "lucide-react";
import type { CaseProjection, SessionProjection } from "../types";

interface SessionTabsProps {
  sessions: SessionProjection[];
  activeSessionId: string;
  onSelect: (id: string) => void;
  onClose: (id: string) => void;
  cases?: CaseProjection[];
  activeTab?: string;
  onSelectCase?: (id: string) => void;
}

export function SessionTabs({ sessions, activeSessionId, onSelect, onClose, cases = [], activeTab, onSelectCase }: SessionTabsProps) {
  const tabsRef = useRef<HTMLElement>(null);
  const openSessions = sessions.filter((session) => !session.closed && !session.hidden);
  const selectedTab = activeTab ?? `session:${activeSessionId}`;
  const displayTitle = (title?: string) => !title || title === "New Chat" ? "新对话" : title;
  const handleWheel = (event: WheelEvent<HTMLElement>) => {
    if (!tabsRef.current || event.deltaY === 0) return;
    if (Math.abs(event.deltaY) > Math.abs(event.deltaX)) {
      tabsRef.current.scrollLeft += event.deltaY;
      event.preventDefault();
    }
  };
  return <nav ref={tabsRef} onWheel={handleWheel} className="session-tabs" aria-label="会话">
    {openSessions.map((session) => <div key={`session-${session.id}`} className={`session-tab ${selectedTab === `session:${session.id}` ? "active" : ""}`}>
      <button className="session-tab-select" onClick={() => onSelect(session.id)} aria-current={selectedTab === `session:${session.id}` ? "page" : undefined}>{displayTitle(session.title)}</button>
      {openSessions.length > 1 && <button className="session-tab-close" aria-label={`关闭 ${displayTitle(session.title)}`} title="关闭会话" onClick={() => onClose(session.id)}><X size={13} /></button>}
    </div>)}
    {cases.map((caseData) => <div key={`case-${caseData.id}`} className={`session-tab session-tab-case ${selectedTab === `case:${caseData.id}` ? "active" : ""}`}>
      <button className="session-tab-select" onClick={() => onSelectCase?.(caseData.id)} aria-current={selectedTab === `case:${caseData.id}` ? "page" : undefined}><BookOpen size={12} aria-hidden="true" />{caseData.name}</button>
      <button className="session-tab-close" aria-label={`关闭 ${caseData.name}`} title="关闭案例" onClick={() => onClose(`case:${caseData.id}`)}><X size={13} /></button>
    </div>)}
  </nav>;
}
