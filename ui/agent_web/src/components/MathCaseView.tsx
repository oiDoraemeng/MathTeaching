import { MarkdownContent } from "./MarkdownContent";
import type { CaseProjection } from "../types";

export function MathCaseView({ caseData }: { caseData: CaseProjection }) {
  return <section className="math-case-view" aria-label={`${caseData.name}数学解释`}>
    <header className="math-case-header"><span>{caseData.category}</span><h1>{caseData.name}</h1>{caseData.summary && <p>{caseData.summary}</p>}</header>
    <div className="math-case-formula" aria-label="公式"><MarkdownContent>{`$$${caseData.formula}$$`}</MarkdownContent></div>
    <ol className="math-case-steps">{caseData.steps.map((step, index) => <li key={`${caseData.id}-${index}`}><MarkdownContent>{step}</MarkdownContent></li>)}</ol>
    <section className="math-case-conclusion"><h2>结论</h2><MarkdownContent>{caseData.conclusion}</MarkdownContent></section>
  </section>;
}
