import DOMPurify from "dompurify";
import MarkdownIt from "markdown-it";
import katex from "katex";
import "katex/dist/katex.min.css";

const markdown = new MarkdownIt({ html: false, linkify: false, breaks: true });

function renderMath(source: string): string {
  return source
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, expression: string) => katex.renderToString(expression, { displayMode: true, throwOnError: false }))
    .replace(/\$\$([\s\S]*?)\$\$/g, (_, expression: string) => katex.renderToString(expression, { displayMode: true, throwOnError: false }))
    .replace(/\$([^$\n]+)\$/g, (_, expression: string) => katex.renderToString(expression, { throwOnError: false }));
}

export function MarkdownContent({ children }: { children: string }) {
  const html = DOMPurify.sanitize(markdown.render(renderMath(children)), { USE_PROFILES: { html: true } });
  return <div className="markdown-content" dangerouslySetInnerHTML={{ __html: html }} />;
}
