#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集导出模块

支持多种数据集格式导出：
- USD (Universal Scene Description) 文件
- JSON 元数据文件
- DINO 格式数据集
- KITTI 格式数据集

作者: Chinese License Plate Generator
版本: 1.0.0
"""

import json
import os
import shutil
import zipfile
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import uuid

import numpy as np
from PIL import Image


class DatasetFormat(Enum):
    """数据集格式枚举"""
    DINO = "dino"
    KITTI = "kitti"
    COCO = "coco"
    YOLO = "yolo"
    CUSTOM = "custom"


class ExportStatus(Enum):
    """导出状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BoundingBox:
    """边界框数据类"""
    x_min: float  # 左上角 x
    y_min: float  # 左上角 y
    x_max: float  # 右下角 x
    y_max: float  # 右下角 y
    
    @property
    def width(self) -> float:
        return self.x_max - self.x_min
    
    @property
    def height(self) -> float:
        return self.y_max - self.y_min
    
    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2)
    
    def to_yolo_format(self, img_width: int, img_height: int) -> Tuple[float, float, float, float]:
        """转换为 YOLO 格式 (center_x, center_y, width, height) 归一化"""
        cx, cy = self.center
        return (
            cx / img_width,
            cy / img_height,
            self.width / img_width,
            self.height / img_height
        )
    
    def to_coco_format(self) -> List[float]:
        """转换为 COCO 格式 [x, y, width, height]"""
        return [self.x_min, self.y_min, self.width, self.height]


@dataclass
class PlateAnnotation:
    """车牌标注数据类"""
    plate_number: str
    plate_type: str
    is_double: bool
    bbox: BoundingBox
    confidence: float = 1.0
    occlusion_ratio: float = 0.0
    truncation_ratio: float = 0.0
    noise_level: str = "none"
    noise_types: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "plate_number": self.plate_number,
            "plate_type": self.plate_type,
            "is_double": self.is_double,
            "bbox": {
                "x_min": self.bbox.x_min,
                "y_min": self.bbox.y_min,
                "x_max": self.bbox.x_max,
                "y_max": self.bbox.y_max,
                "width": self.bbox.width,
                "height": self.bbox.height
            },
            "confidence": self.confidence,
            "occlusion_ratio": self.occlusion_ratio,
            "truncation_ratio": self.truncation_ratio,
            "noise_level": self.noise_level,
            "noise_types": self.noise_types
        }


@dataclass
class ImageMetadata:
    """图像元数据类"""
    image_id: str
    filename: str
    width: int
    height: int
    channels: int = 3
    format: str = "jpg"
    created_at: str = ""
    annotations: List[PlateAnnotation] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.image_id:
            self.image_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "image_id": self.image_id,
            "filename": self.filename,
            "width": self.width,
            "height": self.height,
            "channels": self.channels,
            "format": self.format,
            "created_at": self.created_at,
            "annotations": [ann.to_dict() for ann in self.annotations]
        }


