#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
带噪声的车牌生成脚本

集成噪声模块，生成多样化的车牌图像，包含污渍、阴影、掉漆、异物遮挡等效果。
基于原有的MultiPlateGenerator，确保字符正确合成。

使用方法:
    python scripts/generate_noisy_plates.py --number 20 --preset medium
    python scripts/generate_noisy_plates.py --number 50 --preset heavy --output data/output/noisy
"""

import os
import sys
import argparse
import random
from pathlib import Path
from typing import List, Optional

import numpy as np
import cv2
from PIL import Image
from tqdm import tqdm

# 添加项目根目录和assets目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "assets"))

from core.noise_module import (
    CompositeNoiseApplicator,
    CompositeNoiseConfig,
    StainConfig,
    ShadowConfig,
    PaintPeelingConfig,
    OcclusionConfig,
    NoiseIntensity,
    NoiseType,
)

# 导入原有的车牌生成器
from generate_multi_plate import MultiPlateGenerator


class NoisyPlateGenerator:
    """带噪声的车牌生成器"""
    
    def __init__(self, 
                 output_dir: str = None,
                 noise_preset: str = 'medium'):
        """
        初始化生成器
        
        Args:
            output_dir: 输出目录
            noise_preset: 噪声预设 ('clean', 'light', 'medium', 'heavy', 'extreme', 'random')
        """
        self.project_root = PROJECT_ROOT
        
        # 设置输出目录
        self.output_dir = Path(output_dir) if output_dir else \
                          self.project_root / "data" / "output" / "noisy"
        
        # 创建输出目录
        (self.output_dir / "img").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "txt").mkdir(parents=True, exist_ok=True)
        
        self.noise_preset = noise_preset
        
        # 初始化原有的车牌生成器
        self.plate_generator = MultiPlateGenerator(
            adr_plate_model='plate_model',
            adr_font='font_model'
        )
        
        print(f"✅ 带噪声车牌生成器初始化完成")
        print(f"📁 输出目录: {self.output_dir}")
        print(f"🎨 噪声预设: {self.noise_preset}")
    
    def _get_random_noise_config(self) -> CompositeNoiseConfig:
        """获取随机噪声配置"""
        intensities = [NoiseIntensity.LIGHT, NoiseIntensity.MEDIUM, 
                      NoiseIntensity.HEAVY, NoiseIntensity.EXTREME]
        
        return CompositeNoiseConfig(
            stain=StainConfig(
                enabled=random.random() > 0.3,
                intensity=random.choice(intensities),
                probability=random.uniform(0.3, 0.8),
                stain_types=random.sample(['mud', 'oil', 'dust', 'water'], 
                                         k=random.randint(1, 3)),
            ),
            shadow=ShadowConfig(
                enabled=random.random() > 0.2,
                intensity=random.choice(intensities),
                probability=random.uniform(0.4, 0.9),
                shadow_types=random.sample(['gradient', 'spot', 'edge', 'vignette'],
                                          k=random.randint(1, 3)),
            ),
            paint_peeling=PaintPeelingConfig(
                enabled=random.random() > 0.5,
                intensity=random.choice(intensities),
                probability=random.uniform(0.2, 0.6),
                peeling_types=random.sample(['edge', 'spot', 'crack', 'flake'],
                                           k=random.randint(1, 3)),
            ),
            occlusion=OcclusionConfig(
                enabled=random.random() > 0.6,
                intensity=random.choice(intensities),
                probability=random.uniform(0.1, 0.5),
                occlusion_types=random.sample(['leaf', 'sticker', 'tape', 'dirt_blob', 'screw'],
                                             k=random.randint(1, 3)),
            ),
        )
    
    def _apply_noise(self, image: np.ndarray, randomize: bool = True) -> np.ndarray:
        """
        应用噪声到图像
        
        Args:
            image: 输入图像 (BGR格式，OpenCV)
            randomize: 是否随机化噪声配置
            
        Returns:
            带噪声的图像
        """
        # 转换为RGB格式
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        if randomize or self.noise_preset == 'random':
            # 使用随机配置
            config = self._get_random_noise_config()
            applicator = CompositeNoiseApplicator(config)
            noisy_image = applicator.apply_random(image_rgb, min_types=1, max_types=4)
        else:
            # 使用预设
            applicator = CompositeNoiseApplicator.create_preset(self.noise_preset)
            noisy_image = applicator.apply(image_rgb)
        
        # 转换回BGR格式
        return cv2.cvtColor(noisy_image, cv2.COLOR_RGB2BGR)
    
    def generate(self, number: int = 20, 
                 randomize_noise: bool = True) -> List[str]:
        """
        生成带噪声的车牌
        
        Args:
            number: 生成数量
            randomize_noise: 是否随机化噪声配置
            
        Returns:
            生成的文件路径列表
        """
        generated_files = []
        
        print(f"\n🚗 开始生成 {number} 个带噪声的车牌...")
        
        for i in tqdm(range(number), desc="生成进度"):
            try:
                # 使用原有生成器生成车牌
                img_plate, font_mask, number_xy, plate_number, bg_color, is_double = \
                    self.plate_generator.generate_plate(enhance=False)
                
                # 应用噪声
                noisy_plate = self._apply_noise(img_plate, randomize=randomize_noise)
                
                # 确定噪声级别标签
                noise_level = self.noise_preset if not randomize_noise else 'random'
                
                # 保存图像
                filename = f"{plate_number}_{bg_color}_{noise_level}_{i:04d}.jpg"
                output_path = self.output_dir / "img" / filename
                
                cv2.imwrite(str(output_path), noisy_plate, 
                           [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                # 保存标注
                txt_filename = f"{plate_number}_{bg_color}_{noise_level}_{i:04d}.txt"
                txt_path = self.output_dir / "txt" / txt_filename
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(f"plate_number: {plate_number}\n")
                    f.write(f"plate_type: {bg_color}\n")
                    f.write(f"is_double: {is_double}\n")
                    f.write(f"noise_level: {noise_level}\n")
                
                generated_files.append(str(output_path))
                
            except Exception as e:
                print(f"⚠️ 生成第 {i} 个车牌失败: {e}")
                continue
        
        print(f"\n✅ 成功生成 {len(generated_files)} 个带噪声的车牌")
        print(f"📁 输出目录: {self.output_dir}")
        
        return generated_files


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='生成带噪声的车牌图像',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python generate_noisy_plates.py --number 20
  python generate_noisy_plates.py --number 50 --preset heavy
  python generate_noisy_plates.py --number 100 --preset random --output data/output/noisy
        """
    )
    
    parser.add_argument('--number', '-n', type=int, default=20,
                       help='生成数量 (默认: 20)')
    parser.add_argument('--preset', '-p', type=str, default='medium',
                       choices=['clean', 'light', 'medium', 'heavy', 'extreme', 'random'],
                       help='噪声预设 (默认: medium)')
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='输出目录')
    parser.add_argument('--randomize', '-r', action='store_true',
                       help='随机化噪声配置')
    parser.add_argument('--seed', '-s', type=int, default=None,
                       help='随机种子')
    
    args = parser.parse_args()
    
    # 设置随机种子
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)
    
    # 创建生成器
    generator = NoisyPlateGenerator(
        output_dir=args.output,
        noise_preset=args.preset
    )
    
    # 生成车牌
    generator.generate(
        number=args.number,
        randomize_noise=args.randomize or args.preset == 'random'
    )


if __name__ == '__main__':
    main()
