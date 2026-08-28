import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SessionTabs } from "./SessionTabs";

describe("SessionTabs", () => {
  it("switches sessions and closes a selected tab", () => {
    const onSelect = vi.fn();
    const onClose = vi.fn();
    const sessions = [
      { id: "a", title: "One", mode: "Agent" as const, executionMode: "confirm" as const, model: "DeepSeek", turns: [] },
      { id: "b", title: "Two", mode: "Ask" as const, executionMode: "confirm" as const, model: "Local", turns: [] },
    ];
    render(<SessionTabs sessions={sessions} activeSessionId="a" onSelect={onSelect} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "Two" }));
    fireEvent.click(screen.getByRole("button", { name: "关闭 One" }));
    expect(onSelect).toHaveBeenCalledWith("b");
    expect(onClose).toHaveBeenCalledWith("a");
  });

  it("does not render closed or hidden sessions as live tabs", () => {
    render(<SessionTabs
      sessions={[
        { id: "closed", title: "Closed", mode: "Agent", executionMode: "continuous", model: "DeepSeek", turns: [], closed: true },
        { id: "hidden", title: "Hidden", mode: "Agent", executionMode: "continuous", model: "DeepSeek", turns: [], hidden: true },
        { id: "open", title: "Open", mode: "Agent", executionMode: "continuous", model: "DeepSeek", turns: [] },
      ]}
      activeSessionId="open"
      onSelect={vi.fn()}
      onClose={vi.fn()}
    />);
    expect(screen.getByText("Open")).toBeInTheDocument();
    expect(screen.queryByText("Closed")).not.toBeInTheDocument();
    expect(screen.queryByText("Hidden")).not.toBeInTheDocument();
  });

  it("renders case tabs alongside sessions and closes a case tab", () => {
    const onSelectCase = vi.fn();
    const onClose = vi.fn();
    render(<SessionTabs
      sessions={[{ id: "open", title: "Open", mode: "Agent", executionMode: "continuous", model: "DeepSeek", turns: [] }]}
      cases={[{ id: "vector-addition", category: "向量", name: "向量加法", formula: "a+b", steps: ["step"], conclusion: "sum" }]}
      activeSessionId="open"
      activeTab="case:vector-addition"
      onSelect={vi.fn()}
      onSelectCase={onSelectCase}
      onClose={onClose}
    />);
    fireEvent.click(screen.getByRole("button", { name: "向量加法" }));
    fireEvent.click(screen.getByRole("button", { name: /关闭 向量加法/ }));
    expect(onSelectCase).toHaveBeenCalledWith("vector-addition");
    expect(onClose).toHaveBeenCalledWith("case:vector-addition");
  });
});
