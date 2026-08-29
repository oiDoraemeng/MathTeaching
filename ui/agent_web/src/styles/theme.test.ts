import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const themePath = join(process.cwd(), "src", "styles", "theme.css");
const themeCss = () => readFileSync(themePath, "utf8");

const branch = (css: string, selector: string) => {
  const match = css.match(new RegExp(`${selector}\\s*\\{([\\s\\S]*?)\\n\\}`, "m"));
  if (!match) throw new Error(`Missing ${selector} branch`);
  return match[1];
};

const variables = (block: string) => [...new Set([...block.matchAll(/--agent-[a-z0-9-]+/g)].map((match) => match[0]))].sort();

describe("Agent Web theme CSS", () => {
  it("exposes both explicit theme branches with a light fallback", () => {
    const css = themeCss();
    expect(css).toContain(":root, [data-theme=\"light\"]");
    expect(css).toContain('[data-theme="dark"]');
    expect(css).toContain("color-scheme: light");
    expect(css).toContain("color-scheme: dark");
    expect(css).not.toContain("prefers-color-scheme");
    expect(css).not.toMatch(/:root\s*\{\s*color-scheme:\s*dark/);
  });

  it("keeps the token names aligned across branches", () => {
    const css = themeCss();
    const light = variables(branch(css, ":root, \\[data-theme=\"light\"\\]"));
    const dark = variables(branch(css, "\\[data-theme=\"dark\"\\]"));
    expect(light).toEqual(dark);
    expect(light).toEqual([
      "--agent-accent",
      "--agent-accent-hover",
      "--agent-accent-pressed",
      "--agent-accent-soft-bg",
      "--agent-bg",
      "--agent-border",
      "--agent-border-strong",
      "--agent-border-subtle",
      "--agent-canvas",
      "--agent-elevated",
      "--agent-error",
      "--agent-font-family",
      "--agent-font-size-body",
      "--agent-font-size-caption",
      "--agent-font-size-subtitle",
      "--agent-font-size-title",
      "--agent-motion-duration-fast",
      "--agent-motion-duration-normal",
      "--agent-motion-duration-slow",
      "--agent-motion-easing-out",
      "--agent-muted",
      "--agent-overlay",
      "--agent-scene",
      "--agent-secondary",
      "--agent-shadow-modal",
      "--agent-shadow-overlay",
      "--agent-success",
      "--agent-surface",
      "--agent-text",
      "--agent-text-on-accent",
      "--agent-warning",
    ]);
  });
});
