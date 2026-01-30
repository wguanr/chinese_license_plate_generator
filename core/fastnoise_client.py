#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastNoiseLite Go服务客户端 (FastNoiseLite Go Service Client)

Python客户端，用于调用Go实现的FastNoiseLite噪声生成服务
提供高性能的程序化噪声生成能力

作者: PCG-USD车牌材质系统
版本: 1.0.0
"""

import json
import requests
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from PIL import Image


@dataclass
class FastNoiseConfig:
    """
    FastNoiseLite噪声配置
    
    Attributes:
        width: 纹理宽度
        height: 纹理高度
        noise_type: 噪声类型 ("opensimplex2", "opensimplex2s", "perlin", "cellular", "value", "value_cubic")
        seed: 随机种子
        frequency: 噪声频率
        fractal_type: 分形类型 ("none", "fbm", "ridged", "pingpong")
        fractal_octaves: 分形层数
        fractal_lacunarity: 间隙度
        fractal_gain: 增益
        cellular_distance_func: Cellular距离函数 ("euclidean", "manhattan", "hybrid")
        cellular_return_type: Cellular返回类型 ("cellvalue", "distance", "distance2", "distance2add", "distance2sub")
    """
    width: int = 512
    height: int = 512
    noise_type: str = "opensimplex2"
    seed: int = 1337
    frequency: float = 0.01
    fractal_type: str = "fbm"
    fractal_octaves: int = 6
    fractal_lacunarity: float = 2.0
    fractal_gain: float = 0.5
    cellular_distance_func: str = "euclidean"
    cellular_return_type: str = "distance"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "width": self.width,
            "height": self.height,
            "noise_type": self.noise_type,
            "seed": self.seed,
            "frequency": self.frequency,
            "fractal_type": self.fractal_type,
            "fractal_octaves": self.fractal_octaves,
            "fractal_lacunarity": self.fractal_lacunarity,
            "fractal_gain": self.fractal_gain,
            "cellular_distance_func": self.cellular_distance_func,
            "cellular_return_type": self.cellular_return_type,
        }


class FastNoiseClient:
    """
    FastNoiseLite Go服务客户端
    
    通过HTTP调用Go服务生成高性能噪声纹理
    """
    
    def __init__(self, service_url: str = "http://localhost:8080"):
        """
        初始化客户端
        
        Args:
            service_url: Go服务的URL地址
        """
        self.service_url = service_url.rstrip('/')
        self._check_service()
    
    def _check_service(self):
        """检查服务是否可用"""
        try:
            response = requests.get(f"{self.service_url}/health", timeout=2)
            if response.status_code != 200:
                raise ConnectionError(f"Service health check failed: {response.status_code}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Cannot connect to FastNoiseLite service at {self.service_url}: {e}")
    
    def generate(self, config: FastNoiseConfig) -> np.ndarray:
        """
        生成噪声纹理
        
        Args:
            config: 噪声配置
        
        Returns:
            噪声纹理数组 (height, width)，uint8格式，值范围 [0, 255]
        """
        # 发送POST请求
        response = requests.post(
            f"{self.service_url}/generate",
            json=config.to_dict(),
            timeout=30
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Failed to generate noise: {response.status_code} - {response.text}")
        
        # 获取尺寸信息
        width = int(response.headers.get('X-Width', config.width))
        height = int(response.headers.get('X-Height', config.height))
        
        # 解析二进制数据
        noise_data = np.frombuffer(response.content, dtype=np.uint8)
        noise_array = noise_data.reshape((height, width))
        
        return noise_array
    
    def generate_to_file(self, config: FastNoiseConfig, output_path: str):
        """
        生成噪声并保存为图片文件
        
        Args:
            config: 噪声配置
            output_path: 输出文件路径
        """
        noise_array = self.generate(config)
        img = Image.fromarray(noise_array, mode='L')
        img.save(output_path)


# ============================================================================
# 噪声预设
# ============================================================================

class FastNoisePresets:
    """FastNoiseLite噪声预设"""
    
    @staticmethod
    def perlin_fbm(width: int = 512, height: int = 512, seed: int = 1337) -> FastNoiseConfig:
        """Perlin FBM噪声（适合自然纹理）"""
        return FastNoiseConfig(
            width=width,
            height=height,
            noise_type="perlin",
            seed=seed,
            frequency=0.01,
            fractal_type="fbm",
            fractal_octaves=6,
            fractal_lacunarity=2.0,
            fractal_gain=0.5
        )
    
    @staticmethod
    def opensimplex_ridged(width: int = 512, height: int = 512, seed: int = 1337) -> FastNoiseConfig:
        """OpenSimplex Ridged噪声（适合山脊/划痕效果）"""
        return FastNoiseConfig(
            width=width,
            height=height,
            noise_type="opensimplex2",
            seed=seed,
            frequency=0.01,
            fractal_type="ridged",
            fractal_octaves=6,
            fractal_lacunarity=2.0,
            fractal_gain=0.5
        )
    
    @staticmethod
    def cellular_cracks(width: int = 512, height: int = 512, seed: int = 1337) -> FastNoiseConfig:
        """Cellular噪声（适合裂纹效果）"""
        return FastNoiseConfig(
            width=width,
            height=height,
            noise_type="cellular",
            seed=seed,
            frequency=0.02,
            fractal_type="none",
            cellular_distance_func="euclidean",
            cellular_return_type="distance2sub"
        )
    
    @staticmethod
    def cellular_voronoi(width: int = 512, height: int = 512, seed: int = 1337) -> FastNoiseConfig:
        """Cellular Voronoi噪声（适合细胞状纹理）"""
        return FastNoiseConfig(
            width=width,
            height=height,
            noise_type="cellular",
            seed=seed,
            frequency=0.03,
            fractal_type="none",
            cellular_distance_func="euclidean",
            cellular_return_type="distance"
        )
    
    @staticmethod
    def pingpong_waves(width: int = 512, height: int = 512, seed: int = 1337) -> FastNoiseConfig:
        """Ping Pong噪声（适合波浪效果）"""
        return FastNoiseConfig(
            width=width,
            height=height,
            noise_type="opensimplex2",
            seed=seed,
            frequency=0.015,
            fractal_type="pingpong",
            fractal_octaves=4,
            fractal_lacunarity=2.0,
            fractal_gain=0.5
        )


# ============================================================================
# 便捷函数
# ============================================================================

def generate_fast_noise(noise_type: str = "perlin",
                       width: int = 512,
                       height: int = 512,
                       seed: int = 1337,
                       service_url: str = "http://localhost:8080") -> np.ndarray:
    """
    快速生成噪声（便捷函数）
    
    Args:
        noise_type: 噪声类型 ("perlin", "opensimplex", "cellular", "ridged", "pingpong")
        width: 宽度
        height: 高度
        seed: 随机种子
        service_url: 服务URL
    
    Returns:
        噪声纹理数组
    """
    client = FastNoiseClient(service_url)
    
    # 根据类型选择预设
    presets = {
        "perlin": FastNoisePresets.perlin_fbm,
        "opensimplex": FastNoisePresets.perlin_fbm,  # 使用相同配置但不同类型
        "cellular": FastNoisePresets.cellular_cracks,
        "ridged": FastNoisePresets.opensimplex_ridged,
        "pingpong": FastNoisePresets.pingpong_waves,
    }
    
    if noise_type in presets:
        config = presets[noise_type](width, height, seed)
        if noise_type == "opensimplex":
            config.noise_type = "opensimplex2"
    else:
        # 默认配置
        config = FastNoiseConfig(
            width=width,
            height=height,
            noise_type="opensimplex2",
            seed=seed
        )
    
    return client.generate(config)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    import time
    
    print("测试FastNoiseLite Go服务客户端...")
    
    try:
        client = FastNoiseClient()
        print("✓ 成功连接到Go服务")
        
        # 测试不同噪声类型
        test_configs = [
            ("Perlin FBM", FastNoisePresets.perlin_fbm(256, 256, 42)),
            ("OpenSimplex Ridged", FastNoisePresets.opensimplex_ridged(256, 256, 42)),
            ("Cellular Cracks", FastNoisePresets.cellular_cracks(256, 256, 42)),
            ("Cellular Voronoi", FastNoisePresets.cellular_voronoi(256, 256, 42)),
            ("Ping Pong Waves", FastNoisePresets.pingpong_waves(256, 256, 42)),
        ]
        
        for name, config in test_configs:
            print(f"\n生成 {name}...")
            start_time = time.time()
            noise = client.generate(config)
            elapsed = time.time() - start_time
            
            # 保存图片
            output_path = f"/tmp/fastnoise_{name.lower().replace(' ', '_')}.png"
            Image.fromarray(noise).save(output_path)
            
            print(f"  ✓ 完成，耗时 {elapsed:.3f}秒")
            print(f"  - 形状: {noise.shape}")
            print(f"  - 值范围: [{noise.min()}, {noise.max()}]")
            print(f"  - 已保存到: {output_path}")
        
        print("\n✅ 所有测试完成！")
        
    except ConnectionError as e:
        print(f"❌ 连接错误: {e}")
        print("请确保Go服务正在运行: cd go_noise_service && ./noise-service")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
