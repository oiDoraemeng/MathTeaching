import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MathCaseView } from "./MathCaseView";

describe("MathCaseView", () => {
  it("renders semantic formula and conclusion cards with spaced steps", () => {
    render(<MathCaseView caseData={{ id: "case-1", category: "向量", name: "向量加法", formula: "a+b", steps: ["第一步"], conclusion: "结论" }} />);
    expect(screen.getByRole("heading", { name: "向量加法" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "结论", level: 2 })).toBeInTheDocument();
  });
});
