"use client"

import { useState, useEffect } from 'react';
import { useAuth, SignedIn, SignedOut, RedirectToSignIn, UserButton } from '@clerk/nextjs';
import Link from 'next/link';

interface HistoryItem {
    id: number;
    user_id: string;
    session_type: string;
    question: string;
    answer: string;
    created_at: string;
}

interface DrugInteraction {
    drug_pair: [string, string];
    severity: string;
    description: string;
    clinical_recommendation: string;
    source: string;
}

function HistoryList() {
    const { getToken } = useAuth();
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedId, setExpandedId] = useState<number | null>(null);
    
    // ✅ 新增：存储 Verify 详细数据
    const [verifyDetails, setVerifyDetails] = useState<{[key: number]: {
        interactions: DrugInteraction[];
        risk_level: string;
        loading: boolean;
    }}>({});
    
    useEffect(() => {
        loadHistory();
    }, []);
    
    async function loadHistory() {
        try {
            const token = await getToken();
            const res = await fetch('http://127.0.0.1:8000/api/history', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!res.ok) throw new Error('Failed to load history');
            
            const data = await res.json();
            setHistory(data);
        } catch (err) {
            console.error('History load error:', err);
        } finally {
            setLoading(false);
        }
    }
    
    // ✅ 新增：点击 Verify 记录时重新查询详细数据
    async function fetchVerifyDetails(item: HistoryItem) {
        // 从 question 中提取药物列表
        // 格式："Drugs: Warfarin, Aspirin"
        const match = item.question.match(/Drugs:\s*(.+)/);
        if (!match) return;
        
        const drugsStr = match[1];
        const drugs = drugsStr.split(',').map(d => d.trim());
        
        // 设置加载状态
        setVerifyDetails(prev => ({
            ...prev,
            [item.id]: { interactions: [], risk_level: 'Unknown', loading: true }
        }));
        
        try {
            const token = await getToken();
            const res = await fetch('http://127.0.0.1:8000/api/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ drugs, patient_context: null })
            });
            
            if (!res.ok) throw new Error('Failed to fetch verify details');
            
            const data = await res.json();
            setVerifyDetails(prev => ({
                ...prev,
                [item.id]: {
                    interactions: data.interactions || [],
                    risk_level: data.risk_level || 'Unknown',
                    loading: false
                }
            }));
        } catch (err) {
            console.error('Verify details error:', err);
            setVerifyDetails(prev => ({
                ...prev,
                [item.id]: { interactions: [], risk_level: 'Unknown', loading: false }
            }));
        }
    }
    
    function handleToggle(item: HistoryItem) {
        if (expandedId === item.id) {
            setExpandedId(null);
        } else {
            setExpandedId(item.id);
            // ✅ 如果是 Verify 类型且未加载详细数据，则重新查询
            if (item.session_type === 'verify' && !verifyDetails[item.id]) {
                fetchVerifyDetails(item);
            }
        }
    }
    
    const getIcon = (type: string) => {
        switch (type) {
            case 'research': return '🔬';
            case 'verify': return '💊';
            default: return '📝';
        }
    };
    
    const getTypeLabel = (type: string) => {
        switch (type) {
            case 'research': return 'RESEARCH';
            case 'verify': return 'VERIFY';
            default: return type.toUpperCase();
        }
    };
    
    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'Critical': return 'bg-red-50 border-red-300 text-red-800';
            case 'Major': return 'bg-orange-50 border-orange-300 text-orange-800';
            case 'Moderate': return 'bg-yellow-50 border-yellow-300 text-yellow-800';
            case 'Minor': return 'bg-blue-50 border-blue-300 text-blue-800';
            default: return 'bg-gray-50 border-gray-300 text-gray-800';
        }
    };
    
    if (loading) {
        return (
            <div className="text-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-4 text-gray-500">載入中...</p>
            </div>
        );
    }
    
    if (history.length === 0) {
        return (
            <div className="text-center py-12">
                <p className="text-gray-500">尚無查詢紀錄</p>
                <Link 
                    href="/research"
                    className="mt-4 inline-block text-blue-600 hover:text-blue-700"
                >
                    開始第一次查詢 →
                </Link>
            </div>
        );
    }
    
    return (
        <div className="space-y-4">
            {history.map(item => (
                <div 
                    key={item.id}
                    className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden"
                >
                    {/* Header - 可点击展开 */}
                    <button
                        onClick={() => handleToggle(item)}
                        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                    >
                        <div className="flex items-center gap-4">
                            <span className="text-3xl">{getIcon(item.session_type)}</span>
                            <div className="text-left">
                                <h3 className="font-medium text-gray-900 dark:text-gray-100">
                                    {item.question.length > 60 
                                        ? item.question.slice(0, 60) + '...' 
                                        : item.question}
                                </h3>
                                <p className="text-sm text-gray-500 dark:text-gray-400">
                                    {new Date(item.created_at).toLocaleString('zh-TW')} • {getTypeLabel(item.session_type)}
                                </p>
                            </div>
                        </div>
                        
                        <svg 
                            className={`w-5 h-5 text-gray-400 transition-transform ${expandedId === item.id ? 'rotate-180' : ''}`}
                            fill="none" 
                            stroke="currentColor" 
                            viewBox="0 0 24 24"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                    </button>
                    
                    {/* Expanded Content */}
                    {expandedId === item.id && (
                        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
                            {/* Research 类型 - 显示完整答案 */}
                            {item.session_type === 'research' && (
                                <div className="prose prose-blue dark:prose-invert max-w-none">
                                    <p className="whitespace-pre-wrap">{item.answer}</p>
                                </div>
                            )}
                            
                            {/* Verify 类型 - 显示详细交互作用 */}
                            {item.session_type === 'verify' && (
                                <div className="space-y-4">
                                    {/* 总结 */}
                                    <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                                        <p className="text-gray-700 dark:text-gray-300">{item.answer}</p>
                                    </div>
                                    
                                    {/* 详细交互作用 */}
                                    {verifyDetails[item.id]?.loading && (
                                        <div className="text-center py-8">
                                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                                            <p className="mt-2 text-sm text-gray-500">載入詳細資訊...</p>
                                        </div>
                                    )}
                                    
                                    {!verifyDetails[item.id]?.loading && verifyDetails[item.id]?.interactions && verifyDetails[item.id].interactions.length > 0 && (
                                        <div>
                                            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">
                                                詳細交互作用 ({verifyDetails[item.id].interactions.length})
                                            </h4>
                                            
                                            <div className="space-y-3">
                                                {verifyDetails[item.id].interactions.map((interaction, idx) => (
                                                    <div 
                                                        key={idx}
                                                        className={`border-l-4 rounded-lg p-4 ${getSeverityColor(interaction.severity)}`}
                                                    >
                                                        <div className="flex justify-between items-start mb-2">
                                                            <h5 className="font-semibold">
                                                                {interaction.drug_pair[0]} ↔ {interaction.drug_pair[1]}
                                                            </h5>
                                                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                                                                interaction.severity === 'Critical' ? 'bg-red-200 text-red-900' :
                                                                interaction.severity === 'Major' ? 'bg-orange-200 text-orange-900' :
                                                                interaction.severity === 'Moderate' ? 'bg-yellow-200 text-yellow-900' :
                                                                'bg-blue-200 text-blue-900'
                                                            }`}>
                                                                {interaction.severity}
                                                            </span>
                                                        </div>
                                                        
                                                        <div className="space-y-2 text-sm">
                                                            <p className="text-gray-700 dark:text-gray-300">
                                                                {interaction.description}
                                                            </p>
                                                            
                                                            {interaction.clinical_recommendation && (
                                                                <p className="text-gray-600 dark:text-gray-400">
                                                                    💡 {interaction.clinical_recommendation}
                                                                </p>
                                                            )}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}

export default function History() {
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
                                    className="text-gray-600 dark:text-gray-400 hover:text-blue-600"
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
                                    className="text-blue-600 dark:text-blue-400 font-medium"
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
                <div className="container mx-auto px-4 py-8 max-w-4xl">
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-6 flex items-center gap-2">
                        📚 查詢歷史紀錄
                    </h1>
                    <HistoryList />
                </div>
            </SignedIn>
            
            <SignedOut>
                <RedirectToSignIn />
            </SignedOut>
        </main>
    );
}