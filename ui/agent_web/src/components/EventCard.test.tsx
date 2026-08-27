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
});
