import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { normalizeLatexDelimiters } from "./markdown-utils";
import type { Components } from "react-markdown";

interface MarkdownProps {
  children: string;
}

/** Custom component overrides for ReactMarkdown. */
const components: Components = {
  /** Wrap pre/code blocks (incl. ASCII diagrams) in a horizontally scrollable container. */
  pre: ({ children, ...props }) => (
    <div className="overflow-x-auto rounded-lg bg-muted/60 my-3">
      <pre className="font-mono text-sm p-4 m-0" {...props}>{children}</pre>
    </div>
  ),
  /** Wrap tables in a scrollable container for mobile. */
  table: ({ children, ...props }) => (
    <div className="overflow-x-auto my-3">
      <table className="w-full border-collapse" {...props}>{children}</table>
    </div>
  ),
};

/** Renders chat content with GFM tables, LaTeX math, ASCII diagram blocks, and themed prose. */
export function Markdown({ children }: MarkdownProps) {
  const normalizedMarkdown = normalizeLatexDelimiters(children);

  return (
    <div className="prose prose-sm max-w-none text-foreground break-words overflow-wrap-anywhere prose-headings:font-display prose-headings:font-bold prose-headings:tracking-tight prose-p:leading-relaxed prose-strong:text-foreground prose-code:text-primary prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-[''] prose-code:after:content-[''] prose-table:my-3 prose-th:bg-muted prose-th:text-foreground prose-blockquote:border-l-primary prose-blockquote:bg-accent/40 prose-blockquote:py-1 prose-blockquote:px-3 prose-blockquote:rounded-md prose-blockquote:not-italic prose-li:my-0.5">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={components}
      >
        {normalizedMarkdown}
      </ReactMarkdown>
    </div>
  );
}
