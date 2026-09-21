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

  it("4.1.3 按讲义顺序排版：定义（不拼「定义与公式」）→ 几何直观 → 子空间证明", () => {
    render(<MathCaseView caseData={{
      id: "ch04.subspace.col-null",
      topicId: "ch04.subspace.col-null",
      category: "线性空间与子空间",
      name: "4.1.3 两大核心子空间：列空间与零空间",
      formula: "",
      steps: ["Col(A) 是子空间的证明: ① $0 = A \\cdot 0 \\in \\operatorname{Col}(A)$；"],
      conclusion: "",
      definition: "定义 4.3（列空间） $\\operatorname{Col}(A) = \\{Ax \\mid x \\in R^{n}\\}$。",
      geometricMeaning: "几何直观：\n$A = \\begin{pmatrix}1 & 0 \\\\ 0 & 0\\end{pmatrix}$（投影到 x 轴）",
      workedExamples: [
        { id: "example.ch04.subspace.col-null.column-space", title: "案例一", calculation: ["$$\\boldsymbol A\\boldsymbol x=(2,-1,0)^{\\mathsf T}$$"] },
      ],
      sections: [
        { id: "definition", title: "定义" },
        { id: "geometric_meaning", title: "几何直观" },
        { id: "derivation", title: "列空间和零空间为子空间的证明" },
        { id: "worked_examples", title: "数学案例" },
      ],
      caseLayout: {
        defaultPaneCount: 2,
        cases: [
          { id: "case.ch04.subspace.col-null.column-space", topicId: "ch04.subspace.col-null", exampleRef: "example.ch04.subspace.col-null.column-space", claimRefs: [], stageRefs: ["stage.ch04.subspace.col-null.column_space"], purpose: "① 列空间" },
          { id: "case.ch04.subspace.col-null.null-space", topicId: "ch04.subspace.col-null", exampleRef: "example.ch04.subspace.col-null.null-space", claimRefs: [], stageRefs: ["stage.ch04.subspace.col-null.null_space"], purpose: "② 零空间" },
        ],
      },
    }} />);
    expect(screen.getByRole("heading", { name: "定义", level: 2 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "定义与公式", level: 2 })).not.toBeInTheDocument();
    const headings = screen.getAllByRole("heading", { level: 2 }).map((node) => node.textContent ?? "");
    expect(headings.indexOf("几何直观")).toBeGreaterThan(headings.indexOf("定义"));
    expect(headings.indexOf("几何直观")).toBeLessThan(headings.indexOf("列空间和零空间为子空间的证明"));
    expect(screen.getByRole("button", { name: "全部显示" })).toBeInTheDocument();
  });

  it("4.2 uses the definition heading and exposes all four confirmed cases", () => {
    const cases = [
      "① 一根向量：张成直线",
      "② 两根不共线向量：张成平面",
      "③ 加入平面外方向：张成整个三维空间",
      "④ 加入冗余方向：仍只张成原平面",
    ];
    render(<MathCaseView caseData={{
      id: "ch04.dependence.redundancy",
      topicId: "ch04.dependence.redundancy",
      category: "线性空间与子空间",
      name: "4.2 线性组合、线性相关与线性无关",
      formula: "",
      steps: [],
      conclusion: "",
      definition: "**（生成集）** $\\operatorname{Span}\\{\\boldsymbol u\\}$ 是所有线性组合。",
      workedExamples: cases.map((purpose, index) => ({
        id: `example-${index + 1}`,
        title: `案例${index + 1}`,
        calculation: [purpose],
      })),
      sections: [
        { id: "definition", title: "定义" },
        { id: "worked_examples", title: "数学案例" },
      ],
      caseLayout: {
        defaultPaneCount: 4,
        cases: cases.map((purpose, index) => ({
          id: `case-${index + 1}`,
          topicId: "ch04.dependence.redundancy",
          exampleRef: `example-${index + 1}`,
          claimRefs: [],
          stageRefs: [`stage-${index + 1}`],
          purpose,
        })),
      },
    }} />);

    expect(screen.getByRole("heading", { name: "定义", level: 2 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "定义与公式", level: 2 })).not.toBeInTheDocument();
    cases.forEach((name) => expect(screen.getByRole("button", { name })).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "全部显示" })).toHaveAttribute("aria-pressed", "true");
  });

  it("4.4 merges the lecture into Definition and exposes both cases by default", () => {
    const { container } = render(<MathCaseView caseData={{
      id: "ch04.linear-map.definition",
      topicId: "ch04.linear-map.definition",
      category: "线性变换",
      name: "线性变换的定义",
      formula: "",
      steps: [],
      conclusion: "",
      definition: "定义 4.11（线性变换）\n\n| 是 | 公式 | 不是 | 公式 |\n| --- | --- | --- | --- |\n| 拉伸 | $T(x,y)=(ax,by)$ | 平移 | $T(x,y)=(x+1,y)$ |",
      workedExamples: [
        { id: "stretch", title: "拉伸（是）", calculation: ["$$T(\\boldsymbol u+\\boldsymbol v)=(2,1)$$"] },
        { id: "translation", title: "平移（不是）", calculation: ["$$T(\\boldsymbol u)+T(\\boldsymbol v)=(3,1)$$"] },
      ],
      sections: [
        { id: "definition", title: "定义" },
        { id: "worked_examples", title: "数学案例" },
      ],
      caseLayout: {
        defaultPaneCount: 2,
        cases: [
          { id: "stretch-case", topicId: "ch04.linear-map.definition", exampleRef: "stretch", claimRefs: [], stageRefs: ["stretch-stage"], purpose: "拉伸（是）" },
          { id: "translation-case", topicId: "ch04.linear-map.definition", exampleRef: "translation", claimRefs: [], stageRefs: ["translation-stage"], purpose: "平移（不是）" },
        ],
      },
    }} />);

    expect(screen.getByRole("heading", { name: "定义", level: 2 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "定义与公式", level: 2 })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "拉伸（是）" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "平移（不是）" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "全部显示" })).toHaveAttribute("aria-pressed", "true");
    expect(container.querySelector("table")).toBeInTheDocument();
    expect(container.querySelectorAll(".katex-html").length).toBeGreaterThan(0);
    const visibleMath = Array.from(container.querySelectorAll(".katex-html"))
      .map((node) => node.textContent ?? "")
      .join(" ");
    expect(visibleMath).not.toContain("\\boldsymbol");
    expect(visibleMath).not.toContain("\\n");
  });
});
