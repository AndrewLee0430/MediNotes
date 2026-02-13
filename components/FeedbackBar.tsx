"use client"

import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';

interface FeedbackBarProps {
    query: string;
    response: string;
    category: 'research' | 'verify';
}

export default function FeedbackBar({ query, response, category }: FeedbackBarProps) {
    const { getToken } = useAuth();
    const [status, setStatus] = useState<'idle' | 'liked' | 'disliked' | 'edited'>('idle');
    const [isEditing, setIsEditing] = useState(false);
    const [editedResponse, setEditedResponse] = useState(response);
    const [loading, setLoading] = useState(false);

    const sendFeedback = async (rating: number, text?: string) => {
        setLoading(true);
        try {
            const token = await getToken();
            const res = await fetch('http://127.0.0.1:8000/api/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    query,
                    response, // 原始回答
                    rating,
                    feedback_text: text || null, // 修正後的內容或評論
                    category
                })
            });
            
            if (!res.ok) throw new Error('Feedback failed');
            
        } catch (err) {
            console.error('Feedback failed:', err);
            // 失敗時回復狀態 (UX 選擇：也可以靜默失敗)
            setStatus('idle');
        } finally {
            setLoading(false);
        }
    };

    const handleLike = () => {
        if (status === 'liked') return;
        setStatus('liked');
        sendFeedback(1);
    };

    const handleDislike = () => {
        if (status === 'disliked') return;
        setStatus('disliked');
        sendFeedback(-1);
    };

    const handleCopy = () => {
        navigator.clipboard.writeText(response);
        // 這裡可以加個簡單的 Toast，目前先用 console 代替
        console.log('已複製到剪貼簿');
    };

    const handleSaveEdit = () => {
        setIsEditing(false);
        setStatus('edited');
        // 編輯視為 "Strong Like" (Rating 2)，因為使用者投入了心力修正
        sendFeedback(2, editedResponse); 
        alert("感謝您的修正！這將幫助 AI 學習更準確的醫學知識。");
    };

    if (isEditing) {
        return (
            <div className="mt-4 border-t border-gray-100 dark:border-gray-700 pt-4 animate-fadeIn">
                <label className="block text-xs font-semibold text-gray-500 mb-2">修正 AI 的回答：</label>
                <textarea
                    value={editedResponse}
                    onChange={(e) => setEditedResponse(e.target.value)}
                    className="w-full p-3 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    rows={6}
                />
                <div className="flex justify-end gap-2 mt-3">
                    <button 
                        onClick={() => setIsEditing(false)}
                        className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700 rounded-lg transition-colors"
                        disabled={loading}
                    >
                        取消
                    </button>
                    <button 
                        onClick={handleSaveEdit}
                        className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                        disabled={loading}
                    >
                        {loading ? '儲存中...' : '確認修正'}
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-wrap items-center gap-2 mt-6 pt-4 border-t border-gray-100 dark:border-gray-700 text-sm text-gray-500 select-none">
            <span className="text-xs mr-2">此回答有幫助嗎？</span>
            
            <button 
                onClick={handleLike}
                disabled={status !== 'idle'}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg transition-all ${
                    status === 'liked' 
                        ? 'text-green-700 bg-green-100 dark:bg-green-900/30 dark:text-green-400 font-medium' 
                        : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400'
                } ${status !== 'idle' && status !== 'liked' ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
                👍 有幫助
            </button>

            <button 
                onClick={handleDislike}
                disabled={status !== 'idle'}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg transition-all ${
                    status === 'disliked' 
                        ? 'text-red-700 bg-red-100 dark:bg-red-900/30 dark:text-red-400 font-medium' 
                        : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400'
                } ${status !== 'idle' && status !== 'disliked' ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
                👎 有錯誤
            </button>

            <div className="w-px h-4 bg-gray-300 dark:bg-gray-600 mx-2 hidden sm:block"></div>

            <button 
                onClick={() => setIsEditing(true)}
                disabled={status === 'edited'}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg transition-all ${
                    status === 'edited'
                        ? 'text-blue-700 bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400 font-medium'
                        : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400'
                }`}
            >
                📝 {status === 'edited' ? '已修正' : '修改'}
            </button>

            <button 
                onClick={handleCopy}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 transition-colors"
            >
                📋 複製
            </button>
        </div>
    );
}