#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PBR 贴图生成模块

实现 PBR (Physically Based Rendering) 风格的贴图生成：
- BaseColor: 基础颜色贴图（污渍、灰尘、飞溅等叠加）
- Normal: 法线贴图（裂纹、划痕转换）
- Roughness: 粗糙度贴图
- Metallic: 金属度贴图

贴图类型分类：
- BaseColor 类型（可多层叠加）: dirt, dust, Grunge-Dirt, splat
- Normal 类型（转换为法线）: Cracks, scratch
"""

import os
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from PIL import Image, ImageFilter, ImageOps


class TextureChannel(Enum):
    """贴图通道类型"""
    BASECOLOR = "basecolor"
    NORMAL = "normal"
    ROUGHNESS = "roughness"
    METALLIC = "metallic"
    AO = "ao"  # Ambient Occlusion


class TextureCategory(Enum):
    """贴图分类"""
    # BaseColor 类型 - 影响颜色，可多层叠加
    DIRT = "dirt"
    DUST = "dust"
    GRUNGE = "Grunge-Dirt"
    SPLAT = "splat"
    
    # Normal 类型 - 转换为法线贴图
    CRACKS = "Cracks"
    SCRATCH = "scratch"


class BlendMode(Enum):
    """混合模式"""
    MULTIPLY = "multiply"      # 正片叠底 - 适合污渍
    OVERLAY = "overlay"        # 叠加 - 适合增强对比
    SOFT_LIGHT = "soft_light"  # 柔光 - 适合轻微效果
    SCREEN = "screen"          # 滤色 - 适合高光
    DARKEN = "darken"          # 变暗 - 适合阴影
    NORMAL = "normal"          # 正常混合


@dataclass
class TextureLayerConfig:
    """单层贴图配置"""
    category: TextureCategory
    opacity: float = 0.5  # 不透明度 0-1
    blend_mode: BlendMode = BlendMode.MULTIPLY
    uv_scale: float = 3.0  # UV 缩放倍数
    rotation: float = 0.0  # 旋转角度
    flip_h: bool = False  # 水平翻转
    flip_v: bool = False  # 垂直翻转
    invert: bool = False  # 反转颜色


@dataclass
class PBRTextureConfig:
    """PBR 贴图配置"""
    # BaseColor 层配置（可多层叠加）
    basecolor_layers: List[TextureLayerConfig] = field(default_factory=list)
    
    # Normal 层配置（可多层叠加）
    normal_layers: List[TextureLayerConfig] = field(default_factory=list)
    
    # Roughness 基础值
    base_roughness: float = 0.5
    roughness_variation: float = 0.2
    
    # Metallic 基础值
    base_metallic: float = 0.0
    metallic_variation: float = 0.1
    
    # 法线强度
    normal_strength: float = 1.0


@dataclass
class PBRTextureSet:
    """PBR 贴图集"""
    basecolor: np.ndarray  # RGB
    normal: np.ndarray     # RGB (法线贴图)
    roughness: np.ndarray  # Grayscale
    metallic: np.ndarray   # Grayscale
    
    def save(self, output_dir: Path, base_name: str) -> Dict[str, Path]:
        """保存所有贴图"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        paths = {}
        
        # 保存 BaseColor
        basecolor_path = output_dir / f"{base_name}_basecolor.png"
        Image.fromarray(self.basecolor).save(str(basecolor_path))
        paths['basecolor'] = basecolor_path
        
        # 保存 Normal
        normal_path = output_dir / f"{base_name}_normal.png"
        Image.fromarray(self.normal).save(str(normal_path))
        paths['normal'] = normal_path
        
        # 保存 Roughness
        roughness_path = output_dir / f"{base_name}_roughness.png"
        Image.fromarray(self.roughness).save(str(roughness_path))
        paths['roughness'] = roughness_path
        
        # 保存 Metallic
        metallic_path = output_dir / f"{base_name}_metallic.png"
        Image.fromarray(self.metallic).save(str(metallic_path))
        paths['metallic'] = metallic_path
        
        return paths


