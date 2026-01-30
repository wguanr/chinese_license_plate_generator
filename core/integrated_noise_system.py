#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成噪声系统 (Integrated Noise System)

将FastNoiseLite Go服务、预制资源和现有噪声模块整合为统一的噪声生成系统
提供三层架构：
  - Layer 1: 预制资源（extracted目录）
  - Layer 2: FastNoiseLite Go服务（高性能程序化生成）
  - Layer 3: Python原生噪声生成器（备用方案）

作者: PCG-USD车牌材质系统
版本: 1.0.0
"""

import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional, List

import numpy as np
from PIL import Image

# 导入FastNoiseLite客户端
try:
    from .fastnoise_client import FastNoiseClient, FastNoiseConfig, FastNoisePresets
    FASTNOISE_AVAILABLE = True
except ImportError:
    FASTNOISE_AVAILABLE = False


# ============================================================================
# 噪声源优先级
# ============================================================================

class NoiseSourcePriority(Enum):
    """噪声源优先级"""
    ASSET_FIRST = auto()        # 优先使用预制资源
    FASTNOISE_FIRST = auto()    # 优先使用FastNoiseLite
    BALANCED = auto()           # 平衡使用（50/50）
    FASTNOISE_ONLY = auto()     # 仅使用FastNoiseLite
    ASSET_ONLY = auto()         # 仅使用预制资源


# ============================================================================
# 集成噪声配置
# ============================================================================

@dataclass
class IntegratedNoiseConfig:
    """
    集成噪声配置
    
    Attributes:
        priority: 噪声源优先级
        asset_path: 预制资源路径
        fastnoise_service_url: FastNoiseLite服务URL
        fallback_enabled: 是否启用备用方案
        cache_enabled: 是否启用缓存
    """
    priority: NoiseSourcePriority = NoiseSourcePriority.BALANCED
    asset_path: Optional[Path] = None
    fastnoise_service_url: str = "http://localhost:8080"
    fallback_enabled: bool = True
    cache_enabled: bool = True


# ============================================================================
# 集成噪声生成器
# ============================================================================

class IntegratedNoiseGenerator:
    """
    集成噪声生成器
    
    根据配置的优先级自动选择最佳噪声源
    """
    
    def __init__(self, config: IntegratedNoiseConfig = None):
        """
        初始化集成噪声生成器
        
        Args:
            config: 集成噪声配置
        """
        self.config = config or IntegratedNoiseConfig()
        self._asset_cache = {}
        self._fastnoise_client = None
        
        # 初始化FastNoiseLite客户端
        if FASTNOISE_AVAILABLE and self.config.priority != NoiseSourcePriority.ASSET_ONLY:
            try:
                self._fastnoise_client = FastNoiseClient(self.config.fastnoise_service_url)
                print("✓ FastNoiseLite Go服务已连接")
            except Exception as e:
                print(f"⚠ FastNoiseLite Go服务不可用: {e}")
                if not self.config.fallback_enabled:
                    raise
        
        # 设置资源路径
        if self.config.asset_path is None:
            self.config.asset_path = Path(__file__).parent.parent / "assets" / "noise_textures" / "extracted"
    
    def generate(self, width: int, height: int,
                noise_type: str = "dirt",
                seed: Optional[int] = None) -> np.ndarray:
        """
        生成噪声纹理
        
        Args:
            width: 宽度
            height: 高度
            noise_type: 噪声类型 ("dirt", "crack", "scratch", "dust", "splat")
            seed: 随机种子
        
        Returns:
            噪声纹理数组 (height, width)，uint8格式
        """
        if seed is not None:
            random.seed(seed)
        
        # 根据优先级选择噪声源
        if self.config.priority == NoiseSourcePriority.ASSET_ONLY:
            return self._generate_from_asset(width, height, noise_type)
        
        elif self.config.priority == NoiseSourcePriority.FASTNOISE_ONLY:
            return self._generate_from_fastnoise(width, height, noise_type, seed)
        
        elif self.config.priority == NoiseSourcePriority.ASSET_FIRST:
            # 80% 使用资源，20% 使用FastNoiseLite
            if random.random() < 0.8:
                return self._generate_from_asset(width, height, noise_type)
            else:
                return self._generate_from_fastnoise(width, height, noise_type, seed)
        
        elif self.config.priority == NoiseSourcePriority.FASTNOISE_FIRST:
            # 80% 使用FastNoiseLite，20% 使用资源
            if random.random() < 0.8:
                return self._generate_from_fastnoise(width, height, noise_type, seed)
            else:
                return self._generate_from_asset(width, height, noise_type)
        
        else:  # BALANCED
            # 50/50
            if random.random() < 0.5:
                return self._generate_from_asset(width, height, noise_type)
            else:
                return self._generate_from_fastnoise(width, height, noise_type, seed)
    
    def _generate_from_asset(self, width: int, height: int, noise_type: str) -> np.ndarray:
        """从预制资源生成噪声"""
        # 查找对应类型的资源
        type_mapping = {
            "dirt": ["dirt", "Grunge-Dirt"],
            "crack": ["Cracks"],
            "scratch": ["scratch"],
            "dust": ["dust"],
            "splat": ["splat"],
        }
        
        search_dirs = type_mapping.get(noise_type, ["dirt"])
        asset_files = []
        
        for dir_name in search_dirs:
            dir_path = self.config.asset_path / dir_name
            if dir_path.exists():
                asset_files.extend(list(dir_path.glob("*.jpg")))
                asset_files.extend(list(dir_path.glob("*.png")))
        
        if not asset_files:
            # 如果没有找到资源，尝试使用FastNoiseLite
            if self._fastnoise_client and self.config.fallback_enabled:
                print(f"⚠ 未找到 {noise_type} 类型的预制资源，切换到FastNoiseLite")
                return self._generate_from_fastnoise(width, height, noise_type)
            else:
                # 返回空白噪声
                return np.zeros((height, width), dtype=np.uint8)
        
        # 随机选择一个资源
        selected_file = random.choice(asset_files)
        
        # 检查缓存
        cache_key = f"{selected_file}_{width}_{height}"
        if self.config.cache_enabled and cache_key in self._asset_cache:
            return self._asset_cache[cache_key].copy()
        
        # 加载并调整大小
        img = Image.open(selected_file).convert('L')
        img = img.resize((width, height), Image.LANCZOS)
        noise_array = np.array(img, dtype=np.uint8)
        
        # 缓存
        if self.config.cache_enabled:
            self._asset_cache[cache_key] = noise_array
        
        return noise_array.copy()
    
    def _generate_from_fastnoise(self, width: int, height: int,
                                 noise_type: str,
                                 seed: Optional[int] = None) -> np.ndarray:
        """从FastNoiseLite生成噪声"""
        if not self._fastnoise_client:
            if self.config.fallback_enabled:
                print("⚠ FastNoiseLite不可用，切换到预制资源")
                return self._generate_from_asset(width, height, noise_type)
            else:
                raise RuntimeError("FastNoiseLite service is not available")
        
        if seed is None:
            seed = random.randint(0, 999999)
        
        # 根据噪声类型选择预设
        preset_mapping = {
            "dirt": lambda: FastNoisePresets.perlin_fbm(width, height, seed),
            "crack": lambda: FastNoisePresets.cellular_cracks(width, height, seed),
            "scratch": lambda: FastNoisePresets.opensimplex_ridged(width, height, seed),
            "dust": lambda: FastNoisePresets.perlin_fbm(width, height, seed),
            "splat": lambda: FastNoisePresets.cellular_voronoi(width, height, seed),
        }
        
        if noise_type in preset_mapping:
            config = preset_mapping[noise_type]()
        else:
            # 默认配置
            config = FastNoiseConfig(
                width=width,
                height=height,
                noise_type="opensimplex2",
                seed=seed,
                frequency=0.01,
                fractal_type="fbm"
            )
        
        try:
            return self._fastnoise_client.generate(config)
        except Exception as e:
            if self.config.fallback_enabled:
                print(f"⚠ FastNoiseLite生成失败: {e}，切换到预制资源")
                return self._generate_from_asset(width, height, noise_type)
            else:
                raise
    
    def generate_multi_layer(self, width: int, height: int,
                            noise_types: List[str],
                            blend_mode: str = 'multiply') -> np.ndarray:
        """
        生成多层噪声并混合
        
        Args:
            width: 宽度
            height: 高度
            noise_types: 噪声类型列表
            blend_mode: 混合模式 ('multiply', 'add', 'overlay', 'screen')
        
        Returns:
            混合后的噪声纹理
        """
        if not noise_types:
            return np.zeros((height, width), dtype=np.uint8)
        
        # 生成第一层
        result = self.generate(width, height, noise_types[0]).astype(np.float32) / 255.0
        
        # 生成并混合其他层
        for i, noise_type in enumerate(noise_types[1:], start=1):
            layer = self.generate(width, height, noise_type, seed=i).astype(np.float32) / 255.0
            result = self._blend_layers(result, layer, blend_mode)
        
        # 归一化并转换回uint8
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return result
    
    def _blend_layers(self, base: np.ndarray, layer: np.ndarray, mode: str) -> np.ndarray:
        """混合两层噪声"""
        if mode == 'multiply':
            return base * layer
        elif mode == 'add':
            return np.clip(base + layer, 0, 1)
        elif mode == 'overlay':
            mask = base < 0.5
            result = np.zeros_like(base)
            result[mask] = 2 * base[mask] * layer[mask]
            result[~mask] = 1 - 2 * (1 - base[~mask]) * (1 - layer[~mask])
            return result
        elif mode == 'screen':
            return 1 - (1 - base) * (1 - layer)
        else:
            return base


# ============================================================================
# 便捷函数
# ============================================================================

def create_integrated_generator(priority: NoiseSourcePriority = NoiseSourcePriority.BALANCED) -> IntegratedNoiseGenerator:
    """
    创建集成噪声生成器（便捷函数）
    
    Args:
        priority: 噪声源优先级
    
    Returns:
        配置好的集成噪声生成器
    """
    config = IntegratedNoiseConfig(priority=priority)
    return IntegratedNoiseGenerator(config)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    import time
    
    print("测试集成噪声系统...")
    print(f"FastNoiseLite可用: {FASTNOISE_AVAILABLE}")
    
    # 测试不同优先级
    priorities = [
        ("ASSET_FIRST", NoiseSourcePriority.ASSET_FIRST),
        ("FASTNOISE_FIRST", NoiseSourcePriority.FASTNOISE_FIRST),
        ("BALANCED", NoiseSourcePriority.BALANCED),
    ]
    
    noise_types = ["dirt", "crack", "scratch"]
    
    for priority_name, priority in priorities:
        print(f"\n=== 测试 {priority_name} ===")
        generator = create_integrated_generator(priority)
        
        for noise_type in noise_types:
            print(f"  生成 {noise_type} 噪声...")
            start_time = time.time()
            noise = generator.generate(256, 256, noise_type, seed=42)
            elapsed = time.time() - start_time
            
            output_path = f"/tmp/integrated_{priority_name.lower()}_{noise_type}.png"
            Image.fromarray(noise).save(output_path)
            
            print(f"    ✓ 完成，耗时 {elapsed:.3f}秒，形状: {noise.shape}")
    
    # 测试多层混合
    print("\n=== 测试多层混合 ===")
    generator = create_integrated_generator(NoiseSourcePriority.BALANCED)
    multi_layer = generator.generate_multi_layer(256, 256, ["dirt", "crack", "dust"], blend_mode='multiply')
    Image.fromarray(multi_layer).save('/tmp/integrated_multi_layer.png')
    print("  ✓ 多层混合完成")
    
    print("\n✅ 所有测试完成！")
