#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用真实贴图噪声生成车牌

集成贴图噪声模块，使用高质量噪声贴图生成多样化的车牌图像。
"""

import sys
import random
import cv2
import numpy as np
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "assets"))

from PIL import Image
from assets.generate_multi_plate import MultiPlateGenerator
from core.texture_noise_module import (
    TextureManager, TextureNoiseGenerator, 
    CompositeTextureNoiseConfig, NoiseIntensity
)


def cv2_to_pil(cv2_image):
    """将 OpenCV 图像转换为 PIL 图像"""
    # OpenCV 使用 BGR，PIL 使用 RGB
    rgb_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb_image)


def pil_to_cv2(pil_image):
    """将 PIL 图像转换为 OpenCV 图像"""
    rgb_array = np.array(pil_image)
    return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)


def generate_plates_with_texture_noise(
    count: int = 20,
    output_dir: Path = None,
    noise_preset: str = 'random'
):
    """
    使用贴图噪声生成车牌
    
    Args:
        count: 生成数量
        output_dir: 输出目录
        noise_preset: 噪声预设 ('clean', 'light', 'medium', 'heavy', 'extreme', 'random')
    """
    if output_dir is None:
        output_dir = project_root / "data" / "output" / "texture_noisy" / "img"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化车牌生成器
    plate_generator = MultiPlateGenerator(
        adr_plate_model="plate_model",
        adr_font="font_model"
    )
    
    # 初始化贴图噪声生成器
    texture_manager = TextureManager()
    noise_generator = TextureNoiseGenerator(texture_manager)
    
    print(f"📦 贴图资源统计:")
    for t, c in texture_manager.get_all_counts().items():
        print(f"   {t}: {c} 张")
    
    print(f"\n🚗 开始生成 {count} 张带贴图噪声的车牌...")
    
    generated = 0
    for i in range(count):
        try:
            # 使用原生的 generate_plate 方法
            result = plate_generator.generate_plate(enhance=False)
            cv2_plate_image, _, _, plate_number, bg_color, is_double = result
            
            # 转换为 PIL 图像
            pil_plate_image = cv2_to_pil(cv2_plate_image)
            
            # 确定噪声预设
            if noise_preset == 'random':
                current_preset = random.choice(['light', 'medium', 'heavy'])
            else:
                current_preset = noise_preset
            
            # 应用贴图噪声
            noisy_image = noise_generator.apply_preset(pil_plate_image, current_preset)
            
            # 构建文件名
            double_str = "double" if is_double else "single"
            filename = f"{plate_number}_{bg_color}_{double_str}_{current_preset}_{i:04d}.jpg"
            filepath = output_dir / filename
            
            # 保存
            noisy_image.save(str(filepath), quality=95)
            generated += 1
            
            print(f"✅ [{generated}/{count}] {filename}")
            
        except Exception as e:
            print(f"❌ 生成错误: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n🎉 完成! 共生成 {generated} 张车牌")
    print(f"📁 输出目录: {output_dir}")
    
    return generated


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="使用贴图噪声生成车牌")
    parser.add_argument("--count", type=int, default=20, help="生成数量")
    parser.add_argument("--preset", type=str, default="random", 
                        choices=['clean', 'light', 'medium', 'heavy', 'extreme', 'random'],
                        help="噪声预设")
    parser.add_argument("--output", type=str, default=None, help="输出目录")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output) if args.output else None
    
    generate_plates_with_texture_noise(
        count=args.count,
        output_dir=output_dir,
        noise_preset=args.preset
    )
