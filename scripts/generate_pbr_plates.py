#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PBR 车牌生成脚本

生成带有完整 PBR 贴图的车牌资产：
- BaseColor: 基础颜色 + 污渍/灰尘叠加
- Normal: 裂纹/划痕转换的法线贴图
- Roughness: 粗糙度贴图
- Metallic: 金属度贴图

同时导出 USD 文件用于 3D 渲染。
"""

import argparse
import random
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "assets"))

import cv2
import numpy as np
from PIL import Image

# 导入核心模块
from core.pbr_texture_module import (
    PBRTextureManager, PBRTextureGenerator, PBRTextureConfig,
    get_pbr_config, PBR_PRESETS
)
from core.pbr_usd_exporter import PBRUSDGenerator, PlateAssetInfo, PBRTexturePaths

# 导入车牌生成器
from generate_multi_plate import MultiPlateGenerator


def generate_pbr_plates(
    count: int = 20,
    preset: str = "random",
    output_dir: Path = None
):
    """
    生成带 PBR 贴图的车牌
    
    Args:
        count: 生成数量
        preset: 噪声预设 (clean, light, medium, heavy, extreme, random)
        output_dir: 输出目录
    """
    # 设置输出目录
    if output_dir is None:
        output_dir = PROJECT_ROOT / "data" / "output" / "pbr"
    output_dir = Path(output_dir)
    
    # 创建子目录
    img_dir = output_dir / "img"
    textures_dir = output_dir / "textures"
    usd_dir = output_dir / "usd"
    
    img_dir.mkdir(parents=True, exist_ok=True)
    textures_dir.mkdir(parents=True, exist_ok=True)
    usd_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化车牌生成器
    plate_model_dir = PROJECT_ROOT / "assets" / "plate_model"
    font_model_dir = PROJECT_ROOT / "assets" / "font_model"
    
    if not plate_model_dir.exists() or not font_model_dir.exists():
        print("❌ 资源目录不存在，请确保 plate_model 和 font_model 目录存在")
        return
    
    plate_generator = MultiPlateGenerator(str(plate_model_dir), str(font_model_dir))
    print("✅ 车牌生成器初始化成功")
    
    # 初始化 PBR 贴图管理器
    texture_root = PROJECT_ROOT / "assets" / "noise_textures"
    if not texture_root.exists():
        print("❌ 噪声贴图目录不存在")
        return
    
    pbr_manager = PBRTextureManager(texture_root)
    pbr_generator = PBRTextureGenerator(pbr_manager)
    print("✅ PBR 贴图生成器初始化成功")
    
    # 初始化 USD 生成器
    usd_generator = PBRUSDGenerator(usd_dir)
    print("✅ USD 生成器初始化成功")
    
    # 车牌类型列表
    plate_types = [
        ("blue", False),
        ("yellow", False),
        ("yellow", True),
        ("green_car", False),
        ("green_truck", False),
        ("white", False),
        ("black", False),
        ("black_shi", False),
    ]
    
    # 生成车牌
    print(f"\n🚗 开始生成 {count} 张 PBR 车牌...")
    
    assets = []
    
    for i in range(count):
        # 生成车牌（使用 generate_plate 方法）
        try:
            # generate_plate 返回: img_plate_model, font_img_mask, number_xy, plate_number, bg_color, is_double
            result = plate_generator.generate_plate()
            plate_img_cv = result[0]  # OpenCV 格式 (BGR)
            plate_number = result[3]
            bg_color = result[4]
            is_double = result[5]
            plate_type = bg_color
            
            # 转换为 PIL Image (RGB)
            plate_img = Image.fromarray(cv2.cvtColor(plate_img_cv, cv2.COLOR_BGR2RGB))
        except Exception as e:
            print(f"⚠️ 生成车牌失败: {e}")
            import traceback
            traceback.print_exc()
            continue
        
        # 转换为 numpy 数组
        base_image = np.array(plate_img)
        
        # 获取 PBR 配置
        if preset == "random":
            current_preset = random.choice(["light", "medium", "heavy"])
        else:
            current_preset = preset
        
        pbr_config = get_pbr_config(current_preset)
        
        # 生成 PBR 贴图
        try:
            pbr_set = pbr_generator.generate(base_image, pbr_config)
        except Exception as e:
            print(f"⚠️ 生成 PBR 贴图失败: {e}")
            # 使用原图作为 basecolor
            pbr_set = None
        
        # 保存文件
        base_name = f"{plate_number}_{plate_type}_{current_preset}_{i:04d}"
        
        # 保存原始车牌图片
        img_path = img_dir / f"{base_name}.jpg"
        plate_img.save(str(img_path), quality=95)
        
        # 保存 PBR 贴图
        if pbr_set:
            texture_paths = pbr_set.save(textures_dir, base_name)
            
            pbr_texture_paths = PBRTexturePaths(
                basecolor=texture_paths['basecolor'],
                normal=texture_paths['normal'],
                roughness=texture_paths['roughness'],
                metallic=texture_paths['metallic']
            )
        else:
            pbr_texture_paths = None
        
        # 创建资产信息
        asset_info = PlateAssetInfo(
            plate_number=plate_number,
            plate_type=plate_type,
            is_double=is_double,
            noise_preset=current_preset,
            pbr_textures=pbr_texture_paths
        )
        assets.append(asset_info)
        
        # 生成单个 USD 文件
        usd_path = usd_generator.generate_plate_usd(asset_info, base_name)
        
        print(f"✅ [{i+1}/{count}] {base_name}")
    
    # 生成主 USD 文件
    if assets:
        main_usd_path, _ = usd_generator.generate_batch_usd(assets, "license_plates_pbr")
        manifest_path = usd_generator.generate_manifest(assets, "license_plates_pbr")
        
        print(f"\n🎉 完成! 共生成 {len(assets)} 张 PBR 车牌")
        print(f"📁 图片目录: {img_dir}")
        print(f"📁 贴图目录: {textures_dir}")
        print(f"📁 USD 目录: {usd_dir}")
        print(f"📄 主 USD 文件: {main_usd_path}")
        print(f"📄 资产清单: {manifest_path}")
    else:
        print("❌ 未生成任何车牌")


def main():
    parser = argparse.ArgumentParser(description="生成带 PBR 贴图的车牌")
    parser.add_argument("--count", type=int, default=20, help="生成数量")
    parser.add_argument("--preset", type=str, default="random",
                       choices=list(PBR_PRESETS.keys()),
                       help="噪声预设")
    parser.add_argument("--output", type=str, default=None, help="输出目录")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output) if args.output else None
    generate_pbr_plates(args.count, args.preset, output_dir)


if __name__ == "__main__":
    main()