class PBRTextureManager:
    """PBR 贴图管理器"""
    
    # 贴图分类映射
    BASECOLOR_CATEGORIES = {
        TextureCategory.DIRT,
        TextureCategory.DUST,
        TextureCategory.GRUNGE,
        TextureCategory.SPLAT,
    }
    
    NORMAL_CATEGORIES = {
        TextureCategory.CRACKS,
        TextureCategory.SCRATCH,
    }
    
    def __init__(self, texture_root: Union[str, Path]):
        """
        初始化贴图管理器
        
        Args:
            texture_root: 贴图资源根目录
        """
        self.texture_root = Path(texture_root)
        self.texture_cache: Dict[TextureCategory, List[Path]] = {}
        self._scan_textures()
    
    def _scan_textures(self):
        """扫描并缓存贴图文件"""
        # 查找解压后的目录
        mega_pack_dir = None
        for item in self.texture_root.iterdir():
            if item.is_dir() and "MEGA" in item.name:
                mega_pack_dir = item
                break
        
        if not mega_pack_dir:
            print(f"⚠️ 未找到贴图资源包目录: {self.texture_root}")
            return
        
        # 扫描各类型贴图
        for category in TextureCategory:
            category_dir = mega_pack_dir / category.value
            if category_dir.exists():
                textures = list(category_dir.glob("*.jpg")) + list(category_dir.glob("*.png"))
                self.texture_cache[category] = textures
                print(f"📁 {category.value}: 加载 {len(textures)} 张贴图")
            else:
                self.texture_cache[category] = []
                print(f"⚠️ {category.value}: 目录不存在")
    
    def get_random_texture(self, category: TextureCategory) -> Optional[Image.Image]:
        """获取随机贴图"""
        textures = self.texture_cache.get(category, [])
        if not textures:
            return None
        
        texture_path = random.choice(textures)
        try:
            return Image.open(texture_path).convert('RGB')
        except Exception as e:
            print(f"⚠️ 加载贴图失败: {texture_path}, {e}")
            return None
    
    def sample_texture_region(
        self,
        texture: Image.Image,
        target_size: Tuple[int, int],
        uv_scale: float = 3.0
    ) -> Image.Image:
        """
        从贴图中采样一个区域
        
        Args:
            texture: 源贴图
            target_size: 目标尺寸 (width, height)
            uv_scale: UV 缩放倍数，越大采样区域越小
        """
        tex_w, tex_h = texture.size
        target_w, target_h = target_size
        
        # 计算采样区域大小
        sample_w = int(tex_w / uv_scale)
        sample_h = int(tex_h / uv_scale)
        
        # 确保采样区域不超过贴图尺寸
        sample_w = min(sample_w, tex_w)
        sample_h = min(sample_h, tex_h)
        
        # 随机选择采样起点
        max_x = tex_w - sample_w
        max_y = tex_h - sample_h
        start_x = random.randint(0, max(0, max_x))
        start_y = random.randint(0, max(0, max_y))
        
        # 裁剪并缩放到目标尺寸
        region = texture.crop((start_x, start_y, start_x + sample_w, start_y + sample_h))
        return region.resize(target_size, Image.Resampling.LANCZOS)


