import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { MarkdownContent } from "./MarkdownContent";
import type { CaseProjection } from "../types";

/** Keep source-grounded explanations readable as one continuous lecture note. */
export function MathCaseView({
  caseData,
  onSelectStage,
}: {
  caseData: CaseProjection;
  onSelectStage?: (stageId: string) => void;
}) {
  const stages = caseData.storyboard ?? [];
  const [stageIndex, setStageIndex] = useState(0);
  const stage = stages[stageIndex];
  const definitionAndFormula = [
    caseData.definition?.trim(),
    caseData.formula ? `$$${caseData.formula}$$` : "",
  ].filter(Boolean).join("\n\n");
  const hasStructuredExplanation = Boolean(
    caseData.definition?.trim() ||
    caseData.derivation?.length ||
    caseData.intuition?.trim() ||
    caseData.geometricMeaning?.trim() ||
    caseData.workedExamples?.length ||
    caseData.readGuide?.length ||
    caseData.analogyBoundary?.trim(),
  );
  const hasLecture = !hasStructuredExplanation && Boolean(caseData.sourceExcerpt?.trim());

  useEffect(() => {
    setStageIndex(0);
  }, [caseData.id]);

  const selectStage = (index: number) => {
    const next = Math.max(0, Math.min(index, stages.length - 1));
    setStageIndex(next);
    if (stages[next]) onSelectStage?.(stages[next].id);
  };

  const section = (title: string, value?: string) => (
    value?.trim()
      ? <section className="math-case-section" key={title}><h2>{title}</h2><MarkdownContent>{value}</MarkdownContent></section>
      : null
  );

  return (
    <article className="math-case-view" aria-label={`${caseData.name}数学解释`}>
      <header className="math-case-header">
        <span>{caseData.category}</span>
        <h1>{caseData.name}</h1>
        {caseData.summary && <p>{caseData.summary}</p>}
      </header>
      {hasLecture ? (
        <section className="math-case-lecture" aria-label="讲义正文">
          <MarkdownContent>{caseData.sourceExcerpt ?? ""}</MarkdownContent>
        </section>
      ) : (
        <section className="math-case-structured" aria-label="结构化数学解释">
          {section("定义与公式", definitionAndFormula)}
          {caseData.steps.length > 0 && (
            <section className="math-case-section">
              <h2>推导</h2>
              <ol className="math-case-steps">
                {caseData.steps.map((step, index) => (
                  <li key={`${caseData.id}-${index}`}><MarkdownContent>{step}</MarkdownContent></li>
                ))}
              </ol>
            </section>
          )}
          {section("直觉", caseData.intuition)}
          {section("几何意义", caseData.geometricMeaning)}
          {workedExamples(caseData)}
          {section("误区", caseData.pitfalls?.join("\n"))}
          {section("不变量", caseData.invariants?.join("\n"))}
          {section("关联", caseData.connections?.join("\n"))}
          {section("类比边界", caseData.analogyBoundary)}
          {section("迁移", caseData.transferNote)}
          {section("读图提示", caseData.readGuide?.join("\n"))}
        </section>
      )}
      {stages.length > 0 && (
        <section className="math-case-storyboard" aria-label="几何图形例子">
          <div className="math-case-section-heading">
            <h2>图形例子</h2>
            <span>{stageIndex + 1}/{stages.length}</span>
          </div>
          <div className="math-case-stage-track" role="list" aria-label="几何例子">
            {stages.map((item, index) => (
              <button
                key={item.id}
                type="button"
                className={index === stageIndex ? "active" : ""}
                aria-current={index === stageIndex ? "step" : undefined}
                onClick={() => selectStage(index)}
              >
                {item.title}
              </button>
            ))}
          </div>
          <div className="math-case-stage">
            <h3>{stage?.title}</h3>
            <p>{stage?.caption}</p>
          </div>
          {stages.length > 1 && (
            <div className="math-case-stage-actions">
              <button
                type="button"
                aria-label="上一几何例子"
                title="上一几何例子"
                disabled={stageIndex === 0}
                onClick={() => selectStage(stageIndex - 1)}
              >
                <ChevronLeft size={15} aria-hidden="true" />
              </button>
              <button
                type="button"
                aria-label="下一几何例子"
                title="下一几何例子"
                disabled={stageIndex === stages.length - 1}
                onClick={() => selectStage(stageIndex + 1)}
              >
                <ChevronRight size={15} aria-hidden="true" />
              </button>
            </div>
          )}
        </section>
      )}
      {caseData.conclusion && (
        <section className="math-case-conclusion">
          <h2>结论</h2>
          <MarkdownContent>{caseData.conclusion}</MarkdownContent>
        </section>
      )}
    </article>
  );
}

function workedExamples(caseData: CaseProjection) {
  if (!(caseData.workedExamples?.length ?? 0)) return null;
  return (
    <section className="math-case-section">
      <h2>数字例题</h2>
      {caseData.workedExamples?.map((example, index) => (
        <article className="math-case-example" key={example.id || `${caseData.id}-example-${index}`}>
          <h3>{example.title || example.kind || `例题 ${index + 1}`}</h3>
          {example.calculation?.map((line, lineIndex) => (
            <MarkdownContent key={`${example.id}-${lineIndex}`}>{line}</MarkdownContent>
          ))}
          <p>结果：{formatValue(example.result)}</p>
          {example.checks?.map((check) => (
            <small key={check.name}>校验 {check.name}: {formatValue(check.expected)}</small>
          ))}
        </article>
      ))}
    </section>
  );
}

function formatValue(value: unknown): string {
  if (value === undefined || value === null) return "未给出";
  return typeof value === "string" ? value : JSON.stringify(value);
}
