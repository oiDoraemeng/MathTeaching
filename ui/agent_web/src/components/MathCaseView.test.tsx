import { fireEvent, render, screen } from "@testing-library/react";
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
});
