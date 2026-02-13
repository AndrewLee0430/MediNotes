"""
FDA Client with Caching
带缓存的 FDA API 客户端

使用方法:
    from api.data_sources.fda_cached import fda_client_cached
    label = fda_client_cached.get_drug_label("Metformin")
"""

import requests
from typing import Optional, Dict, Any
from simple_cache import fda_cache


class FDAClientCached:
    """带缓存的 FDA API 客户端"""
    
    def __init__(self, base_url: str = "https://api.fda.gov/drug/label.json"):
        self.base_url = base_url
        self.cache = fda_cache
    
    def get_drug_label(self, drug_name: str) -> Optional[Dict[str, Any]]:
        """
        获取药品标签（带缓存）
        
        Args:
            drug_name: 药物名称
            
        Returns:
            药品标签数据，如果未找到则返回 None
        """
        # 生成缓存键
        cache_key = f"fda_label:{drug_name.lower()}"
        
        # 1. 尝试从缓存获取
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            print(f"✅ Cache hit for FDA label: {drug_name}")
            return cached_data
        
        # 2. 缓存未命中，调用 API
        print(f"❌ Cache miss for FDA label: {drug_name}, calling FDA API...")
        
        try:
            # 构建搜索查询
            # 尝试多种搜索方式以提高命中率
            search_terms = [
                f'openfda.brand_name:"{drug_name}"',
                f'openfda.generic_name:"{drug_name}"',
                f'openfda.substance_name:"{drug_name}"'
            ]
            
            for search_term in search_terms:
                params = {
                    "search": search_term,
                    "limit": 1
                }
                
                response = requests.get(self.base_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("results"):
                        result = data["results"][0]
                        
                        # 3. 存入缓存（24 小时）
                        self.cache.set(cache_key, result, ttl=86400)
                        print(f"💾 Cached FDA label for {drug_name}")
                        
                        return result
                
                elif response.status_code == 404:
                    # 404 表示未找到，尝试下一个搜索词
                    continue
                
                else:
                    print(f"⚠️ FDA API returned status {response.status_code}")
                    break
            
            # 所有搜索词都未找到
            print(f"⚠️ No FDA label found for {drug_name}")
            
            # 缓存 None 结果（1小时），避免重复查询不存在的药物
            self.cache.set(cache_key, None, ttl=3600)
            
            return None
            
        except requests.exceptions.Timeout:
            print(f"⚠️ FDA API timeout for {drug_name}")
            return None
        
        except Exception as e:
            print(f"❌ Error fetching FDA label for {drug_name}: {e}")
            return None
    
    def search_drugs(self, query: str, limit: int = 5) -> list:
        """
        搜索药物（带缓存）
        
        Args:
            query: 搜索查询
            limit: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        cache_key = f"fda_search:{query.lower()}:{limit}"
        
        # 尝试从缓存获取
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            print(f"✅ Cache hit for FDA search: {query}")
            return cached_data
        
        # 调用 API
        print(f"❌ Cache miss for FDA search: {query}, calling FDA API...")
        
        try:
            params = {
                "search": query,
                "limit": limit
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                # 存入缓存（1 小时）
                self.cache.set(cache_key, results, ttl=3600)
                
                return results
            
            else:
                print(f"⚠️ FDA API returned status {response.status_code}")
                return []
        
        except Exception as e:
            print(f"❌ Error searching FDA: {e}")
            return []
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        return self.cache.get_stats()
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()


# 全局实例（推荐使用）
fda_client_cached = FDAClientCached()


if __name__ == "__main__":
    # 测试
    client = FDAClientCached()
    
    # 第一次查询（API 调用）
    print("\n=== First query (should call API) ===")
    label1 = client.get_drug_label("Metformin")
    print(f"Found: {bool(label1)}")
    
    # 第二次查询（缓存命中）
    print("\n=== Second query (should hit cache) ===")
    label2 = client.get_drug_label("Metformin")
    print(f"Found: {bool(label2)}")
    
    # 打印缓存统计
    print("\n=== Cache statistics ===")
    stats = client.get_cache_stats()
    print(stats)