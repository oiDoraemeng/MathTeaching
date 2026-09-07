import DOMPurify from "dompurify";
import MarkdownIt from "markdown-it";
import katex from "katex";
import { memo } from "react";
import "katex/dist/katex.min.css";

const markdown = new MarkdownIt({ html: false, linkify: false, breaks: true });
const formulaCache = new Map<string, string>();

function renderFormula(expression: string, displayMode: boolean): string {
  const key = `${displayMode ? "display" : "inline"}:${expression}`;
  const cached = formulaCache.get(key);
  if (cached !== undefined) return cached;

  const rendered = katex.renderToString(expression, { displayMode, throwOnError: false });
  formulaCache.set(key, rendered);
  return rendered;
}

function normalizeKaTeXHtml(source: string): string {
  if (!source.includes("katex") || typeof DOMParser === "undefined") return source;
  const document = new DOMParser().parseFromString(source, "text/html");
  const nodes = Array.from(document.body.querySelectorAll(".katex-display, .katex"));
  let normalized = source;
  for (const node of nodes) {
    if (node.closest(".katex-display") && !node.classList.contains("katex-display")) continue;
    const expression = node.querySelector('annotation[encoding="application/x-tex"]')?.textContent?.trim();
    if (!expression) continue;
    const replacement = node.classList.contains("katex-display") ? `$$${expression}$$` : `$${expression}$`;
    normalized = normalized.replace(node.outerHTML, replacement);
  }
  return normalized;
}

function renderMath(source: string): string {
  const tokens: string[] = [];
  const normalized = normalizeKaTeXHtml(source);
  const protectedSource = normalized
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, expression: string) => { const token = `MATH_TOKEN_${tokens.length}`; tokens.push(renderFormula(expression, true)); return token; })
    .replace(/\$\$([\s\S]*?)\$\$/g, (_, expression: string) => { const token = `MATH_TOKEN_${tokens.length}`; tokens.push(renderFormula(expression, true)); return token; })
    .replace(/\$([^$\n]+)\$/g, (_, expression: string) => { const token = `MATH_TOKEN_${tokens.length}`; tokens.push(renderFormula(expression, false)); return token; });
  return markdown.render(protectedSource).replace(/MATH_TOKEN_(\d+)/g, (_, index: string) => tokens[Number(index)] ?? "");
}

export const MarkdownContent = memo(function MarkdownContent({ children }: { children: string }) {
  const html = DOMPurify.sanitize(renderMath(children), {
    USE_PROFILES: { html: true, mathMl: true },
    ADD_TAGS: [
      "math", "semantics", "mrow", "mi", "mn", "mo", "msup", "msub", "msubsup",
      "mfrac", "msqrt", "mroot", "mtable", "mtr", "mtd", "menclose", "mpadded",
      "mstyle", "mspace", "annotation",
    ],
    ADD_ATTR: ["class", "style", "xmlns", "display", "encoding", "aria-hidden", "columnalign", "rowalign"],
  });
  return <div className="markdown-content" dangerouslySetInnerHTML={{ __html: html }} />;
});
