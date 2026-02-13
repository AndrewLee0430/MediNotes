"""
PubMed API Client
使用 NCBI E-utilities API 搜尋和取得醫學文獻

API 文件：https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""

import os
import httpx
from typing import Optional
from dataclasses import dataclass
from xml.etree import ElementTree as ET
import asyncio


@dataclass
class PubMedArticle:
    """PubMed 文章資料結構"""
    pmid: str
    title: str
    abstract: str
    authors: list[str]
    journal: str
    pub_date: str
    doi: Optional[str] = None
    
    @property
    def url(self) -> str:
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"
    
    @property
    def source_id(self) -> str:
        return f"PMID:{self.pmid}"
    
    def to_text(self) -> str:
        """轉換為可用於 RAG 的文字格式"""
        authors_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            authors_str += " et al."
        
        return f"""# {self.title}

**Authors:** {authors_str}
**Journal:** {self.journal} ({self.pub_date})
**PMID:** {self.pmid}

## Abstract
{self.abstract}
"""


class PubMedClient:
    """PubMed E-utilities API 客戶端"""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        email: Optional[str] = None
    ):
        """
        初始化 PubMed 客戶端
        
        Args:
            api_key: NCBI API key（可選，有的話 rate limit 提升到 10/秒）
            email: 聯絡 email（NCBI 建議提供）
        """
        self.api_key = api_key or os.getenv("PUBMED_API_KEY")
        self.email = email or os.getenv("NCBI_EMAIL", "medinotes@example.com")
        
        # Rate limit: 3/秒（無 API key）或 10/秒（有 API key）
        self.rate_limit_delay = 0.1 if self.api_key else 0.34
    
    def _build_params(self, **kwargs) -> dict:
        """建立 API 請求參數"""
        params = {**kwargs}
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["email"] = self.email
        return params
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort: str = "relevance"
    ) -> list[str]:
        """
        搜尋 PubMed，返回 PMID 列表
        
        Args:
            query: 搜尋關鍵字
            max_results: 最多返回筆數
            sort: 排序方式 ("relevance" 或 "date")
            
        Returns:
            PMID 列表
        """
        params = self._build_params(
            db="pubmed",
            term=query,
            retmax=max_results,
            retmode="json",
            sort=sort
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/esearch.fcgi",
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
        
        await asyncio.sleep(self.rate_limit_delay)
        return data.get("esearchresult", {}).get("idlist", [])
    
    async def fetch_details(self, pmids: list[str]) -> list[PubMedArticle]:
        """
        根據 PMID 取得文章詳細資訊
        
        Args:
            pmids: PMID 列表
            
        Returns:
            PubMedArticle 列表
        """
        if not pmids:
            return []
        
        params = self._build_params(
            db="pubmed",
            id=",".join(pmids),
            retmode="xml",
            rettype="abstract"
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/efetch.fcgi",
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            xml_text = response.text
        
        await asyncio.sleep(self.rate_limit_delay)
        return self._parse_xml(xml_text)
    
    def _parse_xml(self, xml_text: str) -> list[PubMedArticle]:
        """解析 PubMed XML 回應"""
        articles = []
        
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return articles
        
        for article_elem in root.findall(".//PubmedArticle"):
            try:
                # PMID
                pmid = article_elem.findtext(".//PMID", "")
                if not pmid:
                    continue
                
                # Title
                title = article_elem.findtext(".//ArticleTitle", "")
                
                # Abstract - 可能有多個段落
                abstract_parts = []
                for abstract_text in article_elem.findall(".//AbstractText"):
                    label = abstract_text.get("Label", "")
                    text = abstract_text.text or ""
                    if label:
                        abstract_parts.append(f"**{label}:** {text}")
                    else:
                        abstract_parts.append(text)
                abstract = "\n\n".join(abstract_parts)
                
                # 如果沒有 abstract，跳過
                if not abstract:
                    continue
                
                # Authors
                authors = []
                for author in article_elem.findall(".//Author"):
                    last_name = author.findtext("LastName", "")
                    fore_name = author.findtext("ForeName", "")
                    if last_name:
                        authors.append(f"{last_name} {fore_name}".strip())
                
                # Journal
                journal = article_elem.findtext(".//Journal/Title", "")
                
                # Publication Date
                pub_date = article_elem.findtext(".//PubDate/Year", "")
                if not pub_date:
                    medline_date = article_elem.findtext(".//PubDate/MedlineDate", "")
                    if medline_date:
                        pub_date = medline_date[:4]  # 取前4個字元（年份）
                
                # DOI
                doi = None
                for id_elem in article_elem.findall(".//ArticleId"):
                    if id_elem.get("IdType") == "doi":
                        doi = id_elem.text
                        break
                
                articles.append(PubMedArticle(
                    pmid=pmid,
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    journal=journal,
                    pub_date=pub_date,
                    doi=doi
                ))
                
            except Exception:
                # 解析單篇文章失敗，繼續下一篇
                continue
        
        return articles
    
    async def search_and_fetch(
        self,
        query: str,
        max_results: int = 10
    ) -> list[PubMedArticle]:
        """
        搜尋並取得文章詳細資訊（組合方法）
        
        Args:
            query: 搜尋關鍵字
            max_results: 最多返回筆數
            
        Returns:
            PubMedArticle 列表
        """
        pmids = await self.search(query, max_results)
        if not pmids:
            return []
        return await self.fetch_details(pmids)


# 同步版本的包裝函數（方便測試）
def search_pubmed_sync(query: str, max_results: int = 10) -> list[PubMedArticle]:
    """同步版本的 PubMed 搜尋"""
    client = PubMedClient()
    return asyncio.run(client.search_and_fetch(query, max_results))


# 測試用
if __name__ == "__main__":
    async def test():
        client = PubMedClient()
        articles = await client.search_and_fetch("metformin drug interaction", max_results=3)
        for article in articles:
            print(f"PMID: {article.pmid}")
            print(f"Title: {article.title}")
            print(f"URL: {article.url}")
            print("-" * 50)
    
    asyncio.run(test())
