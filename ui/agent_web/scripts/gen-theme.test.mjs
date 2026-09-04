import test from "node:test";
import assert from "node:assert/strict";
import { generateThemeCss, loadTokens } from "./gen-theme.mjs";
import { mkdtemp, writeFile, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

test("emits complete light and dark branches", async () => {
  const tokens = await loadTokens();
  const css = generateThemeCss(tokens);
  assert.match(css, /:root, \[data-theme="light"\]/);
  assert.match(css, /\[data-theme="dark"\]/);
  assert.match(css, /--agent-accent: #2f7ebd/);
  assert.match(css, /color-scheme: dark/);
  assert.match(css, /--agent-text-on-accent: #ffffff/);
  assert.match(css, /--agent-motion-easing-out:/);
  const stack = '--agent-font-family: "Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif;';
  assert.equal(css.split(stack).length - 1, 2);
});

test("falls back for malformed structure and import does not write", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "theme-test-"));
  const file = path.join(dir, "bad.json");
  await writeFile(file, JSON.stringify({ themes: {} }));
  const tokens = await loadTokens(file);
  const css = generateThemeCss(tokens);
  assert.match(css, /--agent-accent: #2f7ebd/);
  assert.match(css, /\[data-theme="dark"\][\s\S]*--agent-canvas: #eef1f4/);
  await stat(file);
});