class PBRTextureGenerator:
    """PBR 贴图生成器"""
    
    def __init__(self, texture_manager: PBRTextureManager):
        """
        初始化生成器
        
        Args:
            texture_manager: 贴图管理器
        """
        self.texture_manager = texture_manager
    
    def generate(
        self,
        base_image: np.ndarray,
        config: PBRTextureConfig
    ) -> PBRTextureSet:
        """
        生成 PBR 贴图集
        
        Args:
            base_image: 基础图像（车牌原图）
            config: PBR 贴图配置
            
        Returns:
            PBR 贴图集
        """
        h, w = base_image.shape[:2]
        target_size = (w, h)
        
        # 1. 生成 BaseColor
        basecolor = self._generate_basecolor(base_image, config.basecolor_layers, target_size)
        
        # 2. 生成 Normal
        normal = self._generate_normal(config.normal_layers, target_size, config.normal_strength)
        
        # 3. 生成 Roughness
        roughness = self._generate_roughness(
            config.basecolor_layers + config.normal_layers,
            target_size,
            config.base_roughness,
            config.roughness_variation
        )
        
        # 4. 生成 Metallic
        metallic = self._generate_metallic(
            target_size,
            config.base_metallic,
            config.metallic_variation
        )
        
        return PBRTextureSet(
            basecolor=basecolor,
            normal=normal,
            roughness=roughness,
            metallic=metallic
        )
    
    def _generate_basecolor(
        self,
        base_image: np.ndarray,
        layers: List[TextureLayerConfig],
        target_size: Tuple[int, int]
    ) -> np.ndarray:
        """生成 BaseColor 贴图"""
        result = base_image.copy()
        
        for layer_config in layers:
            # 只处理 BaseColor 类型的贴图
            if layer_config.category not in PBRTextureManager.BASECOLOR_CATEGORIES:
                continue
            
            # 获取随机贴图
            texture = self.texture_manager.get_random_texture(layer_config.category)
            if texture is None:
                continue
            
            # 采样区域
            sampled = self.texture_manager.sample_texture_region(
                texture, target_size, layer_config.uv_scale
            )
            
            # 应用变换
            sampled = self._apply_transforms(sampled, layer_config)
            
            # 转换为数组
            texture_array = np.array(sampled)
            
            # 混合
            result = self._blend_layers(
                result, texture_array,
                layer_config.blend_mode,
                layer_config.opacity
            )
        
        return result.astype(np.uint8)
    
    def _generate_normal(
        self,
        layers: List[TextureLayerConfig],
        target_size: Tuple[int, int],
        strength: float = 1.0
    ) -> np.ndarray:
        """生成 Normal 贴图"""
        # 初始化为平坦法线 (0.5, 0.5, 1.0) -> RGB (128, 128, 255)
        w, h = target_size
        normal = np.zeros((h, w, 3), dtype=np.float32)
        normal[:, :, 0] = 0.5  # X
        normal[:, :, 1] = 0.5  # Y
        normal[:, :, 2] = 1.0  # Z
        
        for layer_config in layers:
            # 只处理 Normal 类型的贴图
            if layer_config.category not in PBRTextureManager.NORMAL_CATEGORIES:
                continue
            
            # 获取随机贴图
            texture = self.texture_manager.get_random_texture(layer_config.category)
            if texture is None:
                continue
            
            # 采样区域
            sampled = self.texture_manager.sample_texture_region(
                texture, target_size, layer_config.uv_scale
            )
            
            # 应用变换
            sampled = self._apply_transforms(sampled, layer_config)
            
            # 转换为灰度图
            grayscale = sampled.convert('L')
            height_map = np.array(grayscale, dtype=np.float32) / 255.0
            
            # 从高度图生成法线
            layer_normal = self._height_to_normal(height_map, strength * layer_config.opacity)
            
            # 混合法线（使用 Reoriented Normal Mapping）
            normal = self._blend_normals(normal, layer_normal)
        
        # 转换为 0-255 范围
        normal_rgb = ((normal * 0.5 + 0.5) * 255).astype(np.uint8)
        return normal_rgb
    
    def _height_to_normal(
        self,
        height_map: np.ndarray,
        strength: float = 1.0
    ) -> np.ndarray:
        """
        从高度图生成法线贴图
        
        使用 Sobel 算子计算梯度
        """
        h, w = height_map.shape
        
        # 计算梯度
        # 使用 Sobel 算子
        dx = np.zeros_like(height_map)
        dy = np.zeros_like(height_map)
        
        # X 方向梯度
        dx[:, 1:-1] = (height_map[:, 2:] - height_map[:, :-2]) * 0.5
        dx[:, 0] = height_map[:, 1] - height_map[:, 0]
        dx[:, -1] = height_map[:, -1] - height_map[:, -2]
        
        # Y 方向梯度
        dy[1:-1, :] = (height_map[2:, :] - height_map[:-2, :]) * 0.5
        dy[0, :] = height_map[1, :] - height_map[0, :]
        dy[-1, :] = height_map[-1, :] - height_map[-2, :]
        
        # 应用强度
        dx *= strength
        dy *= strength
        
        # 构建法线
        normal = np.zeros((h, w, 3), dtype=np.float32)
        normal[:, :, 0] = -dx  # X
        normal[:, :, 1] = -dy  # Y
        normal[:, :, 2] = 1.0  # Z
        
        # 归一化
        length = np.sqrt(np.sum(normal ** 2, axis=2, keepdims=True))
        length = np.maximum(length, 1e-8)  # 避免除零
        normal = normal / length
        
        return normal
    
    def _blend_normals(
        self,
        base: np.ndarray,
        detail: np.ndarray
    ) -> np.ndarray:
        """
        混合两个法线贴图
        
        使用 Reoriented Normal Mapping (RNM) 方法
        """
        # 将法线从 [0, 1] 转换到 [-1, 1]
        n1 = base * 2.0 - 1.0
        n2 = detail * 2.0 - 1.0
        
        # RNM 混合
        n1[:, :, 2] += 1.0
        n2[:, :, 0] = -n2[:, :, 0]
        n2[:, :, 1] = -n2[:, :, 1]
        n2[:, :, 2] += 1.0
        
        # 计算混合结果
        result = n1 * np.sum(n1 * n2, axis=2, keepdims=True) - n2 * n1[:, :, 2:3]
        
        # 归一化
        length = np.sqrt(np.sum(result ** 2, axis=2, keepdims=True))
        length = np.maximum(length, 1e-8)
        result = result / length
        
        # 转换回 [0, 1]
        return result * 0.5 + 0.5
    
    def _generate_roughness(
        self,
        layers: List[TextureLayerConfig],
        target_size: Tuple[int, int],
        base_value: float = 0.5,
        variation: float = 0.2
    ) -> np.ndarray:
        """生成 Roughness 贴图"""
        w, h = target_size
        
        # 基础粗糙度
        roughness = np.full((h, w), base_value, dtype=np.float32)
        
        # 根据噪声层增加粗糙度变化
        for layer_config in layers:
            texture = self.texture_manager.get_random_texture(layer_config.category)
            if texture is None:
                continue
            
            sampled = self.texture_manager.sample_texture_region(
                texture, target_size, layer_config.uv_scale
            )
            sampled = self._apply_transforms(sampled, layer_config)
            
            # 转换为灰度
            grayscale = np.array(sampled.convert('L'), dtype=np.float32) / 255.0
            
            # 污渍和划痕会增加粗糙度
            roughness_delta = grayscale * variation * layer_config.opacity
            
            # 裂纹和划痕增加更多粗糙度
            if layer_config.category in PBRTextureManager.NORMAL_CATEGORIES:
                roughness_delta *= 1.5
            
            roughness = np.clip(roughness + roughness_delta, 0, 1)
        
        return (roughness * 255).astype(np.uint8)
    
    def _generate_metallic(
        self,
        target_size: Tuple[int, int],
        base_value: float = 0.0,
        variation: float = 0.1
    ) -> np.ndarray:
        """生成 Metallic 贴图"""
        w, h = target_size
        
        # 车牌通常不是金属材质，但边缘可能有金属框
        metallic = np.full((h, w), base_value, dtype=np.float32)
        
        # 添加轻微变化
        noise = np.random.rand(h, w) * variation
        metallic = np.clip(metallic + noise, 0, 1)
        
        return (metallic * 255).astype(np.uint8)
    
    def _apply_transforms(
        self,
        image: Image.Image,
        config: TextureLayerConfig
    ) -> Image.Image:
        """应用变换"""
        result = image
        
        # 翻转
        if config.flip_h:
            result = ImageOps.mirror(result)
        if config.flip_v:
            result = ImageOps.flip(result)
        
        # 旋转
        if config.rotation != 0:
            result = result.rotate(config.rotation, expand=False, fillcolor=(128, 128, 128))
        
        # 反转
        if config.invert:
            result = ImageOps.invert(result)
        
        return result
    
    def _blend_layers(
        self,
        base: np.ndarray,
        overlay: np.ndarray,
        mode: BlendMode,
        opacity: float
    ) -> np.ndarray:
        """混合两个图层"""
        base_f = base.astype(np.float32) / 255.0
        overlay_f = overlay.astype(np.float32) / 255.0
        
        if mode == BlendMode.MULTIPLY:
            blended = base_f * overlay_f
        elif mode == BlendMode.OVERLAY:
            mask = base_f < 0.5
            blended = np.where(
                mask,
                2 * base_f * overlay_f,
                1 - 2 * (1 - base_f) * (1 - overlay_f)
            )
        elif mode == BlendMode.SOFT_LIGHT:
            blended = (1 - 2 * overlay_f) * base_f ** 2 + 2 * overlay_f * base_f
        elif mode == BlendMode.SCREEN:
            blended = 1 - (1 - base_f) * (1 - overlay_f)
        elif mode == BlendMode.DARKEN:
            blended = np.minimum(base_f, overlay_f)
        else:  # NORMAL
            blended = overlay_f
        
        # 应用不透明度
        result = base_f * (1 - opacity) + blended * opacity
        
        return (np.clip(result, 0, 1) * 255).astype(np.uint8)


