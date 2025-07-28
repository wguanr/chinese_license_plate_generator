

import math
import numpy as np
from pathlib import Path
from PIL import Image

class NoiseTextureGenerator:
    """专门的噪声贴图生成器类"""
    
    def __init__(self):
        pass
    
    def generate_perlin_noise(self, width, height, scale=10.0, octaves=6, persistence=0.5, lacunarity=2.0, seed=None):
        """生成增强版Perlin噪声"""
        if seed is not None:
            np.random.seed(seed)
        
        noise = np.zeros((height, width))
        
        for i in range(height):
            for j in range(width):
                x = j / width * scale
                y = i / height * scale
                
                amplitude = 1.0
                frequency = 1.0
                noise_value = 0.0
                
                for octave in range(octaves):
                    sample_x = x * frequency
                    sample_y = y * frequency
                    
                    # 增强的噪声函数，添加更多随机性
                    noise_val = math.sin(sample_x * 0.1 + sample_y * 0.1) * math.cos(sample_x * 0.2 - sample_y * 0.15)
                    noise_val += math.sin(sample_x * 0.3 + sample_y * 0.25) * 0.5
                    noise_val += math.sin(sample_x * 0.5 - sample_y * 0.4) * 0.25
                    
                    # 添加额外的随机性层
                    noise_val += math.sin(sample_x * 1.2 + sample_y * 0.8) * 0.15
                    noise_val += math.cos(sample_x * 0.7 - sample_y * 1.1) * 0.1
                    
                    noise_value += noise_val * amplitude
                    amplitude *= persistence
                    frequency *= lacunarity
                
                noise[i, j] = noise_value
        
        # 归一化并增强50%强度
        noise = (noise - noise.min()) / (noise.max() - noise.min())
        noise = np.clip(noise * 1.5, 0, 1)  # 增强50%强度
        return noise
    
    def generate_scratches_noise(self, width, height, num_scratches=50, intensity_multiplier=1.0, seed=None):
        """生成增强版刮痕噪声"""
        if seed is not None:
            np.random.seed(seed)
        
        noise = np.zeros((height, width))
        
        # 随机化刮痕数量
        actual_scratches = int(num_scratches * np.random.uniform(0.8, 1.5))
        
        for _ in range(actual_scratches):
            # 随机刮痕参数，增加变化范围
            x1 = np.random.randint(0, width)
            y1 = np.random.randint(0, height)
            length = np.random.randint(15, min(width, height) // 1.5)  # 增加长度范围
            angle = np.random.uniform(0, 2 * math.pi)
            thickness = np.random.randint(1, 4)  # 增加厚度范围
            intensity = np.random.uniform(0.4, 1.2) * intensity_multiplier  # 增强强度
            
            # 计算刮痕终点
            x2 = int(x1 + length * math.cos(angle))
            y2 = int(y1 + length * math.sin(angle))
            
            # 绘制刮痕线
            self._draw_line(noise, x1, y1, x2, y2, thickness, intensity)
        
        # 增强50%强度
        noise = np.clip(noise * 1.5, 0, 1)
        return noise
    
    def generate_dirt_noise(self, width, height, num_spots=200, intensity_multiplier=1.0, seed=None):
        """生成增强版污渍噪声"""
        if seed is not None:
            np.random.seed(seed)
        
        noise = np.zeros((height, width))
        
        # 随机化污渍数量
        actual_spots = int(num_spots * np.random.uniform(0.7, 1.8))
        
        for _ in range(actual_spots):
            # 随机污渍参数，增加变化范围
            x = np.random.randint(0, width)
            y = np.random.randint(0, height)
            radius = np.random.randint(1, 12)  # 增加半径范围
            intensity = np.random.uniform(0.3, 1.0) * intensity_multiplier
            
            # 随机形状变化
            ellipse_ratio = np.random.uniform(0.6, 1.4)
            
            # 绘制椭圆形污渍
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    nx = x + dx
                    ny = y + int(dy * ellipse_ratio)
                    
                    if 0 <= nx < width and 0 <= ny < height:
                        distance = math.sqrt((dx**2) + (dy * ellipse_ratio)**2)
                        if distance <= radius:
                            fade = 1.0 - (distance / radius)
                            # 添加不规则边缘
                            fade *= np.random.uniform(0.8, 1.2)
                            noise[ny, nx] = max(noise[ny, nx], intensity * fade * fade)
        
        # 增强50%强度
        noise = np.clip(noise * 1.5, 0, 1)
        return noise
    
    def generate_corrosion_noise(self, width, height, num_patches=80, seed=None):
        """生成腐蚀噪声"""
        if seed is not None:
            np.random.seed(seed)
        
        noise = np.zeros((height, width))
        
        for _ in range(int(num_patches * np.random.uniform(0.8, 1.3))):
            x = np.random.randint(0, width)
            y = np.random.randint(0, height)
            size = np.random.randint(8, 25)
            intensity = np.random.uniform(0.4, 0.9)
            
            # 不规则腐蚀形状
            for dy in range(-size, size + 1):
                for dx in range(-size, size + 1):
                    nx = x + dx
                    ny = y + dy
                    
                    if 0 <= nx < width and 0 <= ny < height:
                        distance = math.sqrt(dx*dx + dy*dy)
                        if distance <= size:
                            # 腐蚀效果的不规则边缘
                            fade = 1.0 - (distance / size)
                            fade *= np.random.uniform(0.5, 1.0)
                            if np.random.random() > 0.3:  # 随机空洞
                                noise[ny, nx] = max(noise[ny, nx], intensity * fade)
        
        return np.clip(noise * 1.5, 0, 1)
    
    def generate_wear_noise(self, width, height, num_areas=60, seed=None):
        """生成磨损噪声"""
        if seed is not None:
            np.random.seed(seed)
        
        noise = np.zeros((height, width))
        
        for _ in range(int(num_areas * np.random.uniform(0.9, 1.4))):
            x = np.random.randint(0, width)
            y = np.random.randint(0, height)
            width_area = np.random.randint(15, 40)
            height_area = np.random.randint(8, 25)
            intensity = np.random.uniform(0.3, 0.8)
            
            # 椭圆形磨损区域
            for dy in range(-height_area, height_area + 1):
                for dx in range(-width_area, width_area + 1):
                    nx = x + dx
                    ny = y + dy
                    
                    if 0 <= nx < width and 0 <= ny < height:
                        # 椭圆内部检测
                        if (dx/width_area)**2 + (dy/height_area)**2 <= 1:
                            fade = 1.0 - math.sqrt((dx/width_area)**2 + (dy/height_area)**2)
                            fade *= np.random.uniform(0.7, 1.0)
                            noise[ny, nx] = max(noise[ny, nx], intensity * fade)
        
        return np.clip(noise * 1.5, 0, 1)
    
    def _draw_line(self, noise, x1, y1, x2, y2, thickness, intensity):
        """在噪声贴图上绘制线条"""
        height, width = noise.shape
        
        x1 = max(0, min(width - 1, x1))
        x2 = max(0, min(width - 1, x2))
        y1 = max(0, min(height - 1, y1))
        y2 = max(0, min(height - 1, y2))
        
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        steps = max(dx, dy)
        
        if steps == 0:
            return
        
        x_step = (x2 - x1) / steps
        y_step = (y2 - y1) / steps
        
        for i in range(steps + 1):
            x = int(x1 + i * x_step)
            y = int(y1 + i * y_step)
            
            # 绘制粗线，添加随机变化
            actual_thickness = max(1, int(thickness * np.random.uniform(0.8, 1.2)))  # 确保至少为1
            for dy in range(-actual_thickness, actual_thickness + 1):
                for dx in range(-actual_thickness, actual_thickness + 1):
                    nx = x + dx
                    ny = y + dy
                    
                    if 0 <= nx < width and 0 <= ny < height:
                        distance = math.sqrt(dx*dx + dy*dy)
                        if distance <= actual_thickness:
                            fade = 1.0 - (distance / actual_thickness) if actual_thickness > 0 else 1.0
                            fade *= np.random.uniform(0.8, 1.2)  # 添加随机强度变化
                            noise[ny, nx] = max(noise[ny, nx], intensity * fade)
    
    def save_noise_texture(self, noise, filepath):
        """保存噪声贴图到文件"""
        noise_uint8 = (noise * 255).astype(np.uint8)
        image = Image.fromarray(noise_uint8, mode='L')
        image.save(filepath)
        print(f"✓ 保存噪声贴图: {filepath}")
    
    def create_enhanced_noise_textures(self, output_dir, width=512, height=512):
        """创建增强版的20张不同噪声贴图"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查是否已经存在所有噪声贴图
        expected_files = []
        
        # 定义20种不同的噪声贴图
        noise_configs = [
            # 基础噪声类型
            {'name': 'roughness_light', 'type': 'perlin', 'params': {'scale': 6.0, 'octaves': 3}},
            {'name': 'roughness_medium', 'type': 'perlin', 'params': {'scale': 8.0, 'octaves': 4}},
            {'name': 'roughness_heavy', 'type': 'perlin', 'params': {'scale': 12.0, 'octaves': 6}},
            
            # 刮痕类型
            {'name': 'scratches_fine', 'type': 'scratches', 'params': {'num_scratches': 30, 'intensity_multiplier': 0.8}},
            {'name': 'scratches_medium', 'type': 'scratches', 'params': {'num_scratches': 50, 'intensity_multiplier': 1.0}},
            {'name': 'scratches_heavy', 'type': 'scratches', 'params': {'num_scratches': 80, 'intensity_multiplier': 1.3}},
            
            # 污渍类型
            {'name': 'dirt_light', 'type': 'dirt', 'params': {'num_spots': 150, 'intensity_multiplier': 0.7}},
            {'name': 'dirt_medium', 'type': 'dirt', 'params': {'num_spots': 200, 'intensity_multiplier': 1.0}},
            {'name': 'dirt_heavy', 'type': 'dirt', 'params': {'num_spots': 300, 'intensity_multiplier': 1.4}},
            
            # 新增类型
            {'name': 'corrosion_light', 'type': 'corrosion', 'params': {'num_patches': 60}},
            {'name': 'corrosion_heavy', 'type': 'corrosion', 'params': {'num_patches': 100}},
            {'name': 'wear_light', 'type': 'wear', 'params': {'num_areas': 40}},
            {'name': 'wear_heavy', 'type': 'wear', 'params': {'num_areas': 80}},
            
            # 组合类型
            {'name': 'combined_light', 'type': 'combined', 'params': {'weights': [0.4, 0.3, 0.3], 'intensity': 0.8}},
            {'name': 'combined_medium', 'type': 'combined', 'params': {'weights': [0.4, 0.4, 0.2], 'intensity': 1.0}},
            {'name': 'combined_heavy', 'type': 'combined', 'params': {'weights': [0.3, 0.4, 0.3], 'intensity': 1.3}},
            {'name': 'combined_extreme', 'type': 'combined', 'params': {'weights': [0.2, 0.5, 0.3], 'intensity': 1.6}},
            
            # 特殊组合
            {'name': 'weathered', 'type': 'special_combined', 'params': {'types': ['roughness', 'corrosion', 'wear'], 'weights': [0.3, 0.4, 0.3]}},
            {'name': 'damaged', 'type': 'special_combined', 'params': {'types': ['scratches', 'dirt', 'corrosion'], 'weights': [0.5, 0.3, 0.2]}},
            {'name': 'aged', 'type': 'special_combined', 'params': {'types': ['roughness', 'dirt', 'wear'], 'weights': [0.4, 0.3, 0.3]}},
        ]
        
        # 生成文件路径列表
        for config in noise_configs:
            expected_files.append(output_dir / f"{config['name']}.png")
        
        # 检查是否所有文件都存在
        if all(p.exists() for p in expected_files):
            print("✓ 增强版噪声贴图库已存在，跳过生成")
            return {config['name']: f"{config['name']}.png" for config in noise_configs}
        
        print("🎨 生成增强版噪声贴图库 (20种类型)...")
        
        generated_textures = {}
        
        for i, config in enumerate(noise_configs):
            name = config['name']
            noise_type = config['type']
            params = config['params']
            filepath = output_dir / f"{name}.png"
            
            print(f"  [{i+1:02d}/20] 生成 {name}...")
            
            # 使用不同的种子确保每种噪声都不同
            seed = hash(name) % 10000
            
            if noise_type == 'perlin':
                noise = self.generate_perlin_noise(width, height, seed=seed, **params)
            elif noise_type == 'scratches':
                noise = self.generate_scratches_noise(width, height, seed=seed, **params)
            elif noise_type == 'dirt':
                noise = self.generate_dirt_noise(width, height, seed=seed, **params)
            elif noise_type == 'corrosion':
                noise = self.generate_corrosion_noise(width, height, seed=seed, **params)
            elif noise_type == 'wear':
                noise = self.generate_wear_noise(width, height, seed=seed, **params)
            elif noise_type == 'combined':
                # 标准组合：粗糙度 + 刮痕 + 污渍
                roughness = self.generate_perlin_noise(width, height, scale=8.0, octaves=4, seed=seed)
                scratches = self.generate_scratches_noise(width, height, num_scratches=50, seed=seed+1)
                dirt = self.generate_dirt_noise(width, height, num_spots=200, seed=seed+2)
                
                weights = params['weights']
                intensity = params['intensity']
                noise = np.clip((roughness * weights[0] + scratches * weights[1] + dirt * weights[2]) * intensity, 0, 1)
            elif noise_type == 'special_combined':
                # 特殊组合
                types = params['types']
                weights = params['weights']
                noise_layers = []
                
                for j, layer_type in enumerate(types):
                    if layer_type == 'roughness':
                        layer = self.generate_perlin_noise(width, height, scale=8.0, octaves=4, seed=seed+j)
                    elif layer_type == 'scratches':
                        layer = self.generate_scratches_noise(width, height, num_scratches=50, seed=seed+j)
                    elif layer_type == 'dirt':
                        layer = self.generate_dirt_noise(width, height, num_spots=200, seed=seed+j)
                    elif layer_type == 'corrosion':
                        layer = self.generate_corrosion_noise(width, height, num_patches=80, seed=seed+j)
                    elif layer_type == 'wear':
                        layer = self.generate_wear_noise(width, height, num_areas=60, seed=seed+j)
                    
                    noise_layers.append(layer * weights[j])
                
                noise = np.clip(np.sum(noise_layers, axis=0), 0, 1)
            
            self.save_noise_texture(noise, filepath)
            generated_textures[name] = f"{name}.png"
        
        print("✓ 增强版噪声贴图库生成完成 (20种类型)")
        return generated_textures


