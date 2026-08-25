import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SessionTabs } from "./SessionTabs";

const sessions = [
  { id: "a", title: "One", mode: "Agent" as const, executionMode: "confirm" as const, model: "DeepSeek", turns: [] },
  { id: "b", title: "Two", mode: "Ask" as const, executionMode: "confirm" as const, model: "Local", turns: [] },
];

describe("SessionTabs", () => {
  it("switches sessions and closes a selected tab", () => {
    const onSelect = vi.fn();
    const onClose = vi.fn();
    render(<SessionTabs sessions={sessions} activeSessionId="a" onSelect={onSelect} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "Two" }));
    fireEvent.click(screen.getByRole("button", { name: "关闭 One" }));
    expect(onSelect).toHaveBeenCalledWith("b");
    expect(onClose).toHaveBeenCalledWith("a");
  });
});
