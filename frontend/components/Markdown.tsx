"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ children }: { children: string }) {
  return (
    <div className="md-chat text-sm leading-6">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="mb-2 mt-4 font-serif text-2xl">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-2 mt-4 font-serif text-xl">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-1 mt-3 text-base font-semibold">{children}</h3>,
          p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
          ul: ({ children }) => <ul className="mb-3 list-disc space-y-1 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="mb-3 list-decimal space-y-1 pl-5">{children}</ol>,
          li: ({ children }) => <li className="leading-6">{children}</li>,
          strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
          em: ({ children }) => <em className="italic text-ink/90">{children}</em>,
          a: ({ href, children }) => (
            <a href={href} className="text-cyan underline underline-offset-2" target="_blank" rel="noreferrer">
              {children}
            </a>
          ),
          code: ({ className, children }) =>
            className ? (
              <pre className="mb-3 overflow-x-auto rounded-xl bg-void p-3 text-xs">
                <code>{children}</code>
              </pre>
            ) : (
              <code className="rounded bg-void px-1.5 py-0.5 text-[13px]">{children}</code>
            ),
          blockquote: ({ children }) => (
            <blockquote className="mb-3 border-l-2 border-violet/50 pl-3 text-clay">{children}</blockquote>
          ),
          img: ({ src, alt }) =>
            src ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={src}
                alt={alt || ""}
                className="my-3 max-h-[28rem] w-full rounded-xl border border-white/10 object-contain bg-void"
              />
            ) : null,
          table: ({ children }) => (
            <div className="mb-3 overflow-x-auto">
              <table className="w-full text-left text-xs">{children}</table>
            </div>
          ),
          th: ({ children }) => <th className="border-b border-white/15 px-2 py-1">{children}</th>,
          td: ({ children }) => <td className="border-b border-white/5 px-2 py-1">{children}</td>,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
