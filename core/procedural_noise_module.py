#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
程序化噪声生成模块 (Procedural Noise Module)

基于FastNoiseLite理念的Python实现，使用perlin-noise和opensimplex库
提供多种程序化噪声算法，用于生成无限变化的噪声纹理。

噪声类型:
    - Perlin噪声: 经典的梯度噪声，适合自然纹理
    - OpenSimplex噪声: 改进的Simplex噪声，无专利问题
    - Cellular噪声 (Voronoi): 细胞状/裂纹状纹理
    - 分形噪声 (FBM): 多层噪声叠加，增加细节
    - 域扭曲: 扭曲噪声空间，创造更复杂的图案

作者: PCG-USD车牌材质系统
版本: 1.0.0
灵感来源: FastNoiseLite (https://github.com/Auburn/FastNoiseLite)
"""

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Tuple, Optional, List

import numpy as np
from perlin_noise import PerlinNoise
from opensimplex import OpenSimplex


# ============================================================================
# 噪声类型枚举
# ============================================================================

class ProceduralNoiseType(Enum):
    """程序化噪声类型"""
    PERLIN = auto()          # Perlin噪声
    OPENSIMPLEX = auto()     # OpenSimplex噪声
    CELLULAR = auto()        # Cellular/Voronoi噪声
    WHITE_NOISE = auto()     # 白噪声
    VALUE = auto()           # Value噪声


class FractalType(Enum):
    """分形类型"""
    NONE = auto()           # 不使用分形
    FBM = auto()            # Fractional Brownian Motion (分形布朗运动)
    RIDGED = auto()         # Ridged Multifractal (脊状多重分形)
    PING_PONG = auto()      # Ping Pong (乒乓效果)


class CellularDistanceFunction(Enum):
    """Cellular噪声距离函数"""
    EUCLIDEAN = auto()      # 欧几里得距离
    MANHATTAN = auto()      # 曼哈顿距离
    HYBRID = auto()         # 混合距离


class CellularReturnType(Enum):
    """Cellular噪声返回类型"""
    DISTANCE = auto()       # 返回距离值
    DISTANCE2 = auto()      # 返回第二近的距离
    DISTANCE2_ADD = auto()  # 返回两个距离之和
    DISTANCE2_SUB = auto()  # 返回两个距离之差
    DISTANCE2_MUL = auto()  # 返回两个距离之积
    DISTANCE2_DIV = auto()  # 返回两个距离之商


# ============================================================================
# 配置数据类
# ============================================================================

@dataclass
class ProceduralNoiseConfig:
    """
    程序化噪声配置
    
    Attributes:
        noise_type: 噪声类型
        seed: 随机种子
        frequency: 噪声频率（值越大，噪声越密集）
        octaves: 分形层数（用于FBM）
        lacunarity: 间隙度（每层频率的增长因子）
        persistence: 持续性（每层振幅的衰减因子）
        fractal_type: 分形类型
        cellular_distance_func: Cellular噪声距离函数
        cellular_return_type: Cellular噪声返回类型
        cellular_jitter: Cellular噪声抖动强度
        domain_warp_amp: 域扭曲振幅
    """
    noise_type: ProceduralNoiseType = ProceduralNoiseType.PERLIN
    seed: int = 0
    frequency: float = 0.01
    octaves: int = 6
    lacunarity: float = 2.0
    persistence: float = 0.5
    fractal_type: FractalType = FractalType.FBM
    
    # Cellular噪声特定参数
    cellular_distance_func: CellularDistanceFunction = CellularDistanceFunction.EUCLIDEAN
    cellular_return_type: CellularReturnType = CellularReturnType.DISTANCE
    cellular_jitter: float = 1.0
    
    # 域扭曲参数
    domain_warp_amp: float = 0.0


# ============================================================================
# 程序化噪声生成器
# ============================================================================

class ProceduralNoiseGenerator:
    """
    程序化噪声生成器
    
    基于FastNoiseLite的设计理念，使用Python实现
    支持多种噪声算法和分形组合
    """
    
    def __init__(self, config: ProceduralNoiseConfig = None):
        """
        初始化噪声生成器
        
        Args:
            config: 噪声配置对象
        """
        self.config = config or ProceduralNoiseConfig()
        self._setup_generators()
    
    def _setup_generators(self):
        """设置噪声生成器"""
        # Perlin噪声生成器
        self.perlin = PerlinNoise(
            octaves=self.config.octaves,
            seed=self.config.seed
        )
        
        # OpenSimplex噪声生成器
        self.opensimplex = OpenSimplex(seed=self.config.seed)
        
        # 随机数生成器（用于Cellular和White噪声）
        self.rng = np.random.default_rng(self.config.seed)
    
    def generate_2d(self, width: int, height: int) -> np.ndarray:
        """
        生成2D噪声纹理（向量化版本）
        
        Args:
            width: 纹理宽度
            height: 纹理高度
        
        Returns:
            噪声数组 (height, width)，值范围 [-1, 1]
        """
        # 创建坐标网格
        x_coords = np.arange(width)
        y_coords = np.arange(height)
        xx, yy = np.meshgrid(x_coords, y_coords)
        
        # 应用频率
        xx = xx * self.config.frequency
        yy = yy * self.config.frequency
        
        # 向量化生成噪声
        if self.config.noise_type == ProceduralNoiseType.OPENSIMPLEX:
            # OpenSimplex支持向量化
            noise_array = np.vectorize(self.opensimplex.noise2)(xx, yy)
        else:
            # 其他噪声类型使用循环（较慢但功能完整）
            noise_array = np.zeros((height, width), dtype=np.float32)
            for y in range(height):
                for x in range(width):
                    noise_array[y, x] = self._get_noise_2d(x, y)
        
        return noise_array
    
    def generate_2d_normalized(self, width: int, height: int) -> np.ndarray:
        """
        生成归一化的2D噪声纹理
        
        Args:
            width: 纹理宽度
            height: 纹理高度
        
        Returns:
            噪声数组 (height, width)，值范围 [0, 1]
        """
        noise_array = self.generate_2d(width, height)
        # 归一化到 [0, 1]
        noise_array = (noise_array + 1.0) * 0.5
        return np.clip(noise_array, 0, 1)
    
    def generate_2d_uint8(self, width: int, height: int) -> np.ndarray:
        """
        生成uint8格式的2D噪声纹理
        
        Args:
            width: 纹理宽度
            height: 纹理高度
        
        Returns:
            噪声数组 (height, width)，值范围 [0, 255]
        """
        noise_array = self.generate_2d_normalized(width, height)
        return (noise_array * 255).astype(np.uint8)
    
    def _get_noise_2d(self, x: int, y: int) -> float:
        """
        获取单个点的噪声值
        
        Args:
            x: X坐标
            y: Y坐标
        
        Returns:
            噪声值，范围 [-1, 1]
        """
        # 应用域扭曲
        if self.config.domain_warp_amp > 0:
            x, y = self._domain_warp_2d(x, y)
        
        # 应用频率
        x *= self.config.frequency
        y *= self.config.frequency
        
        # 根据分形类型生成噪声
        if self.config.fractal_type == FractalType.NONE:
            return self._single_noise_2d(x, y)
        elif self.config.fractal_type == FractalType.FBM:
            return self._fbm_2d(x, y)
        elif self.config.fractal_type == FractalType.RIDGED:
            return self._ridged_2d(x, y)
        elif self.config.fractal_type == FractalType.PING_PONG:
            return self._ping_pong_2d(x, y)
        else:
            return self._single_noise_2d(x, y)
    
    def _single_noise_2d(self, x: float, y: float) -> float:
        """
        生成单层噪声
        
        Args:
            x: X坐标（已应用频率）
            y: Y坐标（已应用频率）
        
        Returns:
            噪声值，范围 [-1, 1]
        """
        if self.config.noise_type == ProceduralNoiseType.PERLIN:
            return self._perlin_2d(x, y)
        elif self.config.noise_type == ProceduralNoiseType.OPENSIMPLEX:
            return self._opensimplex_2d(x, y)
        elif self.config.noise_type == ProceduralNoiseType.CELLULAR:
            return self._cellular_2d(x, y)
        elif self.config.noise_type == ProceduralNoiseType.WHITE_NOISE:
            return self._white_noise_2d(x, y)
        elif self.config.noise_type == ProceduralNoiseType.VALUE:
            return self._value_noise_2d(x, y)
        else:
            return 0.0
    
    def _perlin_2d(self, x: float, y: float) -> float:
        """Perlin噪声"""
        try:
            value = self.perlin([x, y])
            # perlin-noise库返回值范围约为[-0.5, 0.5]，需要归一化
            return np.clip(value * 2.0, -1.0, 1.0)
        except:
            return 0.0
    
    def _opensimplex_2d(self, x: float, y: float) -> float:
        """OpenSimplex噪声"""
        return self.opensimplex.noise2(x, y)
    
    def _cellular_2d(self, x: float, y: float) -> float:
        """
        Cellular/Voronoi噪声
        
        简化实现：基于网格的特征点
        """
        # 计算所在网格
        cell_x = int(math.floor(x))
        cell_y = int(math.floor(y))
        
        min_dist = float('inf')
        min_dist2 = float('inf')
        
        # 检查周围9个网格
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                # 获取相邻网格的特征点
                feature_x, feature_y = self._get_cellular_feature_point(
                    cell_x + dx, cell_y + dy
                )
                
                # 计算距离
                dist = self._cellular_distance(x, y, feature_x, feature_y)
                
                if dist < min_dist:
                    min_dist2 = min_dist
                    min_dist = dist
                elif dist < min_dist2:
                    min_dist2 = dist
        
        # 根据返回类型计算最终值
        if self.config.cellular_return_type == CellularReturnType.DISTANCE:
            return 1.0 - min(min_dist * 2.0, 1.0)
        elif self.config.cellular_return_type == CellularReturnType.DISTANCE2:
            return 1.0 - min(min_dist2 * 2.0, 1.0)
        elif self.config.cellular_return_type == CellularReturnType.DISTANCE2_ADD:
            return 1.0 - min((min_dist + min_dist2), 1.0)
        elif self.config.cellular_return_type == CellularReturnType.DISTANCE2_SUB:
            return min_dist2 - min_dist
        elif self.config.cellular_return_type == CellularReturnType.DISTANCE2_MUL:
            return 1.0 - min(min_dist * min_dist2 * 4.0, 1.0)
        elif self.config.cellular_return_type == CellularReturnType.DISTANCE2_DIV:
            if min_dist2 > 0:
                return min_dist / min_dist2
            return 0.0
        else:
            return 1.0 - min(min_dist * 2.0, 1.0)
    
    def _get_cellular_feature_point(self, cell_x: int, cell_y: int) -> Tuple[float, float]:
        """获取网格的特征点位置"""
        # 使用哈希函数生成伪随机位置
        hash_val = hash((cell_x, cell_y, self.config.seed)) % (2**31)
        rng = np.random.default_rng(hash_val)
        
        # 在网格内随机偏移
        offset_x = rng.uniform(0, 1) * self.config.cellular_jitter
        offset_y = rng.uniform(0, 1) * self.config.cellular_jitter
        
        return cell_x + offset_x, cell_y + offset_y
    
    def _cellular_distance(self, x1: float, y1: float, 
                          x2: float, y2: float) -> float:
        """计算Cellular噪声的距离"""
        dx = x2 - x1
        dy = y2 - y1
        
        if self.config.cellular_distance_func == CellularDistanceFunction.EUCLIDEAN:
            return math.sqrt(dx * dx + dy * dy)
        elif self.config.cellular_distance_func == CellularDistanceFunction.MANHATTAN:
            return abs(dx) + abs(dy)
        elif self.config.cellular_distance_func == CellularDistanceFunction.HYBRID:
            return abs(dx) + abs(dy) + math.sqrt(dx * dx + dy * dy)
        else:
            return math.sqrt(dx * dx + dy * dy)
    
    def _white_noise_2d(self, x: float, y: float) -> float:
        """白噪声（纯随机）"""
        # 使用坐标和种子生成哈希
        hash_val = hash((int(x * 1000), int(y * 1000), self.config.seed)) % (2**31)
        rng = np.random.default_rng(hash_val)
        return rng.uniform(-1.0, 1.0)
    
    def _value_noise_2d(self, x: float, y: float) -> float:
        """
        Value噪声（简化实现）
        
        基于网格点的随机值进行插值
        """
        # 获取整数坐标
        x0 = int(math.floor(x))
        y0 = int(math.floor(y))
        x1 = x0 + 1
        y1 = y0 + 1
        
        # 获取小数部分
        fx = x - x0
        fy = y - y0
        
        # 平滑插值函数
        sx = fx * fx * (3.0 - 2.0 * fx)
        sy = fy * fy * (3.0 - 2.0 * fy)
        
        # 获取四个角的随机值
        v00 = self._get_value_at_point(x0, y0)
        v10 = self._get_value_at_point(x1, y0)
        v01 = self._get_value_at_point(x0, y1)
        v11 = self._get_value_at_point(x1, y1)
        
        # 双线性插值
        v0 = v00 * (1 - sx) + v10 * sx
        v1 = v01 * (1 - sx) + v11 * sx
        
        return v0 * (1 - sy) + v1 * sy
    
    def _get_value_at_point(self, x: int, y: int) -> float:
        """获取网格点的随机值"""
        hash_val = hash((x, y, self.config.seed)) % (2**31)
        rng = np.random.default_rng(hash_val)
        return rng.uniform(-1.0, 1.0)
    
    def _fbm_2d(self, x: float, y: float) -> float:
        """
        Fractional Brownian Motion (分形布朗运动)
        
        叠加多层不同频率和振幅的噪声
        """
        value = 0.0
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0
        
        for _ in range(self.config.octaves):
            value += self._single_noise_2d(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            
            amplitude *= self.config.persistence
            frequency *= self.config.lacunarity
        
        # 归一化
        if max_value > 0:
            value /= max_value
        
        return value
    
    def _ridged_2d(self, x: float, y: float) -> float:
        """
        Ridged Multifractal (脊状多重分形)
        
        创建山脊状的噪声图案
        """
        value = 0.0
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0
        
        for _ in range(self.config.octaves):
            noise_val = abs(self._single_noise_2d(x * frequency, y * frequency))
            noise_val = 1.0 - noise_val  # 反转
            noise_val = noise_val * noise_val  # 锐化
            
            value += noise_val * amplitude
            max_value += amplitude
            
            amplitude *= self.config.persistence
            frequency *= self.config.lacunarity
        
        # 归一化
        if max_value > 0:
            value /= max_value
        
        return value * 2.0 - 1.0  # 映射回 [-1, 1]
    
    def _ping_pong_2d(self, x: float, y: float) -> float:
        """
        Ping Pong分形
        
        创建波浪状的噪声图案
        """
        value = 0.0
        amplitude = 1.0
        frequency = 1.0
        
        for _ in range(self.config.octaves):
            noise_val = self._single_noise_2d(x * frequency, y * frequency)
            # Ping pong效果：在-1到1之间来回反弹
            noise_val = 1.0 - abs(noise_val)
            
            value += noise_val * amplitude
            
            amplitude *= self.config.persistence
            frequency *= self.config.lacunarity
        
        return value * 2.0 - 1.0  # 映射回 [-1, 1]
    
    def _domain_warp_2d(self, x: float, y: float) -> Tuple[float, float]:
        """
        域扭曲
        
        使用噪声函数扭曲坐标空间
        """
        warp_x = self._single_noise_2d(x * 0.5, y * 0.5) * self.config.domain_warp_amp
        warp_y = self._single_noise_2d(x * 0.5 + 100, y * 0.5 + 100) * self.config.domain_warp_amp
        
        return x + warp_x, y + warp_y


# ============================================================================
# 便捷函数
# ============================================================================

def generate_perlin_noise(width: int, height: int, 
                         frequency: float = 0.01, 
                         octaves: int = 6,
                         seed: int = 0) -> np.ndarray:
    """
    快速生成Perlin噪声
    
    Args:
        width: 宽度
        height: 高度
        frequency: 频率
        octaves: 八度数
        seed: 随机种子
    
    Returns:
        uint8噪声数组 (height, width)
    """
    config = ProceduralNoiseConfig(
        noise_type=ProceduralNoiseType.PERLIN,
        frequency=frequency,
        octaves=octaves,
        seed=seed,
        fractal_type=FractalType.FBM
    )
    generator = ProceduralNoiseGenerator(config)
    return generator.generate_2d_uint8(width, height)


def generate_simplex_noise(width: int, height: int,
                          frequency: float = 0.01,
                          octaves: int = 6,
                          seed: int = 0) -> np.ndarray:
    """
    快速生成OpenSimplex噪声
    
    Args:
        width: 宽度
        height: 高度
        frequency: 频率
        octaves: 八度数
        seed: 随机种子
    
    Returns:
        uint8噪声数组 (height, width)
    """
    config = ProceduralNoiseConfig(
        noise_type=ProceduralNoiseType.OPENSIMPLEX,
        frequency=frequency,
        octaves=octaves,
        seed=seed,
        fractal_type=FractalType.FBM
    )
    generator = ProceduralNoiseGenerator(config)
    return generator.generate_2d_uint8(width, height)


def generate_cellular_noise(width: int, height: int,
                           frequency: float = 0.02,
                           seed: int = 0) -> np.ndarray:
    """
    快速生成Cellular噪声
    
    Args:
        width: 宽度
        height: 高度
        frequency: 频率
        seed: 随机种子
    
    Returns:
        uint8噪声数组 (height, width)
    """
    config = ProceduralNoiseConfig(
        noise_type=ProceduralNoiseType.CELLULAR,
        frequency=frequency,
        seed=seed,
        fractal_type=FractalType.NONE
    )
    generator = ProceduralNoiseGenerator(config)
    return generator.generate_2d_uint8(width, height)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    from PIL import Image
    
    print("测试程序化噪声生成器...")
    
    # 测试Perlin噪声
    print("生成Perlin噪声...")
    perlin = generate_perlin_noise(512, 512, frequency=0.01, octaves=6, seed=42)
    Image.fromarray(perlin, mode='L').save('/tmp/test_perlin.png')
    print("✓ Perlin噪声已保存到 /tmp/test_perlin.png")
    
    # 测试OpenSimplex噪声
    print("生成OpenSimplex噪声...")
    simplex = generate_simplex_noise(512, 512, frequency=0.01, octaves=6, seed=42)
    Image.fromarray(simplex, mode='L').save('/tmp/test_simplex.png')
    print("✓ OpenSimplex噪声已保存到 /tmp/test_simplex.png")
    
    # 测试Cellular噪声
    print("生成Cellular噪声...")
    cellular = generate_cellular_noise(512, 512, frequency=0.02, seed=42)
    Image.fromarray(cellular, mode='L').save('/tmp/test_cellular.png')
    print("✓ Cellular噪声已保存到 /tmp/test_cellular.png")
    
    # 测试Ridged分形
    print("生成Ridged分形噪声...")
    config = ProceduralNoiseConfig(
        noise_type=ProceduralNoiseType.PERLIN,
        frequency=0.01,
        octaves=6,
        seed=42,
        fractal_type=FractalType.RIDGED
    )
    generator = ProceduralNoiseGenerator(config)
    ridged = generator.generate_2d_uint8(512, 512)
    Image.fromarray(ridged, mode='L').save('/tmp/test_ridged.png')
    print("✓ Ridged噪声已保存到 /tmp/test_ridged.png")
    
    print("\n✅ 所有测试完成！")
