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

const components: Components = {
  /** Headings */
  h1: ({ children, ...props }) => (
    <h1
      className="mt-4 mb-2 text-[1.2rem] font-bold text-foreground tracking-tight border-b border-border pb-1.5"
      {...props}
    >
      {children}
    </h1>
  ),
  h2: ({ children, ...props }) => (
    <h2
      className="mt-3 mb-1.5 text-[1.05rem] font-bold text-foreground tracking-tight"
      {...props}
    >
      {children}
    </h2>
  ),
  h3: ({ children, ...props }) => (
    <h3
      className="mt-2.5 mb-1 text-[0.98rem] font-semibold text-foreground"
      {...props}
    >
      {children}
    </h3>
  ),

  /** Paragraph */
  p: ({ children, ...props }) => (
    <p
      className="mb-2 text-[15px] leading-relaxed text-foreground last:mb-0"
      {...props}
    >
      {children}
    </p>
  ),

  /** Strong / em */
  strong: ({ children, ...props }) => (
    <strong className="font-semibold text-foreground" {...props}>
      {children}
    </strong>
  ),
  em: ({ children, ...props }) => (
    <em className="italic text-foreground/80" {...props}>
      {children}
    </em>
  ),

  /** Lists */
  ul: ({ children, ...props }) => (
    <ul
      className="my-2 ml-5 space-y-1 list-disc marker:text-primary/80"
      {...props}
    >
      {children}
    </ul>
  ),
  ol: ({ children, ...props }) => (
    <ol
      className="my-2 ml-5 space-y-1 list-decimal marker:text-primary/80 marker:font-semibold"
      {...props}
    >
      {children}
    </ol>
  ),
  li: ({ children, ...props }) => (
    <li
      className="text-[14.5px] leading-relaxed text-foreground pl-0.5"
      {...props}
    >
      {children}
    </li>
  ),

  /** Inline code — orange pill, distinct from block code */
  code: ({ className, children, ...props }) => {
    const isBlock = Boolean(className);
    if (isBlock) {
      return (
        <code className="font-mono text-slate-200" {...props}>
          {children}
        </code>
      );
    }
    return (
      <code
        className="rounded px-1.5 py-0.5 font-mono text-[0.82em] before:content-[''] after:content-['']"
        {...props}
      >
        {children}
      </code>
    );
  },

  /** Fenced code / ASCII diagram block */
  pre: ({ children, ...props }) => {
    return (
      <div className="my-3 overflow-hidden rounded-xl border border-white/10 bg-[#0d1117]">
        <div className="flex items-center gap-1.5 border-b border-white/10 bg-white/5 px-4 py-2">
          <span className="h-2.5 w-2.5 rounded-full bg-red-500/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-yellow-500/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-green-500/70" />
        </div>
        <pre
          className="overflow-x-auto p-4 m-0 font-mono text-[13px] leading-relaxed text-slate-200"
          {...props}
        >
          {children}
        </pre>
      </div>
    );
  },

  /** Blockquote */
  blockquote: ({ children, ...props }) => (
    <blockquote
      className="my-3 rounded-r-lg border-l-4 border-primary/60 bg-primary/5 px-4 py-2.5 text-[14px] text-foreground/80 not-italic"
      {...props}
    >
      {children}
    </blockquote>
  ),

  /** Horizontal rule */
  hr: (props) => <hr className="my-4 border-border/60" {...props} />,

  /** Tables */
  table: ({ children, ...props }) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-border">
      <table className="w-full border-collapse text-[13.5px]" {...props}>
        {children}
      </table>
    </div>
  ),
  thead: ({ children, ...props }) => (
    <thead className="bg-muted/70" {...props}>
      {children}
    </thead>
  ),
  th: ({ children, ...props }) => (
    <th
      className="border-b border-border px-4 py-2.5 text-left font-semibold text-foreground"
      {...props}
    >
      {children}
    </th>
  ),
  tr: ({ children, ...props }) => (
    <tr
      className="even:bg-muted/20 transition-colors hover:bg-muted/30"
      {...props}
    >
      {children}
    </tr>
  ),
  td: ({ children, ...props }) => (
    <td
      className="border-b border-border/40 px-4 py-2 text-foreground/80 last-of-type:border-0"
      {...props}
    >
      {children}
    </td>
  ),

  /** Links */
  a: ({ children, href, ...props }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-primary underline decoration-primary/40 underline-offset-2 hover:decoration-primary transition-colors"
      {...props}
    >
      {children}
    </a>
  ),
};

/** Renders chat content with GFM tables, LaTeX math, ASCII diagram blocks, and themed prose. */
export function Markdown({ children }: MarkdownProps) {
  const normalizedMarkdown = normalizeLatexDelimiters(children);

  return (
    <div className="max-w-none break-words overflow-wrap-anywhere text-foreground">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { strict: false }]]}
        components={components}
      >
        {normalizedMarkdown}
      </ReactMarkdown>
    </div>
  );
}
