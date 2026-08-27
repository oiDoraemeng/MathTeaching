import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { App } from "./App";

describe("MathAgent shell", () => {
  it("renders the IDE-style empty workspace", () => {
    render(<App />);
    expect(screen.getByText("MathAgent")).toBeInTheDocument();
    expect(screen.getByText("New Chat")).toBeInTheDocument();
    expect(screen.getByText("开始一个数学探索")).toBeInTheDocument();
    expect(screen.getByText("用自然语言描述你想理解或绘制的内容")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /绘制函数|解释几何概念|演示导数|理解矩阵变换/ })).toHaveLength(4);
    expect(screen.getByPlaceholderText('提问或输入 "/"快捷命令')).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Agent 模式" })).toHaveValue("Agent");
  });
  it("keeps one tab and adds a second session", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "新建对话" }));
    expect(screen.getAllByText("New Chat")).toHaveLength(2);
    expect(screen.getAllByRole("button", { name: /关闭 New Chat/ })).toHaveLength(2);
  });
  it("accepts a starter prompt through the composer seam", () => {
    const spy = vi.spyOn(crypto, "randomUUID").mockReturnValue("00000000-0000-0000-0000-000000000001");
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "绘制函数" }));
    expect(spy).toHaveBeenCalled();
    spy.mockRestore();
  });

  it("opens history and settings as visible secondary views", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /\u5386\u53f2\u8bb0\u5f55/ }));
    expect(screen.getByRole("heading", { name: "History" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Back to conversation" }));
    fireEvent.click(screen.getByRole("button", { name: /\u8bbe\u7f6e/ }));
    expect(screen.getByRole("heading", { name: "Settings" })).toBeVisible();
  });
});
