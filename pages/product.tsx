"use client"

import { useState, FormEvent } from 'react';
import { useAuth, SignedIn, SignedOut, RedirectToSignIn, UserButton } from '@clerk/nextjs';
import DatePicker from 'react-datepicker';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import Link from 'next/link';
import Toast from '../components/Toast';

function ConsultationForm() {
    const { getToken } = useAuth();

    // Form state
    const [visitDate, setVisitDate] = useState<Date | null>(new Date());
    const [notes, setNotes] = useState('');

    // Streaming state
    const [output, setOutput] = useState('');
    const [loading, setLoading] = useState(false);
    
    // Toast state
    const [showToast, setShowToast] = useState(false);

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        setOutput('');
        setLoading(true);

        const jwt = await getToken();
        if (!jwt) {
            setOutput('Authentication required');
            setLoading(false);
            return;
        }

        const controller = new AbortController();
        let buffer = '';

        await fetchEventSource('http://127.0.0.1:8000/api/consultation', {
            signal: controller.signal,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${jwt}`,
            },
            body: JSON.stringify({
                patient_name: '[Patient Name]',
                date_of_visit: visitDate?.toISOString().slice(0, 10) || '[Visit Date]',
                notes: notes,  // ✅ 直接传递 notes，不再组合 patient_context
            }),
            onmessage(ev) {
                buffer += ev.data;
                setOutput(buffer);
            },
            onclose() { 
                setLoading(false); 
            },
            onerror(err) {
                console.error('SSE error:', err);
                controller.abort();
                setLoading(false);
            },
        });
    }

    return (
        <div className="container mx-auto px-4 py-8 max-w-3xl">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-4">
                📋 Consultation Note Generator
            </h1>
            
            <p className="text-gray-600 dark:text-gray-400 mb-6">
                Generate professional consultation summaries, next steps, and patient emails.
                Output uses placeholders that you can customize after downloading.
            </p>

            {/* Privacy Notice */}
            <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
                <div className="flex items-start gap-3">
                    <span className="text-xl">🔒</span>
                    <div>
                        <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                            Privacy-First Design
                        </h3>
                        <p className="text-sm text-blue-800 dark:text-blue-200">
                            This tool uses <strong>[Patient Name]</strong> placeholders to protect patient privacy. 
                            Please do not enter any Protected Health Information (PHI) including real patient names, 
                            medical record numbers, or other identifying information.
                        </p>
                    </div>
                </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
                
                {/* Date of Visit */}
                <div className="space-y-2">
                    <label htmlFor="date" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Date of Visit
                    </label>
                    <DatePicker
                        id="date"
                        selected={visitDate}
                        onChange={(d: Date | null) => setVisitDate(d)}
                        dateFormat="yyyy-MM-dd"
                        placeholderText="Select date"
                        required
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                    />
                </div>

                {/* ✅ 扩大的 Consultation Notes */}
                <div className="space-y-2">
                    <label htmlFor="notes" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Consultation Notes
                    </label>
                    <textarea
                        id="notes"
                        required
                        rows={12}
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                        placeholder="Enter consultation notes here...

Example:
Patient: 65yo male with Type 2 DM, HTN
Chief complaint: Follow-up for diabetes management
Assessment: HbA1c improved from 8.2% to 7.1%
Current medications: Metformin 500mg BID, Lisinopril 10mg daily
Plan: Continue current regimen, recheck labs in 3 months"
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                        Include patient demographics and clinical context directly in your notes. Use de-identified information only.
                    </p>
                </div>

                <button 
                    type="submit" 
                    disabled={loading}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200"
                >
                    {loading ? 'Generating...' : 'Generate Consultation Summary'}
                </button>
            </form>

            {/* Output Section */}
            {output && (
                <section className="mt-8 bg-gray-50 dark:bg-gray-800 rounded-xl shadow-lg p-8">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                            Generated Output
                        </h2>
                        <button
                            onClick={() => {
                                navigator.clipboard.writeText(output);
                                setShowToast(true);
                            }}
                            className="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                        >
                            📋 Copy to Clipboard
                        </button>
                    </div>
                    
                    {/* Reminder about placeholders */}
                    <div className="bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3 mb-4">
                        <p className="text-sm text-yellow-800 dark:text-yellow-200">
                            💡 <strong>Remember:</strong> Replace <code className="bg-yellow-100 dark:bg-yellow-800 px-1 rounded">[Patient Name]</code> with the actual patient name after copying.
                        </p>
                    </div>
                    
                    <div className="markdown-content prose prose-blue dark:prose-invert max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                            {output}
                        </ReactMarkdown>
                    </div>
                </section>
            )}

            {/* Footer with Security Info */}
            <div className="mt-8 text-center text-xs text-gray-500 dark:text-gray-400">
                <p>
                    This tool is for educational and reference purposes only. 
                    Not intended to replace professional medical judgment.
                </p>
                <p className="mt-1">
                    🔒 Protected by authentication, audit logging, and PHI detection
                </p>
            </div>
            
            {/* Toast notification */}
            {showToast && (
                <Toast 
                    message="✓ 已複製到剪貼簿" 
                    onClose={() => setShowToast(false)} 
                />
            )}
        </div>
    );
}

export default function Product() {
    return (
        <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
            {/* Navigation */}
            <nav className="bg-white dark:bg-gray-800 shadow-sm">
                <div className="container mx-auto px-4 py-3">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-6">
                            <Link href="/" className="text-xl font-bold text-gray-800 dark:text-gray-200">
                                🏥 MediNotes
                            </Link>
                            <div className="hidden md:flex items-center gap-4">
                                <Link 
                                    href="/research"
                                    className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                                >
                                    Research
                                </Link>
                                <Link 
                                    href="/verify"
                                    className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                                >
                                    Verify
                                </Link>
                                <Link 
                                    href="/product"
                                    className="text-blue-600 dark:text-blue-400 font-medium"
                                >
                                    Document
                                </Link>
                                <Link 
                                    href="/history"
                                    className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                                >
                                    History
                                </Link>
                            </div>
                        </div>
                        <UserButton showName={true} />
                    </div>
                </div>
            </nav>

            {/* Content */}
            <SignedIn>
                <ConsultationForm />
            </SignedIn>
            
            <SignedOut>
                <RedirectToSignIn />
            </SignedOut>
        </main>
    );
}