# ============ 预设配置 ============

def create_clean_config() -> PBRTextureConfig:
    """创建干净配置（无噪声）"""
    return PBRTextureConfig(
        basecolor_layers=[],
        normal_layers=[],
        base_roughness=0.4,
        base_metallic=0.0
    )


def create_light_config() -> PBRTextureConfig:
    """创建轻度噪声配置"""
    return PBRTextureConfig(
        basecolor_layers=[
            TextureLayerConfig(
                category=TextureCategory.DUST,
                opacity=0.15,
                blend_mode=BlendMode.MULTIPLY,
                uv_scale=4.0,
                flip_h=random.choice([True, False]),
                flip_v=random.choice([True, False])
            ),
        ],
        normal_layers=[
            TextureLayerConfig(
                category=TextureCategory.SCRATCH,
                opacity=0.3,
                uv_scale=5.0,
                flip_h=random.choice([True, False])
            ),
        ],
        base_roughness=0.45,
        normal_strength=0.5
    )


def create_medium_config() -> PBRTextureConfig:
    """创建中度噪声配置"""
    return PBRTextureConfig(
        basecolor_layers=[
            TextureLayerConfig(
                category=TextureCategory.DIRT,
                opacity=0.25,
                blend_mode=BlendMode.MULTIPLY,
                uv_scale=3.5,
                flip_h=random.choice([True, False]),
                flip_v=random.choice([True, False])
            ),
            TextureLayerConfig(
                category=TextureCategory.DUST,
                opacity=0.2,
                blend_mode=BlendMode.SOFT_LIGHT,
                uv_scale=4.0,
                flip_h=random.choice([True, False])
            ),
        ],
        normal_layers=[
            TextureLayerConfig(
                category=TextureCategory.SCRATCH,
                opacity=0.5,
                uv_scale=4.0,
                flip_h=random.choice([True, False])
            ),
            TextureLayerConfig(
                category=TextureCategory.CRACKS,
                opacity=0.3,
                uv_scale=5.0,
                flip_v=random.choice([True, False])
            ),
        ],
        base_roughness=0.5,
        normal_strength=0.8
    )


