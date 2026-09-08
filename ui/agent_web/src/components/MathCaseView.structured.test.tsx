import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MathCaseView } from "./MathCaseView";

describe("MathCaseView structured artifact", () => {
  it("keeps the lecture-style structure and switches storyboard stages locally", () => {
    const onSelectStage = vi.fn();
    render(
      <MathCaseView
        caseData={{
          id: "case-2",
          category: "投影",
          name: "投影",
          formula: "p",
          steps: ["推导"],
          conclusion: "结论",
          definition: "定义",
          claims: [
            {
              id: "claim.p",
              statement: "p 是投影",
              formula: "v=p+r",
              formulaSymbols: ["p"],
              entityRefs: ["p"],
              relationRefs: ["projects"],
            },
          ],
          symbolPalette: { p: "#2A9D8F" },
          storyboard: [
            { id: "stage.1", title: "输入", caption: "给出 v", layout: "sequence", visibleRefs: ["v"], visibleAliases: ["sem__v"], anchor: [0, 0] },
            { id: "stage.2", title: "投影", caption: "得到 p", layout: "sequence", visibleRefs: ["p"], visibleAliases: ["sem__p"], anchor: [0, 1] },
          ],
        }}
        onSelectStage={onSelectStage}
      />,
    );

    expect(screen.getByRole("heading", { name: "定义与公式", level: 2 })).toBeInTheDocument();
    expect(screen.queryByText("claim.p")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "下一几何例子" }));
    expect(onSelectStage).toHaveBeenCalledWith("stage.2");
    expect(screen.getByRole("heading", { name: "投影", level: 3 })).toBeInTheDocument();
  });

  it("uses geometry meaning as named examples and keeps the formula inside the definition block", () => {
    const { container } = render(
      <MathCaseView
        caseData={{
          id: "case-add",
          category: "向量",
          name: "向量加法",
          formula: "a+b",
          steps: ["对应分量相加"],
          conclusion: "得到和向量",
          geometricMeaning: "把向量首尾相接。",
          analogyBoundary: "二维里可直接看箭头，类比到高维时只保留代数对应。",
          readGuide: ["先看两个向量的起点，再看两种合成图像。"],
          claims: [
            {
              id: "claim.ch01.ops.addition",
              statement: "按对应分量相加",
              formula: "a+b=(x_1+x_2,y_1+y_2)",
              entityRefs: ["a", "b"],
              relationRefs: ["rel.0.claim.ch01.ops.addition"],
            },
          ],
          storyboard: [
            { id: "stage.triangle", title: "三角形法则", caption: "把 b 平移到 a 的终点。", layout: "sequence", visibleRefs: ["a", "b"], visibleAliases: ["sem__a", "sem__triangle"], anchor: [0, 0] },
            { id: "stage.parallelogram", title: "平行四边形法则", caption: "以 a、b 为邻边作平行四边形。", layout: "sequence", visibleRefs: ["a", "b"], visibleAliases: ["sem__a", "sem__parallelogram"], anchor: [0, 1] },
          ],
        }}
      />,
    );

    const definitionSection = screen.getByRole("heading", { name: "定义与公式", level: 2 }).closest("section");
    expect(container.querySelector(".math-case-formula")).toBeNull();
    expect(definitionSection?.querySelector(".katex-display")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "几何意义", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "图形例子", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "类比边界", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "读图提示", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "三角形法则" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "平行四边形法则" })).toBeInTheDocument();
    expect(screen.queryByText("claim.ch01.ops.addition")).not.toBeInTheDocument();
    expect(screen.queryByText("rel.0.claim.ch01.ops.addition")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "平行四边形法则" }));
    expect(screen.getByText("以 a、b 为邻边作平行四边形。")).toBeInTheDocument();
  });

  it("uses one selector for one-to-one vector-addition cases and hides verification metadata", () => {
    const onSelectStage = vi.fn();
    const onSetCasePaneCount = vi.fn();
    const { container } = render(
      <MathCaseView
        caseData={{
          id: "ch01.ops.addition",
          category: "向量",
          name: "向量加法",
          formula: "a+b",
          steps: [],
          conclusion: "",
          definition: "设\n\n$$a=(1,2)$$",
          invariants: ["交换律：\n\n$$a+b=b+a$$"],
          geometricMeaning: "三角形法则。\n\n平行四边形法则。",
          workedExamples: [{ id: "components", title: "案例一：分量计算", calculation: ["$a=(3,1)$，$b=(1,2)$。", "$$a+b=(4,3)$$", "两种作图得到同一个和向量。"], result: [4, 3], checks: [{ name: "result", expected: [4, 3] }] }],
          storyboard: [
            { id: "stage.components", title: "案例一：分量计算", caption: "对应分量相加。", layout: "overlay", visibleRefs: [], visibleAliases: [], anchor: [0, 0] },
            { id: "stage.geometry", title: "案例二：几何作图", caption: "两种作图。", layout: "overlay", visibleRefs: [], visibleAliases: [], anchor: [0, 1] },
          ],
          caseLayout: {
            defaultPaneCount: 2,
            cases: [
              { id: "case.components", topicId: "ch01.ops.addition", exampleRef: "components", claimRefs: [], stageRefs: ["stage.components"], purpose: "案例一：分量计算" },
              { id: "case.geometry", topicId: "ch01.ops.addition", exampleRef: "geometry", claimRefs: [], stageRefs: ["stage.geometry"], purpose: "案例二：几何作图" },
            ],
          },
        }}
        onSelectStage={onSelectStage}
        onSetCasePaneCount={onSetCasePaneCount}
      />,
    );

    expect(screen.getByRole("heading", { name: "向量加法的基本性质", level: 2 })).toBeInTheDocument();
    expect(screen.queryByText("结果：[4,3]")).not.toBeInTheDocument();
    expect(screen.queryByText("校验 result: [4,3]")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "几何图形例子" })).not.toBeInTheDocument();
    expect(screen.queryByText("对应分量相加。")).not.toBeInTheDocument();
    expect(Array.from(container.querySelectorAll(".math-case-example-prose .markdown-content")).some((item) => item.textContent?.includes("两种作图得到同一个和向量。"))).toBe(true);
    expect(container.querySelector(".math-case-example-formula .katex-display")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "案例二：几何作图" }));
    expect(onSelectStage).toHaveBeenCalledWith("stage.geometry");
    fireEvent.click(screen.getByRole("button", { name: "全部显示" }));
    expect(onSetCasePaneCount).toHaveBeenCalledWith(2);
  });

  it("uses the lecture excerpt as a continuous note instead of section cards", () => {
    render(
      <MathCaseView
        caseData={{
          id: "case-lecture",
          category: "矩阵",
          name: "矩阵乘法",
          formula: "AB",
          steps: ["旧版回退步骤"],
          conclusion: "结论",
          sourceExcerpt: "## 定义与公式\n\n设 $A$ 与 $B$ 维度匹配。\n\n$$ABx=A(Bx)$$\n\n### 几何意义\n\n先做 B，再做 A。",
          storyboard: [],
        }}
      />,
    );

    expect(screen.getByRole("region", { name: "讲义正文" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "定义与公式", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "几何意义", level: 3 })).toBeInTheDocument();
    expect(screen.queryByText("旧版回退步骤")).not.toBeInTheDocument();
  });
});
