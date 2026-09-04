import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { HistoryItem } from "../types";
import { HistoryView } from "./HistoryView";

const item: HistoryItem = {
  id: "session-1",
  title: "Algebra",
  turn_count: 3,
  hidden: false,
  closed: false,
};

function renderView(onIntent = vi.fn()) {
  render(
    <HistoryView
      visible={[item]}
      hidden={[]}
      onBack={vi.fn()}
      onIntent={onIntent}
      onSelect={vi.fn()}
    />,
  );
  return onIntent;
}

describe("HistoryView rename", () => {
  it("cancels rename on Escape without blur saving", () => {
    const onIntent = renderView();
    fireEvent.click(screen.getByRole("button", { name: "重命名 Algebra" }));
    const input = screen.getByRole("textbox", { name: "重命名 Algebra" });
    fireEvent.change(input, { target: { value: "Changed" } });
    fireEvent.keyDown(input, { key: "Escape" });
    fireEvent.blur(input);

    expect(onIntent).not.toHaveBeenCalledWith(expect.objectContaining({ type: "rename_session" }));
    expect(screen.getByText("Algebra")).toBeInTheDocument();
  });

  it("saves a trimmed title once on Enter", () => {
    const onIntent = renderView();
    fireEvent.click(screen.getByRole("button", { name: "重命名 Algebra" }));
    const input = screen.getByRole("textbox", { name: "重命名 Algebra" });
    fireEvent.change(input, { target: { value: "  Changed  " } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(onIntent).toHaveBeenCalledTimes(1);
    expect(onIntent).toHaveBeenCalledWith(expect.objectContaining({ type: "rename_session", payload: { title: "Changed" } }));
  });

  it("saves a trimmed title once on blur", () => {
    const onIntent = renderView();
    fireEvent.click(screen.getByRole("button", { name: "重命名 Algebra" }));
    const input = screen.getByRole("textbox", { name: "重命名 Algebra" });
    fireEvent.change(input, { target: { value: "  Changed  " } });
    fireEvent.blur(input);

    expect(onIntent).toHaveBeenCalledTimes(1);
    expect(onIntent).toHaveBeenCalledWith(expect.objectContaining({ type: "rename_session", payload: { title: "Changed" } }));
  });

  it("shows localized turn count and actions", () => {
    renderView();
    expect(screen.getByText("3 轮")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "隐藏 Algebra" })).toBeInTheDocument();
  });
});
