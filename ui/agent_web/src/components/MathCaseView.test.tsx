import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MathCaseView } from "./MathCaseView";

describe("MathCaseView", () => {
  it.each([["ch01.ops.addition", 3, 3], ["other-lecture", 6, 4]] as const)(
    "requests the current lecture's cases within the viewport limit (%s)",
    (topicId, total, visible) => {
      const onSetCasePaneCount = vi.fn();
      render(<MathCaseView caseData={{
        id: topicId, category: "向量", name: "测试讲义", formula: "a+b", steps: [], conclusion: "",
        workedExamples: [{ id: "example", title: "例题", calculation: ["对应分量相加"], result: 1, checks: [] }],
        storyboard: [{ id: "stage", title: "阶段", caption: "", layout: "overlay", visibleRefs: [], visibleAliases: [], anchor: [0, 0] }],
        caseLayout: { defaultPaneCount: 1, cases: Array.from({ length: total }, (_, i) => ({
          id: `case-${i}`, topicId, exampleRef: "example", claimRefs: [], stageRefs: ["stage"], purpose: `案例 ${i}`,
        })) },
      }} onSetCasePaneCount={onSetCasePaneCount} />);
      fireEvent.click(screen.getByRole("button", { name: "全部显示" }));
      expect(onSetCasePaneCount).toHaveBeenCalledTimes(1);
      expect(onSetCasePaneCount).toHaveBeenCalledWith(visible);
      expect(screen.getByRole("button", { name: "全部显示" })).toHaveAttribute("aria-pressed", "true");
    },
  );

  it("renders semantic formula and conclusion cards with spaced steps", () => {
    render(<MathCaseView caseData={{ id: "case-1", category: "向量", name: "向量加法", formula: "a+b", steps: ["第一步"], conclusion: "结论" }} />);
    expect(screen.getByRole("heading", { name: "向量加法" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "结论", level: 2 })).toBeInTheDocument();
  });

  it("shows a rendered preview without sending case-pane commands before the scene is ready", async () => {
    const onPreviewReady = vi.fn();
    const onSetCasePaneCount = vi.fn();
    render(<MathCaseView caseData={{
      id: "case-preview", category: "向量", name: "预览", formula: "", steps: [], conclusion: "",
      sceneReady: false, previewToken: "preview-8",
      workedExamples: [{ id: "example", calculation: ["预览案例"], checks: [] }],
      caseLayout: { defaultPaneCount: 2, cases: [
        { id: "case-1", topicId: "case-preview", exampleRef: "example", claimRefs: [], stageRefs: [], purpose: "案例 1" },
        { id: "case-2", topicId: "case-preview", exampleRef: "example", claimRefs: [], stageRefs: [], purpose: "案例 2" },
      ] },
    }} onPreviewReady={onPreviewReady} onSetCasePaneCount={onSetCasePaneCount} />);

    expect(screen.getByRole("article", { name: "预览数学解释" })).toHaveAttribute("aria-busy", "true");
    expect(screen.getByRole("button", { name: "案例 1" })).toBeDisabled();
    await waitFor(() => expect(onPreviewReady).toHaveBeenCalledWith("preview-8"));
    expect(onSetCasePaneCount).not.toHaveBeenCalled();
  });

  it("renders the lecture definition and section titles for a case without a standalone formula", () => {
    render(<MathCaseView caseData={{
      id: "ch01.inner.definitions", category: "内积", name: "1.3.1 内积的两种定义", formula: "", steps: [], conclusion: "",
      definition: "定义 1.10（内积）：设 $\\boldsymbol a$ 与 $\\boldsymbol b$ 为两个向量。",
      invariants: ["性质 1.1（对称性）"],
      sections: [{ id: "definition", title: "定义" }, { id: "invariants", title: "内积的基本性质" }],
    }} />);
    expect(screen.getByRole("heading", { name: "定义", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "内积的基本性质", level: 2 })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "讲义正文" })).not.toBeInTheDocument();
  });

  it("renders header LaTeX as math instead of literal dollar signs", () => {
    const { container } = render(<MathCaseView caseData={{
      id: "ch02.matrix.composition", category: "2.6 矩阵 $\\times$ 矩阵", name: "复合变换与 AB≠BA",
      summary: "矩阵乘以矩阵是「变换的复合」——先做 $\\boldsymbol B$ 再做 $\\boldsymbol A$，等于做 $\\boldsymbol A\\boldsymbol B$。",
      formula: "", steps: [], conclusion: "",
    }} />);
    expect(container.querySelector(".math-case-header > span .katex")).not.toBeNull();
    expect(container.querySelector(".math-case-header p .katex")).not.toBeNull();
    expect(container.querySelector(".math-case-header")?.textContent ?? "").not.toContain("$");
  });
});
