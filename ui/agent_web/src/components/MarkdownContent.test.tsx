import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarkdownContent } from "./MarkdownContent";

describe("MarkdownContent", () => {
  it("renders source and previously rendered KaTeX without literal tags", () => {
    const raw = '<span class="katex-display"><span class="katex"><span class="katex-mathml"><math><semantics><annotation encoding="application/x-tex">\\frac{x^2}{a^2}</annotation></semantics></math></span></span></span>';
    const { container } = render(<MarkdownContent>{`$x+y$\n\n${raw}`}</MarkdownContent>);
    expect(container.querySelectorAll(".katex").length).toBeGreaterThan(0);
    expect(container.textContent).not.toContain("<span class=\"katex");
  });
});
