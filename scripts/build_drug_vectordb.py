"""
Build Drug Vector Database
将收集的药物数据向量化并存储到 Chroma DB

使用方法:
    python scripts/build_drug_vectordb.py
"""

# ✅ 第一步：加载环境变量（必须在最开头）
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

# 验证 API key
if not os.getenv('OPENAI_API_KEY'):
    print(f"❌ Error: OPENAI_API_KEY not found")
    print(f"   Checked: {env_path}")
    print(f"   Please add OPENAI_API_KEY to .env file")
    import sys
    sys.exit(1)
else:
    print(f"✅ API Key loaded from {env_path}")

# ✅ 第二步：其他导入
import sys
import json
from typing import List, Dict

# 添加项目根目录到路径
sys.path.insert(0, str(project_root))

try:
    # 尝试新版本导入（LangChain >= 0.1.0）
    from langchain_openai import OpenAIEmbeddings
    from langchain_chroma import Chroma
except ImportError:
    # 回退到旧版本导入
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.vectorstores import Chroma

# Document 的新导入路径
try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.docstore.document import Document


class DrugVectorDBBuilder:
    """药物向量数据库构建器"""
    
    def __init__(
        self, 
        data_dir: str = "data/drug_database",
        vector_db_dir: str = "data/drug_vectordb"
    ):
        self.data_dir = Path(data_dir)
        self.vector_db_dir = Path(vector_db_dir)
        self.embeddings = OpenAIEmbeddings()
        
        # 确保目录存在
        self.vector_db_dir.mkdir(parents=True, exist_ok=True)
        
        self.stats = {
            'total_files': 0,
            'processed': 0,
            'failed': 0
        }
    
    def load_drug_data(self) -> List[Dict]:
        """
        加载所有药物数据
        
        Returns:
            药物数据列表
        """
        drug_data = []
        
        if not self.data_dir.exists():
            print(f"❌ Data directory not found: {self.data_dir}")
            print(f"   Please run collect_drug_data.py first!")
            return drug_data
        
        json_files = list(self.data_dir.glob("*.json"))
        self.stats['total_files'] = len(json_files)
        
        print(f"📂 Found {len(json_files)} drug data files")
        
        for filepath in json_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    drug_data.append(data)
                    self.stats['processed'] += 1
            except Exception as e:
                print(f"❌ Error loading {filepath}: {e}")
                self.stats['failed'] += 1
        
        print(f"✅ Loaded {len(drug_data)} drug data files")
        return drug_data
    
    def create_documents(self, drug_data: List[Dict]) -> List[Document]:
        """
        将药物数据转换为 LangChain Documents
        
        Args:
            drug_data: 药物数据列表
            
        Returns:
            Document 列表
        """
        documents = []
        
        print("📝 Creating documents...")
        
        for data in drug_data:
            drug_name = data.get('drug_name', 'Unknown')
            
            # 创建多个文档片段，提高检索准确性
            
            # 1. 基本信息文档
            basic_info = f"""
Drug: {drug_name}
Generic Name: {data.get('generic_name', '')}
Brand Names: {', '.join(data.get('brand_names', []))}

Indications and Usage:
{data.get('indications', '')}

Dosage and Administration:
{data.get('dosage', '')}
""".strip()
            
            documents.append(Document(
                page_content=basic_info,
                metadata={
                    'drug_name': drug_name,
                    'doc_type': 'basic_info',
                    'source': 'FDA'
                }
            ))
            
            # 2. 禁忌症和警告文档
            if data.get('contraindications') or data.get('warnings'):
                safety_info = f"""
Drug: {drug_name}

Contraindications:
{data.get('contraindications', '')}

Warnings and Precautions:
{data.get('warnings', '')}
""".strip()
                
                documents.append(Document(
                    page_content=safety_info,
                    metadata={
                        'drug_name': drug_name,
                        'doc_type': 'safety',
                        'source': 'FDA'
                    }
                ))
            
            # 3. 不良反应文档
            if data.get('adverse_reactions'):
                adverse_info = f"""
Drug: {drug_name}

Adverse Reactions:
{data.get('adverse_reactions', '')}
""".strip()
                
                documents.append(Document(
                    page_content=adverse_info,
                    metadata={
                        'drug_name': drug_name,
                        'doc_type': 'adverse_reactions',
                        'source': 'FDA'
                    }
                ))
            
            # 4. 药物交互作用文档
            if data.get('drug_interactions'):
                interaction_info = f"""
Drug: {drug_name}

Drug Interactions:
{data.get('drug_interactions', '')}
""".strip()
                
                documents.append(Document(
                    page_content=interaction_info,
                    metadata={
                        'drug_name': drug_name,
                        'doc_type': 'interactions',
                        'source': 'FDA'
                    }
                ))
            
            # 5. 药理学文档
            if data.get('pharmacology'):
                pharm_info = f"""
Drug: {drug_name}

Clinical Pharmacology:
{data.get('pharmacology', '')}
""".strip()
                
                documents.append(Document(
                    page_content=pharm_info,
                    metadata={
                        'drug_name': drug_name,
                        'doc_type': 'pharmacology',
                        'source': 'FDA'
                    }
                ))
        
        print(f"✅ Created {len(documents)} documents from {len(drug_data)} drugs")
        return documents
    
    def build_vector_db(self, documents: List[Document]) -> Chroma:
        """
        构建向量数据库
        
        Args:
            documents: Document 列表
            
        Returns:
            Chroma 向量数据库
        """
        print(f"🔨 Building vector database...")
        print(f"   This may take a while (embedding {len(documents)} documents)...")
        
        # 批量处理，避免一次处理太多
        batch_size = 100
        vector_db = None
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            print(f"   Processing batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}...")
            
            if vector_db is None:
                # 第一批：创建新数据库
                vector_db = Chroma.from_documents(
                    documents=batch,
                    embedding=self.embeddings,
                    persist_directory=str(self.vector_db_dir)
                )
            else:
                # 后续批次：添加到现有数据库
                vector_db.add_documents(batch)
        
        # 持久化
        # 持久化（新版本自动持久化，不需要手动调用）
        print("💾 Vector database persisted automatically")
        # vector_db.persist()  # 新版本已移除此方法
        
        print(f"✅ Vector database built successfully!")
        print(f"   Location: {self.vector_db_dir}")
        print(f"   Total documents: {len(documents)}")
        
        return vector_db
    
    def build(self) -> None:
        """执行完整的构建流程"""
        print("="*60)
        print("🚀 Building Drug Vector Database")
        print("="*60)
        
        # 1. 加载数据
        drug_data = self.load_drug_data()
        
        if not drug_data:
            print("❌ No drug data found. Please run collect_drug_data.py first!")
            return
        
        # 2. 创建文档
        documents = self.create_documents(drug_data)
        
        # 3. 构建向量数据库
        vector_db = self.build_vector_db(documents)
        
        # 4. 测试查询
        print("\n" + "="*60)
        print("🧪 Testing vector database...")
        print("="*60)
        
        test_queries = [
            "What are the side effects of Metformin?",
            "Warfarin drug interactions",
            "Aspirin contraindications"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            results = vector_db.similarity_search(query, k=2)
            for i, doc in enumerate(results, 1):
                print(f"  Result {i}: {doc.metadata['drug_name']} ({doc.metadata['doc_type']})")
                print(f"    Preview: {doc.page_content[:100]}...")
        
        # 5. 最终统计
        print("\n" + "="*60)
        print("✅ Build completed!")
        print("="*60)
        print(f"""
📊 Statistics:
  Total drug data files: {self.stats['total_files']}
  Successfully processed: {self.stats['processed']}
  Failed: {self.stats['failed']}
  Total documents created: {len(documents)}
  Vector database location: {self.vector_db_dir}
""")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Build drug vector database')
    parser.add_argument('--data-dir', type=str, default='data/drug_database',
                       help='Drug data directory (default: data/drug_database)')
    parser.add_argument('--output-dir', type=str, default='data/drug_vectordb',
                       help='Vector database output directory (default: data/drug_vectordb)')
    
    args = parser.parse_args()
    
    # 创建构建器
    builder = DrugVectorDBBuilder(
        data_dir=args.data_dir,
        vector_db_dir=args.output_dir
    )
    
    # 开始构建
    builder.build()


if __name__ == "__main__":
    main()