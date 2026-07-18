import React, { useMemo } from "react";

interface MarkdownRendererProps {
  content: string;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderMarkdown(text: string): string {
  let html = escapeHtml(text);

  // Code blocks (``` ... ```)
  html = html.replace(
    /```(\w*)\n([\s\S]*?)```/g,
    (_match, lang: string, code: string) =>
      `<pre class="bg-gray-800 text-gray-100 rounded-lg p-3 my-2 overflow-x-auto text-sm"><code class="language-${lang || "plaintext"}">${code.trim()}</code></pre>`,
  );

  // Inline code (` ... `)
  html = html.replace(
    /`([^`]+)`/g,
    '<code class="bg-gray-100 text-red-600 px-1.5 py-0.5 rounded text-sm font-mono">$1</code>',
  );

  // Bold
  html = html.replace(
    /\*\*(.+?)\*\*/g,
    '<strong class="font-semibold">$1</strong>',
  );

  // Italic
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

  // Strikethrough
  html = html.replace(/~~(.+?)~~/g, "<del>$1</del>");

  // Links [text](url)
  html = html.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" class="text-primary-600 underline hover:text-primary-800" target="_blank" rel="noopener noreferrer">$1</a>',
  );

  // Images ![alt](url)
  html = html.replace(
    /!\[([^\]]*)\]\(([^)]+)\)/g,
    '<img src="$2" alt="$1" class="max-w-full rounded-lg my-2" />',
  );

  // Headers (process after bold/italic)
  html = html.replace(
    /^### (.+)$/gm,
    '<h4 class="font-semibold text-base mt-3 mb-1">$1</h4>',
  );
  html = html.replace(
    /^## (.+)$/gm,
    '<h3 class="font-semibold text-lg mt-3 mb-1">$1</h3>',
  );
  html = html.replace(
    /^# (.+)$/gm,
    '<h2 class="font-bold text-xl mt-4 mb-2">$1</h2>',
  );

  // Lists
  html = html.replace(/^[\-\*] (.+)$/gm, '<li class="ml-4 list-disc">$1</li>');
  html = html.replace(
    /^\d+[.)] (.+)$/gm,
    '<li class="ml-4 list-decimal">$1</li>',
  );

  // Blockquotes
  html = html.replace(
    /^> (.+)$/gm,
    '<blockquote class="border-l-4 border-gray-300 pl-3 italic text-gray-600 my-2">$1</blockquote>',
  );

  // Horizontal rule
  html = html.replace(/^---$/gm, '<hr class="my-3 border-gray-200" />');

  // Wrap consecutive <li> in <ul>/<ol>
  html = html.replace(
    /((?:<li class="ml-4 list-disc">.*?<\/li>\n?)+)/g,
    '<ul class="my-1">$1</ul>',
  );
  html = html.replace(
    /((?:<li class="ml-4 list-decimal">.*?<\/li>\n?)+)/g,
    '<ol class="my-1">$1</ol>',
  );

  // Paragraph breaks
  html = html.replace(/\n\n/g, "<br/><br/>");
  html = html.replace(/\n/g, "<br/>");

  return html;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
}) => {
  const html = useMemo(() => renderMarkdown(content), [content]);

  if (!content) return null;

  return (
    <div
      className="prose prose-sm max-w-none break-words"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
};

export default MarkdownRenderer;
