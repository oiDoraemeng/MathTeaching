import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Timeline } from "./Timeline";

describe("Timeline", () => {
  it("shows a completed turn action only while hovered", () => {
    const onIntent = vi.fn();
    const session = {
      id: "s1",
      title: "Chat",
      mode: "Agent" as const,
      executionMode: "confirm" as const,
      model: "DeepSeek",
      turns: [{ id: "t1", userMessage: "画点", status: "completed", hovered: true, events: [{ type: "execution", session_id: "s1", turn_id: "t1", payload: { text: "完成" } }] }],
    };
    render(<Timeline session={session} onIntent={onIntent} onHover={() => undefined} onToggleDetails={() => undefined} />);
    expect(screen.getByText("完成")).toBeInTheDocument();
    fireEvent.mouseEnter(screen.getByText("画点").closest(".turn-block")!);
    expect(screen.getByRole("button", { name: "恢复场景" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "恢复场景" }));
    expect(onIntent).toHaveBeenCalledWith(expect.objectContaining({ type: "restore_turn", turn_id: "t1" }));
  });
});
