import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { MarkdownContent } from "./MarkdownContent";
import type { CaseProjection } from "../types";

export function MathCaseView({ caseData }: { caseData: CaseProjection }) {
  const stages = caseData.storyboard ?? [];
  const [stageIndex, setStageIndex] = useState(0);
  const stage = stages[stageIndex];
  const section = (title: string, value?: string) => value?.trim() ? <section className="math-case-section"><h2>{title}</h2><MarkdownContent>{value}</MarkdownContent></section> : null;
  return <section className="math-case-view" aria-label={`${caseData.name}数学解释`}>
    <header className="math-case-header"><span>{caseData.category}</span><h1>{caseData.name}</h1>{caseData.summary && <p>{caseData.summary}</p>}</header>
    <div className="math-case-formula" aria-label="公式"><MarkdownContent>{`$$${caseData.formula}$$`}</MarkdownContent></div>
    {section("定义", caseData.definition)}
    <ol className="math-case-steps">{caseData.steps.map((step, index) => <li key={`${caseData.id}-${index}`}><MarkdownContent>{step}</MarkdownContent></li>)}</ol>
    {section("直觉", caseData.intuition)}
    {section("几何意义", caseData.geometricMeaning)}
    {(caseData.workedExamples?.length ?? 0) > 0 && <section className="math-case-section"><h2>数字例题</h2>{caseData.workedExamples?.map((example, index) => <article className="math-case-example" key={example.id || `${caseData.id}-example-${index}`}><h3>{example.title || example.kind || `例题 ${index + 1}`}</h3>{example.calculation?.map((line, lineIndex) => <MarkdownContent key={`${example.id}-${lineIndex}`}>{line}</MarkdownContent>)}<p>结果：{formatValue(example.result)}</p>{example.checks?.map((check) => <small key={check.name}>校验 {check.name}: {formatValue(check.expected)}</small>)}</article>)}</section>}
    {caseData.claims?.length ? <section className="math-case-section"><h2>数学主张</h2>{caseData.claims.map((claim) => <article className="math-case-claim" key={claim.id}><strong>{claim.id}</strong><MarkdownContent>{claim.statement}</MarkdownContent>{claim.formula && <MarkdownContent>{`$$${claim.formula}$$`}</MarkdownContent>}<div className="math-case-evidence">{claim.formulaSymbols?.map((symbol) => <span key={`${claim.id}-${symbol}`} style={{ borderColor: caseData.symbolPalette?.[symbol] || "var(--agent-border)" }}>{symbol}</span>)}{claim.entityRefs?.map((ref) => <span key={`${claim.id}-entity-${ref}`}>{ref}</span>)}{claim.relationRefs?.map((ref) => <span key={`${claim.id}-relation-${ref}`}>{ref}</span>)}</div></article>)}</section> : null}
    {stages.length > 0 && <section className="math-case-section math-case-storyboard"><div className="math-case-storyboard-header"><h2>读图</h2><span>{stageIndex + 1}/{stages.length}</span></div><div className="math-case-stage"><h3>{stage?.title}</h3><p>{stage?.caption}</p><small>{stage?.visibleRefs.join(" · ")}</small></div><div className="math-case-stage-actions"><button type="button" aria-label="上一阶段" title="上一阶段" disabled={stageIndex === 0} onClick={() => setStageIndex((value) => Math.max(0, value - 1))}><ChevronLeft size={15} aria-hidden="true" /></button><button type="button" aria-label="下一阶段" title="下一阶段" disabled={stageIndex === stages.length - 1} onClick={() => setStageIndex((value) => Math.min(stages.length - 1, value + 1))}><ChevronRight size={15} aria-hidden="true" /></button></div></section>}
    {section("误区", caseData.pitfalls?.join("\n"))}
    {section("不变量", caseData.invariants?.join("\n"))}
    {section("关联", caseData.connections?.join("\n"))}
    {section("迁移", caseData.transferNote)}
    <section className="math-case-conclusion"><h2>结论</h2><MarkdownContent>{caseData.conclusion}</MarkdownContent></section>
  </section>;
}

function formatValue(value: unknown): string {
  if (value === undefined || value === null) return "未给出";
  return typeof value === "string" ? value : JSON.stringify(value);
}
