import { History, Plus, Settings, X } from "lucide-react";

interface AgentHeaderProps {
  onNewChat: () => void;
  onHistory: () => void;
  onSettings: () => void;
  onClose?: () => void;
}

export function AgentHeader({ onNewChat, onHistory, onSettings, onClose }: AgentHeaderProps) {
  return <header className="agent-header">
    <strong>MathAgent</strong><span className="header-spacer" />
    <button aria-label="新建对话" title="新建对话" onClick={onNewChat}><Plus size={16} /></button>
    <button aria-label="历史记录" title="历史记录" onClick={onHistory}><History size={16} /></button>
    <button aria-label="设置" title="设置" onClick={onSettings}><Settings size={16} /></button>
    {onClose && <button aria-label="关闭 Agent" title="关闭 Agent" onClick={onClose}><X size={16} /></button>}
  </header>;
}
