#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强噪声模块 (Enhanced Noise Module)

将程序化噪声生成器集成到现有噪声系统中
提供统一的接口，支持预制贴图和程序化生成两种方式

作者: PCG-USD车牌材质系统
版本: 1.0.0
"""

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional, List, Tuple, Union

import numpy as np
from PIL import Image

# 导入现有噪声模块
from .noise_module import (
    NoiseType, NoiseIntensity, NoiseConfig,
    BaseNoiseGenerator, StainNoiseGenerator, ShadowNoiseGenerator,
    PaintPeelingNoiseGenerator, OcclusionNoiseGenerator
)

# 导入程序化噪声模块
from .procedural_noise_module import (
    ProceduralNoiseGenerator, ProceduralNoiseConfig,
    ProceduralNoiseType, FractalType,
    CellularDistanceFunction, CellularReturnType
)


# ============================================================================
# 噪声源类型
# ============================================================================

class NoiseSourceType(Enum):
    """噪声源类型"""
    ASSET = auto()          # 使用预制资源（extracted目录中的图片）
    PROCEDURAL = auto()     # 使用程序化生成
    MIXED = auto()          # 混合使用（随机选择）


# ============================================================================
# 增强噪声配置
# ============================================================================

@dataclass
class EnhancedNoiseConfig:
    """
    增强噪声配置
    
    Attributes:
        source_type: 噪声源类型
        asset_path: 预制资源路径（当source_type为ASSET或MIXED时使用）
        procedural_config: 程序化噪声配置（当source_type为PROCEDURAL或MIXED时使用）
        mix_ratio: 混合比例（当source_type为MIXED时，ASSET的比例，0.0-1.0）
        cache_procedural: 是否缓存程序化生成的噪声
    """
    source_type: NoiseSourceType = NoiseSourceType.MIXED
    asset_path: Optional[Path] = None
    procedural_config: Optional[ProceduralNoiseConfig] = None
    mix_ratio: float = 0.5  # 50% ASSET, 50% PROCEDURAL
    cache_procedural: bool = True


# ============================================================================
# 增强噪声生成器
# ============================================================================

class EnhancedNoiseGenerator:
    """
    增强噪声生成器
    
    整合预制资源和程序化生成，提供统一的噪声生成接口
    """
    
    def __init__(self, config: EnhancedNoiseConfig = None):
        """
        初始化增强噪声生成器
        
        Args:
            config: 增强噪声配置
        """
        self.config = config or EnhancedNoiseConfig()
        self._procedural_cache = {}
        self._asset_cache = {}
        
        # 初始化程序化噪声生成器
        if self.config.procedural_config:
            self.procedural_generator = ProceduralNoiseGenerator(
                self.config.procedural_config
            )
        else:
            # 使用默认配置
            self.procedural_generator = ProceduralNoiseGenerator()
    
    def generate_noise_texture(self, width: int, height: int,
                              seed: Optional[int] = None) -> np.ndarray:
        """
        生成噪声纹理
        
        Args:
            width: 纹理宽度
            height: 纹理高度
            seed: 随机种子
        
        Returns:
            噪声纹理数组 (height, width)，uint8格式，值范围 [0, 255]
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        
        if self.config.source_type == NoiseSourceType.ASSET:
            return self._load_asset_noise(width, height)
        elif self.config.source_type == NoiseSourceType.PROCEDURAL:
            return self._generate_procedural_noise(width, height, seed)
        elif self.config.source_type == NoiseSourceType.MIXED:
            if random.random() < self.config.mix_ratio:
                return self._load_asset_noise(width, height)
            else:
                return self._generate_procedural_noise(width, height, seed)
        else:
            return self._generate_procedural_noise(width, height, seed)
    
    def _load_asset_noise(self, width: int, height: int) -> np.ndarray:
        """
        从预制资源加载噪声
        
        Args:
            width: 目标宽度
            height: 目标高度
        
        Returns:
            噪声纹理数组
        """
        if self.config.asset_path and self.config.asset_path.exists():
            # 从指定路径加载
            asset_files = list(self.config.asset_path.glob("**/*.jpg"))
            asset_files.extend(list(self.config.asset_path.glob("**/*.png")))
        else:
            # 从默认extracted目录加载
            default_path = Path(__file__).parent.parent / "assets" / "noise_textures" / "extracted"
            if default_path.exists():
                asset_files = list(default_path.glob("**/*.jpg"))
                asset_files.extend(list(default_path.glob("**/*.png")))
            else:
                # 如果没有预制资源，回退到程序化生成
                return self._generate_procedural_noise(width, height)
        
        if not asset_files:
            # 如果没有找到资源，回退到程序化生成
            return self._generate_procedural_noise(width, height)
        
        # 随机选择一个资源
        selected_file = random.choice(asset_files)
        
        # 检查缓存
        cache_key = f"{selected_file}_{width}_{height}"
        if cache_key in self._asset_cache:
            return self._asset_cache[cache_key].copy()
        
        # 加载并调整大小
        img = Image.open(selected_file).convert('L')
        img = img.resize((width, height), Image.LANCZOS)
        noise_array = np.array(img, dtype=np.uint8)
        
        # 缓存
        self._asset_cache[cache_key] = noise_array
        
        return noise_array.copy()
    
    def _generate_procedural_noise(self, width: int, height: int,
                                   seed: Optional[int] = None) -> np.ndarray:
        """
        生成程序化噪声
        
        Args:
            width: 宽度
            height: 高度
            seed: 随机种子
        
        Returns:
            噪声纹理数组
        """
        # 检查缓存
        if self.config.cache_procedural:
            cache_key = f"{width}_{height}_{seed}"
            if cache_key in self._procedural_cache:
                return self._procedural_cache[cache_key].copy()
        
        # 如果提供了seed，更新生成器的seed
        if seed is not None:
            self.procedural_generator.config.seed = seed
            self.procedural_generator._setup_generators()
        
        # 生成噪声
        noise_array = self.procedural_generator.generate_2d_uint8(width, height)
        
        # 缓存
        if self.config.cache_procedural:
            self._procedural_cache[cache_key] = noise_array
        
        return noise_array.copy()
    
    def generate_multi_layer_noise(self, width: int, height: int,
                                   num_layers: int = 3,
                                   blend_mode: str = 'multiply') -> np.ndarray:
        """
        生成多层噪声并混合
        
        Args:
            width: 宽度
            height: 高度
            num_layers: 层数
            blend_mode: 混合模式 ('multiply', 'add', 'overlay', 'screen')
        
        Returns:
            混合后的噪声纹理
        """
        if num_layers <= 0:
            return np.zeros((height, width), dtype=np.uint8)
        
        # 生成第一层
        result = self.generate_noise_texture(width, height).astype(np.float32) / 255.0
        
        # 生成并混合其他层
        for i in range(1, num_layers):
            layer = self.generate_noise_texture(width, height, seed=i).astype(np.float32) / 255.0
            result = self._blend_layers(result, layer, blend_mode)
        
        # 归一化并转换回uint8
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return result
    
    def _blend_layers(self, base: np.ndarray, layer: np.ndarray,
                     mode: str) -> np.ndarray:
        """
        混合两层噪声
        
        Args:
            base: 基础层 (值范围 [0, 1])
            layer: 叠加层 (值范围 [0, 1])
            mode: 混合模式
        
        Returns:
            混合后的结果 (值范围 [0, 1])
        """
        if mode == 'multiply':
            return base * layer
        elif mode == 'add':
            return np.clip(base + layer, 0, 1)
        elif mode == 'overlay':
            # Photoshop风格的overlay混合
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
# 噪声预设
# ============================================================================

