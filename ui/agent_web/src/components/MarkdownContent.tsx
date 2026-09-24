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

function renderMath(source: string, inline = false): string {
  const tokens: string[] = [];
  // ``■`` is an editorial end-of-proof marker from the lecture source, not
  // student-facing content.  Strip it at the final rendering boundary as
  // well, so older published artifacts and source excerpts behave exactly
  // like newly refined artifacts.
  const normalized = normalizeKaTeXHtml(source.replaceAll("■", ""));
  const protect = (expression: string, displayMode: boolean) => {
    const token = `MATH_TOKEN_${tokens.length}`;
    tokens.push(renderFormula(expression, displayMode));
    return token;
  };
  const protectedSource = normalized
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, expression: string) => protect(expression, true))
    .replace(/\$\$([\s\S]*?)\$\$/g, (_, expression: string) => protect(expression, true))
    .replace(/\$([^$\n]+)\$/g, (_, expression: string) => protect(expression, false));
  const html = inline ? markdown.renderInline(protectedSource) : markdown.render(protectedSource);
  // CommonMark 的强调分隔符规则会让紧贴汉字或公式占位符的 ``**…**``（例如
  // ``**算法一（行视角）：**$公式$`` 会变成 ``**算法一（行视角）：**MATH_TOKEN_0``）
  // 无法闭合，从而原样显示 ``**``。这里把渲染结果中仍残留的字面量加粗标记补成
  // ``<strong>``，与桌面端 ``_render_inline_bold`` 的行为保持一致。
  const emphasized = html.replace(
    /\*\*(?=\S)([^<>\n]+?)(?<=\S)\*\*/g,
    "<strong>$1</strong>",
  );
  return emphasized.replace(/MATH_TOKEN_(\d+)/g, (_, index: string) => tokens[Number(index)] ?? "");
}

const SANITIZE_CONFIG = {
  // KaTeX 的根号依赖内联 SVG，清理时需保留基础 SVG 配置。
  USE_PROFILES: { html: true, mathMl: true, svg: true, svgFilters: false },
  ADD_TAGS: [
    "math", "semantics", "mrow", "mi", "mn", "mo", "msup", "msub", "msubsup",
    "mfrac", "msqrt", "mroot", "mtable", "mtr", "mtd", "menclose", "mpadded",
    "mstyle", "mspace", "annotation",
  ],
  ADD_ATTR: ["class", "style", "xmlns", "display", "encoding", "aria-hidden", "columnalign", "rowalign"],
};

export const MarkdownContent = memo(function MarkdownContent({ children }: { children: string }) {
  const html = DOMPurify.sanitize(renderMath(children), SANITIZE_CONFIG);
  return <div className="markdown-content" dangerouslySetInnerHTML={{ __html: html }} />;
});

/** 标题、摘要和讲义来源等行内位置：只做行内渲染，不产生块级元素。 */
export const InlineMarkdown = memo(function InlineMarkdown({ children }: { children: string }) {
  const html = DOMPurify.sanitize(renderMath(children, true), SANITIZE_CONFIG);
  return <span className="markdown-content markdown-content--inline" dangerouslySetInnerHTML={{ __html: html }} />;
});
