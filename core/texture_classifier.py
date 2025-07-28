#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贴图分类器

根据命名约定对贴图进行自动分类，并生成相应的变体组。
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict

from .config import DEFAULT_CONFIG


@dataclass
class TextureInfo:
    """贴图信息数据类"""
    file_path: Path
    filename: str
    category: str
    variant_group: str
    confidence: float  # 分类置信度 (0.0 - 1.0)
    metadata: Dict[str, Any]  # 额外元数据


@dataclass
class ClassificationResult:
    """分类结果数据类"""
    texture_groups: Dict[str, List[TextureInfo]]  # 按变体组分组的贴图
    category_stats: Dict[str, int]  # 各分类的统计信息
    unclassified: List[TextureInfo]  # 未分类的贴图
    total_processed: int


class TextureClassifier:
    """
    贴图分类器
    
    根据文件名命名约定自动对贴图进行分类，生成不同的变体组。
    """
    
    def __init__(self, config: "ConfigSchema"):
        """
        初始化贴图分类器
        
        Args:
            config: 分类配置，默认使用DEFAULT_CONFIG
        """
        self.config = config.texture_classification
        self.paths_config = DEFAULT_CONFIG.paths
        
        # 编译正则表达式模式以提高性能
        self._compile_patterns()
        
        print("✅ 贴图分类器初始化完成")
        if self.config.enable_auto_classification:
            print(f"📋 启用自动分类，支持 {len(self.config.variant_groups)} 个变体组")
        else:
            print("⚠️  自动分类已禁用，将使用默认分类")
    
    def _compile_patterns(self):
        """编译正则表达式模式"""
        self.compiled_patterns = {}
        
        if not hasattr(self.config, 'naming_patterns'):
            raise ValueError("配置中缺少 'naming_patterns'")

        for category, patterns in self.config.naming_patterns.items():
            try:
                # 将字符串模式列表编译成一个正则表达式
                regex = re.compile("|".join(f"({p})" for p in patterns), re.IGNORECASE)
                self.compiled_patterns[category] = regex
            except re.error as e:
                raise ValueError(f"为分类 '{category}' 编译正则表达式失败: {e}")
    
    def classify_texture(self, file_path: Path) -> TextureInfo:
        """
        对单个贴图文件进行分类
        
        Args:
            file_path: 贴图文件路径
            
        Returns:
            贴图信息对象
        """
        filename = file_path.name
        stem = file_path.stem.lower()
        
        # 初始化分类结果
        category = self.config.fallback_category
        confidence = 0.0
        variant_group = self.config.fallback_category
        
        if self.config.enable_auto_classification:
            # 首先尝试基于文件名格式的分类
            parsed_info = self._parse_filename_for_classification(stem)
            if parsed_info:
                category = parsed_info['category']
                confidence = parsed_info['confidence']
                variant_group = self._find_variant_group(category)
            else:
                # 回退到模式匹配
                for priority_category in self.config.category_priority:
                    if priority_category in self.compiled_patterns:
                        match = self.compiled_patterns[priority_category].search(stem)
                        if match:
                            # 计算置信度（基于匹配的模式数量和位置）
                            matched_patterns = len([p for p in self.config.naming_patterns[priority_category] 
                                                  if p.lower() in stem])
                            total_patterns = len(self.config.naming_patterns[priority_category])
                            confidence = matched_patterns / total_patterns
                            
                            # 找到对应的变体组
                            variant_group = self._find_variant_group(priority_category)
                            category = priority_category
                            break
        
        # 提取额外元数据
        metadata = self._extract_metadata(file_path)
        
        return TextureInfo(
            file_path=file_path,
            filename=filename,
            category=category,
            variant_group=variant_group,
            confidence=confidence,
            metadata=metadata
        )
    
    def _parse_filename_for_classification(self, stem: str) -> Optional[Dict[str, Any]]:
        """
        基于文件名格式进行分类
        
        Args:
            stem: 文件名（不含扩展名）
            
        Returns:
            分类信息字典或None
        """
        name_parts = stem.split('_')
        
        if len(name_parts) < 2:
            return None
        
        # 提取颜色信息（第二部分）
        color = name_parts[1]
        
        # 判断是否有special use字段
        # 检查是否是4字段格式：name_color_special_use_is_double
        has_special_use = (len(name_parts) >= 4 and 
                          name_parts[-1].lower() in ["true", "false"] and 
                          name_parts[-2].lower() not in ["true", "false"])
        
        if has_special_use:
            # 4字段格式: name_color_special_use_is_double
            special_use = name_parts[2]
            is_special = name_parts[3].lower() == "true"
        else:
            # 3字段格式: name_color_is_double
            special_use = "unknown"
            is_special = name_parts[2].lower() == "true" if len(name_parts) > 2 else False
        
        # 构建分类信息
        if special_use != "unknown":
            category = f"{color}_{special_use}"
        else:
            category = color
            
        if is_special:
            category += "_special"
        
        # 计算置信度
        confidence = 1.0 if color in ['blue', 'green', 'yellow', 'white', 'black', 'red'] else 0.5
        
        return {
            'category': category,
            'confidence': confidence,
            'color': color,
            'special_use': special_use,
            'is_special': is_special
        }
    
    def _find_variant_group(self, category: str) -> str:
        """
        根据颜色分类找到对应的变体组
        
        Args:
            category: 颜色分类名称
            
        Returns:
            变体组名称
        """
        # 映射颜色到变体组
        color_to_group = {
            'blue': 'civilian',
            'green': 'new_energy', 
            'yellow': 'commercial',
            'white': 'official',
            'black': 'special',
            'red': 'special'
        }
        
        # 处理复合分类名称（如 green_car, white_army 等）
        if '_' in category:
            base_color = category.split('_')[0]
            return color_to_group.get(base_color, self.config.fallback_category)
        
        return color_to_group.get(category, self.config.fallback_category)
    
    def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        提取贴图文件的元数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            元数据字典
        """
        metadata = {
            'file_size': file_path.stat().st_size if file_path.exists() else 0,
            'file_extension': file_path.suffix.lower(),
            'parent_directory': file_path.parent.name,
            'stem': file_path.stem
        }
        
        # 尝试提取图片尺寸信息
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                metadata['width'] = img.width
                metadata['height'] = img.height
                metadata['aspect_ratio'] = img.width / img.height
                metadata['format'] = img.format
        except Exception:
            # 如果无法读取图片信息，使用默认值
            metadata.update({
                'width': 0,
                'height': 0, 
                'aspect_ratio': 1.0,
                'format': 'unknown'
            })
        
        return metadata
    
    def classify_directory(self, directory_path: str = None) -> ClassificationResult:
        """
        对整个目录进行批量分类
        
        Args:
            directory_path: 目录路径，默认使用配置中的输入目录
            
        Returns:
            分类结果
        """
        if directory_path is None:
            directory_path = self.paths_config.input_dir_path
        
        directory = Path(directory_path)
        if not directory.exists():
            raise FileNotFoundError(f"输入目录不存在: {directory}")
        
        print(f"📁 开始分类目录: {directory}")
        
        # 收集所有支持的图片文件
        texture_files = []
        for ext in self.paths_config.supported_image_formats:
            texture_files.extend(directory.rglob(f"*.{ext}"))
            texture_files.extend(directory.rglob(f"*.{ext.upper()}"))
        
        print(f"📋 找到 {len(texture_files)} 个贴图文件")
        
        # 批量分类
        texture_groups = defaultdict(list)
        category_stats = defaultdict(int)
        unclassified = []
        
        for file_path in texture_files:
            try:
                texture_info = self.classify_texture(file_path)
                
                # 根据置信度决定是否分类
                if texture_info.confidence > 0.0:
                    texture_groups[texture_info.variant_group].append(texture_info)
                    category_stats[texture_info.category] += 1
                else:
                    unclassified.append(texture_info)
                    
            except Exception as e:
                print(f"⚠️  分类文件失败 {file_path}: {e}")
                continue
        
        result = ClassificationResult(
            texture_groups=dict(texture_groups),
            category_stats=dict(category_stats),
            unclassified=unclassified,
            total_processed=len(texture_files)
        )
        
        self._print_classification_summary(result)
        return result
    
    def _print_classification_summary(self, result: ClassificationResult):
        """打印分类摘要"""
        print("=" * 60)
        print("🎯 分类结果摘要:")
        print("=" * 60)
        
        print(f"📊 总处理文件: {result.total_processed}")
        print(f"✅ 成功分类: {sum(result.category_stats.values())}")
        print(f"❓ 未分类: {len(result.unclassified)}")
        print("")
        
        if result.category_stats:
            print("📈 分类统计:")
            for category, count in sorted(result.category_stats.items()):
                print(f"   {category}: {count} 个文件")
        print("")
        
        if result.texture_groups:
            print("🎨 变体组统计:")
            for group, textures in result.texture_groups.items():
                group_config = self.config.variant_groups.get(group, {})
                description = group_config.get('description', '未知')
                print(f"   {group} ({description}): {len(textures)} 个贴图")
                
                # 显示平均置信度
                avg_confidence = sum(t.confidence for t in textures) / len(textures)
                print(f"      置信度: {avg_confidence:.2f}")
        print("")
    
    def get_variant_generation_params(self, variant_group: str) -> Dict[str, Any]:
        """
        获取特定变体组的生成参数
        
        Args:
            variant_group: 变体组名称
            
        Returns:
            变体生成参数
        """
        if variant_group not in self.config.variant_groups:
            print(f"⚠️  未知变体组: {variant_group}，使用默认参数")
            variant_group = self.config.fallback_category
        
        group_config = self.config.variant_groups[variant_group]
        
        return {
            'variant_group': variant_group,
            'color_scheme': group_config.get('color_scheme', 'blue'),
            'roughness_range': group_config.get('roughness_range', (0.1, 0.5)),
            'metallic_range': group_config.get('metallic_range', (0.5, 0.9)),
            'description': group_config.get('description', ''),
            'textures': []  # 将由调用者填充
        }
    
    def generate_variant_configs(self, classification_result: ClassificationResult) -> Dict[str, Dict[str, Any]]:
        """
        基于分类结果生成变体配置
        
        Args:
            classification_result: 分类结果
            
        Returns:
            变体配置字典
        """
        variant_configs = {}
        
        for group_name, textures in classification_result.texture_groups.items():
            # 获取基础参数
            params = self.get_variant_generation_params(group_name)
            
            # 添加贴图列表
            params['textures'] = [
                {
                    'path': str(texture.file_path),
                    'filename': texture.filename,
                    'category': texture.category,
                    'confidence': texture.confidence,
                    'metadata': texture.metadata
                }
                for texture in textures
            ]
            
            variant_configs[group_name] = params
        
        print(f"🎨 生成了 {len(variant_configs)} 个变体组配置")
        return variant_configs


def create_texture_classifier(config=None) -> TextureClassifier:
    """
    创建贴图分类器实例
    
    Args:
        config: 可选的配置对象
        
    Returns:
        贴图分类器实例
    """
    return TextureClassifier(config)


def main():
    """测试函数"""
    classifier = create_texture_classifier()
    
    # 测试目录分类
    try:
        result = classifier.classify_directory(
            DEFAULT_CONFIG.paths.input_dir_path)
        
        # 生成变体配置
        variant_configs = classifier.generate_variant_configs(result)
        
        # 打印详细结果
        print("🔧 生成的变体配置:")
        for group_name, config in variant_configs.items():
            print(f"   {group_name}: {len(config['textures'])} 个贴图")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    main() 