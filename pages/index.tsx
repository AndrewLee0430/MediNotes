"use client"

import Link from 'next/link';
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/nextjs';
import { useState, useEffect } from 'react';

export default function Home() {
  // 打字機效果
  const [typedText, setTypedText] = useState('');
  const fullText = 'For Doctors, Pharmacists, Researchers...';
  
  useEffect(() => {
    let index = 0;
    const timer = setInterval(() => {
      if (index <= fullText.length) {
        setTypedText(fullText.slice(0, index));
        index++;
      } else {
        clearInterval(timer);
      }
    }, 50);
    
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-violet-50/20">
      {/* Navigation */}
      <nav className="bg-white/80 backdrop-blur-md shadow-sm sticky top-0 z-50 border-b border-gray-100">
        <div className="container mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="text-3xl">🏥</div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-violet-600 bg-clip-text text-transparent">
                MediNotes
              </h1>
            </div>
            
            {/* Nav Links */}
            <div className="hidden md:flex items-center gap-6">
              <Link href="/research" className="text-gray-600 hover:text-blue-600 transition-colors font-medium">
                Research
              </Link>
              <Link href="/verify" className="text-gray-600 hover:text-blue-600 transition-colors font-medium">
                Verify
              </Link>
              <SignedIn>
                <UserButton />
              </SignedIn>
              <SignedOut>
                <SignInButton mode="modal">
                  <button className="px-5 py-2 bg-gradient-to-r from-blue-600 to-violet-600 text-white rounded-lg hover:shadow-lg hover:scale-105 transition-all duration-200 font-medium">
                    Sign In
                  </button>
                </SignInButton>
              </SignedOut>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section - 左右分欄 */}
      <div className="container mx-auto px-6 py-12 md:py-20">
        <div className="grid lg:grid-cols-2 gap-12 items-center min-h-[calc(100vh-200px)]">
          
          {/* 左側：行動區 (40%) */}
          <div className="space-y-8">
            <div className="space-y-4">
              <h2 className="text-5xl md:text-6xl font-bold text-gray-900 leading-tight">
                Medical Research,
                <br />
                <span className="bg-gradient-to-r from-blue-600 via-violet-600 to-purple-600 bg-clip-text text-transparent">
                  Simplified.
                </span>
              </h2>
              
              <p className="text-xl text-gray-600 font-light">
                Research, Verify, Document.
                <br />
                <span className="text-blue-600 font-medium">One seamless flow.</span>
              </p>
              
              {/* 打字機效果 */}
              <p className="text-lg text-gray-500 italic h-8">
                {typedText}<span className="animate-pulse">|</span>
              </p>
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4">
              <SignedOut>
                <SignInButton mode="modal">
                  <button className="group px-8 py-4 bg-gradient-to-r from-blue-600 to-violet-600 text-white rounded-xl font-semibold text-lg shadow-lg hover:shadow-2xl hover:scale-105 transition-all duration-300 flex items-center justify-center gap-2">
                    免費開始
                    <span className="group-hover:translate-x-1 transition-transform">→</span>
                  </button>
                </SignInButton>
              </SignedOut>
              
              <SignedIn>
                <Link href="/research">
                  <button className="group px-8 py-4 bg-gradient-to-r from-blue-600 to-violet-600 text-white rounded-xl font-semibold text-lg shadow-lg hover:shadow-2xl hover:scale-105 transition-all duration-300 flex items-center justify-center gap-2">
                    開始使用
                    <span className="group-hover:translate-x-1 transition-transform">→</span>
                  </button>
                </Link>
              </SignedIn>
              
              <button className="px-8 py-4 border-2 border-gray-300 text-gray-700 rounded-xl font-semibold text-lg hover:border-blue-600 hover:text-blue-600 hover:bg-blue-50 transition-all duration-200">
                了解更多
              </button>
            </div>

            {/* Trust Badge */}
            <div className="flex items-center gap-3 text-sm text-gray-500">
              <div className="flex -space-x-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 border-2 border-white"></div>
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-400 to-violet-600 border-2 border-white"></div>
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-400 to-purple-600 border-2 border-white"></div>
              </div>
              <span>Trusted by healthcare professionals worldwide</span>
            </div>
          </div>

          {/* 右側：價值展示區 (60%) - Bento Grid */}
          <div className="space-y-6">
            
            {/* 主要區塊：可視化工作流 */}
            <div className="relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-600 to-violet-600 rounded-3xl blur opacity-20 group-hover:opacity-30 transition duration-500"></div>
              <div className="relative bg-white/80 backdrop-blur-md rounded-3xl p-8 shadow-xl border border-gray-100">
                <div className="flex items-center justify-between gap-4">
                  
                  {/* Research */}
                  <div className="flex-1 group/card">
                    <div className="bg-gradient-to-br from-cyan-50 to-blue-50 rounded-2xl p-6 hover:shadow-lg hover:-translate-y-1 transition-all duration-300 border border-cyan-100">
                      <div className="text-4xl mb-3">🔬</div>
                      <h3 className="font-bold text-gray-900 mb-1">Research</h3>
                      <p className="text-xs text-gray-600">PubMed 36M+</p>
                    </div>
                  </div>

                  {/* 動態箭頭 */}
                  <div className="flex-shrink-0">
                    <div className="text-2xl text-blue-500 animate-pulse">→</div>
                  </div>

                  {/* Verify */}
                  <div className="flex-1 group/card">
                    <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl p-6 hover:shadow-lg hover:-translate-y-1 transition-all duration-300 border border-green-100">
                      <div className="text-4xl mb-3">💊</div>
                      <h3 className="font-bold text-gray-900 mb-1">Verify</h3>
                      <p className="text-xs text-gray-600">FDA Official</p>
                    </div>
                  </div>

                  {/* 動態箭頭 */}
                  <div className="flex-shrink-0">
                    <div className="text-2xl text-violet-500 animate-pulse">→</div>
                  </div>

                  {/* Document */}
                  <div className="flex-1 group/card">
                    <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-2xl p-6 hover:shadow-lg hover:-translate-y-1 transition-all duration-300 border border-purple-100">
                      <div className="text-4xl mb-3">📄</div>
                      <h3 className="font-bold text-gray-900 mb-1">Document</h3>
                      <p className="text-xs text-gray-600">AI-Powered</p>
                    </div>
                  </div>

                </div>
              </div>
            </div>

            {/* 次要區塊：三大優勢 */}
            <div className="grid grid-cols-3 gap-4">
              
              {/* Privacy */}
              <div className="group/pillar relative">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-green-400 to-emerald-400 rounded-2xl blur opacity-0 group-hover/pillar:opacity-20 transition duration-500"></div>
                <div className="relative bg-white/80 backdrop-blur-md rounded-2xl p-6 hover:shadow-lg hover:-translate-y-2 transition-all duration-300 border border-gray-100">
                  <div className="text-3xl mb-3">🔒</div>
                  <h4 className="font-bold text-gray-900 text-sm mb-2">Privacy First</h4>
                  <p className="text-xs text-gray-600 opacity-0 group-hover/pillar:opacity-100 transition-opacity duration-300">
                    No PHI stored
                  </p>
                </div>
              </div>

              {/* Trusted */}
              <div className="group/pillar relative">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-400 to-cyan-400 rounded-2xl blur opacity-0 group-hover/pillar:opacity-20 transition duration-500"></div>
                <div className="relative bg-white/80 backdrop-blur-md rounded-2xl p-6 hover:shadow-lg hover:-translate-y-2 transition-all duration-300 border border-gray-100">
                  <div className="text-3xl mb-3">✅</div>
                  <h4 className="font-bold text-gray-900 text-sm mb-2">Trusted Source</h4>
                  <p className="text-xs text-gray-600 opacity-0 group-hover/pillar:opacity-100 transition-opacity duration-300">
                    PubMed & FDA
                  </p>
                </div>
              </div>

              {/* Smarter */}
              <div className="group/pillar relative">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-violet-400 to-purple-400 rounded-2xl blur opacity-0 group-hover/pillar:opacity-20 transition duration-500"></div>
                <div className="relative bg-white/80 backdrop-blur-md rounded-2xl p-6 hover:shadow-lg hover:-translate-y-2 transition-all duration-300 border border-gray-100">
                  <div className="text-3xl mb-3">🚀</div>
                  <h4 className="font-bold text-gray-900 text-sm mb-2">Smarter AI</h4>
                  <p className="text-xs text-gray-600 opacity-0 group-hover/pillar:opacity-100 transition-opacity duration-300">
                    Feedback Loop
                  </p>
                </div>
              </div>

            </div>
          </div>

        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white/50 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-8">
          <p className="text-center text-sm text-gray-500">
            Trusted by HIPAA-compliant AWS infrastructure • Privacy-first architecture
          </p>
        </div>
      </footer>
    </div>
  );
}