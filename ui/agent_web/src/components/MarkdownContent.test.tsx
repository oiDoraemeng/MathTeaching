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

  it("removes editorial proof-end markers from lecture content", () => {
    const { container } = render(
      <MarkdownContent>{`证明：$x=x$。■\n\n结论保留。`}</MarkdownContent>,
    );

    expect(container.textContent).not.toContain("■");
    expect(container.textContent).toContain("证明：");
    expect(container.textContent).toContain("结论保留。");
  });

  it("renders a multiline projection formula with visible stacked fractions", () => {
    const source = String.raw`$$\begin{aligned}
\operatorname{Proj}_{\boldsymbol u}(\boldsymbol v)
&=\frac{\boldsymbol v\cdot\boldsymbol u}{\boldsymbol u\cdot\boldsymbol u}\,\boldsymbol u\\
&=\frac{\boldsymbol v\cdot\boldsymbol u}{\lvert\boldsymbol u\rvert^2}\,\boldsymbol u
\end{aligned}$$`;
    const { container } = render(<MarkdownContent>{source}</MarkdownContent>);

    const visibleFormula = container.querySelector(".katex-display .katex-html");
    expect(visibleFormula).not.toBeNull();
    expect(container.querySelectorAll(".katex-html .frac-line").length).toBe(2);
    expect(visibleFormula?.textContent).not.toContain("\\frac");
  });
});
