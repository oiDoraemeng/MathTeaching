import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const root = path.resolve("src");
const literal = /#[0-9a-f]{3,8}\b|rgba?\s*\(/i;

async function files(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const result = [];
  for (const entry of entries) {
    const file = path.join(dir, entry.name);
    if (entry.isDirectory()) result.push(...await files(file));
    else if (/\.(css|tsx)$/.test(entry.name)) result.push(file);
  }
  return result;
}

test("Web components and layout use semantic colors", async () => {
  const targets = [...await files(path.join(root, "styles")), ...await files(path.join(root, "components"))]
    .filter((file) => !file.endsWith(path.join("styles", "theme.css")));
  const violations = [];
  for (const file of targets) {
    const source = (await readFile(file, "utf8")).replace(/\/\*[\s\S]*?\*\//g, "");
    if (literal.test(source)) violations.push(path.relative(process.cwd(), file));
  }
  assert.deepEqual(violations, []);
});
