import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Timeline } from "./Timeline";

describe("Timeline", () => {
  it("renders a log-style answer, plan status bar, and hover actions", () => {
    const onIntent = vi.fn();
    const session = {
      id: "s1",
      title: "Chat",
      mode: "Agent" as const,
      executionMode: "confirm" as const,
      model: "DeepSeek",
      turns: [{ id: "t1", userMessage: "画点", status: "completed", hovered: true, assistantText: "已完成", reasoningText: "分析图形", commandPlan: { summary: "画点", operations: [{ name: "point.upsert", summary: "x=1, y=2" }] }, drawState: "drawn" as const, events: [] }],
    };
    const expandedSession = {
      ...session,
      turns: [{
        ...session.turns[0],
        planExpanded: true,
        commandPlan: {
          summary: "画点",
          operations: [{ name: "point.upsert", summary: "x=1, y=2", status: "已执行", validation: "已通过" }],
        },
      }],
    };
    render(<Timeline session={expandedSession} onIntent={onIntent} onHover={() => undefined} onToggleDetails={() => undefined} />);
    expect(document.querySelector(".assistant-content")?.textContent).toContain("已完成");
    expect(screen.getByLabelText("绘图指令")).toBeInTheDocument();
    expect(screen.getByText("执行: 已执行")).toBeInTheDocument();
    expect(screen.getByText("校验: 已通过")).toBeInTheDocument();
    fireEvent.mouseEnter(screen.getByText("画点").closest(".turn-block")!);
    const actions = document.querySelector(".turn-actions");
    expect(actions).toHaveClass("visible");
    expect(document.querySelectorAll(".assistant-content")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "复制" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "撤销" }));
    expect(onIntent).toHaveBeenCalledWith(expect.objectContaining({ type: "undo_turn", turn_id: "t1" }));
  });

  const sessionWith = (assistantText: string, turns = 1) => ({
    id: "stream-session",
    title: "Chat",
    mode: "Agent" as const,
    executionMode: "confirm" as const,
    model: "DeepSeek",
    turns: Array.from({ length: turns }, (_, index) => ({
      id: `t${index}`,
      userMessage: `question ${index}`,
      status: "running",
      hovered: false,
      assistantText,
      reasoningText: "",
      events: [],
    })),
  });

  const props = { onIntent: vi.fn(), onHover: vi.fn(), onToggleDetails: vi.fn() };

  it("does not pull the reader down after they scroll up", () => {
    const scrollIntoView = vi.fn();
    Element.prototype.scrollIntoView = scrollIntoView;
    const { rerender } = render(<Timeline session={sessionWith("partial")} {...props} />);
    const timeline = screen.getByLabelText("对话时间线");
    Object.defineProperties(timeline, {
      scrollHeight: { configurable: true, value: 1000 },
      scrollTop: { configurable: true, value: 300 },
      clientHeight: { configurable: true, value: 400 },
    });
    fireEvent.scroll(timeline);
    scrollIntoView.mockClear();
    rerender(<Timeline session={sessionWith("partial more")} {...props} />);
    expect(scrollIntoView).not.toHaveBeenCalled();
  });

  it("keeps following while pinned and resets for a new user turn", () => {
    const scrollIntoView = vi.fn();
    Element.prototype.scrollIntoView = scrollIntoView;
    const { rerender } = render(<Timeline session={sessionWith("partial")} {...props} />);
    const timeline = screen.getByLabelText("对话时间线");
    Object.defineProperties(timeline, {
      scrollHeight: { configurable: true, value: 1000 },
      scrollTop: { configurable: true, value: 580 },
      clientHeight: { configurable: true, value: 400 },
    });
    fireEvent.scroll(timeline);
    scrollIntoView.mockClear();
    rerender(<Timeline session={sessionWith("next token")} {...props} />);
    expect(scrollIntoView).toHaveBeenCalledWith({ block: "nearest" });
    scrollIntoView.mockClear();
    Object.defineProperty(timeline, "scrollTop", { configurable: true, value: 100 });
    fireEvent.scroll(timeline);
    rerender(<Timeline session={sessionWith("new turn", 2)} {...props} />);
    expect(scrollIntoView).toHaveBeenCalledWith({ block: "nearest" });
  });
});
