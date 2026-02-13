"""
初始化醫療知識庫腳本
執行方式：python scripts/init_knowledge_base.py

此腳本會從 PubMed 和 FDA 擷取核心醫療資料並存入本地向量庫
"""

import os
import sys
import asyncio
from pathlib import Path

# 加入 api 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.data_sources.pubmed import PubMedClient
from api.data_sources.fda import FDAClient
from api.database.vector_store import VectorStore
from api.models.schemas import SourceType, CredibilityLevel


# ========== 配置區 ==========

# PubMed 搜尋主題（你可以根據需求調整）
PUBMED_TOPICS = [
    # 常見慢性病
    "diabetes mellitus type 2 treatment guidelines",
    "hypertension management therapy",
    "hyperlipidemia statin treatment",
    
    # 藥物交互作用（重點！）
    "drug interaction warfarin",
    "drug interaction metformin",
    "drug interaction aspirin",
    "polypharmacy elderly adverse effects",
    
    # 常見用藥
    "metformin clinical efficacy safety",
    "ACE inhibitor heart failure",
    "proton pump inhibitor long term effects",
    "NSAID adverse effects elderly",
]

# FDA 常用藥品清單
FDA_DRUGS = [
    # 降血糖
    "metformin", "glipizide", "sitagliptin",
    # 降血壓
    "lisinopril", "amlodipine", "losartan",
    # 降血脂
    "atorvastatin", "simvastatin",
    # 抗凝血
    "warfarin", "aspirin",
    # 其他常用
    "omeprazole", "levothyroxine", "gabapentin",
    "prednisone", "ibuprofen", "acetaminophen"
]

# 每個主題最多抓幾篇
ARTICLES_PER_TOPIC = 20

# ========== 主程式 ==========

async def fetch_pubmed_data(client: PubMedClient):
    """從 PubMed 擷取文獻"""
    print("\n📚 開始擷取 PubMed 文獻...")
    
    all_documents = []
    
    for topic in PUBMED_TOPICS:
        print(f"  搜尋: {topic}")
        try:
            articles = await client.search_and_fetch(topic, ARTICLES_PER_TOPIC)
            
            for article in articles:
                if article.abstract:
                    authors = ", ".join(article.authors[:3])
                    if len(article.authors) > 3:
                        authors += " et al."
                    
                    all_documents.append({
                        "content": article.to_text(),
                        "source_type": SourceType.PUBMED.value,
                        "source_id": article.source_id,
                        "title": article.title,
                        "url": article.url,
                        "credibility": CredibilityLevel.PEER_REVIEWED.value,
                        "year": article.pub_date,
                        "authors": authors,
                        "journal": article.journal
                    })
            
            print(f"    ✓ 取得 {len(articles)} 篇")
            
        except Exception as e:
            print(f"    ✗ 錯誤: {e}")
        
        # Rate limit
        await asyncio.sleep(0.5)
    
    print(f"✅ PubMed 擷取完成：{len(all_documents)} 篇文獻")
    return all_documents


async def fetch_fda_data(client: FDAClient):
    """從 FDA 擷取藥品資料"""
    print("\n💊 開始擷取 FDA 藥品資料...")
    
    all_documents = []
    
    for drug in FDA_DRUGS:
        print(f"  搜尋: {drug}")
        try:
            labels = await client.search_drug_labels(drug, limit=1)
            
            for label in labels:
                all_documents.append({
                    "content": label.to_text(),
                    "source_type": SourceType.FDA.value,
                    "source_id": label.source_id,
                    "title": f"{label.brand_name} ({label.generic_name})",
                    "url": label.url,
                    "credibility": CredibilityLevel.OFFICIAL.value,
                    "year": None,
                    "authors": label.manufacturer,
                    "journal": None
                })
            
            if labels:
                print(f"    ✓ 取得 {len(labels)} 筆")
            else:
                print(f"    - 無資料")
            
        except Exception as e:
            print(f"    ✗ 錯誤: {e}")
        
        # Rate limit
        await asyncio.sleep(0.3)
    
    print(f"✅ FDA 擷取完成：{len(all_documents)} 筆藥品資料")
    return all_documents


async def main():
    print("=" * 60)
    print("🏥 MediNotes 知識庫初始化工具")
    print("=" * 60)
    
    # 檢查 OpenAI API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ 錯誤：請設定 OPENAI_API_KEY 環境變數")
        print("   export OPENAI_API_KEY=your-api-key")
        sys.exit(1)
    
    # 初始化客戶端
    pubmed_client = PubMedClient()
    fda_client = FDAClient()
    
    # 擷取資料
    pubmed_docs = await fetch_pubmed_data(pubmed_client)
    fda_docs = await fetch_fda_data(fda_client)
    
    # 合併
    all_docs = pubmed_docs + fda_docs
    print(f"\n📊 總計：{len(all_docs)} 份文件")
    
    if not all_docs:
        print("❌ 沒有擷取到任何資料，請檢查網路連線")
        sys.exit(1)
    
    # 存入向量庫
    print("\n🔧 開始建立向量索引...")
    print("   （這可能需要幾分鐘，取決於資料量）")
    
    try:
        vector_store = VectorStore(
            persist_directory="data/chroma_db",
            collection_name="medical_knowledge"
        )
        
        # 清空舊資料（可選）
        # vector_store.clear()
        
        # 新增文件
        added = vector_store.add_documents(all_docs, batch_size=50)
        
        print(f"✅ 已存入 {added} 份文件")
        
        # 顯示統計
        stats = vector_store.get_stats()
        print(f"\n📈 資料庫統計：")
        print(f"   總文件數：{stats['total_documents']}")
        print(f"   儲存路徑：{stats['persist_directory']}")
        
    except Exception as e:
        print(f"❌ 建立向量索引時發生錯誤：{e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 知識庫初始化完成！")
    print("=" * 60)
    print("\n現在可以啟動伺服器：")
    print("   uvicorn api.server:app --reload")


if __name__ == "__main__":
    asyncio.run(main())
