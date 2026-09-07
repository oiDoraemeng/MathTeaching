import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const indexHtml = readFileSync(resolve(process.cwd(), "index.html"), "utf8");
const policy = indexHtml.match(/http-equiv="Content-Security-Policy"\s+content="([^"]+)"/i)?.[1] ?? "";

describe("MathAgent document policy", () => {
  it("allows KaTeX inline positioning styles while keeping scripts restricted", () => {
    expect(policy).toContain("style-src 'self' 'unsafe-inline' mathagent://app");
    expect(policy).not.toContain("script-src 'self' 'unsafe-inline'");
  });
});
