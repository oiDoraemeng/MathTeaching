import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MathCaseView } from "./MathCaseView";

describe("MathCaseView chapters 4-8 payload", () => {
  it("renders semantic source, formula, reading guide and analogy boundary", () => {
    render(<MathCaseView caseData={{
      id: "ch08.principal-axis",
      topicId: "ch08.principal-axis",
      category: "二次型",
      name: "主轴定理",
      formula: "Q^TAQ=diag(\\lambda_1,\\lambda_2)",
      steps: ["正交变换消去交叉项"],
      conclusion: "得到标准形",
      definition: "对称矩阵可以正交对角化。",
      geometricMeaning: "旋转坐标轴使等值线对齐。",
      readGuide: ["先看原坐标，再看主轴。"],
      analogyBoundary: "高维只保留代数对应。",
      storyboard: [{ id: "original", title: "原坐标", caption: "带交叉项", layout: "sequence", visibleRefs: [], visibleAliases: [], anchor: [0, 0] }],
    }} />);
    expect(screen.getByText("二次型")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "读图提示", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "类比边界", level: 2 })).toBeInTheDocument();
    expect(screen.getByText("旋转坐标轴使等值线对齐。")).toBeInTheDocument();
  });
});
