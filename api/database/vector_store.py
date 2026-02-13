"""
Vector Store - ChromaDB 操作封裝
處理文件的 embedding 和檢索
"""

import os
from typing import Optional
from openai import OpenAI
import chromadb
from chromadb.config import Settings

from api.models.schemas import (
    RetrievedDocument,
    SourceType,
    CredibilityLevel
)


class VectorStore:
    """ChromaDB 向量資料庫封裝"""
    
    def __init__(
        self,
        persist_directory: str = "data/chroma_db",
        collection_name: str = "medical_knowledge"
    ):
        """
        初始化向量資料庫
        
        Args:
            persist_directory: 資料庫持久化路徑
            collection_name: Collection 名稱
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # 初始化 OpenAI client
        self.openai = OpenAI()
        
        # 初始化 ChromaDB
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 取得或建立 collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Medical knowledge base for MediNotes"}
        )
    
    def _get_embedding(self, text: str) -> list[float]:
        """取得文字的 embedding"""
        response = self.openai.embeddings.create(
            model="text-embedding-3-small",  # 較便宜的版本
            input=text
        )
        return response.data[0].embedding
    
    def _get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """批次取得 embeddings"""
        response = self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        return [item.embedding for item in response.data]
    
    def add_documents(
        self,
        documents: list[dict],
        batch_size: int = 100
    ) -> int:
        """
        新增文件到向量資料庫
        
        Args:
            documents: 文件列表，每個文件需包含:
                - content: 文字內容
                - source_type: 來源類型
                - source_id: 來源 ID
                - title: 標題
                - url: 連結
                - credibility: 可信度
                - year: 年份（可選）
                - authors: 作者（可選）
                - journal: 期刊（可選）
            batch_size: 批次處理大小
            
        Returns:
            新增的文件數量
        """
        total_added = 0
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            ids = []
            texts = []
            metadatas = []
            
            for doc in batch:
                doc_id = f"{doc['source_type']}_{doc['source_id']}_{i}"
                
                ids.append(doc_id)
                texts.append(doc["content"])
                metadatas.append({
                    "source_type": doc["source_type"],
                    "source_id": doc["source_id"],
                    "title": doc["title"],
                    "url": doc["url"],
                    "credibility": doc["credibility"],
                    "year": doc.get("year", ""),
                    "authors": doc.get("authors", ""),
                    "journal": doc.get("journal", "")
                })
            
            # 取得 embeddings
            embeddings = self._get_embeddings_batch(texts)
            
            # 新增到 ChromaDB
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            
            total_added += len(batch)
        
        return total_added
    
    def search(
        self,
        query: str,
        n_results: int = 10,
        source_filter: Optional[list[str]] = None,
        min_score: float = 0.0
    ) -> list[RetrievedDocument]:
        """
        搜尋相關文件
        
        Args:
            query: 搜尋查詢
            n_results: 返回數量
            source_filter: 來源類型過濾
            min_score: 最低相關度分數
            
        Returns:
            RetrievedDocument 列表
        """
        # 取得查詢的 embedding
        query_embedding = self._get_embedding(query)
        
        # 建立過濾條件
        where_filter = None
        if source_filter:
            where_filter = {
                "source_type": {"$in": source_filter}
            }
        
        # 查詢
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        # 轉換結果
        documents = []
        
        if not results["documents"] or not results["documents"][0]:
            return documents
        
        for doc, metadata, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            # ChromaDB 的 distance 越小越好，轉換成 score (0-1)
            score = 1 / (1 + distance)
            
            if score < min_score:
                continue
            
            documents.append(RetrievedDocument(
                content=doc,
                source_type=SourceType(metadata["source_type"]),
                source_id=metadata["source_id"],
                title=metadata["title"],
                url=metadata["url"],
                credibility=CredibilityLevel(metadata["credibility"]),
                year=metadata.get("year"),
                authors=metadata.get("authors"),
                journal=metadata.get("journal"),
                relevance_score=score
            ))
        
        return documents
    
    def get_stats(self) -> dict:
        """取得資料庫統計資訊"""
        count = self.collection.count()
        
        # 嘗試取得各來源類型的數量
        stats = {
            "total_documents": count,
            "collection_name": self.collection_name,
            "persist_directory": self.persist_directory
        }
        
        return stats
    
    def clear(self):
        """清空 collection（危險操作！）"""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Medical knowledge base for MediNotes"}
        )


# Singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """取得 VectorStore 單例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