@dataclass
class DatasetMetadata:
    """数据集元数据类"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    created_at: str = ""
    total_images: int = 0
    total_annotations: int = 0
    categories: Dict[str, int] = field(default_factory=dict)
    splits: Dict[str, int] = field(default_factory=dict)
    license: str = "MIT"
    author: str = "Chinese License Plate Generator"
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class USDGenerator:
    """USD 文件生成器"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_plate_usd(self, 
                          image_path: Path,
                          annotation: PlateAnnotation,
                          output_name: str = None) -> Path:
        """
        生成车牌的 USD 文件
        
        Args:
            image_path: 车牌图像路径
            annotation: 车牌标注
            output_name: 输出文件名（不含扩展名）
            
        Returns:
            生成的 USD 文件路径
        """
        if output_name is None:
            output_name = annotation.plate_number
        
        # 获取图像尺寸
        with Image.open(image_path) as img:
            width, height = img.size
        
        # 计算3D尺寸（假设车牌标准尺寸 440mm x 140mm）
        plate_width_m = 0.44 if not annotation.is_double else 0.44
        plate_height_m = 0.14 if not annotation.is_double else 0.22
        
        # 生成 USD 文件内容
        usd_content = self._generate_usd_content(
            plate_number=annotation.plate_number,
            plate_type=annotation.plate_type,
            texture_path=str(image_path.name),
            width=plate_width_m,
            height=plate_height_m,
            is_double=annotation.is_double
        )
        
        # 写入 USD 文件
        usd_path = self.output_dir / f"{output_name}.usda"
        with open(usd_path, 'w', encoding='utf-8') as f:
            f.write(usd_content)
        
        return usd_path
    
    def _generate_usd_content(self,
                             plate_number: str,
                             plate_type: str,
                             texture_path: str,
                             width: float,
                             height: float,
                             is_double: bool) -> str:
        """生成 USD 文件内容"""
        
        # 顶点坐标（平面矩形）
        half_w = width / 2
        half_h = height / 2
        
        usd_template = f'''#usda 1.0
(
    defaultPrim = "LicensePlate"
    metersPerUnit = 1
    upAxis = "Y"
    doc = "Chinese License Plate Asset - {plate_number}"
)

def Xform "LicensePlate" (
    kind = "component"
    customData = {{
        string plate_number = "{plate_number}"
        string plate_type = "{plate_type}"
        bool is_double_layer = {str(is_double).lower()}
        float width_meters = {width}
        float height_meters = {height}
    }}
)
{{
    def Mesh "PlateGeometry"
    {{
        # 顶点位置
        point3f[] points = [
            ({-half_w}, {-half_h}, 0),
            ({half_w}, {-half_h}, 0),
            ({half_w}, {half_h}, 0),
            ({-half_w}, {half_h}, 0)
        ]
        
        # 面顶点索引
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        
        # 法线
        normal3f[] normals = [(0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1)]
        
        # UV 坐标
        texCoord2f[] primvars:st = [(0, 0), (1, 0), (1, 1), (0, 1)] (
            interpolation = "vertex"
        )
        
        # 材质绑定
        rel material:binding = </LicensePlate/Materials/PlateMaterial>
    }}
    
    def Scope "Materials"
    {{
        def Material "PlateMaterial"
        {{
            token outputs:surface.connect = </LicensePlate/Materials/PlateMaterial/PBRShader.outputs:surface>
            
            def Shader "PBRShader"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor.connect = </LicensePlate/Materials/PlateMaterial/DiffuseTexture.outputs:rgb>
                float inputs:metallic = 0.1
                float inputs:roughness = 0.7
                token outputs:surface
            }}
            
            def Shader "DiffuseTexture"
            {{
                uniform token info:id = "UsdUVTexture"
                asset inputs:file = @{texture_path}@
                float2 inputs:st.connect = </LicensePlate/Materials/PlateMaterial/TexCoordReader.outputs:result>
                token inputs:wrapS = "clamp"
                token inputs:wrapT = "clamp"
                float3 outputs:rgb
            }}
            
            def Shader "TexCoordReader"
            {{
                uniform token info:id = "UsdPrimvarReader_float2"
                string inputs:varname = "st"
                float2 outputs:result
            }}
        }}
    }}
}}
'''
        return usd_template
    
    def generate_dataset_usd(self,
                            images: List[Tuple[Path, PlateAnnotation]],
                            dataset_name: str = "license_plates") -> Path:
        """
        生成数据集的 USD 文件（包含所有车牌的引用）
        
        Args:
            images: (图像路径, 标注) 元组列表
            dataset_name: 数据集名称
            
        Returns:
            生成的 USD 文件路径
        """
        # 生成每个车牌的 USD 文件
        plate_usds = []
        for i, (img_path, annotation) in enumerate(images):
            usd_path = self.generate_plate_usd(
                img_path, annotation, 
                output_name=f"{annotation.plate_number}_{i:04d}"
            )
            plate_usds.append(usd_path.name)
        
        # 生成主 USD 文件
        main_usd_content = self._generate_dataset_usd_content(
            dataset_name, plate_usds
        )
        
        main_usd_path = self.output_dir / f"{dataset_name}.usda"
        with open(main_usd_path, 'w', encoding='utf-8') as f:
            f.write(main_usd_content)
        
        return main_usd_path
    
    def _generate_dataset_usd_content(self,
                                      dataset_name: str,
                                      plate_files: List[str]) -> str:
        """生成数据集 USD 文件内容"""
        
        references = ""
        for i, plate_file in enumerate(plate_files):
            references += f'''
    def Xform "Plate_{i:04d}" (
        references = @./{plate_file}@
    )
    {{
        double3 xformOp:translate = ({(i % 10) * 0.5}, 0, {(i // 10) * 0.3})
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }}
'''
        
        usd_content = f'''#usda 1.0
(
    defaultPrim = "LicensePlateDataset"
    metersPerUnit = 1
    upAxis = "Y"
    doc = "Chinese License Plate Dataset - {dataset_name}"
)

def Xform "LicensePlateDataset" (
    kind = "assembly"
    customData = {{
        string dataset_name = "{dataset_name}"
        int total_plates = {len(plate_files)}
        string created_at = "{datetime.now().isoformat()}"
    }}
)
{{{references}
}}
'''
        return usd_content


