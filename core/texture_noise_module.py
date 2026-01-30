#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贴图噪声模块 (Texture-Based Noise Module)

基于真实贴图的噪声生成模块，使用高质量的噪声贴图替代程序化生成。
支持 UV 缩放、随机采样、多贴图混合等功能。

贴图类型映射:
    - Cracks: 裂纹/掉漆效果
    - dirt: 污渍效果
    - dust: 灰尘效果
    - Grunge-Dirt: 重度污渍效果
    - scratch: 划痕效果
    - splat: 飞溅/遮挡效果

作者: PCG-USD车牌材质系统
版本: 3.0.0
"""

import os
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any, Union

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


# ============================================================================
# 贴图类型枚举
# ============================================================================

class TextureNoiseType(Enum):
    """贴图噪声类型"""
    CRACKS = "Cracks"           # 裂纹
    DIRT = "dirt"               # 污渍
    DUST = "dust"               # 灰尘
    GRUNGE_DIRT = "Grunge-Dirt" # 重度污渍
    SCRATCH = "scratch"         # 划痕
    SPLAT = "splat"             # 飞溅/遮挡


class NoiseIntensity(Enum):
    """噪声强度等级"""
    NONE = 0
    LIGHT = 1
    MEDIUM = 2
    HEAVY = 3
    EXTREME = 4


class BlendMode(Enum):
    """混合模式"""
    MULTIPLY = auto()       # 正片叠底
    OVERLAY = auto()        # 叠加
    SOFT_LIGHT = auto()     # 柔光
    SCREEN = auto()         # 滤色
    DARKEN = auto()         # 变暗


# ============================================================================
# 配置数据类
# ============================================================================

@dataclass
class TextureNoiseConfig:
    """
    贴图噪声配置
    
    Attributes:
        noise_type: 噪声类型
        enabled: 是否启用
        intensity: 噪声强度
        probability: 应用概率
        uv_scale: UV 缩放范围 (最小, 最大)
        opacity: 不透明度范围 (最小, 最大)
        blend_mode: 混合模式
        invert: 是否反转贴图
        rotation_range: 旋转角度范围
        flip_horizontal: 是否允许水平翻转
        flip_vertical: 是否允许垂直翻转
    """
    noise_type: TextureNoiseType = TextureNoiseType.DIRT
    enabled: bool = True
    intensity: NoiseIntensity = NoiseIntensity.MEDIUM
    probability: float = 0.5
    uv_scale: Tuple[float, float] = (2.0, 6.0)  # 贴图缩放倍数
    opacity: Tuple[float, float] = (0.3, 0.8)
    blend_mode: BlendMode = BlendMode.MULTIPLY
    invert: bool = False
    rotation_range: Tuple[float, float] = (0, 360)
    flip_horizontal: bool = True
    flip_vertical: bool = True


@dataclass
class CompositeTextureNoiseConfig:
    """
    组合贴图噪声配置
    
    用于配置多种贴图噪声的组合应用
    """
    # 各类型噪声配置
    cracks: TextureNoiseConfig = field(default_factory=lambda: TextureNoiseConfig(
        noise_type=TextureNoiseType.CRACKS,
        probability=0.3,
        uv_scale=(3.0, 8.0),
        opacity=(0.2, 0.5),
        blend_mode=BlendMode.MULTIPLY
    ))
    
    dirt: TextureNoiseConfig = field(default_factory=lambda: TextureNoiseConfig(
        noise_type=TextureNoiseType.DIRT,
        probability=0.5,
        uv_scale=(2.0, 5.0),
        opacity=(0.3, 0.7),
        blend_mode=BlendMode.MULTIPLY
    ))
    
    dust: TextureNoiseConfig = field(default_factory=lambda: TextureNoiseConfig(
        noise_type=TextureNoiseType.DUST,
        probability=0.4,
        uv_scale=(1.5, 4.0),
        opacity=(0.2, 0.5),
        blend_mode=BlendMode.SOFT_LIGHT
    ))
    
    grunge_dirt: TextureNoiseConfig = field(default_factory=lambda: TextureNoiseConfig(
        noise_type=TextureNoiseType.GRUNGE_DIRT,
        probability=0.3,
        uv_scale=(2.0, 6.0),
        opacity=(0.4, 0.8),
        blend_mode=BlendMode.MULTIPLY
    ))
    
    scratch: TextureNoiseConfig = field(default_factory=lambda: TextureNoiseConfig(
        noise_type=TextureNoiseType.SCRATCH,
        probability=0.3,
        uv_scale=(2.0, 5.0),
        opacity=(0.2, 0.4),
        blend_mode=BlendMode.OVERLAY
    ))
    
    splat: TextureNoiseConfig = field(default_factory=lambda: TextureNoiseConfig(
        noise_type=TextureNoiseType.SPLAT,
        probability=0.2,
        uv_scale=(4.0, 10.0),
        opacity=(0.5, 0.9),
        blend_mode=BlendMode.DARKEN
    ))
    
    # 全局设置
    global_intensity: NoiseIntensity = NoiseIntensity.MEDIUM
    max_layers: int = 3  # 最大叠加层数
    seed: Optional[int] = None


# ============================================================================
# 贴图管理器
# ============================================================================

class TextureManager:
    """
    贴图管理器
    
    负责加载、缓存和管理噪声贴图资源
    """
    
    # 默认贴图目录
    DEFAULT_TEXTURE_DIR = Path(__file__).parent.parent / "assets" / "noise_textures" / \
                          "MEGA PACK - 500 Practical and useful Stencil imperfection"
    
    def __init__(self, texture_dir: Optional[Path] = None):
        """
        初始化贴图管理器
        
        Args:
            texture_dir: 贴图目录路径，默认使用内置资源
        """
        self.texture_dir = Path(texture_dir) if texture_dir else self.DEFAULT_TEXTURE_DIR
        self._cache: Dict[TextureNoiseType, List[Path]] = {}
        self._image_cache: Dict[str, Image.Image] = {}
        self._scan_textures()
    
    def _scan_textures(self):
        """扫描并索引所有贴图文件"""
        if not self.texture_dir.exists():
            print(f"⚠️ 贴图目录不存在: {self.texture_dir}")
            return
        
        for noise_type in TextureNoiseType:
            subdir = self.texture_dir / noise_type.value
            if subdir.exists():
                textures = list(subdir.glob("*.jpg")) + list(subdir.glob("*.png"))
                self._cache[noise_type] = sorted(textures)
                print(f"📁 {noise_type.value}: 加载 {len(textures)} 张贴图")
            else:
                self._cache[noise_type] = []
    
    def get_random_texture(self, noise_type: TextureNoiseType, 
                           seed: Optional[int] = None) -> Optional[Image.Image]:
        """
        获取指定类型的随机贴图
        
        Args:
            noise_type: 噪声类型
            seed: 随机种子
            
        Returns:
            PIL Image 对象，如果没有可用贴图则返回 None
        """
        textures = self._cache.get(noise_type, [])
        if not textures:
            return None
        
        if seed is not None:
            random.seed(seed)
        
        texture_path = random.choice(textures)
        
        # 使用缓存
        cache_key = str(texture_path)
        if cache_key not in self._image_cache:
            try:
                self._image_cache[cache_key] = Image.open(texture_path).convert('L')
            except Exception as e:
                print(f"⚠️ 加载贴图失败: {texture_path}, {e}")
                return None
        
        return self._image_cache[cache_key].copy()
    
    def get_texture_count(self, noise_type: TextureNoiseType) -> int:
        """获取指定类型的贴图数量"""
        return len(self._cache.get(noise_type, []))
    
    def get_all_counts(self) -> Dict[str, int]:
        """获取所有类型的贴图数量"""
        return {t.value: len(self._cache.get(t, [])) for t in TextureNoiseType}


# ============================================================================
# 贴图噪声生成器
# ============================================================================

class TextureNoiseGenerator:
    """
    贴图噪声生成器
    
    使用真实贴图生成噪声效果，支持 UV 缩放和随机采样
    """
    
    def __init__(self, texture_manager: Optional[TextureManager] = None,
                 config: Optional[CompositeTextureNoiseConfig] = None):
        """
        初始化贴图噪声生成器
        
        Args:
            texture_manager: 贴图管理器实例
            config: 组合噪声配置
        """
        self.texture_manager = texture_manager or TextureManager()
        self.config = config or CompositeTextureNoiseConfig()
        self._rng = random.Random(self.config.seed)
    
    def _get_config_for_type(self, noise_type: TextureNoiseType) -> TextureNoiseConfig:
        """获取指定类型的配置"""
        config_map = {
            TextureNoiseType.CRACKS: self.config.cracks,
            TextureNoiseType.DIRT: self.config.dirt,
            TextureNoiseType.DUST: self.config.dust,
            TextureNoiseType.GRUNGE_DIRT: self.config.grunge_dirt,
            TextureNoiseType.SCRATCH: self.config.scratch,
            TextureNoiseType.SPLAT: self.config.splat,
        }
        return config_map.get(noise_type, self.config.dirt)
    
    def _get_intensity_multiplier(self) -> float:
        """根据全局强度获取乘数"""
        multipliers = {
            NoiseIntensity.NONE: 0.0,
            NoiseIntensity.LIGHT: 0.5,
            NoiseIntensity.MEDIUM: 1.0,
            NoiseIntensity.HEAVY: 1.5,
            NoiseIntensity.EXTREME: 2.0,
        }
        return multipliers.get(self.config.global_intensity, 1.0)
    
    def _sample_texture_region(self, texture: Image.Image, 
                                target_size: Tuple[int, int],
                                config: TextureNoiseConfig) -> Image.Image:
        """
        从贴图中采样一个区域
        
        Args:
            texture: 原始贴图
            target_size: 目标尺寸 (width, height)
            config: 噪声配置
            
        Returns:
            采样后的贴图区域
        """
        tex_w, tex_h = texture.size
        target_w, target_h = target_size
        
        # 计算 UV 缩放
        uv_scale = self._rng.uniform(config.uv_scale[0], config.uv_scale[1])
        
        # 采样区域大小（缩放后的目标尺寸）
        sample_w = int(target_w * uv_scale)
        sample_h = int(target_h * uv_scale)
        
        # 确保采样区域不超过贴图尺寸
        sample_w = min(sample_w, tex_w)
        sample_h = min(sample_h, tex_h)
        
        # 随机选择采样起点
        max_x = max(0, tex_w - sample_w)
        max_y = max(0, tex_h - sample_h)
        start_x = self._rng.randint(0, max_x) if max_x > 0 else 0
        start_y = self._rng.randint(0, max_y) if max_y > 0 else 0
        
        # 裁剪采样区域
        region = texture.crop((start_x, start_y, start_x + sample_w, start_y + sample_h))
        
        # 缩放到目标尺寸
        region = region.resize(target_size, Image.Resampling.LANCZOS)
        
        # 应用变换
        if config.flip_horizontal and self._rng.random() > 0.5:
            region = ImageOps.mirror(region)
        
        if config.flip_vertical and self._rng.random() > 0.5:
            region = ImageOps.flip(region)
        
        # 旋转
        rotation = self._rng.uniform(config.rotation_range[0], config.rotation_range[1])
        if rotation != 0:
            region = region.rotate(rotation, resample=Image.Resampling.BILINEAR, expand=False)
        
        # 反转
        if config.invert:
            region = ImageOps.invert(region)
        
        return region
    
    def _blend_texture(self, base: Image.Image, texture: Image.Image,
                       config: TextureNoiseConfig) -> Image.Image:
        """
        将贴图混合到基础图像
        
        Args:
            base: 基础图像 (RGB)
            texture: 噪声贴图 (L 灰度)
            config: 噪声配置
            
        Returns:
            混合后的图像
        """
        # 计算不透明度
        opacity = self._rng.uniform(config.opacity[0], config.opacity[1])
        opacity *= self._get_intensity_multiplier()
        opacity = min(opacity, 1.0)
        
        # 将灰度贴图转换为 RGB
        if base.mode == 'RGB':
            texture_rgb = texture.convert('RGB')
        elif base.mode == 'RGBA':
            texture_rgb = texture.convert('RGBA')
        else:
            texture_rgb = texture
        
        # 根据混合模式应用
        if config.blend_mode == BlendMode.MULTIPLY:
            # 正片叠底：变暗效果
            result = self._blend_multiply(base, texture_rgb, opacity)
        elif config.blend_mode == BlendMode.OVERLAY:
            # 叠加：增强对比度
            result = self._blend_overlay(base, texture_rgb, opacity)
        elif config.blend_mode == BlendMode.SOFT_LIGHT:
            # 柔光：柔和效果
            result = self._blend_soft_light(base, texture_rgb, opacity)
        elif config.blend_mode == BlendMode.SCREEN:
            # 滤色：变亮效果
            result = self._blend_screen(base, texture_rgb, opacity)
        elif config.blend_mode == BlendMode.DARKEN:
            # 变暗：取最小值
            result = self._blend_darken(base, texture_rgb, opacity)
        else:
            result = base
        
        return result
    
    def _blend_multiply(self, base: Image.Image, texture: Image.Image, 
                        opacity: float) -> Image.Image:
        """正片叠底混合"""
        base_arr = np.array(base, dtype=np.float32) / 255.0
        tex_arr = np.array(texture, dtype=np.float32) / 255.0
        
        # 正片叠底公式: result = base * texture
        result = base_arr * tex_arr
        
        # 应用不透明度
        result = base_arr * (1 - opacity) + result * opacity
        
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return Image.fromarray(result, mode=base.mode)
    
    def _blend_overlay(self, base: Image.Image, texture: Image.Image,
                       opacity: float) -> Image.Image:
        """叠加混合"""
        base_arr = np.array(base, dtype=np.float32) / 255.0
        tex_arr = np.array(texture, dtype=np.float32) / 255.0
        
        # 叠加公式
        mask = base_arr < 0.5
        result = np.where(mask, 
                         2 * base_arr * tex_arr,
                         1 - 2 * (1 - base_arr) * (1 - tex_arr))
        
        result = base_arr * (1 - opacity) + result * opacity
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return Image.fromarray(result, mode=base.mode)
    
    def _blend_soft_light(self, base: Image.Image, texture: Image.Image,
                          opacity: float) -> Image.Image:
        """柔光混合"""
        base_arr = np.array(base, dtype=np.float32) / 255.0
        tex_arr = np.array(texture, dtype=np.float32) / 255.0
        
        # 柔光公式
        mask = tex_arr < 0.5
        result = np.where(mask,
                         base_arr - (1 - 2 * tex_arr) * base_arr * (1 - base_arr),
                         base_arr + (2 * tex_arr - 1) * (self._d(base_arr) - base_arr))
        
        result = base_arr * (1 - opacity) + result * opacity
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return Image.fromarray(result, mode=base.mode)
    
    def _d(self, x: np.ndarray) -> np.ndarray:
        """柔光混合的辅助函数"""
        mask = x <= 0.25
        return np.where(mask,
                       ((16 * x - 12) * x + 4) * x,
                       np.sqrt(x))
    
    def _blend_screen(self, base: Image.Image, texture: Image.Image,
                      opacity: float) -> Image.Image:
        """滤色混合"""
        base_arr = np.array(base, dtype=np.float32) / 255.0
        tex_arr = np.array(texture, dtype=np.float32) / 255.0
        
        # 滤色公式: result = 1 - (1 - base) * (1 - texture)
        result = 1 - (1 - base_arr) * (1 - tex_arr)
        
        result = base_arr * (1 - opacity) + result * opacity
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return Image.fromarray(result, mode=base.mode)
    
    def _blend_darken(self, base: Image.Image, texture: Image.Image,
                      opacity: float) -> Image.Image:
        """变暗混合"""
        base_arr = np.array(base, dtype=np.float32) / 255.0
        tex_arr = np.array(texture, dtype=np.float32) / 255.0
        
        # 变暗公式: result = min(base, texture)
        result = np.minimum(base_arr, tex_arr)
        
        result = base_arr * (1 - opacity) + result * opacity
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return Image.fromarray(result, mode=base.mode)
    
    def apply_single_noise(self, image: Image.Image, 
                           noise_type: TextureNoiseType) -> Image.Image:
        """
        应用单一类型的噪声
        
        Args:
            image: 输入图像
            noise_type: 噪声类型
            
        Returns:
            应用噪声后的图像
        """
        config = self._get_config_for_type(noise_type)
        
        if not config.enabled:
            return image
        
        if self._rng.random() > config.probability:
            return image
        
        # 获取随机贴图
        texture = self.texture_manager.get_random_texture(noise_type)
        if texture is None:
            return image
        
        # 采样贴图区域
        sampled = self._sample_texture_region(texture, image.size, config)
        
        # 混合贴图
        result = self._blend_texture(image, sampled, config)
        
        return result
    
    def apply_random_noise(self, image: Image.Image, 
                           num_layers: Optional[int] = None) -> Image.Image:
        """
        应用随机组合的噪声
        
        Args:
            image: 输入图像
            num_layers: 噪声层数，默认使用配置的最大层数
            
        Returns:
            应用噪声后的图像
        """
        if self.config.global_intensity == NoiseIntensity.NONE:
            return image
        
        # 确定层数
        max_layers = num_layers or self.config.max_layers
        actual_layers = self._rng.randint(1, max_layers + 1)
        
        # 根据强度调整层数
        intensity_mult = self._get_intensity_multiplier()
        actual_layers = max(1, int(actual_layers * intensity_mult))
        
        # 随机选择噪声类型
        available_types = [t for t in TextureNoiseType 
                          if self.texture_manager.get_texture_count(t) > 0]
        
        if not available_types:
            return image
        
        result = image.copy()
        
        for _ in range(actual_layers):
            noise_type = self._rng.choice(available_types)
            result = self.apply_single_noise(result, noise_type)
        
        return result
    
    def apply_preset(self, image: Image.Image, preset: str) -> Image.Image:
        """
        应用预设噪声配置
        
        Args:
            image: 输入图像
            preset: 预设名称 ('clean', 'light', 'medium', 'heavy', 'extreme', 'random')
            
        Returns:
            应用噪声后的图像
        """
        preset_configs = {
            'clean': NoiseIntensity.NONE,
            'light': NoiseIntensity.LIGHT,
            'medium': NoiseIntensity.MEDIUM,
            'heavy': NoiseIntensity.HEAVY,
            'extreme': NoiseIntensity.EXTREME,
        }
        
        if preset == 'random':
            preset = self._rng.choice(['light', 'medium', 'heavy'])
        
        self.config.global_intensity = preset_configs.get(preset, NoiseIntensity.MEDIUM)
        
        return self.apply_random_noise(image)


# ============================================================================
# 便捷函数
# ============================================================================

def apply_texture_noise(image: Image.Image, 
                        preset: str = 'medium',
                        texture_dir: Optional[Path] = None,
                        seed: Optional[int] = None) -> Image.Image:
    """
    便捷函数：应用贴图噪声
    
    Args:
        image: 输入图像
        preset: 预设名称
        texture_dir: 贴图目录
        seed: 随机种子
        
    Returns:
        应用噪声后的图像
    """
    config = CompositeTextureNoiseConfig(seed=seed)
    texture_manager = TextureManager(texture_dir)
    generator = TextureNoiseGenerator(texture_manager, config)
    
    return generator.apply_preset(image, preset)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("贴图噪声模块测试")
    print("=" * 60)
    
    # 初始化贴图管理器
    manager = TextureManager()
    print("\n贴图统计:")
    for noise_type, count in manager.get_all_counts().items():
        print(f"  {noise_type}: {count} 张")
    
    # 测试噪声生成
    print("\n测试噪声生成...")
    generator = TextureNoiseGenerator(manager)
    
    # 创建测试图像
    test_image = Image.new('RGB', (440, 140), color=(30, 144, 255))
    
    # 应用不同预设
    for preset in ['light', 'medium', 'heavy']:
        result = generator.apply_preset(test_image.copy(), preset)
        print(f"  {preset}: 生成成功")
    
    print("\n✅ 测试完成")
