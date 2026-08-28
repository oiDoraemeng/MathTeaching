import test from "node:test";
import assert from "node:assert/strict";
import { generateThemeCss, loadTokens } from "./gen-theme.mjs";

test("emits complete light and dark branches", async () => {
  const tokens = await loadTokens();
  const css = generateThemeCss(tokens);
  assert.match(css, /:root, \[data-theme="light"\]/);
  assert.match(css, /\[data-theme="dark"\]/);
  assert.match(css, /--agent-accent: #2f7ebd/);
  assert.match(css, /color-scheme: dark/);
});
