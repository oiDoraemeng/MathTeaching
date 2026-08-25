import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Composer } from "./Composer";
import type { ContextUsage } from "../types";

const contextUsage: ContextUsage = { usedTokens: 25, maxTokens: 100, percentage: 25 };
describe("Composer", () => {
  it("sends on Enter and preserves newline with Shift+Enter", () => {
    const onIntent = vi.fn();
    render(<Composer sessionId="s1" mode="Agent" executionMode="confirm" model="DeepSeek" contextUsage={contextUsage} onIntent={onIntent} />);
    const input = screen.getByPlaceholderText('提问或输入 "/"快捷命令');
    fireEvent.change(input, { target: { value: "画一个点" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onIntent).toHaveBeenCalledWith(expect.objectContaining({ type: "send_message", session_id: "s1" }));
    fireEvent.change(input, { target: { value: "第一行" } });
    fireEvent.keyDown(input, { key: "Enter", shiftKey: true });
    expect(input).toHaveValue("第一行");
  });
  it("changes mode and sends stop while busy", () => {
    const onIntent = vi.fn();
    render(<Composer sessionId="s1" mode="Agent" executionMode="confirm" model="DeepSeek" contextUsage={contextUsage} busy onIntent={onIntent} />);
    fireEvent.change(screen.getByRole("combobox", { name: "Agent 模式" }), { target: { value: "Plan" } });
    expect(onIntent).toHaveBeenCalledWith(expect.objectContaining({ type: "change_mode" }));
    fireEvent.change(screen.getByRole("combobox", { name: "执行方式" }), { target: { value: "continuous" } });
    expect(onIntent).toHaveBeenCalledWith(expect.objectContaining({ type: "change_execution_mode" }));
    fireEvent.click(screen.getByRole("button", { name: "停止" }));
    expect(onIntent).toHaveBeenCalledWith(expect.objectContaining({ type: "stop_turn" }));
  });
  it("exposes read-only context usage percentage", () => {
    render(<Composer sessionId="s1" mode="Agent" executionMode="confirm" model="DeepSeek" contextUsage={contextUsage} onIntent={vi.fn()} />);
    expect(screen.getByRole("img", { name: "上下文用量 25%" })).toHaveAttribute("title", "上下文用量：25%");
  });
});
