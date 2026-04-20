import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

interface MarkdownProps {
  children: string;
}

/** Renders chat content with GFM tables, LaTeX, and themed prose. */
export function Markdown({ children }: MarkdownProps) {
  return (
    <div className="prose prose-sm max-w-none text-foreground prose-headings:font-display prose-headings:font-bold prose-headings:tracking-tight prose-p:leading-relaxed prose-strong:text-foreground prose-code:text-primary prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-[''] prose-code:after:content-[''] prose-table:my-3 prose-th:bg-muted prose-th:text-foreground prose-blockquote:border-l-primary prose-blockquote:bg-accent/40 prose-blockquote:py-1 prose-blockquote:px-3 prose-blockquote:rounded-md prose-blockquote:not-italic prose-li:my-0.5">
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
