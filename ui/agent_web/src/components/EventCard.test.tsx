import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EventCard } from "./EventCard";

describe("EventCard", () => {
  it("collapses streamed reasoning when the formal answer starts", () => {
    const { container } = render(
      <EventCard
        event={{ type: "explanation", session_id: "s1", turn_id: "t1", payload: { reasoning: "step one", text: "answer" } }}
        sessionId="s1"
        onIntent={vi.fn()}
      />,
    );

    expect(container.querySelector(".reasoning-block")?.hasAttribute("open")).toBe(false);
  });

  it("renders capability lifecycle and conflict cards", () => {
    const { getByLabelText, getByText } = render(
      <EventCard event={{ type: "scene_conflict", session_id: "s1", payload: { message: "2D 与 3D 不能混用" } }} sessionId="s1" onIntent={vi.fn()} />,
    );

    expect(getByLabelText("场景冲突")).toBeInTheDocument();
    expect(getByText("2D 与 3D 不能混用")).toBeInTheDocument();
  });
});
