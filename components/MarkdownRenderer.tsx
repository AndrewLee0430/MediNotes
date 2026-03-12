"use client"

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

interface MarkdownRendererProps {
    content: string;
    accentColor?: string;
    className?: string;
}

/**
 * Unified Markdown renderer for Vela's dark theme.
 * Uses inline CSS variables to override Tailwind prose defaults —
 * avoids reliance on `dark:` prefix which requires <html class="dark">.
 *
 * Usage:
 *   <MarkdownRenderer content={text} accentColor="#ff8e6e" />
 *   <MarkdownRenderer content={text} accentColor="#68d391" />
 */
export default function MarkdownRenderer({
    content,
    accentColor = '#ff8e6e',
    className = '',
}: MarkdownRendererProps) {
    return (
        <div
            className={`prose max-w-none prose-sm prose-headings:font-semibold prose-h2:text-base prose-h2:pb-1 prose-p:leading-relaxed prose-li:leading-relaxed ${className}`}
            style={{
                color: 'rgba(255,255,255,0.85)',
                '--tw-prose-headings': '#ffffff',
                '--tw-prose-bold': '#ffffff',
                '--tw-prose-links': accentColor,
                '--tw-prose-bullets': 'rgba(255,255,255,0.5)',
                '--tw-prose-counters': 'rgba(255,255,255,0.5)',
                '--tw-prose-code': accentColor,
                '--tw-prose-hr': 'rgba(255,255,255,0.15)',
                '--tw-prose-quote-borders': accentColor,
                '--tw-prose-captions': 'rgba(255,255,255,0.45)',
            } as React.CSSProperties}
        >
            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                {content}
            </ReactMarkdown>
        </div>
    );
}