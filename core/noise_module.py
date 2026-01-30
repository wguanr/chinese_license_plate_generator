#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
噪声模块 (Noise Module)

独立的噪声生成模块，用于为车牌图像添加多种真实感噪声效果。
遵循职责分离原则，只处理噪声相关的配置和生成。

噪声类型:
    - 污渍 (Stain): 模拟泥土、灰尘、油污等污染
    - 阴影 (Shadow): 模拟光照不均匀产生的阴影效果
    - 掉漆 (PaintPeeling): 模拟车牌老化、漆面脱落
    - 异物遮挡 (Occlusion): 模拟树叶、贴纸、螺丝等遮挡物

作者: PCG-USD车牌材质系统
版本: 2.0.0
"""

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Tuple, Optional, Dict, Any, Union
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


# ============================================================================
# 噪声类型枚举
# ============================================================================

class NoiseType(Enum):
    """噪声类型枚举"""
    STAIN = auto()          # 污渍
    SHADOW = auto()         # 阴影
    PAINT_PEELING = auto()  # 掉漆
    OCCLUSION = auto()      # 异物遮挡
    SCRATCH = auto()        # 刮痕
    DUST = auto()           # 灰尘
    WATER_STAIN = auto()    # 水渍
    RUST = auto()           # 锈迹


class NoiseIntensity(Enum):
    """噪声强度等级"""
    NONE = 0
    LIGHT = 1
    MEDIUM = 2
    HEAVY = 3
    EXTREME = 4


# ============================================================================
# 噪声配置数据类
# ============================================================================

@dataclass
class NoiseConfig:
    """
    噪声配置基类
    
    Attributes:
        enabled: 是否启用该噪声
        intensity: 噪声强度等级
        probability: 应用概率 (0.0-1.0)
        seed: 随机种子，用于可重复生成
    """
    enabled: bool = True
    intensity: NoiseIntensity = NoiseIntensity.MEDIUM
    probability: float = 0.5
    seed: Optional[int] = None


@dataclass
class StainConfig(NoiseConfig):
    """
    污渍噪声配置
    
    Attributes:
        stain_types: 污渍类型列表 ('mud', 'oil', 'dust', 'water')
        num_spots: 污渍斑点数量范围
        spot_size_range: 斑点大小范围
        color_variation: 颜色变化范围
        edge_blur: 边缘模糊程度
    """
    stain_types: List[str] = field(default_factory=lambda: ['mud', 'oil', 'dust'])
    num_spots: Tuple[int, int] = (10, 50)
    spot_size_range: Tuple[int, int] = (5, 30)
    color_variation: float = 0.3
    edge_blur: float = 2.0


@dataclass
class ShadowConfig(NoiseConfig):
    """
    阴影噪声配置
    
    Attributes:
        shadow_types: 阴影类型列表 ('gradient', 'spot', 'edge', 'vignette')
        darkness: 阴影深度 (0.0-1.0)
        softness: 阴影柔和度
        direction: 阴影方向角度 (度)
        coverage: 阴影覆盖面积比例
    """
    shadow_types: List[str] = field(default_factory=lambda: ['gradient', 'spot', 'edge'])
    darkness: float = 0.4
    softness: float = 20.0
    direction: float = 45.0
    coverage: float = 0.3


@dataclass
class PaintPeelingConfig(NoiseConfig):
    """
    掉漆噪声配置
    
    Attributes:
        peeling_types: 掉漆类型列表 ('edge', 'spot', 'crack', 'flake')
        num_areas: 掉漆区域数量范围
        area_size_range: 区域大小范围
        edge_roughness: 边缘粗糙度
        base_color: 底层颜色 (露出的金属/底漆颜色)
    """
    peeling_types: List[str] = field(default_factory=lambda: ['edge', 'spot', 'flake'])
    num_areas: Tuple[int, int] = (3, 15)
    area_size_range: Tuple[int, int] = (10, 50)
    edge_roughness: float = 0.5
    base_color: Tuple[int, int, int] = (80, 80, 80)


@dataclass
class OcclusionConfig(NoiseConfig):
    """
    异物遮挡噪声配置
    
    Attributes:
        occlusion_types: 遮挡物类型列表 ('leaf', 'sticker', 'tape', 'dirt_blob', 'screw')
        num_objects: 遮挡物数量范围
        size_range: 遮挡物大小范围
        opacity_range: 不透明度范围
        position_bias: 位置偏好 ('random', 'edge', 'corner', 'center')
    """
    occlusion_types: List[str] = field(default_factory=lambda: ['leaf', 'sticker', 'dirt_blob'])
    num_objects: Tuple[int, int] = (1, 5)
    size_range: Tuple[int, int] = (20, 80)
    opacity_range: Tuple[float, float] = (0.6, 1.0)
    position_bias: str = 'random'


@dataclass
class CompositeNoiseConfig:
    """
    组合噪声配置
    
    用于配置多种噪声的组合应用
    """
    stain: StainConfig = field(default_factory=StainConfig)
    shadow: ShadowConfig = field(default_factory=ShadowConfig)
    paint_peeling: PaintPeelingConfig = field(default_factory=PaintPeelingConfig)
    occlusion: OcclusionConfig = field(default_factory=OcclusionConfig)
    
    # 全局设置
    global_intensity: NoiseIntensity = NoiseIntensity.MEDIUM
    randomize: bool = True
    seed: Optional[int] = None


# ============================================================================
# 噪声生成器基类
# ============================================================================

class BaseNoiseGenerator(ABC):
    """噪声生成器抽象基类"""
    
    def __init__(self, config: NoiseConfig):
        """
        初始化噪声生成器
        
        Args:
            config: 噪声配置对象
        """
        self.config = config
        self._rng = np.random.default_rng(config.seed)
    
    @abstractmethod
    def generate(self, width: int, height: int) -> np.ndarray:
        """
        生成噪声遮罩
        
        Args:
            width: 图像宽度
            height: 图像高度
            
        Returns:
            噪声遮罩数组 (height, width)，值范围 [0, 1]
        """
        pass
    
    @abstractmethod
    def apply(self, image: np.ndarray) -> np.ndarray:
        """
        将噪声应用到图像
        
        Args:
            image: 输入图像数组 (height, width, channels)
            
        Returns:
            应用噪声后的图像数组
        """
        pass
    
    def _get_intensity_multiplier(self) -> float:
        """根据强度等级获取乘数"""
        multipliers = {
            NoiseIntensity.NONE: 0.0,
            NoiseIntensity.LIGHT: 0.5,
            NoiseIntensity.MEDIUM: 1.0,
            NoiseIntensity.HEAVY: 1.5,
            NoiseIntensity.EXTREME: 2.0,
        }
        return multipliers.get(self.config.intensity, 1.0)
    
    def _should_apply(self) -> bool:
        """根据概率决定是否应用噪声"""
        if not self.config.enabled:
            return False
        return self._rng.random() < self.config.probability


# ============================================================================
# 污渍噪声生成器
# ============================================================================

class StainNoiseGenerator(BaseNoiseGenerator):
    """污渍噪声生成器"""
    
    def __init__(self, config: StainConfig = None):
        super().__init__(config or StainConfig())
        self.config: StainConfig = self.config
    
    def generate(self, width: int, height: int) -> np.ndarray:
        """生成污渍噪声遮罩"""
        mask = np.zeros((height, width), dtype=np.float32)
        
        if not self._should_apply():
            return mask
        
        intensity_mult = self._get_intensity_multiplier()
        num_spots = self._rng.integers(
            int(self.config.num_spots[0] * intensity_mult),
            int(self.config.num_spots[1] * intensity_mult) + 1
        )
        
        for _ in range(num_spots):
            stain_type = self._rng.choice(self.config.stain_types)
            mask = self._add_stain_spot(mask, width, height, stain_type)
        
        # 应用高斯模糊使边缘更自然
        if self.config.edge_blur > 0:
            from scipy.ndimage import gaussian_filter
            mask = gaussian_filter(mask, sigma=self.config.edge_blur)
        
        return np.clip(mask, 0, 1)
    
    def _add_stain_spot(self, mask: np.ndarray, width: int, height: int, 
                        stain_type: str) -> np.ndarray:
        """添加单个污渍斑点"""
        cx = self._rng.integers(0, width)
        cy = self._rng.integers(0, height)
        
        size = self._rng.integers(
            self.config.spot_size_range[0],
            self.config.spot_size_range[1] + 1
        )
        
        # 根据污渍类型调整形状
        if stain_type == 'mud':
            # 泥土：不规则大块
            mask = self._draw_irregular_blob(mask, cx, cy, size, 0.8)
        elif stain_type == 'oil':
            # 油污：圆形扩散
            mask = self._draw_circular_gradient(mask, cx, cy, size, 0.9)
        elif stain_type == 'dust':
            # 灰尘：细小颗粒群
            mask = self._draw_dust_particles(mask, cx, cy, size, 0.5)
        elif stain_type == 'water':
            # 水渍：环形痕迹
            mask = self._draw_water_ring(mask, cx, cy, size, 0.6)
        
        return mask
    
    def _draw_irregular_blob(self, mask: np.ndarray, cx: int, cy: int, 
                             size: int, intensity: float) -> np.ndarray:
        """绘制不规则斑块"""
        height, width = mask.shape
        
        # 使用多个重叠的椭圆创建不规则形状
        num_ellipses = self._rng.integers(3, 7)
        
        for _ in range(num_ellipses):
            offset_x = self._rng.integers(-size // 3, size // 3 + 1)
            offset_y = self._rng.integers(-size // 3, size // 3 + 1)
            
            rx = self._rng.integers(size // 3, size)
            ry = self._rng.integers(size // 3, size)
            
            for y in range(max(0, cy + offset_y - ry), min(height, cy + offset_y + ry + 1)):
                for x in range(max(0, cx + offset_x - rx), min(width, cx + offset_x + rx + 1)):
                    dx = (x - (cx + offset_x)) / rx if rx > 0 else 0
                    dy = (y - (cy + offset_y)) / ry if ry > 0 else 0
                    dist = dx * dx + dy * dy
                    
                    if dist <= 1:
                        fade = (1 - dist) * intensity
                        fade *= self._rng.uniform(0.7, 1.0)  # 添加随机变化
                        mask[y, x] = max(mask[y, x], fade)
        
        return mask
    
    def _draw_circular_gradient(self, mask: np.ndarray, cx: int, cy: int,
                                radius: int, intensity: float) -> np.ndarray:
        """绘制圆形渐变"""
        height, width = mask.shape
        
        for y in range(max(0, cy - radius), min(height, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(width, cx + radius + 1)):
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist <= radius:
                    fade = (1 - dist / radius) ** 2 * intensity
                    mask[y, x] = max(mask[y, x], fade)
        
        return mask
    
    def _draw_dust_particles(self, mask: np.ndarray, cx: int, cy: int,
                             spread: int, intensity: float) -> np.ndarray:
        """绘制灰尘颗粒"""
        height, width = mask.shape
        num_particles = self._rng.integers(20, 50)
        
        for _ in range(num_particles):
            px = cx + self._rng.integers(-spread, spread + 1)
            py = cy + self._rng.integers(-spread, spread + 1)
            
            if 0 <= px < width and 0 <= py < height:
                particle_size = self._rng.integers(1, 4)
                particle_intensity = intensity * self._rng.uniform(0.3, 1.0)
                
                for dy in range(-particle_size, particle_size + 1):
                    for dx in range(-particle_size, particle_size + 1):
                        nx, ny = px + dx, py + dy
                        if 0 <= nx < width and 0 <= ny < height:
                            dist = math.sqrt(dx * dx + dy * dy)
                            if dist <= particle_size:
                                fade = (1 - dist / particle_size) * particle_intensity
                                mask[ny, nx] = max(mask[ny, nx], fade)
        
        return mask
    
    def _draw_water_ring(self, mask: np.ndarray, cx: int, cy: int,
                         radius: int, intensity: float) -> np.ndarray:
        """绘制水渍环"""
        height, width = mask.shape
        ring_width = max(2, radius // 5)
        
        for y in range(max(0, cy - radius), min(height, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(width, cx + radius + 1)):
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                
                # 环形区域
                if radius - ring_width <= dist <= radius:
                    ring_pos = (dist - (radius - ring_width)) / ring_width
                    fade = math.sin(ring_pos * math.pi) * intensity
                    fade *= self._rng.uniform(0.8, 1.0)
                    mask[y, x] = max(mask[y, x], fade)
        
        return mask
    
    def apply(self, image: np.ndarray) -> np.ndarray:
        """将污渍应用到图像"""
        if not self._should_apply():
            return image
        
        height, width = image.shape[:2]
        mask = self.generate(width, height)
        
        # 生成污渍颜色
        result = image.copy().astype(np.float32)
        
        for stain_type in self.config.stain_types:
            stain_color = self._get_stain_color(stain_type)
            
            # 应用污渍
            for c in range(min(3, result.shape[2])):
                color_var = 1 + self._rng.uniform(
                    -self.config.color_variation, 
                    self.config.color_variation
                )
                result[:, :, c] = result[:, :, c] * (1 - mask * 0.7) + \
                                  stain_color[c] * color_var * mask * 0.7
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def _get_stain_color(self, stain_type: str) -> Tuple[int, int, int]:
        """获取污渍颜色"""
        colors = {
            'mud': (101, 67, 33),      # 棕色泥土
            'oil': (40, 40, 45),       # 深灰油污
            'dust': (150, 140, 130),   # 浅灰灰尘
            'water': (180, 180, 190),  # 浅色水渍
        }
        return colors.get(stain_type, (100, 100, 100))


# ============================================================================
# 阴影噪声生成器
# ============================================================================

class ShadowNoiseGenerator(BaseNoiseGenerator):
    """阴影噪声生成器"""
    
    def __init__(self, config: ShadowConfig = None):
        super().__init__(config or ShadowConfig())
        self.config: ShadowConfig = self.config
    
    def generate(self, width: int, height: int) -> np.ndarray:
        """生成阴影遮罩"""
        mask = np.ones((height, width), dtype=np.float32)
        
        if not self._should_apply():
            return mask
        
        intensity_mult = self._get_intensity_multiplier()
        
        for shadow_type in self.config.shadow_types:
            if self._rng.random() < 0.5:  # 随机选择是否应用每种阴影
                if shadow_type == 'gradient':
                    mask = self._apply_gradient_shadow(mask, width, height, intensity_mult)
                elif shadow_type == 'spot':
                    mask = self._apply_spot_shadow(mask, width, height, intensity_mult)
                elif shadow_type == 'edge':
                    mask = self._apply_edge_shadow(mask, width, height, intensity_mult)
                elif shadow_type == 'vignette':
                    mask = self._apply_vignette(mask, width, height, intensity_mult)
        
        return np.clip(mask, 0, 1)
    
    def _apply_gradient_shadow(self, mask: np.ndarray, width: int, height: int,
                               intensity: float) -> np.ndarray:
        """应用渐变阴影"""
        angle_rad = math.radians(self.config.direction)
        
        # 创建方向性渐变
        for y in range(height):
            for x in range(width):
                # 计算在阴影方向上的位置
                pos = (x * math.cos(angle_rad) + y * math.sin(angle_rad)) / max(width, height)
                
                # 应用渐变
                shadow_strength = pos * self.config.darkness * intensity * self.config.coverage
                mask[y, x] *= (1 - shadow_strength)
        
        return mask
    
    def _apply_spot_shadow(self, mask: np.ndarray, width: int, height: int,
                           intensity: float) -> np.ndarray:
        """应用斑点阴影"""
        num_spots = self._rng.integers(2, 6)
        
        for _ in range(num_spots):
            cx = self._rng.integers(0, width)
            cy = self._rng.integers(0, height)
            radius = self._rng.integers(
                int(min(width, height) * 0.1),
                int(min(width, height) * 0.3)
            )
            
            for y in range(max(0, cy - radius), min(height, cy + radius + 1)):
                for x in range(max(0, cx - radius), min(width, cx + radius + 1)):
                    dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                    if dist <= radius:
                        fade = (1 - dist / radius) ** 2
                        shadow = self.config.darkness * intensity * fade
                        mask[y, x] *= (1 - shadow * 0.5)
        
        return mask
    
    def _apply_edge_shadow(self, mask: np.ndarray, width: int, height: int,
                           intensity: float) -> np.ndarray:
        """应用边缘阴影"""
        edge_width = int(self.config.softness * intensity)
        
        # 随机选择边缘
        edges = self._rng.choice(['top', 'bottom', 'left', 'right'], 
                                  size=self._rng.integers(1, 3), replace=False)
        
        for edge in edges:
            if edge == 'top':
                for y in range(min(edge_width, height)):
                    fade = 1 - y / edge_width
                    mask[y, :] *= (1 - self.config.darkness * fade * 0.5)
            elif edge == 'bottom':
                for y in range(max(0, height - edge_width), height):
                    fade = (y - (height - edge_width)) / edge_width
                    mask[y, :] *= (1 - self.config.darkness * fade * 0.5)
            elif edge == 'left':
                for x in range(min(edge_width, width)):
                    fade = 1 - x / edge_width
                    mask[:, x] *= (1 - self.config.darkness * fade * 0.5)
            elif edge == 'right':
                for x in range(max(0, width - edge_width), width):
                    fade = (x - (width - edge_width)) / edge_width
                    mask[:, x] *= (1 - self.config.darkness * fade * 0.5)
        
        return mask
    
    def _apply_vignette(self, mask: np.ndarray, width: int, height: int,
                        intensity: float) -> np.ndarray:
        """应用暗角效果"""
        cx, cy = width // 2, height // 2
        max_dist = math.sqrt(cx ** 2 + cy ** 2)
        
        for y in range(height):
            for x in range(width):
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                vignette = (dist / max_dist) ** 2 * self.config.darkness * intensity
                mask[y, x] *= (1 - vignette * 0.3)
        
        return mask
    
    def apply(self, image: np.ndarray) -> np.ndarray:
        """将阴影应用到图像"""
        if not self._should_apply():
            return image
        
        height, width = image.shape[:2]
        mask = self.generate(width, height)
        
        result = image.copy().astype(np.float32)
        
        # 应用阴影遮罩
        for c in range(min(3, result.shape[2])):
            result[:, :, c] *= mask
        
        return np.clip(result, 0, 255).astype(np.uint8)


# ============================================================================
# 掉漆噪声生成器
# ============================================================================

class PaintPeelingNoiseGenerator(BaseNoiseGenerator):
    """掉漆噪声生成器"""
    
    def __init__(self, config: PaintPeelingConfig = None):
        super().__init__(config or PaintPeelingConfig())
        self.config: PaintPeelingConfig = self.config
    
    def generate(self, width: int, height: int) -> np.ndarray:
        """生成掉漆遮罩"""
        mask = np.zeros((height, width), dtype=np.float32)
        
        if not self._should_apply():
            return mask
        
        intensity_mult = self._get_intensity_multiplier()
        num_areas = self._rng.integers(
            int(self.config.num_areas[0] * intensity_mult),
            int(self.config.num_areas[1] * intensity_mult) + 1
        )
        
        for _ in range(num_areas):
            peeling_type = self._rng.choice(self.config.peeling_types)
            mask = self._add_peeling_area(mask, width, height, peeling_type)
        
        return np.clip(mask, 0, 1)
    
    def _add_peeling_area(self, mask: np.ndarray, width: int, height: int,
                          peeling_type: str) -> np.ndarray:
        """添加掉漆区域"""
        if peeling_type == 'edge':
            return self._add_edge_peeling(mask, width, height)
        elif peeling_type == 'spot':
            return self._add_spot_peeling(mask, width, height)
        elif peeling_type == 'crack':
            return self._add_crack_peeling(mask, width, height)
        elif peeling_type == 'flake':
            return self._add_flake_peeling(mask, width, height)
        return mask
    
    def _add_edge_peeling(self, mask: np.ndarray, width: int, height: int) -> np.ndarray:
        """添加边缘掉漆"""
        edge = self._rng.choice(['top', 'bottom', 'left', 'right'])
        peeling_depth = self._rng.integers(5, 20)
        
        if edge == 'top':
            for x in range(width):
                depth = self._rng.integers(0, peeling_depth)
                for y in range(depth):
                    if y < height:
                        mask[y, x] = max(mask[y, x], self._rng.uniform(0.7, 1.0))
        elif edge == 'bottom':
            for x in range(width):
                depth = self._rng.integers(0, peeling_depth)
                for y in range(height - depth, height):
                    if y >= 0:
                        mask[y, x] = max(mask[y, x], self._rng.uniform(0.7, 1.0))
        elif edge == 'left':
            for y in range(height):
                depth = self._rng.integers(0, peeling_depth)
                for x in range(depth):
                    if x < width:
                        mask[y, x] = max(mask[y, x], self._rng.uniform(0.7, 1.0))
        elif edge == 'right':
            for y in range(height):
                depth = self._rng.integers(0, peeling_depth)
                for x in range(width - depth, width):
                    if x >= 0:
                        mask[y, x] = max(mask[y, x], self._rng.uniform(0.7, 1.0))
        
        return mask
    
    def _add_spot_peeling(self, mask: np.ndarray, width: int, height: int) -> np.ndarray:
        """添加斑点掉漆"""
        cx = self._rng.integers(0, width)
        cy = self._rng.integers(0, height)
        size = self._rng.integers(
            self.config.area_size_range[0],
            self.config.area_size_range[1] + 1
        )
        
        # 创建不规则形状
        num_points = self._rng.integers(5, 12)
        angles = sorted([self._rng.uniform(0, 2 * math.pi) for _ in range(num_points)])
        radii = [size * self._rng.uniform(0.5, 1.0) for _ in range(num_points)]
        
        for y in range(max(0, cy - size), min(height, cy + size + 1)):
            for x in range(max(0, cx - size), min(width, cx + size + 1)):
                angle = math.atan2(y - cy, x - cx)
                if angle < 0:
                    angle += 2 * math.pi
                
                # 找到对应的半径
                for i in range(len(angles)):
                    if angles[i] >= angle:
                        break
                
                # 插值半径
                idx1 = (i - 1) % len(angles)
                idx2 = i % len(angles)
                t = (angle - angles[idx1]) / (angles[idx2] - angles[idx1] + 0.001)
                radius = radii[idx1] * (1 - t) + radii[idx2] * t
                
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist <= radius:
                    roughness = self._rng.uniform(0.8, 1.0) if self._rng.random() > self.config.edge_roughness else 0
                    mask[y, x] = max(mask[y, x], roughness)
        
        return mask
    
    def _add_crack_peeling(self, mask: np.ndarray, width: int, height: int) -> np.ndarray:
        """添加裂纹掉漆"""
        # 起点
        x1 = self._rng.integers(0, width)
        y1 = self._rng.integers(0, height)
        
        # 绘制分叉裂纹
        self._draw_crack_branch(mask, x1, y1, width, height, 
                                self._rng.uniform(0, 2 * math.pi), 
                                depth=3)
        
        return mask
    
    def _draw_crack_branch(self, mask: np.ndarray, x: int, y: int, 
                           width: int, height: int, angle: float, depth: int):
        """递归绘制裂纹分支"""
        if depth <= 0:
            return
        
        length = self._rng.integers(20, 60)
        thickness = max(1, depth)
        
        for i in range(length):
            # 添加随机扰动
            angle += self._rng.uniform(-0.2, 0.2)
            
            nx = int(x + i * math.cos(angle))
            ny = int(y + i * math.sin(angle))
            
            if 0 <= nx < width and 0 <= ny < height:
                for dy in range(-thickness, thickness + 1):
                    for dx in range(-thickness, thickness + 1):
                        px, py = nx + dx, ny + dy
                        if 0 <= px < width and 0 <= py < height:
                            mask[py, px] = max(mask[py, px], 0.9)
            
            # 随机分叉
            if self._rng.random() < 0.1 and depth > 1:
                branch_angle = angle + self._rng.choice([-1, 1]) * self._rng.uniform(0.3, 0.8)
                self._draw_crack_branch(mask, nx, ny, width, height, branch_angle, depth - 1)
    
    def _add_flake_peeling(self, mask: np.ndarray, width: int, height: int) -> np.ndarray:
        """添加片状掉漆"""
        cx = self._rng.integers(0, width)
        cy = self._rng.integers(0, height)
        
        # 多个小片状区域
        num_flakes = self._rng.integers(3, 8)
        
        for _ in range(num_flakes):
            fx = cx + self._rng.integers(-30, 31)
            fy = cy + self._rng.integers(-30, 31)
            
            flake_w = self._rng.integers(5, 20)
            flake_h = self._rng.integers(5, 20)
            
            for y in range(max(0, fy), min(height, fy + flake_h)):
                for x in range(max(0, fx), min(width, fx + flake_w)):
                    if self._rng.random() > 0.2:  # 不规则边缘
                        mask[y, x] = max(mask[y, x], self._rng.uniform(0.8, 1.0))
        
        return mask
    
    def apply(self, image: np.ndarray) -> np.ndarray:
        """将掉漆效果应用到图像"""
        if not self._should_apply():
            return image
        
        height, width = image.shape[:2]
        mask = self.generate(width, height)
        
        result = image.copy().astype(np.float32)
        base_color = np.array(self.config.base_color, dtype=np.float32)
        
        # 在掉漆区域显示底层颜色
        for c in range(min(3, result.shape[2])):
            result[:, :, c] = result[:, :, c] * (1 - mask) + base_color[c] * mask
        
        return np.clip(result, 0, 255).astype(np.uint8)


# ============================================================================
# 异物遮挡噪声生成器
# ============================================================================

class OcclusionNoiseGenerator(BaseNoiseGenerator):
    """异物遮挡噪声生成器"""
    
    def __init__(self, config: OcclusionConfig = None):
        super().__init__(config or OcclusionConfig())
        self.config: OcclusionConfig = self.config
    
    def generate(self, width: int, height: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        生成遮挡物遮罩和颜色
        
        Returns:
            (遮罩数组, 颜色数组)
        """
        mask = np.zeros((height, width), dtype=np.float32)
        color = np.zeros((height, width, 3), dtype=np.float32)
        
        if not self._should_apply():
            return mask, color
        
        intensity_mult = self._get_intensity_multiplier()
        num_objects = self._rng.integers(
            int(self.config.num_objects[0] * intensity_mult),
            int(self.config.num_objects[1] * intensity_mult) + 1
        )
        
        for _ in range(num_objects):
            occlusion_type = self._rng.choice(self.config.occlusion_types)
            mask, color = self._add_occlusion(mask, color, width, height, occlusion_type)
        
        return mask, color
    
    def _get_position(self, width: int, height: int, size: int) -> Tuple[int, int]:
        """根据位置偏好获取遮挡物位置"""
        bias = self.config.position_bias
        
        if bias == 'edge':
            edge = self._rng.choice(['top', 'bottom', 'left', 'right'])
            if edge == 'top':
                return self._rng.integers(0, width), self._rng.integers(0, size)
            elif edge == 'bottom':
                return self._rng.integers(0, width), self._rng.integers(height - size, height)
            elif edge == 'left':
                return self._rng.integers(0, size), self._rng.integers(0, height)
            else:
                return self._rng.integers(width - size, width), self._rng.integers(0, height)
        elif bias == 'corner':
            corner = self._rng.choice(['tl', 'tr', 'bl', 'br'])
            if corner == 'tl':
                return self._rng.integers(0, size), self._rng.integers(0, size)
            elif corner == 'tr':
                return self._rng.integers(width - size, width), self._rng.integers(0, size)
            elif corner == 'bl':
                return self._rng.integers(0, size), self._rng.integers(height - size, height)
            else:
                return self._rng.integers(width - size, width), self._rng.integers(height - size, height)
        elif bias == 'center':
            return (self._rng.integers(width // 4, 3 * width // 4),
                    self._rng.integers(height // 4, 3 * height // 4))
        else:  # random
            return self._rng.integers(0, width), self._rng.integers(0, height)
    
    def _add_occlusion(self, mask: np.ndarray, color: np.ndarray, 
                       width: int, height: int, occlusion_type: str) -> Tuple[np.ndarray, np.ndarray]:
        """添加遮挡物"""
        size = self._rng.integers(
            self.config.size_range[0],
            self.config.size_range[1] + 1
        )
        cx, cy = self._get_position(width, height, size)
        opacity = self._rng.uniform(*self.config.opacity_range)
        
        if occlusion_type == 'leaf':
            return self._add_leaf(mask, color, cx, cy, size, opacity, width, height)
        elif occlusion_type == 'sticker':
            return self._add_sticker(mask, color, cx, cy, size, opacity, width, height)
        elif occlusion_type == 'tape':
            return self._add_tape(mask, color, cx, cy, size, opacity, width, height)
        elif occlusion_type == 'dirt_blob':
            return self._add_dirt_blob(mask, color, cx, cy, size, opacity, width, height)
        elif occlusion_type == 'screw':
            return self._add_screw(mask, color, cx, cy, size, opacity, width, height)
        
        return mask, color
    
    def _add_leaf(self, mask: np.ndarray, color: np.ndarray, cx: int, cy: int,
                  size: int, opacity: float, width: int, height: int) -> Tuple[np.ndarray, np.ndarray]:
        """添加树叶遮挡"""
        # 叶子颜色（绿色到棕色）
        leaf_colors = [
            (34, 139, 34),   # 绿色
            (107, 142, 35),  # 橄榄绿
            (139, 69, 19),   # 棕色
            (160, 82, 45),   # 赭色
        ]
        leaf_color = np.array(self._rng.choice(leaf_colors), dtype=np.float32)
        
        # 绘制叶子形状（椭圆形）
        for y in range(max(0, cy - size), min(height, cy + size + 1)):
            for x in range(max(0, cx - size // 2), min(width, cx + size // 2 + 1)):
                dx = (x - cx) / (size // 2 + 0.001)
                dy = (y - cy) / (size + 0.001)
                
                # 叶子形状
                if dx * dx + dy * dy <= 1:
                    # 添加叶脉效果
                    vein = abs(math.sin(dy * 10)) * 0.1
                    
                    mask[y, x] = max(mask[y, x], opacity)
                    for c in range(3):
                        color[y, x, c] = leaf_color[c] * (1 - vein)
        
        return mask, color
    
    def _add_sticker(self, mask: np.ndarray, color: np.ndarray, cx: int, cy: int,
                     size: int, opacity: float, width: int, height: int) -> Tuple[np.ndarray, np.ndarray]:
        """添加贴纸遮挡"""
        # 贴纸颜色
        sticker_colors = [
            (255, 255, 255),  # 白色
            (255, 0, 0),      # 红色
            (255, 255, 0),    # 黄色
            (0, 0, 255),      # 蓝色
        ]
        sticker_color = np.array(self._rng.choice(sticker_colors), dtype=np.float32)
        
        # 矩形贴纸
        half_w = size // 2
        half_h = size // 3
        
        for y in range(max(0, cy - half_h), min(height, cy + half_h + 1)):
            for x in range(max(0, cx - half_w), min(width, cx + half_w + 1)):
                mask[y, x] = max(mask[y, x], opacity)
                for c in range(3):
                    color[y, x, c] = sticker_color[c]
        
        return mask, color
    
    def _add_tape(self, mask: np.ndarray, color: np.ndarray, cx: int, cy: int,
                  size: int, opacity: float, width: int, height: int) -> Tuple[np.ndarray, np.ndarray]:
        """添加胶带遮挡"""
        tape_color = np.array([200, 180, 150], dtype=np.float32)  # 米色胶带
        
        # 斜向胶带条
        angle = self._rng.uniform(-0.5, 0.5)
        tape_width = self._rng.integers(10, 25)
        
        for i in range(-size, size + 1):
            x = int(cx + i * math.cos(angle))
            y = int(cy + i * math.sin(angle))
            
            for w in range(-tape_width // 2, tape_width // 2 + 1):
                nx = int(x - w * math.sin(angle))
                ny = int(y + w * math.cos(angle))
                
                if 0 <= nx < width and 0 <= ny < height:
                    mask[ny, nx] = max(mask[ny, nx], opacity * 0.7)  # 胶带半透明
                    for c in range(3):
                        color[ny, nx, c] = tape_color[c]
        
        return mask, color
    
    def _add_dirt_blob(self, mask: np.ndarray, color: np.ndarray, cx: int, cy: int,
                       size: int, opacity: float, width: int, height: int) -> Tuple[np.ndarray, np.ndarray]:
        """添加污泥块遮挡"""
        dirt_color = np.array([80, 60, 40], dtype=np.float32)  # 深棕色
        
        # 不规则形状
        for y in range(max(0, cy - size), min(height, cy + size + 1)):
            for x in range(max(0, cx - size), min(width, cx + size + 1)):
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                
                # 添加随机扰动
                noise = self._rng.uniform(0.7, 1.3)
                
                if dist <= size * noise:
                    fade = (1 - dist / (size * noise)) ** 0.5
                    mask[y, x] = max(mask[y, x], opacity * fade)
                    for c in range(3):
                        color[y, x, c] = dirt_color[c] * self._rng.uniform(0.8, 1.2)
        
        return mask, color
    
    def _add_screw(self, mask: np.ndarray, color: np.ndarray, cx: int, cy: int,
                   size: int, opacity: float, width: int, height: int) -> Tuple[np.ndarray, np.ndarray]:
        """添加螺丝遮挡"""
        screw_color = np.array([150, 150, 160], dtype=np.float32)  # 金属灰
        screw_size = min(size // 3, 15)
        
        # 圆形螺丝头
        for y in range(max(0, cy - screw_size), min(height, cy + screw_size + 1)):
            for x in range(max(0, cx - screw_size), min(width, cx + screw_size + 1)):
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                
                if dist <= screw_size:
                    mask[y, x] = max(mask[y, x], opacity)
                    
                    # 添加十字槽
                    if abs(x - cx) < 2 or abs(y - cy) < 2:
                        for c in range(3):
                            color[y, x, c] = screw_color[c] * 0.5
                    else:
                        for c in range(3):
                            color[y, x, c] = screw_color[c]
        
        return mask, color
    
    def apply(self, image: np.ndarray) -> np.ndarray:
        """将遮挡物应用到图像"""
        if not self._should_apply():
            return image
        
        height, width = image.shape[:2]
        mask, occlusion_color = self.generate(width, height)
        
        result = image.copy().astype(np.float32)
        
        # 混合遮挡物
        for c in range(min(3, result.shape[2])):
            result[:, :, c] = result[:, :, c] * (1 - mask) + occlusion_color[:, :, c] * mask
        
        return np.clip(result, 0, 255).astype(np.uint8)


# ============================================================================
# 组合噪声应用器
# ============================================================================

class CompositeNoiseApplicator:
    """
    组合噪声应用器
    
    用于将多种噪声效果组合应用到图像上
    """
    
    def __init__(self, config: CompositeNoiseConfig = None):
        """
        初始化组合噪声应用器
        
        Args:
            config: 组合噪声配置
        """
        self.config = config or CompositeNoiseConfig()
        
        # 初始化各噪声生成器
        self.stain_generator = StainNoiseGenerator(self.config.stain)
        self.shadow_generator = ShadowNoiseGenerator(self.config.shadow)
        self.paint_peeling_generator = PaintPeelingNoiseGenerator(self.config.paint_peeling)
        self.occlusion_generator = OcclusionNoiseGenerator(self.config.occlusion)
        
        # 设置全局随机种子
        if self.config.seed is not None:
            np.random.seed(self.config.seed)
            random.seed(self.config.seed)
    
    def apply(self, image: np.ndarray, 
              noise_types: List[NoiseType] = None) -> np.ndarray:
        """
        应用噪声到图像
        
        Args:
            image: 输入图像数组
            noise_types: 要应用的噪声类型列表，None表示应用所有启用的噪声
            
        Returns:
            应用噪声后的图像
        """
        result = image.copy()
        
        if noise_types is None:
            noise_types = [NoiseType.STAIN, NoiseType.SHADOW, 
                          NoiseType.PAINT_PEELING, NoiseType.OCCLUSION]
        
        # 按顺序应用噪声（顺序很重要）
        # 1. 先应用阴影（影响整体亮度）
        if NoiseType.SHADOW in noise_types and self.config.shadow.enabled:
            result = self.shadow_generator.apply(result)
        
        # 2. 应用掉漆（露出底层）
        if NoiseType.PAINT_PEELING in noise_types and self.config.paint_peeling.enabled:
            result = self.paint_peeling_generator.apply(result)
        
        # 3. 应用污渍（覆盖在表面）
        if NoiseType.STAIN in noise_types and self.config.stain.enabled:
            result = self.stain_generator.apply(result)
        
        # 4. 最后应用遮挡物（最上层）
        if NoiseType.OCCLUSION in noise_types and self.config.occlusion.enabled:
            result = self.occlusion_generator.apply(result)
        
        return result
    
    def apply_random(self, image: np.ndarray, 
                     min_types: int = 1, max_types: int = 4) -> np.ndarray:
        """
        随机应用噪声
        
        Args:
            image: 输入图像
            min_types: 最少应用的噪声类型数
            max_types: 最多应用的噪声类型数
            
        Returns:
            应用噪声后的图像
        """
        all_types = [NoiseType.STAIN, NoiseType.SHADOW, 
                     NoiseType.PAINT_PEELING, NoiseType.OCCLUSION]
        
        num_types = random.randint(min_types, max_types)
        selected_types = random.sample(all_types, num_types)
        
        return self.apply(image, selected_types)
    
    @staticmethod
    def create_preset(preset_name: str) -> 'CompositeNoiseApplicator':
        """
        创建预设配置的噪声应用器
        
        Args:
            preset_name: 预设名称 ('clean', 'light', 'medium', 'heavy', 'extreme')
            
        Returns:
            配置好的噪声应用器
        """
        presets = {
            'clean': CompositeNoiseConfig(
                stain=StainConfig(enabled=False),
                shadow=ShadowConfig(enabled=True, intensity=NoiseIntensity.LIGHT, probability=0.3),
                paint_peeling=PaintPeelingConfig(enabled=False),
                occlusion=OcclusionConfig(enabled=False),
            ),
            'light': CompositeNoiseConfig(
                stain=StainConfig(intensity=NoiseIntensity.LIGHT, probability=0.3),
                shadow=ShadowConfig(intensity=NoiseIntensity.LIGHT, probability=0.4),
                paint_peeling=PaintPeelingConfig(enabled=False),
                occlusion=OcclusionConfig(enabled=False),
            ),
            'medium': CompositeNoiseConfig(
                stain=StainConfig(intensity=NoiseIntensity.MEDIUM, probability=0.5),
                shadow=ShadowConfig(intensity=NoiseIntensity.MEDIUM, probability=0.5),
                paint_peeling=PaintPeelingConfig(intensity=NoiseIntensity.LIGHT, probability=0.3),
                occlusion=OcclusionConfig(intensity=NoiseIntensity.LIGHT, probability=0.2),
            ),
            'heavy': CompositeNoiseConfig(
                stain=StainConfig(intensity=NoiseIntensity.HEAVY, probability=0.7),
                shadow=ShadowConfig(intensity=NoiseIntensity.HEAVY, probability=0.6),
                paint_peeling=PaintPeelingConfig(intensity=NoiseIntensity.MEDIUM, probability=0.5),
                occlusion=OcclusionConfig(intensity=NoiseIntensity.MEDIUM, probability=0.4),
            ),
            'extreme': CompositeNoiseConfig(
                stain=StainConfig(intensity=NoiseIntensity.EXTREME, probability=0.9),
                shadow=ShadowConfig(intensity=NoiseIntensity.EXTREME, probability=0.8),
                paint_peeling=PaintPeelingConfig(intensity=NoiseIntensity.HEAVY, probability=0.7),
                occlusion=OcclusionConfig(intensity=NoiseIntensity.HEAVY, probability=0.6),
            ),
        }
        
        config = presets.get(preset_name, presets['medium'])
        return CompositeNoiseApplicator(config)


# ============================================================================
# 便捷函数
# ============================================================================

def apply_noise_to_image(image: Union[np.ndarray, Image.Image, str],
                         preset: str = 'medium',
                         noise_types: List[NoiseType] = None) -> np.ndarray:
    """
    便捷函数：将噪声应用到图像
    
    Args:
        image: 输入图像（numpy数组、PIL Image或文件路径）
        preset: 预设名称
        noise_types: 要应用的噪声类型
        
    Returns:
        应用噪声后的numpy数组
    """
    # 处理输入
    if isinstance(image, str):
        image = np.array(Image.open(image))
    elif isinstance(image, Image.Image):
        image = np.array(image)
    
    # 确保是RGB格式
    if len(image.shape) == 2:
        image = np.stack([image] * 3, axis=-1)
    elif image.shape[2] == 4:
        image = image[:, :, :3]
    
    # 应用噪声
    applicator = CompositeNoiseApplicator.create_preset(preset)
    return applicator.apply(image, noise_types)


def save_noisy_image(image: np.ndarray, output_path: str):
    """
    保存带噪声的图像
    
    Args:
        image: 图像数组
        output_path: 输出路径
    """
    Image.fromarray(image.astype(np.uint8)).save(output_path)


# ============================================================================
# 主函数（用于测试）
# ============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='噪声模块测试')
    parser.add_argument('--input', type=str, required=True, help='输入图像路径')
    parser.add_argument('--output', type=str, required=True, help='输出图像路径')
    parser.add_argument('--preset', type=str, default='medium',
                       choices=['clean', 'light', 'medium', 'heavy', 'extreme'],
                       help='噪声预设')
    
    args = parser.parse_args()
    
    # 应用噪声
    result = apply_noise_to_image(args.input, args.preset)
    save_noisy_image(result, args.output)
    
    print(f"✅ 噪声已应用，输出: {args.output}")
