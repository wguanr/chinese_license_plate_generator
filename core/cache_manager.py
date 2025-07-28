#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
缓存管理器模块

提供材质实例的智能缓存和管理功能。
"""

import json
import pickle
import hashlib
from typing import Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime, timedelta


class CacheManager:
    """
    缓存管理器
    
    支持材质实例的内存缓存和磁盘缓存，提供智能的缓存策略。
    """
    
    def __init__(self, cache_dir: Union[str, Path] = None, max_memory_cache: int = 100):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录路径
            max_memory_cache: 最大内存缓存数量
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path.cwd() / ".cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        self.max_memory_cache = max_memory_cache
        self._memory_cache: Dict[str, Any] = {}
        self._cache_metadata: Dict[str, Dict[str, Any]] = {}
        
        # 加载缓存元数据
        self._load_cache_metadata()
    
    def _generate_cache_key(self, data: Any) -> str:
        """
        生成缓存键
        
        Args:
            data: 要缓存的数据
            
        Returns:
            缓存键字符串
        """
        if hasattr(data, 'to_dict'):
            data_str = json.dumps(data.to_dict(), sort_keys=True)
        else:
            data_str = str(data)
        
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def put(self, key: str, value: Any, expire_hours: Optional[int] = None) -> bool:
        """
        放入缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            expire_hours: 过期时间（小时），None表示永不过期
            
        Returns:
            是否成功
        """
        try:
            # 内存缓存
            self._memory_cache[key] = value
            
            # 如果内存缓存超过限制，移除最老的条目
            if len(self._memory_cache) > self.max_memory_cache:
                oldest_key = min(self._cache_metadata.keys(), 
                               key=lambda k: self._cache_metadata[k].get('access_time', datetime.min))
                self._memory_cache.pop(oldest_key, None)
            
            # 磁盘缓存
            cache_file = self.cache_dir / f"{key}.pkl"
            with open(cache_file, 'wb') as f:
                pickle.dump(value, f)
            
            # 更新元数据
            self._cache_metadata[key] = {
                'created_time': datetime.now(),
                'access_time': datetime.now(),
                'expire_time': datetime.now() + timedelta(hours=expire_hours) if expire_hours else None,
                'file_path': str(cache_file)
            }
            
            self._save_cache_metadata()
            return True
            
        except Exception as e:
            print(f"⚠️  缓存写入失败: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或过期则返回None
        """
        # 检查是否过期
        if self._is_expired(key):
            self.remove(key)
            return None
        
        # 先检查内存缓存
        if key in self._memory_cache:
            self._update_access_time(key)
            return self._memory_cache[key]
        
        # 检查磁盘缓存
        if key in self._cache_metadata:
            try:
                cache_file = Path(self._cache_metadata[key]['file_path'])
                if cache_file.exists():
                    with open(cache_file, 'rb') as f:
                        value = pickle.load(f)
                    
                    # 加载到内存缓存
                    self._memory_cache[key] = value
                    self._update_access_time(key)
                    
                    return value
            except Exception as e:
                print(f"⚠️  缓存读取失败: {e}")
                self.remove(key)
        
        return None
    
    def remove(self, key: str) -> bool:
        """
        移除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功
        """
        try:
            # 从内存缓存移除
            self._memory_cache.pop(key, None)
            
            # 从磁盘缓存移除
            if key in self._cache_metadata:
                cache_file = Path(self._cache_metadata[key]['file_path'])
                if cache_file.exists():
                    cache_file.unlink()
                
                del self._cache_metadata[key]
                self._save_cache_metadata()
            
            return True
            
        except Exception as e:
            print(f"⚠️  缓存移除失败: {e}")
            return False
    
    def clear(self, clear_disk: bool = True) -> bool:
        """
        清除所有缓存
        
        Args:
            clear_disk: 是否清除磁盘缓存
            
        Returns:
            是否成功
        """
        try:
            # 清除内存缓存
            self._memory_cache.clear()
            
            if clear_disk:
                # 清除磁盘缓存
                for key in list(self._cache_metadata.keys()):
                    self.remove(key)
            
            return True
            
        except Exception as e:
            print(f"⚠️  缓存清除失败: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """
        清理过期缓存
        
        Returns:
            清理的缓存数量
        """
        expired_keys = []
        
        for key in self._cache_metadata.keys():
            if self._is_expired(key):
                expired_keys.append(key)
        
        for key in expired_keys:
            self.remove(key)
        
        return len(expired_keys)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        return {
            'memory_cache_size': len(self._memory_cache),
            'disk_cache_size': len(self._cache_metadata),
            'cache_dir': str(self.cache_dir),
            'max_memory_cache': self.max_memory_cache
        }
    
    def _is_expired(self, key: str) -> bool:
        """
        检查缓存是否过期
        
        Args:
            key: 缓存键
            
        Returns:
            是否过期
        """
        if key not in self._cache_metadata:
            return True
        
        expire_time = self._cache_metadata[key].get('expire_time')
        if expire_time and datetime.now() > expire_time:
            return True
        
        return False
    
    def _update_access_time(self, key: str):
        """
        更新访问时间
        
        Args:
            key: 缓存键
        """
        if key in self._cache_metadata:
            self._cache_metadata[key]['access_time'] = datetime.now()
    
    def _load_cache_metadata(self):
        """加载缓存元数据"""
        metadata_file = self.cache_dir / "cache_metadata.json"
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 转换时间字符串为datetime对象
                for key, meta in data.items():
                    if 'created_time' in meta:
                        meta['created_time'] = datetime.fromisoformat(meta['created_time'])
                    if 'access_time' in meta:
                        meta['access_time'] = datetime.fromisoformat(meta['access_time'])
                    if 'expire_time' in meta and meta['expire_time']:
                        meta['expire_time'] = datetime.fromisoformat(meta['expire_time'])
                
                self._cache_metadata = data
                
            except Exception as e:
                print(f"⚠️  缓存元数据加载失败: {e}")
                self._cache_metadata = {}
    
    def _save_cache_metadata(self):
        """保存缓存元数据"""
        metadata_file = self.cache_dir / "cache_metadata.json"
        
        try:
            # 转换datetime对象为字符串
            data = {}
            for key, meta in self._cache_metadata.items():
                data[key] = meta.copy()
                if 'created_time' in data[key]:
                    data[key]['created_time'] = data[key]['created_time'].isoformat()
                if 'access_time' in data[key]:
                    data[key]['access_time'] = data[key]['access_time'].isoformat()
                if 'expire_time' in data[key] and data[key]['expire_time']:
                    data[key]['expire_time'] = data[key]['expire_time'].isoformat()
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"⚠️  缓存元数据保存失败: {e}") 