class DINOExporter:
    """DINO 格式数据集导出器"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export(self,
               images: List[Tuple[Path, ImageMetadata]],
               dataset_name: str = "license_plates_dino") -> Path:
        """
        导出 DINO 格式数据集
        
        DINO 格式结构:
        dataset/
        ├── images/
        │   ├── train/
        │   └── val/
        ├── annotations/
        │   ├── train.json
        │   └── val.json
        └── metadata.json
        
        Args:
            images: (图像路径, 元数据) 元组列表
            dataset_name: 数据集名称
            
        Returns:
            导出目录路径
        """
        export_dir = self.output_dir / dataset_name
        
        # 创建目录结构
        (export_dir / "images" / "train").mkdir(parents=True, exist_ok=True)
        (export_dir / "images" / "val").mkdir(parents=True, exist_ok=True)
        (export_dir / "annotations").mkdir(parents=True, exist_ok=True)
        
        # 分割数据集 (80% train, 20% val)
        np.random.shuffle(images)
        split_idx = int(len(images) * 0.8)
        train_images = images[:split_idx]
        val_images = images[split_idx:]
        
        # 导出训练集
        train_annotations = self._export_split(
            train_images, export_dir / "images" / "train", "train"
        )
        
        # 导出验证集
        val_annotations = self._export_split(
            val_images, export_dir / "images" / "val", "val"
        )
        
        # 保存标注文件
        with open(export_dir / "annotations" / "train.json", 'w', encoding='utf-8') as f:
            json.dump(train_annotations, f, ensure_ascii=False, indent=2)
        
        with open(export_dir / "annotations" / "val.json", 'w', encoding='utf-8') as f:
            json.dump(val_annotations, f, ensure_ascii=False, indent=2)
        
        # 生成元数据
        metadata = {
            "name": dataset_name,
            "format": "DINO",
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "total_images": len(images),
            "splits": {
                "train": len(train_images),
                "val": len(val_images)
            },
            "categories": self._get_categories(images),
            "description": "Chinese License Plate Dataset in DINO format"
        }
        
        with open(export_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return export_dir
    
    def _export_split(self,
                      images: List[Tuple[Path, ImageMetadata]],
                      output_dir: Path,
                      split_name: str) -> Dict:
        """导出数据集分割"""
        
        annotations = {
            "info": {
                "description": f"Chinese License Plate Dataset - {split_name}",
                "version": "1.0.0",
                "year": datetime.now().year,
                "date_created": datetime.now().isoformat()
            },
            "licenses": [{"id": 1, "name": "MIT", "url": ""}],
            "images": [],
            "annotations": [],
            "categories": [
                {"id": 1, "name": "license_plate", "supercategory": "vehicle"}
            ]
        }
        
        ann_id = 1
        for img_id, (img_path, metadata) in enumerate(images, 1):
            # 复制图像
            new_filename = f"{img_id:06d}.jpg"
            shutil.copy(img_path, output_dir / new_filename)
            
            # 添加图像信息
            annotations["images"].append({
                "id": img_id,
                "file_name": new_filename,
                "width": metadata.width,
                "height": metadata.height,
                "date_captured": metadata.created_at
            })
            
            # 添加标注
            for ann in metadata.annotations:
                annotations["annotations"].append({
                    "id": ann_id,
                    "image_id": img_id,
                    "category_id": 1,
                    "bbox": ann.bbox.to_coco_format(),
                    "area": ann.bbox.width * ann.bbox.height,
                    "iscrowd": 0,
                    "attributes": {
                        "plate_number": ann.plate_number,
                        "plate_type": ann.plate_type,
                        "is_double": ann.is_double,
                        "occlusion": ann.occlusion_ratio,
                        "truncation": ann.truncation_ratio
                    }
                })
                ann_id += 1
        
        return annotations
    
    def _get_categories(self, images: List[Tuple[Path, ImageMetadata]]) -> Dict[str, int]:
        """统计类别分布"""
        categories = {}
        for _, metadata in images:
            for ann in metadata.annotations:
                plate_type = ann.plate_type
                categories[plate_type] = categories.get(plate_type, 0) + 1
        return categories


class KITTIExporter:
    """KITTI 格式数据集导出器"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export(self,
               images: List[Tuple[Path, ImageMetadata]],
               dataset_name: str = "license_plates_kitti") -> Path:
        """
        导出 KITTI 格式数据集
        
        KITTI 格式结构:
        dataset/
        ├── training/
        │   ├── image_2/
        │   └── label_2/
        ├── testing/
        │   └── image_2/
        └── metadata.json
        
        KITTI 标注格式 (每行):
        type truncated occluded alpha bbox(4) dimensions(3) location(3) rotation_y [score]
        
        Args:
            images: (图像路径, 元数据) 元组列表
            dataset_name: 数据集名称
            
        Returns:
            导出目录路径
        """
        export_dir = self.output_dir / dataset_name
        
        # 创建目录结构
        (export_dir / "training" / "image_2").mkdir(parents=True, exist_ok=True)
        (export_dir / "training" / "label_2").mkdir(parents=True, exist_ok=True)
        (export_dir / "testing" / "image_2").mkdir(parents=True, exist_ok=True)
        
        # 分割数据集 (80% train, 20% test)
        np.random.shuffle(images)
        split_idx = int(len(images) * 0.8)
        train_images = images[:split_idx]
        test_images = images[split_idx:]
        
        # 导出训练集
        self._export_split(
            train_images,
            export_dir / "training" / "image_2",
            export_dir / "training" / "label_2"
        )
        
        # 导出测试集（无标注）
        self._export_split(
            test_images,
            export_dir / "testing" / "image_2",
            None
        )
        
        # 生成元数据
        metadata = {
            "name": dataset_name,
            "format": "KITTI",
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "total_images": len(images),
            "splits": {
                "training": len(train_images),
                "testing": len(test_images)
            },
            "categories": self._get_categories(images),
            "description": "Chinese License Plate Dataset in KITTI format",
            "label_format": "type truncated occluded alpha bbox(4) dimensions(3) location(3) rotation_y"
        }
        
        with open(export_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # 生成 ImageSets
        self._generate_imagesets(export_dir, len(train_images), len(test_images))
        
        return export_dir
    
    def _export_split(self,
                      images: List[Tuple[Path, ImageMetadata]],
                      image_dir: Path,
                      label_dir: Optional[Path]) -> None:
        """导出数据集分割"""
        
        for img_id, (img_path, metadata) in enumerate(images):
            # 复制图像
            new_filename = f"{img_id:06d}.png"
            
            # 转换为 PNG 格式（KITTI 标准）
            with Image.open(img_path) as img:
                img.save(image_dir / new_filename)
            
            # 生成标注文件
            if label_dir is not None:
                label_filename = f"{img_id:06d}.txt"
                label_lines = []
                
                for ann in metadata.annotations:
                    # KITTI 格式标注
                    # type truncated occluded alpha bbox dimensions location rotation_y
                    line = self._format_kitti_label(ann, metadata.width, metadata.height)
                    label_lines.append(line)
                
                with open(label_dir / label_filename, 'w') as f:
                    f.write('\n'.join(label_lines))
    
    def _format_kitti_label(self,
                           ann: PlateAnnotation,
                           img_width: int,
                           img_height: int) -> str:
        """格式化 KITTI 标注行"""
        
        # 类型映射
        type_name = "LicensePlate"
        
        # 截断和遮挡
        truncated = ann.truncation_ratio
        occluded = int(ann.occlusion_ratio * 3)  # 0-3
        
        # 观察角度（假设正面）
        alpha = 0.0
        
        # 边界框
        bbox = f"{ann.bbox.x_min:.2f} {ann.bbox.y_min:.2f} {ann.bbox.x_max:.2f} {ann.bbox.y_max:.2f}"
        
        # 3D 尺寸（高度、宽度、长度，单位：米）
        if ann.is_double:
            dimensions = "0.22 0.44 0.01"  # 双层车牌
        else:
            dimensions = "0.14 0.44 0.01"  # 单层车牌
        
        # 3D 位置（相机坐标系，假设距离 5 米）
        location = "0.00 0.00 5.00"
        
        # 旋转角度
        rotation_y = 0.0
        
        return f"{type_name} {truncated:.2f} {occluded} {alpha:.2f} {bbox} {dimensions} {location} {rotation_y:.2f}"
    
    def _get_categories(self, images: List[Tuple[Path, ImageMetadata]]) -> Dict[str, int]:
        """统计类别分布"""
        categories = {}
        for _, metadata in images:
            for ann in metadata.annotations:
                plate_type = ann.plate_type
                categories[plate_type] = categories.get(plate_type, 0) + 1
        return categories
    
    def _generate_imagesets(self, export_dir: Path, train_count: int, test_count: int) -> None:
        """生成 ImageSets 文件"""
        imagesets_dir = export_dir / "ImageSets"
        imagesets_dir.mkdir(exist_ok=True)
        
        # 训练集
        with open(imagesets_dir / "train.txt", 'w') as f:
            f.write('\n'.join([f"{i:06d}" for i in range(train_count)]))
        
        # 测试集
        with open(imagesets_dir / "test.txt", 'w') as f:
            f.write('\n'.join([f"{i:06d}" for i in range(test_count)]))


class DatasetExporter:
    """数据集导出器主类"""
    
    def __init__(self, 
                 input_dir: Path,
                 output_dir: Path):
        """
        初始化导出器
        
        Args:
            input_dir: 输入图像目录
            output_dir: 输出目录
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化各格式导出器
        self.usd_generator = USDGenerator(self.output_dir / "usd")
        self.dino_exporter = DINOExporter(self.output_dir)
        self.kitti_exporter = KITTIExporter(self.output_dir)
    
    def scan_images(self) -> List[Tuple[Path, ImageMetadata]]:
        """
        扫描输入目录中的图像并生成元数据
        
        Returns:
            (图像路径, 元数据) 元组列表
        """
        images = []
        
        for img_path in sorted(self.input_dir.glob("*.jpg")):
            metadata = self._parse_image_metadata(img_path)
            if metadata:
                images.append((img_path, metadata))
        
        for img_path in sorted(self.input_dir.glob("*.png")):
            metadata = self._parse_image_metadata(img_path)
            if metadata:
                images.append((img_path, metadata))
        
        return images
    
    def _parse_image_metadata(self, img_path: Path) -> Optional[ImageMetadata]:
        """解析图像元数据"""
        try:
            with Image.open(img_path) as img:
                width, height = img.size
            
            # 从文件名解析信息
            # 格式: 车牌号_类型_噪声级别_序号.jpg
            filename = img_path.stem
            parts = filename.rsplit('_', 3)
            
            if len(parts) >= 2:
                plate_number = parts[0]
                plate_type = parts[1] if len(parts) > 1 else "unknown"
                noise_level = parts[2] if len(parts) > 2 else "none"
            else:
                plate_number = filename
                plate_type = "unknown"
                noise_level = "none"
            
            # 判断是否双层
            is_double = "double" in plate_type or "220" in plate_type or "挂" in plate_number
            
            # 创建标注
            annotation = PlateAnnotation(
                plate_number=plate_number,
                plate_type=plate_type,
                is_double=is_double,
                bbox=BoundingBox(0, 0, width, height),
                noise_level=noise_level
            )
            
            # 创建元数据
            metadata = ImageMetadata(
                image_id=str(uuid.uuid4()),
                filename=img_path.name,
                width=width,
                height=height,
                annotations=[annotation]
            )
            
            return metadata
            
        except Exception as e:
            print(f"⚠️ 解析图像失败 {img_path}: {e}")
            return None
    
    def export_json(self, images: List[Tuple[Path, ImageMetadata]], 
                   output_name: str = "dataset_info.json") -> Path:
        """
        导出 JSON 元数据文件
        
        Args:
            images: (图像路径, 元数据) 元组列表
            output_name: 输出文件名
            
        Returns:
            JSON 文件路径
        """
        # 统计信息
        categories = {}
        colors = {}
        
        for _, metadata in images:
            for ann in metadata.annotations:
                # 类型统计
                categories[ann.plate_type] = categories.get(ann.plate_type, 0) + 1
                
                # 颜色统计
                color = self._get_color_from_type(ann.plate_type)
                colors[color] = colors.get(color, 0) + 1
        
        # 构建 JSON 数据
        dataset_info = {
            "dataset": {
                "name": "Chinese License Plate Dataset",
                "version": "1.0.0",
                "created_at": datetime.now().isoformat(),
                "description": "Synthetic Chinese license plate images with noise augmentation",
                "license": "MIT",
                "author": "Chinese License Plate Generator"
            },
            "statistics": {
                "total_images": len(images),
                "categories": categories,
                "colors": colors
            },
            "images": [metadata.to_dict() for _, metadata in images],
            "export_formats": ["DINO", "KITTI", "USD"]
        }
        
        output_path = self.output_dir / output_name
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset_info, f, ensure_ascii=False, indent=2)
        
        return output_path
    
    def _get_color_from_type(self, plate_type: str) -> str:
        """从类型获取颜色"""
        if "blue" in plate_type:
            return "blue"
        elif "yellow" in plate_type:
            return "yellow"
        elif "green" in plate_type:
            return "green"
        elif "white" in plate_type:
            return "white"
        elif "black" in plate_type:
            return "black"
        else:
            return "unknown"
    
    def export_usd(self, images: List[Tuple[Path, ImageMetadata]],
                  dataset_name: str = "license_plates") -> Path:
        """
        导出 USD 文件
        
        Args:
            images: (图像路径, 元数据) 元组列表
            dataset_name: 数据集名称
            
        Returns:
            USD 目录路径
        """
        # 复制图像到 USD 目录
        usd_dir = self.output_dir / "usd"
        usd_dir.mkdir(exist_ok=True)
        
        plate_data = []
        for img_path, metadata in images:
            # 复制图像
            shutil.copy(img_path, usd_dir / img_path.name)
            
            # 添加标注
            for ann in metadata.annotations:
                plate_data.append((usd_dir / img_path.name, ann))
        
        # 生成 USD 文件
        self.usd_generator.generate_dataset_usd(plate_data, dataset_name)
        
        return usd_dir
    
    def export_dino(self, images: List[Tuple[Path, ImageMetadata]],
                   dataset_name: str = "license_plates_dino") -> Path:
        """导出 DINO 格式"""
        return self.dino_exporter.export(images, dataset_name)
    
    def export_kitti(self, images: List[Tuple[Path, ImageMetadata]],
                    dataset_name: str = "license_plates_kitti") -> Path:
        """导出 KITTI 格式"""
        return self.kitti_exporter.export(images, dataset_name)
    
    def export_all(self, dataset_name: str = "license_plates") -> Dict[str, Path]:
        """
        导出所有格式
        
        Args:
            dataset_name: 数据集名称
            
        Returns:
            格式名称到路径的映射
        """
        # 扫描图像
        images = self.scan_images()
        
        if not images:
            raise ValueError("未找到任何图像")
        
        print(f"📊 扫描到 {len(images)} 张图像")
        
        results = {}
        
        # 导出 JSON
        print("📝 导出 JSON 元数据...")
        results["json"] = self.export_json(images, f"{dataset_name}_info.json")
        
        # 导出 USD
        print("🎨 导出 USD 文件...")
        results["usd"] = self.export_usd(images, dataset_name)
        
        # 导出 DINO
        print("🦕 导出 DINO 格式...")
        results["dino"] = self.export_dino(images, f"{dataset_name}_dino")
        
        # 导出 KITTI
        print("🚗 导出 KITTI 格式...")
        results["kitti"] = self.export_kitti(images, f"{dataset_name}_kitti")
        
        print("✅ 所有格式导出完成")
        
        return results
    
    def create_download_package(self, 
                               format_type: str,
                               dataset_name: str = "license_plates") -> Path:
        """
        创建可下载的压缩包
        
        Args:
            format_type: 格式类型 ('dino', 'kitti', 'usd', 'all')
            dataset_name: 数据集名称
            
        Returns:
            压缩包路径
        """
        # 扫描图像
        images = self.scan_images()
        
        if format_type == "dino":
            export_dir = self.export_dino(images, f"{dataset_name}_dino")
        elif format_type == "kitti":
            export_dir = self.export_kitti(images, f"{dataset_name}_kitti")
        elif format_type == "usd":
            export_dir = self.export_usd(images, dataset_name)
        elif format_type == "all":
            self.export_all(dataset_name)
            export_dir = self.output_dir
        else:
            raise ValueError(f"未知的格式类型: {format_type}")
        
        # 创建压缩包
        zip_path = self.output_dir / f"{dataset_name}_{format_type}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(export_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(export_dir)
                    zipf.write(file_path, arcname)
        
        return zip_path


# 便捷函数
def export_dataset(input_dir: str,
                   output_dir: str,
                   format_type: str = "all",
                   dataset_name: str = "license_plates") -> Dict[str, Path]:
    """
    便捷导出函数
    
    Args:
        input_dir: 输入图像目录
        output_dir: 输出目录
        format_type: 格式类型 ('dino', 'kitti', 'usd', 'json', 'all')
        dataset_name: 数据集名称
        
    Returns:
        导出结果
    """
    exporter = DatasetExporter(Path(input_dir), Path(output_dir))
    images = exporter.scan_images()
    
    results = {}
    
    if format_type in ["json", "all"]:
        results["json"] = exporter.export_json(images, f"{dataset_name}_info.json")
    
    if format_type in ["usd", "all"]:
        results["usd"] = exporter.export_usd(images, dataset_name)
    
    if format_type in ["dino", "all"]:
        results["dino"] = exporter.export_dino(images, f"{dataset_name}_dino")
    
    if format_type in ["kitti", "all"]:
        results["kitti"] = exporter.export_kitti(images, f"{dataset_name}_kitti")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="数据集导出工具")
    parser.add_argument("--input", "-i", required=True, help="输入图像目录")
    parser.add_argument("--output", "-o", required=True, help="输出目录")
    parser.add_argument("--format", "-f", default="all",
                       choices=["dino", "kitti", "usd", "json", "all"],
                       help="导出格式")
    parser.add_argument("--name", "-n", default="license_plates",
                       help="数据集名称")
    
    args = parser.parse_args()
    
    results = export_dataset(
        args.input,
        args.output,
        args.format,
        args.name
    )
    
    print("\n📦 导出结果:")
    for fmt, path in results.items():
        print(f"  {fmt}: {path}")
