#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
程序化车牌生成器

使用纯Python和PIL生成车牌图片，不依赖外部资源文件。
"""

import os
import random
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

# 省份简称
PROVINCES = ['京', '津', '沪', '渝', '冀', '豫', '云', '辽', '黑', '湘', 
             '皖', '鲁', '新', '苏', '浙', '赣', '鄂', '桂', '甘', '晋',
             '蒙', '陕', '吉', '闽', '贵', '粤', '川', '青', '藏', '琼', '宁']

# 字母（不包含I和O，避免与数字混淆）
LETTERS = 'ABCDEFGHJKLMNPQRSTUVWXYZ'

# 数字
DIGITS = '0123456789'

# 车牌颜色配置
PLATE_COLORS = {
    'blue': {'bg': (0, 80, 160), 'text': (255, 255, 255), 'name': '蓝色'},
    'yellow': {'bg': (255, 200, 0), 'text': (0, 0, 0), 'name': '黄色'},
    'green': {'bg': (80, 180, 100), 'text': (0, 0, 0), 'name': '绿色'},
    'white': {'bg': (255, 255, 255), 'text': (0, 0, 0), 'name': '白色'},
    'black': {'bg': (30, 30, 30), 'text': (255, 255, 255), 'name': '黑色'},
}


class PlateGenerator:
    """车牌生成器类"""
    
    def __init__(self, output_dir: str = None):
        """
        初始化车牌生成器
        
        Args:
            output_dir: 输出目录
        """
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent.parent / "data" / "output" / "generated"
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 尝试加载中文字体
        self.font = self._load_font()
        self.font_small = self._load_font(size=60)
    
    def _load_font(self, size: int = 80) -> ImageFont.FreeTypeFont:
        """
        加载字体
        
        Args:
            size: 字体大小
            
        Returns:
            字体对象
        """
        # 尝试多个常见的中文字体路径
        font_paths = [
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/System/Library/Fonts/PingFang.ttc',  # macOS
            'C:/Windows/Fonts/msyh.ttc',  # Windows
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    continue
        
        # 如果没有找到合适的字体，使用默认字体
        return ImageFont.load_default()
    
    def generate_plate_number(self, plate_type: str = 'random') -> Tuple[str, str, bool]:
        """
        生成车牌号码
        
        Args:
            plate_type: 车牌类型 ('blue', 'yellow', 'green', 'white', 'black', 'random')
            
        Returns:
            (车牌号码, 颜色, 是否双层)
        """
        if plate_type == 'random':
            plate_type = random.choice(['blue', 'blue', 'blue', 'yellow', 'green'])
        
        province = random.choice(PROVINCES)
        city_letter = random.choice(LETTERS)
        
        if plate_type == 'green':
            # 新能源车牌 8位
            if random.random() > 0.5:
                # 小型新能源 D/F开头
                first = random.choice(['D', 'F'])
                rest = ''.join(random.choices(DIGITS + LETTERS, k=5))
            else:
                # 大型新能源 数字开头
                first = random.choice(DIGITS)
                rest = ''.join(random.choices(DIGITS + LETTERS, k=4))
                rest += random.choice(['D', 'F'])
            plate_number = f"{province}{city_letter}{first}{rest}"
            is_double = False
        else:
            # 普通车牌 7位
            rest = ''.join(random.choices(DIGITS + LETTERS, k=5))
            plate_number = f"{province}{city_letter}{rest}"
            is_double = plate_type == 'yellow' and random.random() > 0.7
        
        return plate_number, plate_type, is_double
    
    def create_plate_image(self, plate_number: str, color: str = 'blue', 
                          is_double: bool = False) -> Image.Image:
        """
        创建车牌图片
        
        Args:
            plate_number: 车牌号码
            color: 颜色
            is_double: 是否双层
            
        Returns:
            PIL Image对象
        """
        color_config = PLATE_COLORS.get(color, PLATE_COLORS['blue'])
        
        if is_double:
            # 双层车牌
            width, height = 440, 220
        else:
            # 单层车牌
            if len(plate_number) == 8:
                width, height = 480, 140
            else:
                width, height = 440, 140
        
        # 创建背景
        img = Image.new('RGB', (width, height), color_config['bg'])
        draw = ImageDraw.Draw(img)
        
        # 添加边框
        border_color = (50, 50, 50) if color in ['yellow', 'white'] else (200, 200, 200)
        draw.rectangle([0, 0, width-1, height-1], outline=border_color, width=3)
        
        # 绘制车牌号码
        text_color = color_config['text']
        
        if is_double:
            # 双层车牌布局
            top_text = plate_number[:2]
            bottom_text = plate_number[2:]
            
            # 上层文字
            self._draw_centered_text(draw, top_text, (width//2, 45), 
                                    self.font_small, text_color)
            # 下层文字
            self._draw_centered_text(draw, bottom_text, (width//2, 155), 
                                    self.font, text_color)
        else:
            # 单层车牌布局
            # 添加分隔点
            display_text = plate_number[:2] + '·' + plate_number[2:]
            self._draw_centered_text(draw, display_text, (width//2, height//2), 
                                    self.font, text_color)
        
        # 添加一些随机噪点增加真实感
        self._add_noise(img, intensity=0.02)
        
        return img
    
    def _draw_centered_text(self, draw: ImageDraw.Draw, text: str, 
                           center: Tuple[int, int], font: ImageFont.FreeTypeFont,
                           color: Tuple[int, int, int]):
        """
        绘制居中文字
        
        Args:
            draw: ImageDraw对象
            text: 文字内容
            center: 中心坐标
            font: 字体
            color: 颜色
        """
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except Exception:
            # 旧版PIL兼容
            text_width, text_height = draw.textsize(text, font=font)
        
        x = center[0] - text_width // 2
        y = center[1] - text_height // 2
        
        draw.text((x, y), text, font=font, fill=color)
    
    def _add_noise(self, img: Image.Image, intensity: float = 0.02):
        """
        添加噪点
        
        Args:
            img: PIL Image对象
            intensity: 噪点强度
        """
        import random as rand
        
        pixels = img.load()
        width, height = img.size
        
        num_noise = int(width * height * intensity)
        
        for _ in range(num_noise):
            x = rand.randint(0, width - 1)
            y = rand.randint(0, height - 1)
            
            r, g, b = pixels[x, y]
            delta = rand.randint(-30, 30)
            
            r = max(0, min(255, r + delta))
            g = max(0, min(255, g + delta))
            b = max(0, min(255, b + delta))
            
            pixels[x, y] = (r, g, b)
    
    def generate_and_save(self, count: int = 20, 
                         plate_type: str = 'random') -> list:
        """
        生成并保存多个车牌
        
        Args:
            count: 生成数量
            plate_type: 车牌类型
            
        Returns:
            生成的文件路径列表
        """
        generated_files = []
        
        for i in range(count):
            plate_number, color, is_double = self.generate_plate_number(plate_type)
            
            # 创建图片
            img = self.create_plate_image(plate_number, color, is_double)
            
            # 生成文件名
            filename = f"{plate_number}_{color}_{str(is_double).lower()}.jpg"
            filepath = self.output_dir / filename
            
            # 保存图片
            img.save(str(filepath), 'JPEG', quality=95)
            
            generated_files.append({
                'filepath': str(filepath),
                'filename': filename,
                'plate_number': plate_number,
                'color': color,
                'is_double': is_double
            })
            
            print(f"✅ [{i+1}/{count}] 生成车牌: {plate_number} ({color})")
        
        print(f"\n📁 所有车牌已保存到: {self.output_dir}")
        return generated_files


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='程序化车牌生成器')
    parser.add_argument('--count', type=int, default=20, help='生成数量')
    parser.add_argument('--type', type=str, default='random', 
                       choices=['blue', 'yellow', 'green', 'white', 'black', 'random'],
                       help='车牌类型')
    parser.add_argument('--output', type=str, default=None, help='输出目录')
    
    args = parser.parse_args()
    
    generator = PlateGenerator(output_dir=args.output)
    generator.generate_and_save(count=args.count, plate_type=args.type)


if __name__ == '__main__':
    main()
