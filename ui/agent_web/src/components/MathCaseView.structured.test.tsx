import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MathCaseView } from "./MathCaseView";

describe("MathCaseView structured artifact", () => {
  it("renders claim evidence and keeps storyboard navigation local", async () => {
    render(<MathCaseView caseData={{ id: "case-2", category: "投影", name: "投影", formula: "p", steps: ["推导"], conclusion: "结论", definition: "定义", claims: [{ id: "claim.p", statement: "p 是投影", formula: "v=p+r", formulaSymbols: ["p"], entityRefs: ["p"], relationRefs: ["projects"] }], symbolPalette: { p: "#2A9D8F" }, storyboard: [{ id: "stage.1", title: "输入", caption: "给出 v", layout: "sequence", visibleRefs: ["v"], visibleAliases: ["sem__v"], anchor: [0, 0] }, { id: "stage.2", title: "投影", caption: "得到 p", layout: "sequence", visibleRefs: ["p"], visibleAliases: ["sem__p"], anchor: [0, 1] }] }} />);
    expect(screen.getByRole("heading", { name: "定义", level: 2 })).toBeInTheDocument();
    expect(screen.getByText("claim.p")).toBeInTheDocument();
    expect(screen.getByText("输入")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "下一阶段" }));
    expect(screen.getByRole("heading", { name: "投影", level: 3 })).toBeInTheDocument();
  });
});
