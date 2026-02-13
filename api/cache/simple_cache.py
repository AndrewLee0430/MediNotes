"""
Simple in-memory cache with TTL (Time To Live)
用于缓存 FDA 和 PubMed API 响应
"""

from datetime import datetime, timedelta
from typing import Optional, Any
import json


class SimpleCache:
    """简单的内存缓存，支持过期时间"""
    
    def __init__(self, default_ttl_seconds: int = 86400):
        """
        初始化缓存
        
        Args:
            default_ttl_seconds: 默认过期时间（秒），默认 24 小时
        """
        self.cache = {}
        self.default_ttl = default_ttl_seconds
        self.stats = {
            'hits': 0,      # 缓存命中次数
            'misses': 0,    # 缓存未命中次数
            'sets': 0,      # 写入次数
            'evictions': 0  # 过期清理次数
        }
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的值，如果不存在或已过期则返回 None
        """
        if key in self.cache:
            data, timestamp, ttl = self.cache[key]
            
            # 检查是否过期
            if datetime.now() - timestamp < timedelta(seconds=ttl):
                self.stats['hits'] += 1
                return data
            else:
                # 过期，删除
                del self.cache[key]
                self.stats['evictions'] += 1
                self.stats['misses'] += 1
                return None
        else:
            self.stats['misses'] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 要缓存的值
            ttl: 过期时间（秒），如果不指定则使用默认值
        """
        if ttl is None:
            ttl = self.default_ttl
        
        self.cache[key] = (value, datetime.now(), ttl)
        self.stats['sets'] += 1
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        self.cache.clear()
        print("✅ Cache cleared")
    
    def cleanup_expired(self) -> int:
        """
        清理所有过期的缓存
        
        Returns:
            清理的数量
        """
        expired_keys = []
        now = datetime.now()
        
        for key, (data, timestamp, ttl) in self.cache.items():
            if now - timestamp >= timedelta(seconds=ttl):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
            self.stats['evictions'] += 1
        
        if expired_keys:
            print(f"✅ Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def get_stats(self) -> dict:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_entries': len(self.cache),
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': f"{hit_rate:.2f}%",
            'sets': self.stats['sets'],
            'evictions': self.stats['evictions']
        }
    
    def __len__(self) -> int:
        """返回缓存中的条目数"""
        return len(self.cache)
    
    def __contains__(self, key: str) -> bool:
        """检查键是否在缓存中且未过期"""
        return self.get(key) is not None


# ============================================================
# 预配置的缓存实例
# ============================================================

# FDA API 缓存（24 小时）
fda_cache = SimpleCache(default_ttl_seconds=86400)

# PubMed API 缓存（1 小时，因为文献更新较快）
pubmed_cache = SimpleCache(default_ttl_seconds=3600)

# 药物交互作用缓存（7 天，相对稳定）
interaction_cache = SimpleCache(default_ttl_seconds=604800)


# ============================================================
# 缓存装饰器（可选，方便使用）
# ============================================================

def cached(cache_instance: SimpleCache, ttl: Optional[int] = None):
    """
    缓存装饰器
    
    使用示例:
        @cached(fda_cache, ttl=86400)
        def get_drug_label(drug_name):
            # 实际的 API 调用
            return fda_api.get(drug_name)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试从缓存获取
            cached_result = cache_instance.get(cache_key)
            if cached_result is not None:
                print(f"✅ Cache hit for {func.__name__}")
                return cached_result
            
            # 缓存未命中，调用实际函数
            print(f"❌ Cache miss for {func.__name__}, calling API...")
            result = func(*args, **kwargs)
            
            # 存入缓存
            cache_instance.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


if __name__ == "__main__":
    # 测试代码
    cache = SimpleCache(default_ttl_seconds=5)
    
    # 测试基本功能
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    print("✅ Basic get/set works")
    
    # 测试过期
    import time
    cache.set("key2", "value2", ttl=2)
    assert cache.get("key2") == "value2"
    time.sleep(3)
    assert cache.get("key2") is None
    print("✅ TTL expiration works")
    
    # 测试统计
    stats = cache.get_stats()
    print(f"✅ Cache stats: {stats}")
    
    print("\n✅ All cache tests passed!")