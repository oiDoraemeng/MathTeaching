import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ModelSelector } from "./ModelSelector";

describe("ModelSelector", () => {
  it("shows a detail card for every model on hover", () => {
    const onIntent = vi.fn();
    const catalog = { builtin: [
      { id: "a", name: "Alpha", group: "builtin", capabilities: ["reasoning"] },
      { id: "b", name: "Beta", group: "builtin", capabilities: ["image_input"] },
    ], custom: [] };
    render(<ModelSelector model="a" sessionId="s1" catalog={catalog} onIntent={onIntent} />);
    fireEvent.click(screen.getByRole("button", { name: "模型" }));
    fireEvent.mouseEnter(screen.getByRole("menuitem", { name: "Alpha" }).parentElement!);
    expect(screen.getByRole("tooltip")).toHaveTextContent("Alpha");
    fireEvent.mouseLeave(screen.getByRole("menuitem", { name: "Alpha" }).parentElement!);
    fireEvent.mouseEnter(screen.getByRole("menuitem", { name: "Beta" }).parentElement!);
    expect(screen.getByRole("tooltip")).toHaveTextContent("Beta");
  });
});
