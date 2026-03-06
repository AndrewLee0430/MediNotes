"use client"

import { useState, FormEvent, useRef, useEffect, useCallback } from 'react';
import { useAuth, SignedIn, SignedOut, RedirectToSignIn, UserButton } from '@clerk/nextjs';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import Link from 'next/link';
import CitationPanel, { Citation } from '../components/CitationPanel';
import FeedbackBar from '../components/FeedbackBar';

// Research accent color
const ACCENT = '#ff8e6e';

const defaultSuggestions = [
    "What are the common side effects of Metformin?",
    "Which drugs interact with Warfarin?",
    "What should I know about NSAIDs in elderly patients?",
    "Medication safety for diabetic patients?",
    "Contraindications of ACE inhibitors in hypertension?",
    "How to manage statin-induced myopathy?",
    "DOACs vs Warfarin — key differences?",
    "Safety of antibiotics in pregnancy?",
    "When to use beta-blockers in heart failure?",
    "Long-term risks of proton pump inhibitors?",
];

class FatalError extends Error {}

function FallbackBanner() {
    return (
        <div className="mb-4 flex items-start gap-3 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
            <span className="text-amber-500 text-sm mt-0.5 font-bold">⚠</span>
            <div>
                <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">
                    No literature found for this query
                </p>
                <p className="text-sm text-amber-700 dark:text-amber-400 mt-0.5">
                    This answer is based on general medical knowledge, not retrieved PubMed or FDA literature.
                    Please verify with current clinical guidelines before applying clinically.
                </p>
            </div>
        </div>
    );
}

