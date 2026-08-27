import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PlanCard } from "./PlanCard";

describe("PlanCard", () => {
  it("renders operations from the runtime plan envelope", () => {
    render(
      <PlanCard
        sessionId="s1"
        onIntent={vi.fn()}
        event={{
          type: "plan_ready",
          session_id: "s1",
          turn_id: "t1",
          payload: {
            plan: {
              summary: "向量加法",
              operations: [{ op: "teach.vector_addition" }],
            },
          },
        }}
      />,
    );

    expect(screen.getByText("向量加法")).toBeInTheDocument();
    expect(screen.getByText("1 个操作")).toBeInTheDocument();
  });
});
