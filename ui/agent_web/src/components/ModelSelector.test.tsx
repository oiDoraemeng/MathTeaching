import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ModelSelector } from "./ModelSelector";

describe("ModelSelector", () => {
  const catalog = { builtin: [
    { id: "a", name: "Alpha", group: "builtin", capabilities: ["reasoning"] },
    { id: "b", name: "Beta", group: "builtin", capabilities: ["image_input"] },
  ], custom: [] };

  function renderSelector(onIntent = vi.fn()) {
    render(<ModelSelector model="a" sessionId="s1" catalog={catalog} onIntent={onIntent} />);
    return onIntent;
  }

  it("shows a detail card for every model on hover", () => {
    const onIntent = vi.fn();
    render(<ModelSelector model="a" sessionId="s1" catalog={catalog} onIntent={onIntent} />);
    fireEvent.click(screen.getByRole("button", { name: "模型" }));
    fireEvent.mouseEnter(screen.getByRole("menuitem", { name: "Alpha" }).parentElement!);
    expect(screen.getByRole("tooltip")).toHaveTextContent("Alpha");
    fireEvent.mouseLeave(screen.getByRole("menuitem", { name: "Alpha" }).parentElement!);
    fireEvent.mouseEnter(screen.getByRole("menuitem", { name: "Beta" }).parentElement!);
    expect(screen.getByRole("tooltip")).toHaveTextContent("Beta");
  });

  it.each(["Escape", "outside"])("closes through %s", (path) => {
    renderSelector();
    const trigger = screen.getByRole("button", { name: "模型" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    if (path === "Escape") fireEvent.keyDown(document, { key: "Escape" });
    else fireEvent.mouseDown(document.body);
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  it("closes after selecting a model and emits the change intent", () => {
    const onIntent = renderSelector();
    const trigger = screen.getByRole("button", { name: "模型" });
    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole("menuitem", { name: "Beta" }));
    expect(onIntent).toHaveBeenCalledWith(expect.objectContaining({ type: "change_model", payload: { model: "b" } }));
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});
