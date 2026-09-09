import { useEffect, useState, type ReactNode } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { MarkdownContent } from "./MarkdownContent";
import type { CaseProjection } from "../types";

/** Keep source-grounded explanations readable as one continuous lecture note. */
export function MathCaseView({
  caseData,
  onSelectStage,
  onSelectCasePane,
  onSetCasePaneCount,
}: {
  caseData: CaseProjection;
  onSelectStage?: (stageId: string) => void;
  onSelectCasePane?: (paneId: string, stageId?: string) => void;
  onSetCasePaneCount?: (count: number) => void;
}) {
  const stages = caseData.storyboard ?? [];
  const paneCases = caseData.caseLayout?.cases ?? [];
  const [activePaneId, setActivePaneId] = useState(caseData.activeCaseId ?? paneCases[0]?.id ?? "");
  const [showingAllPanes, setShowingAllPanes] = useState(false);
  const [stageIndex, setStageIndex] = useState(0);
  const stage = stages[stageIndex];
  const isVectorAddition = caseData.id === "ch01.ops.addition";
  const definitionAndFormula = isVectorAddition
    ? caseData.definition?.trim() ?? ""
    : [
      caseData.definition?.trim(),
      caseData.formula ? `$$${caseData.formula}$$` : "",
    ].filter(Boolean).join("\n\n");
  const caseControlsCoverStages = paneCases.length === stages.length
    && paneCases.length > 0
    && paneCases.every((pane) => pane.stageRefs.length === 1 && stages.some((item) => item.id === pane.stageRefs[0]));
  const hasStructuredExplanation = Boolean(
    caseData.definition?.trim() ||
    caseData.derivation?.length ||
    caseData.intuition?.trim() ||
    caseData.geometricMeaning?.trim() ||
    caseData.invariants?.length ||
    caseData.workedExamples?.length ||
    caseData.readGuide?.length ||
    caseData.analogyBoundary?.trim(),
  );
  const hasLecture = !hasStructuredExplanation && Boolean(caseData.sourceExcerpt?.trim());

  useEffect(() => {
    setStageIndex(0);
    setActivePaneId(caseData.activeCaseId ?? paneCases[0]?.id ?? "");
    setShowingAllPanes(false);
  }, [caseData.id, caseData.activeCaseId]);

  const selectPane = (paneId: string, stageId?: string) => {
    setActivePaneId(paneId);
    setShowingAllPanes(false);
    const nextIndex = stageId ? stages.findIndex((item) => item.id === stageId) : -1;
    if (nextIndex >= 0) {
      setStageIndex(nextIndex);
      onSelectStage?.(stageId!);
    }
    onSelectCasePane?.(paneId, stageId);
  };

  const showAllPanes = () => {
    setShowingAllPanes(true);
    onSetCasePaneCount?.(Math.min(4, paneCases.length));
  };

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
    <article className={`math-case-view${isVectorAddition ? " math-case-view--vector-addition" : ""}`} aria-label={`${caseData.name}数学解释`}>
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
          {section(isVectorAddition ? "向量加法的基本性质" : "不变量", caseData.invariants?.join("\n\n"))}
          {section("几何意义", caseData.geometricMeaning)}
          {workedExamples(caseData, isVectorAddition && paneCases.length > 0 ? (
            <div className="math-case-example-controls" role="list" aria-label="二维案例选择">
              {paneCases.map((pane) => (
                <button
                  key={pane.id}
                  type="button"
                  className={!showingAllPanes && pane.id === activePaneId ? "active" : ""}
                  aria-current={!showingAllPanes && pane.id === activePaneId ? "true" : undefined}
                  onClick={() => selectPane(pane.id, pane.stageRefs[0])}
                >
                  {pane.purpose}
                </button>
              ))}
              <button
                type="button"
                className={showingAllPanes ? "active" : ""}
                aria-pressed={showingAllPanes}
                onClick={showAllPanes}
              >
                全部显示
              </button>
            </div>
          ) : null)}
          {section("误区", caseData.pitfalls?.join("\n"))}
          {section("关联", caseData.connections?.join("\n"))}
          {section("类比边界", caseData.analogyBoundary)}
          {section("迁移", caseData.transferNote)}
          {section("读图提示", caseData.readGuide?.join("\n"))}
        </section>
      )}
      {stages.length > 0 && !isVectorAddition && (
        <section className="math-case-storyboard" aria-label="几何图形例子">
          {paneCases.length > 0 && (
            <div className="math-case-pane-cases" role="list" aria-label="案例窗格">
              {paneCases.map((pane) => (
                <button
                  key={pane.id}
                  type="button"
                  className={!showingAllPanes && pane.id === activePaneId ? "active" : ""}
                  aria-current={!showingAllPanes && pane.id === activePaneId ? "true" : undefined}
                  onClick={() => selectPane(pane.id, pane.stageRefs[0])}
                >
                  {pane.purpose}
                </button>
              ))}
              <button
                type="button"
                className={showingAllPanes ? "active" : ""}
                aria-pressed={showingAllPanes}
                onClick={showAllPanes}
              >
                全部显示
              </button>
            </div>
          )}
          <div className="math-case-section-heading">
            <h2>图形例子</h2>
            <span>{stageIndex + 1}/{stages.length}</span>
          </div>
          {!caseControlsCoverStages && (
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
          )}
          <div className="math-case-stage">
            <h3>{stage?.title}</h3>
            <p>{stage?.caption}</p>
          </div>
          {stages.length > 1 && !caseControlsCoverStages && (
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

function workedExamples(caseData: CaseProjection, controls?: ReactNode) {
  if (!(caseData.workedExamples?.length ?? 0)) return null;
  const isVectorAddition = caseData.id === "ch01.ops.addition";
  return (
    <section className="math-case-section">
      <h2>{isVectorAddition ? "案例" : "数字例题"}</h2>
      {caseData.workedExamples?.map((example, index) => (
        <article className="math-case-example" key={example.id || `${caseData.id}-example-${index}`}>
          <h3>{example.title || example.kind || `例题 ${index + 1}`}</h3>
          {example.calculation?.map((line, lineIndex) => (
            <div
              className={isVectorAddition && isFormulaOnly(line) ? "math-case-example-formula" : "math-case-example-prose"}
              key={`${example.id}-${lineIndex}`}
            >
              <MarkdownContent>{line}</MarkdownContent>
            </div>
          ))}
          {!isVectorAddition && <p>结果：{formatValue(example.result)}</p>}
          {!isVectorAddition && example.checks?.map((check) => (
            <small key={check.name}>校验 {check.name}: {formatValue(check.expected)}</small>
          ))}
        </article>
      ))}
      {controls}
    </section>
  );
}

function isFormulaOnly(line: string): boolean {
  const trimmed = line.trim();
  return (trimmed.startsWith("$$") && trimmed.endsWith("$$")) || (trimmed.startsWith("$") && trimmed.endsWith("$"));
}

function formatValue(value: unknown): string {
  if (value === undefined || value === null) return "未给出";
  return typeof value === "string" ? value : JSON.stringify(value);
}
