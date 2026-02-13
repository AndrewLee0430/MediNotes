"""
Answer Generator - 答案生成器
使用 LLM 基於檢索到的文件生成答案，並支援串流輸出
"""

import json
from typing import List, AsyncGenerator
from openai import OpenAI
from api.models.schemas import (
    RetrievedDocument,
    Citation,
    StreamEvent,
    StreamEventType
)


class AnswerGenerator:
    """
    答案生成器
    
    功能：
    1. 基於檢索到的文件生成答案
    2. 支援串流輸出（SSE）
    3. 自動標註引用來源
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        初始化生成器
        
        Args:
            model: OpenAI 模型名稱
        """
        self.model = model
        self.client = OpenAI()
    
    async def generate_stream(
        self,
        question: str,
        documents: List[RetrievedDocument]
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        串流生成答案
        
        Args:
            question: 使用者問題
            documents: 檢索到的文件
            
        Yields:
            StreamEvent - 包含答案片段、引用或錯誤
        """
        if not documents:
            yield StreamEvent(
                type=StreamEventType.ERROR,
                content="未找到相關資料，請嘗試調整問題或查詢關鍵字。"
            )
            yield StreamEvent(type=StreamEventType.DONE)
            return
        
        # 準備 context
        context = self._build_context(documents)
        
        # 準備 prompt
        system_prompt = self._get_system_prompt()
        user_prompt = self._build_user_prompt(question, context)
        
        # 生成 citations
        citations = [
            doc.to_citation(citation_id=i+1) 
            for i, doc in enumerate(documents)
        ]
        
        try:
            # 串流生成答案
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=True,
                temperature=0.3,  # 降低隨機性，提高準確性
                max_tokens=2000
            )
            
            # 逐步輸出答案
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield StreamEvent(
                        type=StreamEventType.ANSWER,
                        content=chunk.choices[0].delta.content
                    )
            
            # 輸出 citations
            yield StreamEvent(
                type=StreamEventType.CITATIONS,
                content=citations
            )
            
            # 完成
            yield StreamEvent(type=StreamEventType.DONE)
            
        except Exception as e:
            yield StreamEvent(
                type=StreamEventType.ERROR,
                content=f"生成答案時發生錯誤: {str(e)}"
            )
            yield StreamEvent(type=StreamEventType.DONE)
    
    def _build_context(self, documents: List[RetrievedDocument]) -> str:
        """
        將文件列表轉換為 context 字串
        
        格式:
        [1] {title}
        {content}
        
        [2] {title}
        {content}
        ...
        """
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            # 截斷過長的內容
            content = doc.content[:2000] + "..." if len(doc.content) > 2000 else doc.content
            
            context_parts.append(f"[{i}] {doc.title}\n{content}")
        
        return "\n\n".join(context_parts)
    
    def _get_system_prompt(self) -> str:
        """
        系統 prompt - 定義 AI 助手的角色和行為
        """
        return """You are a medical AI assistant designed to help healthcare professionals.

Your responsibilities:
1. Provide accurate, evidence-based medical information
2. ALWAYS cite sources using [1], [2], etc. format
3. Be concise but comprehensive
4. Acknowledge uncertainty when evidence is limited
5. Use professional medical terminology
6. Respond in Traditional Chinese (繁體中文)

Citation rules:
- Every factual claim MUST be cited
- Use [1], [2] format corresponding to the context documents
- Multiple citations can be combined: [1][2]
- If information is not in the context, clearly state that

Important:
- Do NOT provide treatment recommendations without emphasizing consultation with healthcare providers
- Do NOT make claims beyond what's supported by the provided context
- If asked about specific patient cases, remind that individual medical advice requires clinical evaluation"""
    
    def _build_user_prompt(self, question: str, context: str) -> str:
        """
        使用者 prompt - 包含問題和 context
        """
        return f"""Context (reference documents):
{context}

Question: {question}

Instructions:
1. Answer the question based ONLY on the provided context
2. Cite sources using [1], [2], etc.
3. If the context doesn't contain enough information, clearly state what's missing
4. Be specific and precise
5. Use Traditional Chinese (繁體中文)

Answer:"""
    
    async def generate_non_stream(
        self,
        question: str,
        documents: List[RetrievedDocument]
    ) -> tuple[str, List[Citation]]:
        """
        非串流生成答案（用於需要完整答案的場景）
        
        Args:
            question: 使用者問題
            documents: 檢索到的文件
            
        Returns:
            (answer, citations) tuple
        """
        if not documents:
            return "未找到相關資料，請嘗試調整問題或查詢關鍵字。", []
        
        context = self._build_context(documents)
        system_prompt = self._get_system_prompt()
        user_prompt = self._build_user_prompt(question, context)
        
        citations = [
            doc.to_citation(citation_id=i+1) 
            for i, doc in enumerate(documents)
        ]
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            answer = completion.choices[0].message.content
            return answer, citations
            
        except Exception as e:
            return f"生成答案時發生錯誤: {str(e)}", citations