def create_heavy_config() -> PBRTextureConfig:
    """创建重度噪声配置"""
    return PBRTextureConfig(
        basecolor_layers=[
            TextureLayerConfig(
                category=TextureCategory.GRUNGE,
                opacity=0.35,
                blend_mode=BlendMode.MULTIPLY,
                uv_scale=3.0,
                flip_h=random.choice([True, False]),
                flip_v=random.choice([True, False])
            ),
            TextureLayerConfig(
                category=TextureCategory.DIRT,
                opacity=0.3,
                blend_mode=BlendMode.MULTIPLY,
                uv_scale=3.5,
                flip_h=random.choice([True, False])
            ),
            TextureLayerConfig(
                category=TextureCategory.SPLAT,
                opacity=0.2,
                blend_mode=BlendMode.DARKEN,
                uv_scale=4.0,
                flip_v=random.choice([True, False])
            ),
        ],
        normal_layers=[
            TextureLayerConfig(
                category=TextureCategory.CRACKS,
                opacity=0.7,
                uv_scale=3.0,
                flip_h=random.choice([True, False]),
                flip_v=random.choice([True, False])
            ),
            TextureLayerConfig(
                category=TextureCategory.SCRATCH,
                opacity=0.6,
                uv_scale=3.5,
                flip_h=random.choice([True, False])
            ),
        ],
        base_roughness=0.6,
        roughness_variation=0.3,
        normal_strength=1.2
    )


