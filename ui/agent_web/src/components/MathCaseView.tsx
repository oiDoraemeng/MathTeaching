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
  // 数学案例流程的 default_pane_count 为 2：首屏即“全部显示”，两个步骤并排。
  const [showingAllPanes, setShowingAllPanes] = useState(
    paneCases.length > 1 && (caseData.caseLayout?.defaultPaneCount ?? 1) > 1,
  );
  const [stageIndex, setStageIndex] = useState(0);
  const stage = stages[stageIndex];
  const isVectorAddition = caseData.id === "ch01.ops.addition";
  // 1.5 的几何证明小节按讲义正文排版，与带案例的小节同一字号层级。
  const isLectureProof = lectureProofSubsection(caseData.id);
  // 讲义 1.2.1–1.2.4 都写成“自带公式的定义 + 正下方的几何解释”。
  const definitionOwnsFormula = lectureDefinitionOwnsFormula(caseData.id);
  const hasCaseLayout = paneCases.length > 0;
  const definitionAndFormula = definitionOwnsFormula
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
    const showAll = paneCases.length > 1 && (caseData.caseLayout?.defaultPaneCount ?? 1) > 1;
    setShowingAllPanes(showAll);
    if (showAll) onSetCasePaneCount?.(Math.min(4, paneCases.length));
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
    <article className={`math-case-view${isVectorAddition ? " math-case-view--vector-addition" : ""}${hasCaseLayout && !isVectorAddition ? " math-case-view--case-layout" : ""}${isLectureProof ? " math-case-view--proof" : ""}`} aria-label={`${caseData.name}数学解释`}>
      <header className="math-case-header">
        <span>{caseData.category}</span>
        <h1>{caseData.name}</h1>
        {caseData.summary && <p>{caseData.summary}</p>}
        {caseData.source && (caseData.source.headingPath.length > 0 || caseData.source.sourcePath.length > 0) && (
          <section className="math-case-source" aria-label="讲义来源">
            <span>讲义来源：</span>
            <span>{[...caseData.source.sourcePath, ...caseData.source.headingPath].join(" / ")}</span>
            {caseData.source.sourceHash && <small>（{caseData.source.sourceHash}）</small>}
          </section>
        )}
        {caseData.sourceDiagnostic && (
          <p className="math-case-source-diagnostic" role="status">
            讲义来源已变化：{caseData.sourceDiagnostic.code}（已发布 {caseData.sourceDiagnostic.publishedHash}，当前 {caseData.sourceDiagnostic.currentHash}）
          </p>
        )}
      </header>
      {hasLecture ? (
        <section className="math-case-lecture" aria-label="讲义正文">
          <MarkdownContent>{caseData.sourceExcerpt ?? ""}</MarkdownContent>
        </section>
      ) : (
        <section className="math-case-structured" aria-label="结构化数学解释">
          {section(sectionTitle(caseData, "definition", definitionOwnsFormula ? "定义" : "定义与公式"), definitionAndFormula)}
          {caseData.steps.length > 0 && (
            <section className="math-case-section">
              <h2>{sectionTitle(caseData, "derivation", "推导")}</h2>
              {/* 只有一段证明时它是连贯的讲义正文，不再套上“1.”的编号。 */}
              <ol className={`math-case-steps${caseData.steps.length === 1 ? " math-case-steps--single" : ""}`}>
                {caseData.steps.map((step, index) => (
                  <li key={`${caseData.id}-${index}`}><MarkdownContent>{step}</MarkdownContent></li>
                ))}
              </ol>
            </section>
          )}
          {section(sectionTitle(caseData, "intuition", "直觉"), caseData.intuition)}
          {/* 讲义把几何解释直接写在定义下方，向量加法与减法保留这一顺序。 */}
          {definitionOwnsFormula && section(sectionTitle(caseData, "geometric_meaning", "几何意义"), caseData.geometricMeaning)}
          {section(
            sectionTitle(
              caseData,
              "invariants",
              isVectorAddition
                ? "向量加法的基本性质"
                : caseData.id === "ch01.inner.definitions" ? "内积的基本性质" : "不变量",
            ),
            caseData.invariants?.join("\n\n"),
          )}
          {!definitionOwnsFormula && section(sectionTitle(caseData, "geometric_meaning", "几何意义"), caseData.geometricMeaning)}
          {workedExamples(caseData, hasCaseLayout && paneCases.length > 1 ? (
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
      {stages.length > 0 && !hasCaseLayout && (
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
          {/* 只有一张图时不再重复标题与说明，只保留切换按钮。 */}
          {stages.length > 1 && (
            <div className="math-case-section-heading">
              <h2>图形例子</h2>
              <span>{stageIndex + 1}/{stages.length}</span>
            </div>
          )}
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
          {stages.length > 1 && (
            <div className="math-case-stage">
              <h3>{stage?.title}</h3>
              <p>{stage?.caption}</p>
            </div>
          )}
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
  const hasCaseLayout = (caseData.caseLayout?.cases?.length ?? 0) > 0;
  return (
    <section className="math-case-section">
      <h2>{hasCaseLayout ? sectionTitle(caseData, "worked_examples", lectureDefinitionOwnsFormula(caseData.id) ? "数学案例" : "案例") : "数字例题"}</h2>
      {caseData.workedExamples?.map((example, index) => (
        <article className="math-case-example" key={example.id || `${caseData.id}-example-${index}`}>
          {!hasCaseLayout && <h3>{example.title || example.kind || `例题 ${index + 1}`}</h3>}
          {example.calculation?.map((line, lineIndex) => (
            <div
              className={hasCaseLayout && isFormulaOnly(line) ? "math-case-example-formula" : "math-case-example-prose"}
              key={`${example.id}-${lineIndex}`}
            >
              <MarkdownContent>{line}</MarkdownContent>
            </div>
          ))}
          {/* Results and checker payloads are audit data.  The displayed
              calculation already states the mathematical result, so showing
              both produces the duplicated "结果/校验" lines the lecture view
              must avoid. */}
        </article>
      ))}
      {controls}
    </section>
  );
}

/** 分节标题以讲义为准：artifact 的 sections 给出标题，缺失或仍是英文 id 时回退默认值。 */
function sectionTitle(caseData: CaseProjection, id: string, fallback: string): string {
  const title = caseData.sections?.find((item) => item.id === id)?.title?.trim();
  return title && title !== id ? title : fallback;
}

/** 讲义把公式写在定义（或定理、例题）块内的同构小节：定义块自带公式，不再单列「公式」分节。 */
function lectureDefinitionOwnsFormula(topicId: string): boolean {
  return topicId === "ch01.ops.addition"
    || topicId === "ch01.ops.subtraction"
    || topicId === "ch01.ops.scalar"
    || topicId === "ch01.ops.linear-combination"
    || topicId === "ch01.inner.definitions"
    || topicId === "ch01.projection.definition"
    // 讲义 2.5 的三个小节：公式写在定义（2.5.1）、定理（2.5.2）与例题（2.5.3）之内。
    || topicId === "ch02.matrix.row-column"
    || topicId === "ch02.matrix.transformed-grid"
    || topicId === "ch02.matrix.stretch-rotate-scale";
}

/** 讲义 1.5 的三个几何证明小节按讲义正文排版（没有案例窗格，字号仍按讲义层级）。 */
function lectureProofSubsection(topicId: string): boolean {
  return topicId === "ch01.proof.midline"
    || topicId === "ch01.proof.centroid"
    || topicId === "ch01.proof.parallelogram-diagonals";
}

function isFormulaOnly(line: string): boolean {
  const trimmed = line.trim();
  return (trimmed.startsWith("$$") && trimmed.endsWith("$$")) || (trimmed.startsWith("$") && trimmed.endsWith("$"));
}

function formatValue(value: unknown): string {
  if (value === undefined || value === null) return "未给出";
  return typeof value === "string" ? value : JSON.stringify(value);
}
