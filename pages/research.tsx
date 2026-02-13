"use client"

import { useState, FormEvent, useRef, useEffect } from 'react';
import { useAuth, SignedIn, SignedOut, RedirectToSignIn, UserButton } from '@clerk/nextjs';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import Link from 'next/link';
import CitationPanel, { Citation } from '../components/CitationPanel';
import FeedbackBar from '../components/FeedbackBar';

// ✅ 扩展常见问题建议（增加到 10 个）
const defaultSuggestions = [
    "Metformin 的常見副作用有哪些？",
    "Warfarin 和哪些藥物有交互作用？",
    "老年患者使用 NSAIDs 需要注意什麼？",
    "糖尿病患者的用藥注意事項？",
    "高血壓藥物 ACE inhibitors 的禁忌症？",
    "Statin 類藥物的肌肉副作用如何處理？",
    "抗凝血劑 DOACs 與傳統 Warfarin 的比較？",
    "孕婦使用抗生素的安全性？",
    "Beta-blocker 在心衰竭的使用時機？",
    "Proton pump inhibitors 長期使用的風險？",
];

function ResearchForm() {
    const { getToken } = useAuth();
    
    // 查询状态
    const [question, setQuestion] = useState('');
    const [answer, setAnswer] = useState('');
    const [citations, setCitations] = useState<Citation[]>([]);
    const [loading, setLoading] = useState(false);
    const [queryTime, setQueryTime] = useState<number | null>(null);
    const [error, setError] = useState<string>('');
    
    // 自动滚动
    const answerRef = useRef<HTMLDivElement>(null);
    
    useEffect(() => {
        if (answerRef.current && answer) {
            answerRef.current.scrollTop = answerRef.current.scrollHeight;
        }
    }, [answer]);
    
    // ✅ 新增：Reset 功能
    const handleReset = () => {
        setQuestion('');
        setAnswer('');
        setCitations([]);
        setQueryTime(null);
        setError('');
    };
    
    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        if (!question.trim()) return;
        
        setAnswer('');
        setCitations([]);
        setQueryTime(null);
        setLoading(true);
        setError('');
        
        try {
            const jwt = await getToken();
            
            if (!jwt) {
                setError('❌ 認證失敗，請重新登入');
                setLoading(false);
                return;
            }
            
            const controller = new AbortController();
            
            await fetchEventSource('http://127.0.0.1:8000/api/research', {
                signal: controller.signal,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${jwt}`,
                },
                body: JSON.stringify({
                    question: question,
                    max_results: 5
                }),
                
                async onopen(response) {
                    if (response.ok) {
                        return;
                    }
                    
                    if (response.status === 403) {
                        throw new Error('❌ 認證失敗 (403)，請重新整理頁面並登入');
                    } else if (response.status === 401) {
                        throw new Error('❌ 未授權 (401)，請重新登入');
                    } else if (response.status >= 400) {
                        throw new Error(`❌ 伺服器錯誤 (${response.status})`);
                    }
                },
                
                onmessage(ev) {
                    try {
                        const data = JSON.parse(ev.data);
                        
                        if (data.type === 'answer') {
                            setAnswer(prev => prev + data.content);
                        } else if (data.type === 'citations') {
                            setCitations(data.content);
                        } else if (data.type === 'error') {
                            setError(data.content);
                            setAnswer(prev => prev + `\n\n❌ 錯誤: ${data.content}`);
                        } else if (data.type === 'done') {
                            setLoading(false);
                            if (data.query_time_ms) {
                                setQueryTime(data.query_time_ms);
                            }
                        }
                    } catch (e) {
                        console.error('Parse error:', e);
                    }
                },
                
                onclose() {
                    setLoading(false);
                },
                
                onerror(err) {
                    console.error('SSE error:', err);
                    controller.abort();
                    setLoading(false);
                    
                    if (err instanceof Error) {
                        setError(err.message);
                        setAnswer(prev => prev + `\n\n${err.message}`);
                    } else {
                        setError('連線錯誤，請稍後再試');
                        setAnswer(prev => prev + '\n\n❌ 連線錯誤，請稍後再試');
                    }
                    
                    throw err;
                },
            });
        } catch (err: any) {
            console.error('Request error:', err);
            setLoading(false);
            const errorMsg = err.message || '未知錯誤';
            setError(errorMsg);
            setAnswer(errorMsg);
        }
    }
    
    function handleSuggestionClick(suggestion: string) {
        setQuestion(suggestion);
    }
    
    return (
        <div className="flex flex-col lg:flex-row gap-6 h-full">
            {/* 左侧：对话区 */}
            <div className="flex-1 flex flex-col">
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 flex flex-col flex-1">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                            💬 醫學研究助手
                        </h2>
                        
                        {/* ✅ 新增：Reset 按钮 */}
                        {(answer || question) && (
                            <button
                                onClick={handleReset}
                                className="text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors flex items-center gap-1"
                            >
                                🔄 重新查詢
                            </button>
                        )}
                    </div>
                    
                    {/* 错误提示 */}
                    {error && !loading && (
                        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg border border-red-200 dark:border-red-800">
                            {error}
                        </div>
                    )}
                    
                    {/* 答案显示区 */}
                    <div 
                        ref={answerRef}
                        className="flex-1 overflow-y-auto mb-4 min-h-[300px] max-h-[500px]"
                    >
                        {!answer && !loading && (
                            <div className="text-center py-12">
                                <p className="text-gray-500 dark:text-gray-400 mb-6">
                                    輸入您的醫學問題，我會根據 PubMed 文獻和 FDA 藥品資料為您解答
                                </p>
                                
                                {/* 建议问题 */}
                                <div className="space-y-2">
                                    <p className="text-sm text-gray-400 dark:text-gray-500">試試這些問題：</p>
                                    <div className="flex flex-wrap justify-center gap-2">
                                        {defaultSuggestions.map((suggestion, i) => (
                                            <button
                                                key={i}
                                                onClick={() => handleSuggestionClick(suggestion)}
                                                className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 
                                                         text-gray-700 dark:text-gray-300 rounded-full
                                                         hover:bg-blue-100 dark:hover:bg-blue-900 
                                                         hover:text-blue-700 dark:hover:text-blue-300
                                                         transition-colors"
                                            >
                                                {suggestion}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}
                        
                        {(answer || loading) && (
                            <div className="prose prose-blue dark:prose-invert max-w-none">
                                <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                                    {answer}
                                </ReactMarkdown>
                                {loading && (
                                    <span className="inline-block w-2 h-4 bg-blue-500 animate-pulse ml-1"></span>
                                )}
                                
                                {/* Feedback Bar */}
                                {!loading && answer && !error && (
                                    <FeedbackBar 
                                        query={question} 
                                        response={answer} 
                                        category="research" 
                                    />
                                )}
                            </div>
                        )}
                    </div>
                    
                    {/* 查询时间 */}
                    {queryTime && (
                        <div className="text-xs text-gray-400 dark:text-gray-500 mb-2">
                            查詢耗時: {(queryTime / 1000).toFixed(2)} 秒
                        </div>
                    )}
                    
                    {/* 输入区 */}
                    <form onSubmit={handleSubmit} className="flex gap-2">
                        <input
                            type="text"
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            placeholder="輸入您的醫學問題..."
                            className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 
                                     rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent 
                                     dark:bg-gray-700 dark:text-white"
                            disabled={loading}
                        />
                        <button
                            type="submit"
                            disabled={loading || !question.trim()}
                            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400
                                     text-white font-medium rounded-lg transition-colors
                                     flex items-center gap-2"
                        >
                            {loading ? (
                                <>
                                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    搜尋中
                                </>
                            ) : (
                                <>
                                    🔍 搜尋
                                </>
                            )}
                        </button>
                    </form>
                    
                    {/* 免责声明 */}
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-3 text-center">
                        ⚠️ 此資訊僅供參考，不構成醫療建議。請諮詢專業醫療人員。
                    </p>
                </div>
            </div>
            
            {/* 右侧：Citation 面板 */}
            <div className="lg:w-96">
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 h-full max-h-[700px] overflow-hidden">
                    <CitationPanel 
                        citations={citations} 
                        isLoading={loading && citations.length === 0}
                    />
                </div>
            </div>
        </div>
    );
}

export default function Research() {
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
                                    className="text-blue-600 dark:text-blue-400 font-medium"
                                >
                                    Research
                                </Link>
                                <Link 
                                    href="/verify" 
                                    className="text-gray-600 dark:text-gray-400 hover:text-blue-600"
                                >
                                    Verify
                                </Link>
                                <Link 
                                    href="/product"
                                    className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                                >
                                    Document
                                </Link>
                                <Link 
                                    href="/history" 
                                    className="text-gray-600 dark:text-gray-400 hover:text-blue-600"
                                >
                                    History
                                </Link>
                            </div>
                        </div>
                        <UserButton showName={true} />
                    </div>
                </div>
            </nav>
            
            {/* Main Content */}
            <SignedIn>
                <div className="container mx-auto px-4 py-8">
                    <ResearchForm />
                </div>
            </SignedIn>
            
            <SignedOut>
                <RedirectToSignIn />
            </SignedOut>
        </main>
    );
}