class NoisePresets:
    """噪声预设配置"""
    
    @staticmethod
    def get_dirt_noise() -> EnhancedNoiseConfig:
        """污垢噪声预设"""
        procedural_config = ProceduralNoiseConfig(
            noise_type=ProceduralNoiseType.PERLIN,
            frequency=0.02,
            octaves=4,
            fractal_type=FractalType.FBM
        )
        return EnhancedNoiseConfig(
            source_type=NoiseSourceType.MIXED,
            procedural_config=procedural_config,
            mix_ratio=0.7  # 70% 使用预制资源
        )
    
    @staticmethod
    def get_crack_noise() -> EnhancedNoiseConfig:
        """裂纹噪声预设"""
        procedural_config = ProceduralNoiseConfig(
            noise_type=ProceduralNoiseType.CELLULAR,
            frequency=0.03,
            cellular_return_type=CellularReturnType.DISTANCE2_SUB
        )
        return EnhancedNoiseConfig(
            source_type=NoiseSourceType.MIXED,
            procedural_config=procedural_config,
            mix_ratio=0.6
        )
    
    @staticmethod
    def get_scratch_noise() -> EnhancedNoiseConfig:
        """划痕噪声预设"""
        procedural_config = ProceduralNoiseConfig(
            noise_type=ProceduralNoiseType.OPENSIMPLEX,
            frequency=0.01,
            octaves=3,
            fractal_type=FractalType.RIDGED
        )
        return EnhancedNoiseConfig(
            source_type=NoiseSourceType.MIXED,
            procedural_config=procedural_config,
            mix_ratio=0.8
        )
    
    @staticmethod
    def get_dust_noise() -> EnhancedNoiseConfig:
        """灰尘噪声预设"""
        procedural_config = ProceduralNoiseConfig(
            noise_type=ProceduralNoiseType.PERLIN,
            frequency=0.05,
            octaves=8,
            fractal_type=FractalType.FBM
        )
        return EnhancedNoiseConfig(
            source_type=NoiseSourceType.MIXED,
            procedural_config=procedural_config,
            mix_ratio=0.5
        )
    
    @staticmethod
    def get_splat_noise() -> EnhancedNoiseConfig:
        """飞溅噪声预设"""
        procedural_config = ProceduralNoiseConfig(
            noise_type=ProceduralNoiseType.CELLULAR,
            frequency=0.02,
            cellular_return_type=CellularReturnType.DISTANCE
        )
        return EnhancedNoiseConfig(
            source_type=NoiseSourceType.MIXED,
            procedural_config=procedural_config,
            mix_ratio=0.7
        )


