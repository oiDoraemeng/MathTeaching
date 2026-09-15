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

  it("uses declared cases for another subsection without duplicating storyboard controls", () => {
    const onSelectStage = vi.fn();
    const onSetCasePaneCount = vi.fn();
    const { container } = render(
      <MathCaseView
        caseData={{
          id: "ch01.vector.magnitude",
          category: "向量",
          name: "向量的几何量：方向、长度与零向量",
          formula: "\\lvert\\boldsymbol v\\rvert=\\sqrt{x^2+y^2}",
          steps: [],
          conclusion: "",
          definition: "向量从原点出发。",
          geometricMeaning: "箭头长度是模。",
          workedExamples: [
            { id: "example.nonzero", title: "案例一：非零向量的长度", calculation: ["$$\\boldsymbol v=(3,4)$$", "$$\\lvert\\boldsymbol v\\rvert=5$$"], result: 25, checks: [{ name: "result", expected: 25 }] },
            { id: "example.zero", title: "案例二：零向量", calculation: ["$$\\boldsymbol 0=(0,0)$$", "$$\\lvert\\boldsymbol 0\\rvert=0$$"], result: 0, checks: [{ name: "result", expected: 0 }] },
          ],
          storyboard: [
            { id: "stage.nonzero", title: "案例一", caption: "长度为 5。", layout: "overlay", visibleRefs: [], visibleAliases: [], anchor: [0, 0] },
            { id: "stage.zero", title: "案例二", caption: "长度为 0。", layout: "overlay", visibleRefs: [], visibleAliases: [], anchor: [0, 1] },
          ],
          caseLayout: {
            defaultPaneCount: 1,
            cases: [
              { id: "case.nonzero", topicId: "ch01.vector.magnitude", exampleRef: "example.nonzero", claimRefs: [], stageRefs: ["stage.nonzero"], purpose: "案例一：非零向量的长度" },
              { id: "case.zero", topicId: "ch01.vector.magnitude", exampleRef: "example.zero", claimRefs: [], stageRefs: ["stage.zero"], purpose: "案例二：零向量" },
            ],
          },
        }}
        onSelectStage={onSelectStage}
        onSetCasePaneCount={onSetCasePaneCount}
      />,
    );

    expect(screen.getByRole("heading", { name: "案例", level: 2 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "案例一：非零向量的长度", level: 3 })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "案例二：零向量", level: 3 })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "几何图形例子" })).not.toBeInTheDocument();
    expect(container.querySelector(".math-case-structured .katex-html .sqrt svg path")).toBeTruthy();
    expect(screen.queryByText("结果：25")).not.toBeInTheDocument();
    expect(screen.queryByText("校验 result: 25")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "案例二：零向量" }));
    expect(onSelectStage).toHaveBeenCalledWith("stage.zero");
    fireEvent.click(screen.getByRole("button", { name: "全部显示" }));
    expect(onSetCasePaneCount).toHaveBeenCalledWith(2);
  });

  it("renders 1.2.2 vector subtraction as definition, geometry below it and one math flow", () => {
    const onSetCasePaneCount = vi.fn();
    const { container } = render(
      <MathCaseView
        caseData={{
          id: "ch01.ops.subtraction",
          category: "向量",
          name: "向量减法",
          formula: "\\boldsymbol a-\\boldsymbol b=(x_1-x_2,\\,y_1-y_2)",
          steps: [],
          conclusion: "",
          definition:
            "设二维向量 $\\boldsymbol a=(x_1,y_1)$、$\\boldsymbol b=(x_2,y_2)$。\n\n"
            + "$\\boldsymbol a-\\boldsymbol b$ 定义为 $\\boldsymbol a$ 与 $\\boldsymbol b$ 的负向量之和：\n\n"
            + "$$\\boldsymbol a-\\boldsymbol b=\\boldsymbol a+(-\\boldsymbol b)=(x_1-x_2,\\,y_1-y_2).$$",
          geometricMeaning:
            "从 $\\boldsymbol b$ 的终点指向 $\\boldsymbol a$ 的终点的箭头，恰好等于 $\\boldsymbol a-\\boldsymbol b$。"
            + "这是因为 $\\boldsymbol b+(\\boldsymbol a-\\boldsymbol b)=\\boldsymbol a$。",
          workedExamples: [
            {
              id: "example.subtraction.operands",
              title: "第一步：向量 a 与 b",
              calculation: ["$\\boldsymbol a=(3,1)$，$\\boldsymbol b=(1,2)$，$-\\boldsymbol b=(-1,-2)$。"],
              result: [2, -1],
              checks: [{ name: "sum", expected: [2, -1] }],
            },
            {
              id: "example.subtraction.difference",
              title: "第二步：a-b 的终点关系",
              calculation: ["$$\\boldsymbol a-\\boldsymbol b=\\boldsymbol a+(-\\boldsymbol b)=(3,1)+(-1,-2)=(2,-1)$$"],
              result: [2, -1],
              checks: [{ name: "sum", expected: [2, -1] }],
            },
          ],
          storyboard: [
            {
              id: "stage.subtraction.operands",
              title: "第一步：向量 a 与 b",
              caption: "$\\boldsymbol a=(3,1)$、$\\boldsymbol b=(1,2)$ 从原点出发。",
              layout: "overlay",
              visibleRefs: ["a", "b"],
              visibleAliases: ["sem__a", "sem__b"],
              anchor: [0, 0],
            },
            {
              id: "stage.subtraction.difference",
              title: "第二步：a-b 的终点关系",
              caption: "从 $\\boldsymbol b$ 的终点指向 $\\boldsymbol a$ 的终点的箭头等于 $\\boldsymbol a-\\boldsymbol b$。",
              layout: "overlay",
              visibleRefs: ["a", "b"],
              visibleAliases: ["sem__a", "sem__b", "sem__rel.subtraction.endpoints"],
              anchor: [0, 1],
            },
          ],
          caseLayout: {
            defaultPaneCount: 2,
            cases: [
              { id: "case.subtraction.operands", topicId: "ch01.ops.subtraction", exampleRef: "example.subtraction.operands", claimRefs: [], stageRefs: ["stage.subtraction.operands"], purpose: "第一步：向量 a、b" },
              { id: "case.subtraction.difference", topicId: "ch01.ops.subtraction", exampleRef: "example.subtraction.difference", claimRefs: [], stageRefs: ["stage.subtraction.difference"], purpose: "第二步：a-b 的终点关系" },
            ],
          },
        }}
        onSetCasePaneCount={onSetCasePaneCount}
      />,
    );

    // 讲义 1.2.2 的定义自带公式：显示为「定义」，不另立「公式」分节，也不重复公式。
    expect(screen.getByRole("heading", { name: "定义", level: 2 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "定义与公式", level: 2 })).not.toBeInTheDocument();
    expect(container.querySelector(".math-case-formula")).toBeNull();
    // 几何解释紧跟定义，并排在“数学案例”之前。
    const headings = Array.from(container.querySelectorAll(".math-case-structured h2")).map((item) => item.textContent);
    expect(headings.slice(0, 2)).toEqual(["定义", "几何意义"]);
    expect(headings).toContain("数学案例");
    expect(screen.queryByRole("region", { name: "几何图形例子" })).not.toBeInTheDocument();
    // 首屏默认“全部显示”，两个步骤并排。
    expect(screen.getByRole("button", { name: "全部显示" })).toHaveAttribute("aria-pressed", "true");
    expect(onSetCasePaneCount).toHaveBeenCalledWith(2);
    expect(screen.getByRole("button", { name: "第一步：向量 a、b" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "第二步：a-b 的终点关系" })).toBeInTheDocument();
    // 结果与校验是审计数据，不在讲义视图里重复。
    expect(screen.queryByText("结果：[2,-1]")).not.toBeInTheDocument();
  });

  it("renders 1.2.3 scalar multiplication with the lecture table and one math flow", () => {
    const onSetCasePaneCount = vi.fn();
    const { container } = render(
      <MathCaseView
        caseData={{
          id: "ch01.ops.scalar",
          category: "向量",
          name: "向量数乘",
          formula: "k\\boldsymbol a=(kx,ky)",
          steps: [],
          conclusion: "",
          definition:
            "设 $k$ 是一个实数（标量），$\\boldsymbol a=(x,y)$ 是一个向量，"
            + "则 $k$ 与 $\\boldsymbol a$ 的数乘为\n\n$$k\\cdot\\boldsymbol a=(kx,ky).$$",
          geometricMeaning:
            "数乘就是缩放——把箭头的长度变为原来的 $\\lvert k\\rvert$ 倍；若 $k<0$，则同时反转方向。\n\n"
            + "| $k$ 的值 | 几何效果 |\n| --- | --- |\n| $k>1$ | 拉伸（伸长） |\n"
            + "| $0<k<1$ | 压缩（缩短） |\n| $k=-1$ | 反向，长度不变 |\n| $k<0$ | 反向且缩放 |\n\n"
            + "定义 1.8（共线）：如果存在实数 $k$ 使得 $\\boldsymbol b=k\\boldsymbol a$，"
            + "则称 $\\boldsymbol a$ 与 $\\boldsymbol b$ 共线（方向相同或相反）。",
          workedExamples: [
            {
              id: "example.scalar.vector",
              title: "第一步：向量 a",
              calculation: ["$$\\boldsymbol a=(2,1)$$"],
              result: [2, 1],
              checks: [{ name: "scalar_multiple", expected: [2, 1] }],
            },
            {
              id: "example.scalar.stretch",
              title: "第二步：2a",
              calculation: ["$$2\\boldsymbol a=2\\cdot(2,1)=(4,2)$$"],
              result: [4, 2],
              checks: [{ name: "scalar_multiple", expected: [4, 2] }],
            },
          ],
          storyboard: [
            {
              id: "stage.scalar.vector",
              title: "第一步：向量 a",
              caption: "$\\boldsymbol a=(2,1)$ 从原点出发，终点记为 A。",
              layout: "overlay",
              visibleRefs: ["a"],
              visibleAliases: ["sem__a"],
              anchor: [0, 0],
            },
            {
              id: "stage.scalar.multiple",
              title: "第二步：2a",
              caption: "把 $\\boldsymbol a=(2,1)$ 沿原来的方向拉伸 2 倍得到 $2\\boldsymbol a=(4,2)$，终点记为 B，两者共线。",
              layout: "overlay",
              visibleRefs: ["a", "two_a"],
              visibleAliases: ["sem__a", "sem__two_a"],
              anchor: [0, 1],
            },
          ],
          caseLayout: {
            defaultPaneCount: 2,
            cases: [
              { id: "case.scalar.vector", topicId: "ch01.ops.scalar", exampleRef: "example.scalar.vector", claimRefs: [], stageRefs: ["stage.scalar.vector"], purpose: "第一步：向量 a" },
              { id: "case.scalar.stretch", topicId: "ch01.ops.scalar", exampleRef: "example.scalar.stretch", claimRefs: [], stageRefs: ["stage.scalar.multiple"], purpose: "第二步：2a" },
            ],
          },
        }}
        onSetCasePaneCount={onSetCasePaneCount}
      />,
    );

    // 定义 1.7 自带公式：标题写「定义」，几何意义紧随其后。
    expect(screen.getByRole("heading", { name: "定义", level: 2 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "定义与公式", level: 2 })).not.toBeInTheDocument();
    expect(container.querySelector(".math-case-formula")).toBeNull();
    const headings = Array.from(container.querySelectorAll(".math-case-structured h2")).map((item) => item.textContent);
    expect(headings.slice(0, 2)).toEqual(["定义", "几何意义"]);
    expect(headings).toContain("数学案例");
    // 讲义 1.2.3 的 k 取值表保持为表格，定义 1.8（共线）保留讲义编号与位置。
    const geometrySection = screen
      .getByRole("heading", { name: "几何意义", level: 2 })
      .closest("section");
    expect(geometrySection?.querySelector("table")).toBeTruthy();
    expect(geometrySection?.textContent).toContain("反向，长度不变");
    expect(geometrySection?.textContent).toContain("定义 1.8（共线）");
    // 首屏默认“全部显示”，两个步骤并排。
    expect(screen.getByRole("button", { name: "全部显示" })).toHaveAttribute("aria-pressed", "true");
    expect(onSetCasePaneCount).toHaveBeenCalledWith(2);
    expect(screen.getByRole("button", { name: "第一步：向量 a" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "第二步：2a" })).toBeInTheDocument();
  });

  it("renders 1.2.4 linear combinations as three steps: a, b then 2a, -b then the result", () => {
    const onSetCasePaneCount = vi.fn();
    const { container } = render(
      <MathCaseView
        caseData={{
          id: "ch01.ops.linear-combination",
          category: "向量",
          name: "线性组合",
          formula: "\\alpha_1\\boldsymbol v_1+\\cdots+\\alpha_n\\boldsymbol v_n",
          steps: [],
          conclusion: "",
          definition:
            "给定向量 $\\boldsymbol v_1,\\boldsymbol v_2,\\ldots,\\boldsymbol v_n$ 和标量 "
            + "$\\alpha_1,\\alpha_2,\\ldots,\\alpha_n$，称\n\n"
            + "$$\\alpha_1\\boldsymbol v_1+\\alpha_2\\boldsymbol v_2+\\cdots+\\alpha_n\\boldsymbol v_n$$\n\n"
            + "为 $\\boldsymbol v_1,\\ldots,\\boldsymbol v_n$ 的一个线性组合；$\\alpha_i$ 称为系数。",
          geometricMeaning: "向量的加法与数乘组合在一起，就是线性组合：先按系数缩放各向量，再把所得向量相加。",
          workedExamples: [
            { id: "example.linear-combination.vectors", title: "第一步：向量 a 与 b", calculation: ["$$\\boldsymbol a=(3,1),\\qquad \\boldsymbol b=(1,2)$$"], result: [3, 1], checks: [{ name: "scalar_multiple", expected: [3, 1] }] },
            { id: "example.linear-combination.terms", title: "第二步：2a 与 -b", calculation: ["$$2\\boldsymbol a=(6,2),\\qquad -\\boldsymbol b=(-1,-2)$$"], result: [5, 0], checks: [{ name: "sum", expected: [5, 0] }] },
            { id: "example.linear-combination.result", title: "第三步：线性组合", calculation: ["$$2\\boldsymbol a-\\boldsymbol b=(6,2)+(-1,-2)=(5,0)$$"], result: [5, 0], checks: [{ name: "sum", expected: [5, 0] }] },
          ],
          storyboard: [
            { id: "stage.linear-combination.vectors", title: "第一步：向量 a 与 b", caption: "$\\boldsymbol a=(3,1)$、$\\boldsymbol b=(1,2)$ 从原点出发。", layout: "overlay", visibleRefs: ["a", "b"], visibleAliases: ["sem__a", "sem__b"], anchor: [0, 0] },
            { id: "stage.linear-combination.terms", title: "第二步：2a 与 -b", caption: "系数 2 与 −1 作用在 a、b 上。", layout: "overlay", visibleRefs: ["two_a", "neg_b"], visibleAliases: ["sem__two_a", "sem__neg_b"], anchor: [0, 1] },
            { id: "stage.linear-combination.result", title: "第三步：线性组合 2a-b", caption: "把各项相加：$2\\boldsymbol a+(-\\boldsymbol b)=(5,0)$。", layout: "overlay", visibleRefs: ["two_a", "neg_b", "combination"], visibleAliases: ["sem__two_a", "sem__neg_b", "sem__combination"], anchor: [0, 2] },
          ],
          caseLayout: {
            defaultPaneCount: 3,
            cases: [
              { id: "case.linear-combination.vectors", topicId: "ch01.ops.linear-combination", exampleRef: "example.linear-combination.vectors", claimRefs: [], stageRefs: ["stage.linear-combination.vectors"], purpose: "第一步：向量 a、b" },
              { id: "case.linear-combination.terms", topicId: "ch01.ops.linear-combination", exampleRef: "example.linear-combination.terms", claimRefs: [], stageRefs: ["stage.linear-combination.terms"], purpose: "第二步：2a 与 -b" },
              { id: "case.linear-combination.result", topicId: "ch01.ops.linear-combination", exampleRef: "example.linear-combination.result", claimRefs: [], stageRefs: ["stage.linear-combination.result"], purpose: "第三步：线性组合 2a-b" },
            ],
          },
        }}
        onSetCasePaneCount={onSetCasePaneCount}
      />,
    );

    // 定义 1.9 自带公式：标题写「定义」，几何意义紧随其后。
    expect(screen.getByRole("heading", { name: "定义", level: 2 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "定义与公式", level: 2 })).not.toBeInTheDocument();
    const headings = Array.from(container.querySelectorAll(".math-case-structured h2")).map((item) => item.textContent);
    expect(headings.slice(0, 2)).toEqual(["定义", "几何意义"]);
    expect(headings).toContain("数学案例");
    // 三步并排：三个步骤按钮 + 默认“全部显示”，并向宿主请求 3 个窗格。
    expect(screen.getByRole("button", { name: "第一步：向量 a、b" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "第二步：2a 与 -b" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "第三步：线性组合 2a-b" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "全部显示" })).toHaveAttribute("aria-pressed", "true");
    expect(onSetCasePaneCount).toHaveBeenCalledWith(3);
    expect(screen.queryByRole("region", { name: "几何图形例子" })).not.toBeInTheDocument();
  });

  it("renders 2.5.1 as the lecture definition plus one two-step math case", () => {
    const onSetCasePaneCount = vi.fn();
    const { container } = render(
      <MathCaseView
        caseData={{
          id: "ch02.matrix.row-column",
          category: "2.5 矩阵 × 向量（核心节）",
          name: "矩阵乘向量的行视角与列视角",
          formula: "",
          steps: [],
          conclusion: "",
          definition:
            "设 $\\boldsymbol A$ 是 $m \\times n$ 矩阵，$\\boldsymbol x$ 是 $n$ 维列向量。\n\n"
            + "算法一（行视角 — 内积法）：$\\boldsymbol A\\boldsymbol x$ 的第 $i$ 个分量 $=$ $\\boldsymbol A$ 的第 $i$ 行与 $\\boldsymbol x$ 的内积。\n\n"
            + "$$\\boldsymbol A\\boldsymbol x=x_{1}\\cdot(\\boldsymbol A\\text{ 的第 }1\\text{ 列})+\\cdots$$",
          sections: [
            { id: "definition", title: "定义" },
            { id: "worked_examples", title: "数学案例" },
          ],
          workedExamples: [
            {
              id: "example.ch02.matrix.row-column.1",
              title: "第一步：行视角（内积法）",
              calculation: ["$$\\boldsymbol A\\boldsymbol x=(8,9)$$"],
              result: [8, 9],
              checks: [{ name: "transformed", expected: [8, 9] }],
            },
            {
              id: "example.ch02.matrix.row-column.2",
              title: "第二步：列视角（线性组合法）",
              calculation: ["$$\\boldsymbol A\\boldsymbol x=2\\times(1,3)+3\\times(2,1)=(8,9)$$"],
              result: [8, 9],
              checks: [{ name: "transformed", expected: [8, 9] }],
            },
          ],
          storyboard: [
            { id: "stage.case.ch02.matrix.row-column.1", title: "第一步：行视角（内积法）", caption: "", layout: "overlay", visibleRefs: [], visibleAliases: [], anchor: [0, 0] },
            { id: "stage.case.ch02.matrix.row-column.2", title: "第二步：列视角（线性组合法）", caption: "", layout: "overlay", visibleRefs: [], visibleAliases: [], anchor: [0, 1] },
          ],
          caseLayout: {
            defaultPaneCount: 2,
            cases: [
              { id: "case.ch02.matrix.row-column.1", topicId: "ch02.matrix.row-column", exampleRef: "example.ch02.matrix.row-column.1", claimRefs: [], stageRefs: ["stage.case.ch02.matrix.row-column.1"], purpose: "第一步：行视角（内积法）" },
              { id: "case.ch02.matrix.row-column.2", topicId: "ch02.matrix.row-column", exampleRef: "example.ch02.matrix.row-column.2", claimRefs: [], stageRefs: ["stage.case.ch02.matrix.row-column.2"], purpose: "第二步：列视角（线性组合法）" },
            ],
          },
        }}
        onSetCasePaneCount={onSetCasePaneCount}
      />,
    );

    // 讲义 2.5.1 把两种算法写在定义块内：标题写「定义」，不另立「公式」分节。
    expect(screen.getByRole("heading", { name: "定义", level: 2 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "定义与公式", level: 2 })).not.toBeInTheDocument();
    expect(container.querySelector(".math-case-formula")).toBeNull();
    const headings = Array.from(container.querySelectorAll(".math-case-structured h2")).map((item) => item.textContent);
    expect(headings).toEqual(["定义", "数学案例"]);
    // 首屏默认“全部显示”，两步并排。
    expect(screen.getByRole("button", { name: "全部显示" })).toHaveAttribute("aria-pressed", "true");
    expect(onSetCasePaneCount).toHaveBeenCalledWith(2);
    expect(screen.getByRole("button", { name: "第一步：行视角（内积法）" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "第二步：列视角（线性组合法）" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "几何图形例子" })).not.toBeInTheDocument();
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

  it("renders the shared source identity and stale-source diagnostic", () => {
    render(
      <MathCaseView
        caseData={{
          id: "ch08.principal-axis",
          topicId: "ch08.principal-axis",
          category: "二次型",
          name: "主轴定理",
          formula: "x^TAx",
          steps: [],
          conclusion: "结论",
          source: {
            sourcePath: ["线性代数讲义.md"],
            headingPath: ["第8章 二次型与主轴定理", "8.3 主轴定理"],
            sourceHash: "sha256:published",
          },
          sourceDiagnostic: {
            code: "stale_source",
            publishedHash: "sha256:published",
            currentHash: "sha256:current",
          },
        }}
      />,
    );

    expect(screen.getByRole("region", { name: "讲义来源" })).toHaveTextContent("8.3 主轴定理");
    expect(screen.getByRole("status")).toHaveTextContent("stale_source");
  });
});
