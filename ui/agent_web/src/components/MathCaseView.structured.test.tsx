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
