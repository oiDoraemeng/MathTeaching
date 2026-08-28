import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

export const TOKEN_PATH = fileURLToPath(new URL("../../../design/tokens.json", import.meta.url));
export const OUTPUT_PATH = fileURLToPath(new URL("../src/styles/theme.css", import.meta.url));

const FALLBACK = {
  font: { family_default: "Segoe UI", size: { caption: 11, body: 12, subtitle: 13, title: 15 } },
  motion: { duration: { fast: 120, normal: 150, slow: 200 }, easing_out: "cubic-bezier(0.33, 1, 0.68, 1)" },
  theme: {
    bg: { canvas: "#eef1f4", panel: "#ffffff", elevated: "#f5f7f9", overlay: "#ffffff", scene: "#f4f6f9" },
    text: { primary: "#17212e", secondary: "#3f4c5c", muted: "#66788c", on_accent: "#ffffff" },
    border: { subtle: "#eceff3", default: "#d5dbe3", strong: "#b8c2cd" },
    accent: { default: "#2f7ebd", hover: "#3a8cd0", pressed: "#2970ab", soft_bg: "#e4f0f9" },
    status: { success: "#16825d", warning: "#8a5a00", error: "#b42318" },
    shadow: { overlay: "0 1px 3px rgba(23,33,46,.10), 0 4px 12px rgba(23,33,46,.08)", modal: "0 4px 8px rgba(23,33,46,.10), 0 12px 32px rgba(23,33,46,.14)" }
  }
};

export async function loadTokens(filePath = TOKEN_PATH) {
  try {
    return JSON.parse(await readFile(filePath, "utf8"));
  } catch {
    return { font: FALLBACK.font, motion: FALLBACK.motion, themes: { light: FALLBACK.theme, dark: FALLBACK.theme } };
  }
}

const aliases = {
  "bg.canvas": "canvas", "bg.panel": "bg", "bg.elevated": "elevated", "bg.overlay": "overlay", "bg.scene": "scene",
  "text.primary": "text", "text.secondary": "secondary", "text.muted": "muted", "text.on_accent": "on-accent",
  "border.subtle": "border-subtle", "border.default": "border", "border.strong": "border-strong",
  "accent.default": "accent", "accent.hover": "accent-hover", "accent.pressed": "accent-pressed", "accent.soft_bg": "accent-soft-bg",
  "status.success": "success", "status.warning": "warning", "status.error": "error",
  "shadow.overlay": "shadow-overlay", "shadow.modal": "shadow-modal"
};

function flatten(obj, prefix = [], out = []) {
  for (const [key, value] of Object.entries(obj ?? {})) {
    if (value && typeof value === "object" && !Array.isArray(value)) flatten(value, [...prefix, key], out);
    else out.push([[...prefix, key].join("."), value]);
  }
  return out;
}

function declarations(tokens, theme) {
  const lines = [];
  for (const [key, value] of flatten(theme)) {
    const name = aliases[key] ?? key.replaceAll(".", "-");
    lines.push(`  --agent-${name}: ${value};`);
  }
  for (const [key, value] of flatten(tokens.motion, ["motion"])) lines.push(`  --agent-${key.replaceAll(".", "-")}: ${typeof value === "number" ? `${value}ms` : value};`);
  for (const [key, value] of flatten(tokens.font?.size, ["font-size"])) lines.push(`  --agent-${key.replaceAll(".", "-")}: ${typeof value === "number" ? `${value}px` : value};`);
  lines.push(`  --agent-font-family: ${tokens.font?.family_default ?? FALLBACK.font.family_default};`);
  // Keep the historical Web alias in sync with the semantic panel token.
  const panel = theme?.bg?.panel;
  if (panel !== undefined) lines.push(`  --agent-surface: ${panel};`);
  return lines.join("\n");
}

export function generateThemeCss(tokens) {
  const light = tokens?.themes?.light ?? FALLBACK.theme;
  const dark = tokens?.themes?.dark ?? light;
  return `:root, [data-theme="light"] {\n  color-scheme: light;\n${declarations(tokens ?? FALLBACK, light)}\n}\n\n[data-theme="dark"] {\n  color-scheme: dark;\n${declarations(tokens ?? FALLBACK, dark)}\n}\n\n* { box-sizing: border-box; }\nbody { margin: 0; min-width: 320px; background: var(--agent-bg); color: var(--agent-text); font-family: var(--agent-font-family), sans-serif; }\nbutton, textarea, select { font: inherit; }\nbutton { color: inherit; background: transparent; border: 0; cursor: pointer; }\nbutton:disabled { cursor: default; opacity: .45; }\n.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }\n`;
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))) {
  const tokens = await loadTokens();
  await writeFile(OUTPUT_PATH, generateThemeCss(tokens), "utf8");
}