def create_extreme_config() -> PBRTextureConfig:
    """创建极端噪声配置"""
    return PBRTextureConfig(
        basecolor_layers=[
            TextureLayerConfig(
                category=TextureCategory.GRUNGE,
                opacity=0.45,
                blend_mode=BlendMode.MULTIPLY,
                uv_scale=2.5,
                flip_h=random.choice([True, False]),
                flip_v=random.choice([True, False])
            ),
            TextureLayerConfig(
                category=TextureCategory.DIRT,
                opacity=0.4,
                blend_mode=BlendMode.MULTIPLY,
                uv_scale=3.0,
                flip_h=random.choice([True, False])
            ),
            TextureLayerConfig(
                category=TextureCategory.SPLAT,
                opacity=0.35,
                blend_mode=BlendMode.DARKEN,
                uv_scale=3.5,
                flip_v=random.choice([True, False])
            ),
            TextureLayerConfig(
                category=TextureCategory.DUST,
                opacity=0.25,
                blend_mode=BlendMode.OVERLAY,
                uv_scale=4.0
            ),
        ],
        normal_layers=[
            TextureLayerConfig(
                category=TextureCategory.CRACKS,
                opacity=0.9,
                uv_scale=2.5,
                flip_h=random.choice([True, False]),
                flip_v=random.choice([True, False])
            ),
            TextureLayerConfig(
                category=TextureCategory.SCRATCH,
                opacity=0.8,
                uv_scale=3.0,
                flip_h=random.choice([True, False])
            ),
            TextureLayerConfig(
                category=TextureCategory.CRACKS,
                opacity=0.5,
                uv_scale=4.0,
                flip_v=random.choice([True, False]),
                invert=True
            ),
        ],
        base_roughness=0.7,
        roughness_variation=0.35,
        normal_strength=1.5
    )


def create_random_config() -> PBRTextureConfig:
    """创建随机噪声配置"""
    configs = [
        create_light_config,
        create_medium_config,
        create_heavy_config,
    ]
    return random.choice(configs)()


# ============ 预设映射 ============

PBR_PRESETS = {
    "clean": create_clean_config,
    "light": create_light_config,
    "medium": create_medium_config,
    "heavy": create_heavy_config,
    "extreme": create_extreme_config,
    "random": create_random_config,
}


def get_pbr_config(preset: str) -> PBRTextureConfig:
    """获取预设配置"""
    factory = PBR_PRESETS.get(preset, create_medium_config)
    return factory()


# ============ 测试代码 ============

if __name__ == "__main__":
    import sys
    
    # 测试贴图管理器
    texture_root = Path(__file__).parent.parent / "assets" / "noise_textures"
    
    if texture_root.exists():
        manager = PBRTextureManager(texture_root)
        generator = PBRTextureGenerator(manager)
        
        # 创建测试图像
        test_image = np.random.randint(0, 255, (220, 440, 3), dtype=np.uint8)
        test_image[:, :, 0] = 30  # 蓝色车牌底色
        test_image[:, :, 1] = 80
        test_image[:, :, 2] = 180
        
        # 生成 PBR 贴图
        config = create_medium_config()
        pbr_set = generator.generate(test_image, config)
        
        # 保存测试结果
        output_dir = Path(__file__).parent.parent / "data" / "output" / "pbr_test"
        paths = pbr_set.save(output_dir, "test_plate")
        
        print("✅ PBR 贴图生成测试完成:")
        for channel, path in paths.items():
            print(f"   {channel}: {path}")
    else:
        print(f"⚠️ 贴图目录不存在: {texture_root}")