# ============================================================================
# 便捷函数
# ============================================================================

def create_noise_generator(noise_type: str = 'dirt',
                          source_type: NoiseSourceType = NoiseSourceType.MIXED) -> EnhancedNoiseGenerator:
    """
    创建噪声生成器（便捷函数）
    
    Args:
        noise_type: 噪声类型 ('dirt', 'crack', 'scratch', 'dust', 'splat')
        source_type: 噪声源类型
    
    Returns:
        配置好的增强噪声生成器
    """
    presets = {
        'dirt': NoisePresets.get_dirt_noise,
        'crack': NoisePresets.get_crack_noise,
        'scratch': NoisePresets.get_scratch_noise,
        'dust': NoisePresets.get_dust_noise,
        'splat': NoisePresets.get_splat_noise,
    }
    
    if noise_type in presets:
        config = presets[noise_type]()
        config.source_type = source_type
        return EnhancedNoiseGenerator(config)
    else:
        # 默认配置
        return EnhancedNoiseGenerator()


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    from PIL import Image
    import time
    
    print("测试增强噪声生成器...")
    
    # 测试不同噪声类型
    noise_types = ['dirt', 'crack', 'scratch', 'dust', 'splat']
    
    for noise_type in noise_types:
        print(f"\n生成 {noise_type} 噪声...")
        
        # 测试ASSET模式
        print(f"  - ASSET模式")
        start_time = time.time()
        generator = create_noise_generator(noise_type, NoiseSourceType.ASSET)
        noise = generator.generate_noise_texture(512, 512)
        elapsed = time.time() - start_time
        Image.fromarray(noise).save(f'/tmp/test_{noise_type}_asset.png')
        print(f"    完成，耗时 {elapsed:.2f}秒")
        
        # 测试PROCEDURAL模式
        print(f"  - PROCEDURAL模式")
        start_time = time.time()
        generator = create_noise_generator(noise_type, NoiseSourceType.PROCEDURAL)
        noise = generator.generate_noise_texture(512, 512, seed=42)
        elapsed = time.time() - start_time
        Image.fromarray(noise).save(f'/tmp/test_{noise_type}_procedural.png')
        print(f"    完成，耗时 {elapsed:.2f}秒")
        
        # 测试MIXED模式
        print(f"  - MIXED模式")
        start_time = time.time()
        generator = create_noise_generator(noise_type, NoiseSourceType.MIXED)
        noise = generator.generate_noise_texture(512, 512)
        elapsed = time.time() - start_time
        Image.fromarray(noise).save(f'/tmp/test_{noise_type}_mixed.png')
        print(f"    完成，耗时 {elapsed:.2f}秒")
    
    # 测试多层混合
    print("\n生成多层混合噪声...")
    generator = create_noise_generator('dirt', NoiseSourceType.MIXED)
    multi_layer = generator.generate_multi_layer_noise(512, 512, num_layers=3, blend_mode='multiply')
    Image.fromarray(multi_layer).save('/tmp/test_multi_layer.png')
    print("  完成")
    
    print("\n✅ 所有测试完成！")
    print("生成的图片保存在 /tmp/ 目录下")
