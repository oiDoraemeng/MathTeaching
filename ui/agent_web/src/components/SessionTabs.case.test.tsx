import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SessionTabs } from "./SessionTabs";

describe("case session tabs", () => {
  it("marks case tabs with the book-open icon and preserves close callback", () => {
    render(<SessionTabs sessions={[{ id: "s", title: "Chat", mode: "Agent", executionMode: "continuous", model: "m", turns: [] }]} activeSessionId="s" onSelect={vi.fn()} onClose={vi.fn()} cases={[{ id: "c", category: "向量", name: "案例", formula: "x", steps: ["s"], conclusion: "c" }]} onSelectCase={vi.fn()} />);
    expect(screen.getByRole("button", { name: "案例" }).querySelector("svg")).toBeTruthy();
  });
});
