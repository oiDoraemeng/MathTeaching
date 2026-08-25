interface EmptyStateProps { onStarter?: (prompt: string) => void; }
const starters = ["绘制函数", "解释几何概念", "演示导数", "理解矩阵变换"];
export function EmptyState({ onStarter }: EmptyStateProps) {
  return <div className="empty-state"><h1>开始一个数学探索</h1><p>用自然语言描述你想理解或绘制的内容</p><div className="starter-grid">{starters.map((label) => <button key={label} className="starter-card" onClick={() => onStarter?.(label)}>{label}</button>)}</div></div>;
}