function ResearchForm() {
    const { getToken } = useAuth();

    const [question, setQuestion]   = useState('');
    const [answer, setAnswer]       = useState('');
    const [citations, setCitations] = useState<Citation[]>([]);
    const [loading, setLoading]     = useState(false);
    const [queryTime, setQueryTime] = useState<number | null>(null);
    const [error, setError]         = useState<string>('');
    const [isFallback, setIsFallback] = useState(false);
    const [statusMsg, setStatusMsg] = useState<string>('');

    const answerRef    = useRef<HTMLDivElement>(null);
    const isRunningRef = useRef(false);

    useEffect(() => {
        if (answerRef.current && answer) {
            answerRef.current.scrollTop = answerRef.current.scrollHeight;
        }
    }, [answer]);

    const handleReset = () => {
        setQuestion(''); setAnswer(''); setCitations([]);
        setQueryTime(null); setError(''); setIsFallback(false); setStatusMsg('');
    };

    const runSearch = useCallback(async (q: string) => {
        if (!q.trim() || isRunningRef.current) return;
        isRunningRef.current = true;

        setAnswer(''); setCitations([]); setQueryTime(null);
        setLoading(true); setError(''); setIsFallback(false); setStatusMsg('');

        const controller = new AbortController();

        try {
            const jwt = await getToken({ skipCache: true });
            if (!jwt) {
                setError('Authentication required. Please sign in again.');
                setLoading(false);
                isRunningRef.current = false;
                return;
            }

            await fetchEventSource('http://127.0.0.1:8000/api/research', {
                signal: controller.signal,
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${jwt}` },
                body: JSON.stringify({ question: q, max_results: 5 }),
                openWhenHidden: true,

                async onopen(response) {
                    if (response.ok) return;
                    if (response.status === 403 || response.status === 401)
                        throw new FatalError('Session expired. Please refresh and sign in again.');
                    if (response.status === 429)
                        throw new FatalError('Too many requests. Please wait a moment and try again.');
                    throw new FatalError(`Server error (${response.status}). Please try again.`);
                },

                onmessage(ev) {
                    try {
                        const data = JSON.parse(ev.data);
                        if (data.type === 'status')        setStatusMsg(data.content);
                        else if (data.type === 'answer')   { setStatusMsg(''); setAnswer(prev => prev + data.content); }
                        else if (data.type === 'fallback') setIsFallback(true);
                        else if (data.type === 'citations') setCitations(data.content);
                        else if (data.type === 'error')    setError(data.content);
                        else if (data.type === 'done')     { setLoading(false); if (data.query_time_ms) setQueryTime(data.query_time_ms); }
                    } catch {}
                },

                onclose() { setLoading(false); },

                onerror(err) {
                    if (err instanceof FatalError) throw err;
                    throw new FatalError(err instanceof Error ? err.message : 'Connection lost. Please try again.');
                },
            });

        } catch (err: any) {
            controller.abort();
            setLoading(false);
            setError(err instanceof Error ? err.message : 'Unknown error. Please try again.');
        } finally {
            isRunningRef.current = false;
        }
    }, [getToken]);

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        await runSearch(question);
    }

    return (
        <div className="flex flex-col lg:flex-row gap-6 h-full">
            <div className="flex-1 flex flex-col">
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6 flex flex-col flex-1">

                    <div className="flex justify-between items-center mb-4">
                        <div>
                            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                                Medical Research
                            </h2>
                            <p className="text-xs text-gray-400 mt-0.5">PubMed 36M+ · FDA · Ask in any language</p>
                        </div>
                        {(answer || question) && (
                            <button
                                onClick={handleReset}
                                className="text-sm text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                            >
                                New search
                            </button>
                        )}
                    </div>

                    {error && !loading && (
                        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg border border-red-100 dark:border-red-800 text-sm">
                            {error}
                        </div>
                    )}

                    <div ref={answerRef} className="flex-1 overflow-y-auto mb-4 min-h-[300px] max-h-[500px]">
                        {!answer && !loading && (
                            <div className="text-center py-12">
                                <p className="text-sm text-gray-400 dark:text-gray-500 mb-6">
                                    Ask a clinical question — answers grounded in PubMed literature and FDA drug data.
                                </p>
                                <div className="space-y-2">
                                    <p className="text-xs text-gray-300 dark:text-gray-600 uppercase tracking-widest">Try these</p>
                                    <div className="flex flex-wrap justify-center gap-2">
                                        {defaultSuggestions.map((s, i) => (
                                            <button
                                                key={i}
                                                onClick={() => { setQuestion(s); runSearch(s); }}
                                                disabled={loading}
                                                className="px-3 py-1.5 text-xs bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-full border border-gray-200 dark:border-gray-600 hover:border-orange-300 hover:text-orange-600 dark:hover:text-orange-400 disabled:opacity-50 transition-colors"
                                            >
                                                {s}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}

                        {loading && !answer && statusMsg && (
                            <div className="flex items-center gap-3 py-8 text-gray-400">
                                <div className="w-4 h-4 border-2 border-gray-200 border-t-orange-400 rounded-full animate-spin flex-shrink-0" />
                                <span className="text-sm">{statusMsg}</span>
                            </div>
                        )}

                        {(answer || loading) && (
                            <div className="prose prose-gray dark:prose-invert max-w-none prose-sm prose-headings:font-semibold prose-h2:text-base">
                                {isFallback && !loading && <FallbackBanner />}
                                <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{answer}</ReactMarkdown>
                                {loading && answer && (
                                    <span className="inline-block w-1.5 h-4 rounded-sm animate-pulse ml-0.5" style={{ background: ACCENT }} />
                                )}
                                {!loading && answer && !error && (
                                    <FeedbackBar query={question} response={answer} category="research" />
                                )}
                            </div>
                        )}
                    </div>

                    {queryTime && (
                        <p className="text-xs text-gray-300 dark:text-gray-600 mb-2">
                            Query time: {(queryTime / 1000).toFixed(2)}s
                        </p>
                    )}

                    <form onSubmit={handleSubmit} className="flex gap-2">
                        <input
                            type="text"
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            placeholder="Ask a clinical question in any language..."
                            className="flex-1 px-4 py-2.5 text-sm border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 dark:bg-gray-700 dark:text-white transition-shadow"
                            style={{ '--tw-ring-color': ACCENT } as any}
                            disabled={loading}
                        />
                        <button
                            type="submit"
                            disabled={loading || !question.trim()}
                            className="px-5 py-2.5 text-white text-sm font-medium rounded-lg transition-opacity disabled:opacity-50"
                            style={{ background: ACCENT }}
                        >
                            {loading ? (
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            ) : 'Search'}
                        </button>
                    </form>

                    <p className="text-xs text-gray-300 dark:text-gray-600 mt-3 text-center">
                        ⚠️ For reference only. Not a substitute for professional clinical judgment.
                    </p>
                </div>
            </div>

            <div className="lg:w-96">
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6 h-full max-h-[700px] overflow-hidden">
                    <CitationPanel citations={citations} isLoading={loading && citations.length === 0} />
                </div>
            </div>
        </div>
    );
}

export default function Research() {
    return (
        <main className="min-h-screen bg-gray-50 dark:from-gray-900 dark:to-gray-800">
            <nav className="bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700">
                <div className="container mx-auto px-4 py-3">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-8">
                            <Link href="/" className="text-base font-bold text-gray-900 dark:text-gray-100 tracking-tight">
                                Vela
                            </Link>
                            <div className="hidden md:flex items-center gap-6 text-sm">
                                <Link href="/research" className="font-medium transition-colors" style={{ color: ACCENT }}>Research</Link>
                                <Link href="/verify"   className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">Verify</Link>
                                <Link href="/explain"  className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">Explain</Link>
                                <Link href="/history"  className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">History</Link>
                            </div>
                        </div>
                        <UserButton showName={true} />
                    </div>
                </div>
            </nav>

            <SignedIn>
                <div className="container mx-auto px-4 py-8">
                    <ResearchForm />
                </div>
            </SignedIn>
            <SignedOut><RedirectToSignIn /></SignedOut>
        </main>
    );
}