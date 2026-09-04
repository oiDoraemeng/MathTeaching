import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const layoutPath = join(process.cwd(), "src", "styles", "layout.css");
const layoutCss = () => readFileSync(layoutPath, "utf8");

const block = (selector: string) => {
  const match = layoutCss().match(new RegExp(`${selector.replace(".", "\\.")}\\s*\\{([\\s\\S]*?)\\}`, "m"));
  if (!match) throw new Error(`Missing ${selector} block`);
  return match[1];
};

describe("Agent Web timeline layout", () => {
  it("uses the approved compact density", () => {
    expect(block(".assistant-content")).toContain("font-size: 12px");
    expect(block(".assistant-content")).toContain("line-height: 1.5");
    expect(block(".event-card")).toContain("margin: 6px 0");
    expect(block(".event-card")).toContain("padding: 8px 10px");
    expect(block(".turn-block")).toContain("margin: 0 auto 18px");
    expect(block(".timeline")).toContain("padding: 16px 14px 20px");
    expect(block(".markdown-content p")).toContain("margin: 6px 0");
    expect(block(".reasoning-block")).toContain("padding: 7px 9px");
    expect(block(".reasoning-block")).toContain("font-size: 11px");
    expect(block(".thinking-section")).toContain("margin: 8px 0 10px");
  });

  it("keeps actions out of layout and preserves the readable measure", () => {
    expect(block(".turn-block")).toContain("position: relative");
    expect(block(".turn-block")).toContain("max-width: 620px");
    expect(block(".turn-actions")).toContain("position: absolute");
    expect(block(".turn-actions")).toContain("visibility: hidden");
    expect(block(".turn-actions.visible")).toContain("visibility: visible");
  });
});
