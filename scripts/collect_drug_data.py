"""
Drug Data Collector
从 FDA API 收集 Top 200 药物的详细信息

使用方法:
    python scripts/collect_drug_data.py
    python scripts/collect_drug_data.py --limit 200  # 只收集前 200 个
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from top_200_drugs import TOP_200_DRUGS
from api.data_sources.fda import FDAClient


class DrugDataCollector:
    """药物数据收集器"""
    
    def __init__(self, output_dir: str = "data/drug_database"):
        self.fda_client = FDAClient()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
    
    def collect_drug_info(self, drug_name: str) -> dict:
        """
        收集单个药物的信息
        
        Args:
            drug_name: 药物名称
            
        Returns:
            药物信息字典
        """
        print(f"\n📥 Fetching {drug_name}...")
        
        try:
            # 调用 FDA API
            label_data = self.fda_client.get_drug_label(drug_name)
            
            if not label_data:
                print(f"  ❌ No data found for {drug_name}")
                return None
            
            # 提取关键信息
            drug_info = {
                "drug_name": drug_name,
                "generic_name": self._extract_generic_name(label_data),
                "brand_names": self._extract_brand_names(label_data),
                "indications": self._extract_indications(label_data),
                "dosage": self._extract_dosage(label_data),
                "contraindications": self._extract_contraindications(label_data),
                "warnings": self._extract_warnings(label_data),
                "adverse_reactions": self._extract_adverse_reactions(label_data),
                "drug_interactions": self._extract_interactions(label_data),
                "pharmacology": self._extract_pharmacology(label_data),
                "pregnancy_category": self._extract_pregnancy_info(label_data),
                "full_label": label_data,  # 保留完整标签以备用
                "last_updated": datetime.now().isoformat(),
                "source": "FDA OpenFDA API"
            }
            
            print(f"  ✅ Successfully collected data for {drug_name}")
            return drug_info
            
        except Exception as e:
            print(f"  ❌ Error collecting {drug_name}: {e}")
            return None
    
    def _extract_generic_name(self, label_data: dict) -> str:
        """提取通用名"""
        try:
            return label_data.get("openfda", {}).get("generic_name", [""])[0]
        except:
            return ""
    
    def _extract_brand_names(self, label_data: dict) -> list:
        """提取商品名"""
        try:
            return label_data.get("openfda", {}).get("brand_name", [])
        except:
            return []
    
    def _extract_indications(self, label_data: dict) -> str:
        """提取适应症"""
        try:
            return label_data.get("indications_and_usage", [""])[0]
        except:
            return ""
    
    def _extract_dosage(self, label_data: dict) -> str:
        """提取用法用量"""
        try:
            return label_data.get("dosage_and_administration", [""])[0]
        except:
            return ""
    
    def _extract_contraindications(self, label_data: dict) -> str:
        """提取禁忌症"""
        try:
            return label_data.get("contraindications", [""])[0]
        except:
            return ""
    
    def _extract_warnings(self, label_data: dict) -> str:
        """提取警告"""
        try:
            warnings = label_data.get("warnings", [""])
            if not warnings or not warnings[0]:
                warnings = label_data.get("boxed_warning", [""])
            return warnings[0] if warnings else ""
        except:
            return ""
    
    def _extract_adverse_reactions(self, label_data: dict) -> str:
        """提取不良反应"""
        try:
            return label_data.get("adverse_reactions", [""])[0]
        except:
            return ""
    
    def _extract_interactions(self, label_data: dict) -> str:
        """提取药物交互作用"""
        try:
            return label_data.get("drug_interactions", [""])[0]
        except:
            return ""
    
    def _extract_pharmacology(self, label_data: dict) -> str:
        """提取药理学"""
        try:
            return label_data.get("clinical_pharmacology", [""])[0]
        except:
            return ""
    
    def _extract_pregnancy_info(self, label_data: dict) -> str:
        """提取妊娠信息"""
        try:
            return label_data.get("pregnancy", [""])[0]
        except:
            return ""
    
    def save_drug_info(self, drug_info: dict) -> None:
        """
        保存药物信息到文件
        
        Args:
            drug_info: 药物信息字典
        """
        if not drug_info:
            return
        
        drug_name = drug_info['drug_name']
        # 文件名：去除空格，转小写
        filename = drug_name.replace(' ', '_').replace('/', '_').lower() + '.json'
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(drug_info, f, indent=2, ensure_ascii=False)
        
        print(f"  💾 Saved to {filepath}")
    
    def collect_all(self, drug_list: list, limit: int = None) -> None:
        """
        收集所有药物信息
        
        Args:
            drug_list: 药物列表
            limit: 限制数量，None 表示全部
        """
        if limit:
            drug_list = drug_list[:limit]
        
        self.stats['total'] = len(drug_list)
        
        print(f"🚀 Starting to collect data for {len(drug_list)} drugs...")
        print(f"📁 Output directory: {self.output_dir}")
        
        for i, drug_name in enumerate(drug_list, 1):
            print(f"\n[{i}/{len(drug_list)}] Processing {drug_name}...")
            
            # 检查是否已存在
            filename = drug_name.replace(' ', '_').replace('/', '_').lower() + '.json'
            filepath = self.output_dir / filename
            
            if filepath.exists():
                print(f"  ⏭️  Already exists, skipping...")
                self.stats['skipped'] += 1
                continue
            
            # 收集数据
            drug_info = self.collect_drug_info(drug_name)
            
            if drug_info:
                self.save_drug_info(drug_info)
                self.stats['success'] += 1
            else:
                self.stats['failed'] += 1
            
            # 避免触发 API 限制，每次请求后暂停
            if i < len(drug_list):  # 最后一个不需要暂停
                time.sleep(0.5)  # 暂停 0.5 秒
            
            # 每 10 个药物打印进度
            if i % 10 == 0:
                self._print_progress()
        
        # 最终统计
        print("\n" + "="*60)
        print("✅ Collection completed!")
        self._print_progress()
        print("="*60)
    
    def _print_progress(self) -> None:
        """打印进度统计"""
        print(f"""
📊 Progress:
  Total: {self.stats['total']}
  Success: {self.stats['success']} ✅
  Failed: {self.stats['failed']} ❌
  Skipped: {self.stats['skipped']} ⏭️
  Remaining: {self.stats['total'] - self.stats['success'] - self.stats['failed'] - self.stats['skipped']}
""")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Collect drug data from FDA API')
    parser.add_argument('--limit', type=int, help='Limit number of drugs to collect')
    parser.add_argument('--output', type=str, default='data/drug_database', 
                       help='Output directory (default: data/drug_database)')
    
    args = parser.parse_args()
    
    # 创建收集器
    collector = DrugDataCollector(output_dir=args.output)
    
    # 开始收集
    collector.collect_all(TOP_200_DRUGS, limit=args.limit)


if __name__ == "__main__":
    main()