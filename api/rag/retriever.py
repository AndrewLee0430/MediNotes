"""
Hybrid Retriever
混合檢索器：結合本地向量資料庫、PubMed、FDA API
"""

import asyncio
from typing import Optional
from api.models.schemas import RetrievedDocument, SourceType, CredibilityLevel
from api.database.vector_store import get_vector_store
from api.data_sources.pubmed import PubMedClient
from api.data_sources.fda import FDAClient


class HybridRetriever:
    """
    混合檢索器
    
    檢索順序：
    1. 本地向量資料庫（臨床指引）
    2. PubMed（同行評審文獻）
    3. FDA（官方藥品標籤）
    """
    
    def __init__(
        self,
        local_threshold: float = 0.6,
        enable_local: bool = True,
        enable_pubmed: bool = True,
        enable_fda: bool = True
    ):
        """
        初始化檢索器
        
        Args:
            local_threshold: 本地檢索的最低相關度門檻
            enable_local: 是否啟用本地檢索
            enable_pubmed: 是否啟用 PubMed 檢索
            enable_fda: 是否啟用 FDA 檢索
        """
        self.local_threshold = local_threshold
        self.enable_local = enable_local
        self.enable_pubmed = enable_pubmed
        self.enable_fda = enable_fda
        
        # 初始化客戶端
        self.vector_store = get_vector_store() if enable_local else None
        self.pubmed = PubMedClient() if enable_pubmed else None
        self.fda = FDAClient() if enable_fda else None
    
    async def retrieve(
        self,
        query: str,
        max_results: int = 5,
        source_filter: Optional[list[SourceType]] = None
    ) -> list[RetrievedDocument]:
        """
        混合檢索
        
        Args:
            query: 搜尋查詢
            max_results: 最多返回數量
            source_filter: 來源過濾（None 表示全部）
            
        Returns:
            檢索到的文件列表
        """
        all_documents = []
        
        # 並行執行檢索
        tasks = []
        
        # 1. 本地向量資料庫
        if self.enable_local and (not source_filter or SourceType.LOCAL in source_filter):
            tasks.append(self._search_local(query, max_results))
        
        # 2. PubMed
        if self.enable_pubmed and (not source_filter or SourceType.PUBMED in source_filter):
            tasks.append(self._search_pubmed(query, max_results))
        
        # 3. FDA
        if self.enable_fda and (not source_filter or SourceType.FDA in source_filter):
            tasks.append(self._search_fda(query, max_results))
        
        # 並行執行所有檢索
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合併結果
        for result in results:
            if isinstance(result, list):
                all_documents.extend(result)
            elif isinstance(result, Exception):
                print(f"Retrieval error: {result}")
        
        # 去重（根據 source_id）
        seen = set()
        unique_docs = []
        for doc in all_documents:
            if doc.source_id not in seen:
                seen.add(doc.source_id)
                unique_docs.append(doc)
        
        # 排序（按相關度分數）
        unique_docs.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # 限制數量
        return unique_docs[:max_results]
    
    async def _search_local(self, query: str, max_results: int) -> list[RetrievedDocument]:
        """搜尋本地向量資料庫"""
        try:
            # vector_store.search 是同步方法，需要在 executor 中執行
            loop = asyncio.get_event_loop()
            documents = await loop.run_in_executor(
                None,
                lambda: self.vector_store.search(
                    query=query,
                    n_results=max_results,
                    min_score=self.local_threshold
                )
            )
            return documents
        except Exception as e:
            print(f"Local search error: {e}")
            return []
    
    async def _search_pubmed(self, query: str, max_results: int) -> list[RetrievedDocument]:
        """搜尋 PubMed"""
        try:
            articles = await self.pubmed.search_and_fetch(query, max_results)
            
            documents = []
            for article in articles:
                doc = RetrievedDocument(
                    content=article.to_text(),
                    source_type=SourceType.PUBMED,
                    source_id=article.source_id,
                    title=article.title,
                    url=article.url,
                    credibility=CredibilityLevel.PEER_REVIEWED,
                    year=article.pub_date,
                    authors=", ".join(article.authors[:3]),
                    journal=article.journal,
                    relevance_score=0.8  # PubMed 結果假設高相關度
                )
                documents.append(doc)
            
            return documents
        except Exception as e:
            print(f"PubMed search error: {e}")
            return []
    
    async def _search_fda(self, query: str, max_results: int) -> list[RetrievedDocument]:
        """搜尋 FDA"""
        try:
            labels = await self.fda.search_drug_labels(query, limit=max_results)
            
            documents = []
            for label in labels:
                doc = RetrievedDocument(
                    content=label.to_text(),
                    source_type=SourceType.FDA,
                    source_id=label.source_id,
                    title=f"{label.brand_name} ({label.generic_name})",
                    url=label.url,
                    credibility=CredibilityLevel.OFFICIAL,
                    authors=label.manufacturer,
                    relevance_score=0.75  # FDA 結果相關度
                )
                documents.append(doc)
            
            return documents
        except Exception as e:
            print(f"FDA search error: {e}")
            return []