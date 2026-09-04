import type { CSSProperties } from "react";

export function ContextRing({ percentage }: { percentage: number }) {
  const value = Math.max(0, Math.min(100, percentage));
  return <span className="context-ring" style={{ "--context-progress": `${value}%` } as CSSProperties} title={`上下文用量：${value}%`} aria-label={`上下文用量 ${value}%`} role="img"><span aria-hidden="true">{Math.round(value)}%</span></span>;
}
