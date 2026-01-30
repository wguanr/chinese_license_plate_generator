#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GLTF/GLB 导出模块

将车牌资产导出为 GLTF/GLB 格式，用于 Web 3D 渲染。
支持完整的 PBR 材质。

作者: Chinese License Plate Generator
版本: 1.0.0
"""

import json
import base64
import struct
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from PIL import Image


@dataclass
class GLTFTexture:
    """GLTF 贴图信息"""
    uri: str  # 贴图文件路径或 data URI
    name: str
    
    
@dataclass  
class GLTFMaterial:
    """GLTF PBR 材质"""
    name: str
    basecolor_texture: Optional[GLTFTexture] = None
    normal_texture: Optional[GLTFTexture] = None
    roughness_texture: Optional[GLTFTexture] = None
    metallic_texture: Optional[GLTFTexture] = None
    base_color_factor: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    metallic_factor: float = 0.0
    roughness_factor: float = 0.5


class GLTFExporter:
    """GLTF/GLB 导出器"""
    
    def __init__(self, output_dir: Path):
        """
        初始化导出器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_plate_gltf(
        self,
        plate_number: str,
        plate_type: str,
        is_double: bool,
        pbr_textures: Dict[str, Path],
        output_name: Optional[str] = None,
        embed_textures: bool = True,
        thickness: float = 0.003  # 默认3mm
    ) -> Tuple[Path, Path]:
        """
        导出车牌为 GLTF 和 GLB 格式
        
        Args:
            plate_number: 车牌号
            plate_type: 车牌类型
            is_double: 是否双层
            pbr_textures: PBR 贴图路径字典 {channel: path}
            output_name: 输出文件名（不含扩展名）
            embed_textures: 是否嵌入贴图到 GLB
            
        Returns:
            (GLTF 文件路径, GLB 文件路径)
        """
        if output_name is None:
            output_name = plate_number
        
        # 计算车牌尺寸
        width = 0.44  # 米
        height = 0.22 if is_double else 0.14  # 米
        
        # 创建 GLTF 结构
        gltf = self._create_gltf_structure(
            plate_number=plate_number,
            plate_type=plate_type,
            width=width,
            height=height,
            pbr_textures=pbr_textures,
            embed_textures=embed_textures,
            thickness=thickness
        )
        
        # 保存 GLTF
        gltf_path = self.output_dir / f"{output_name}.gltf"
        with open(gltf_path, 'w', encoding='utf-8') as f:
            json.dump(gltf, f, indent=2, ensure_ascii=False)
        
        # 生成 GLB（二进制格式，嵌入所有资源）
        glb_path = self.output_dir / f"{output_name}.glb"
        self._export_glb(gltf, pbr_textures, glb_path)
        
        return gltf_path, glb_path
    
    def _create_gltf_structure(
        self,
        plate_number: str,
        plate_type: str,
        width: float,
        height: float,
        pbr_textures: Dict[str, Path],
        embed_textures: bool = False,
        thickness: float = 0.003
    ) -> Dict[str, Any]:
        """创建 GLTF JSON 结构"""
        
        # 顶点数据
        half_w = width / 2
        half_h = height / 2
        z_front = thickness / 2
        z_back = -thickness / 2
        
        # 定义立方体的8个顶点 (前4个为正面，后4个为背面)
        # 正面: 0:左下, 1:右下, 2:右上, 3:左上
        # 背面: 4:左下, 5:右下, 6:右上, 7:左上
        
        # 为了处理UV和法线，我们需要为每个面复制顶点
        # 6个面 * 4个顶点 = 24个顶点
        
        # 1. 正面 (Z+)
        p_front = [
            -half_w, -half_h, z_front,  # 0
            half_w, -half_h, z_front,   # 1
            half_w, half_h, z_front,    # 2
            -half_w, half_h, z_front    # 3
        ]
        n_front = [0, 0, 1] * 4
        uv_front = [0, 1, 1, 1, 1, 0, 0, 0]
        
        # 2. 背面 (Z-)
        p_back = [
            half_w, -half_h, z_back,    # 4 (注意顺序以保持法线向外)
            -half_w, -half_h, z_back,   # 5
            -half_w, half_h, z_back,    # 6
            half_w, half_h, z_back      # 7
        ]
        n_back = [0, 0, -1] * 4
        uv_back = [0, 1, 1, 1, 1, 0, 0, 0] # 背面也映射完整UV
        
        # 3. 顶面 (Y+)
        p_top = [
            -half_w, half_h, z_front,   # 3
            half_w, half_h, z_front,    # 2
            half_w, half_h, z_back,     # 6
            -half_w, half_h, z_back     # 7
        ]
        n_top = [0, 1, 0] * 4
        uv_edge = [0, 0, 0, 0, 0, 0, 0, 0] # 边缘使用边缘色
        
        # 4. 底面 (Y-)
        p_bottom = [
            -half_w, -half_h, z_back,   # 5
            half_w, -half_h, z_back,    # 4
            half_w, -half_h, z_front,   # 1
            -half_w, -half_h, z_front   # 0
        ]
        n_bottom = [0, -1, 0] * 4
        
        # 5. 右面 (X+)
        p_right = [
            half_w, -half_h, z_front,   # 1
            half_w, -half_h, z_back,    # 4
            half_w, half_h, z_back,     # 7
            half_w, half_h, z_front     # 2
        ]
        n_right = [1, 0, 0] * 4
        
        # 6. 左面 (X-)
        p_left = [
            -half_w, -half_h, z_back,   # 5
            -half_w, -half_h, z_front,  # 0
            -half_w, half_h, z_front,   # 3
            -half_w, half_h, z_back     # 6
        ]
        n_left = [-1, 0, 0] * 4
        
        # 合并所有数据
        positions = p_front + p_back + p_top + p_bottom + p_right + p_left
        normals = n_front + n_back + n_top + n_bottom + n_right + n_left
        texcoords = uv_front + uv_back + uv_edge + uv_edge + uv_edge + uv_edge
        
        # 生成索引 (每个面2个三角形)
        indices = []
        for i in range(6):
            base = i * 4
            # 0, 1, 2 和 0, 2, 3
            indices.extend([base, base+1, base+2, base, base+2, base+3])
        
        # 将数据转换为二进制
        positions_bytes = struct.pack(f'{len(positions)}f', *positions)
        normals_bytes = struct.pack(f'{len(normals)}f', *normals)
        texcoords_bytes = struct.pack(f'{len(texcoords)}f', *texcoords)
        indices_bytes = struct.pack(f'{len(indices)}H', *indices)
        
        # 合并为单个 buffer
        buffer_data = indices_bytes + positions_bytes + normals_bytes + texcoords_bytes
        buffer_base64 = base64.b64encode(buffer_data).decode('ascii')
        
        # 计算偏移量
        indices_offset = 0
        indices_length = len(indices_bytes)
        positions_offset = indices_length
        positions_length = len(positions_bytes)
        normals_offset = positions_offset + positions_length
        normals_length = len(normals_bytes)
        texcoords_offset = normals_offset + normals_length
        texcoords_length = len(texcoords_bytes)
        
        # 构建 GLTF
        gltf = {
            "asset": {
                "version": "2.0",
                "generator": "Chinese License Plate Generator v2.0",
                "extras": {
                    "plate_number": plate_number,
                    "plate_type": plate_type,
                    "created_at": datetime.now().isoformat()
                }
            },
            "scene": 0,
            "scenes": [
                {
                    "name": "LicensePlate",
                    "nodes": [0]
                }
            ],
            "nodes": [
                {
                    "name": plate_number,
                    "mesh": 0
                }
            ],
            "meshes": [
                {
                    "name": "PlateGeometry",
                    "primitives": [
                        {
                            "attributes": {
                                "POSITION": 1,
                                "NORMAL": 2,
                                "TEXCOORD_0": 3
                            },
                            "indices": 0,
                            "material": 0
                        }
                    ]
                }
            ],
            "accessors": [
                # 索引
                {
                    "bufferView": 0,
                    "componentType": 5123,  # UNSIGNED_SHORT
                    "count": len(indices),
                    "type": "SCALAR"
                },
                # 位置
                {
                    "bufferView": 1,
                    "componentType": 5126,  # FLOAT
                    "count": len(positions) // 3,
                    "type": "VEC3",
                    "min": [-half_w, -half_h, z_back],
                    "max": [half_w, half_h, z_front]
                },
                # 法线
                {
                    "bufferView": 2,
                    "componentType": 5126,
                    "count": len(normals) // 3,
                    "type": "VEC3"
                },
                # UV
                {
                    "bufferView": 3,
                    "componentType": 5126,
                    "count": len(texcoords) // 2,
                    "type": "VEC2"
                }
            ],
            "bufferViews": [
                # 索引
                {
                    "buffer": 0,
                    "byteOffset": indices_offset,
                    "byteLength": indices_length,
                    "target": 34963  # ELEMENT_ARRAY_BUFFER
                },
                # 位置
                {
                    "buffer": 0,
                    "byteOffset": positions_offset,
                    "byteLength": positions_length,
                    "target": 34962  # ARRAY_BUFFER
                },
                # 法线
                {
                    "buffer": 0,
                    "byteOffset": normals_offset,
                    "byteLength": normals_length,
                    "target": 34962
                },
                # UV
                {
                    "buffer": 0,
                    "byteOffset": texcoords_offset,
                    "byteLength": texcoords_length,
                    "target": 34962
                }
            ],
            "buffers": [
                {
                    "uri": f"data:application/octet-stream;base64,{buffer_base64}",
                    "byteLength": len(buffer_data)
                }
            ],
            "materials": [],
            "textures": [],
            "images": [],
            "samplers": [
                {
                    "magFilter": 9729,  # LINEAR
                    "minFilter": 9987,  # LINEAR_MIPMAP_LINEAR
                    "wrapS": 10497,     # REPEAT
                    "wrapT": 10497
                }
            ]
        }
        
        # 添加材质和贴图
        self._add_pbr_material(gltf, pbr_textures, embed_textures)
        
        return gltf
    
    def _add_pbr_material(
        self,
        gltf: Dict[str, Any],
        pbr_textures: Dict[str, Path],
        embed_textures: bool
    ):
        """添加 PBR 材质到 GLTF"""
        
        material = {
            "name": "PlateMaterial",
            "pbrMetallicRoughness": {
                "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                "metallicFactor": 0.0,
                "roughnessFactor": 0.5
            },
            "doubleSided": False
        }
        
        texture_index = 0
        
        # BaseColor 贴图
        if "basecolor" in pbr_textures and pbr_textures["basecolor"].exists():
            image_index = self._add_image(gltf, pbr_textures["basecolor"], embed_textures)
            gltf["textures"].append({
                "sampler": 0,
                "source": image_index,
                "name": "basecolor"
            })
            material["pbrMetallicRoughness"]["baseColorTexture"] = {
                "index": texture_index
            }
            texture_index += 1
        
        # Normal 贴图
        if "normal" in pbr_textures and pbr_textures["normal"].exists():
            image_index = self._add_image(gltf, pbr_textures["normal"], embed_textures)
            gltf["textures"].append({
                "sampler": 0,
                "source": image_index,
                "name": "normal"
            })
            material["normalTexture"] = {
                "index": texture_index,
                "scale": 1.0
            }
            texture_index += 1
        
        # Metallic-Roughness 贴图 (GLTF 使用合并的 metallic-roughness 贴图)
        # 需要将 roughness 和 metallic 合并为一张贴图
        # G 通道 = roughness, B 通道 = metallic
        if "roughness" in pbr_textures and pbr_textures["roughness"].exists():
            metallic_path = pbr_textures.get("metallic")
            roughness_path = pbr_textures["roughness"]
            
            # 合并贴图
            mr_image = self._create_metallic_roughness_texture(
                roughness_path,
                metallic_path if metallic_path and metallic_path.exists() else None
            )
            
            if mr_image:
                # 保存临时文件或嵌入
                if embed_textures:
                    import io
                    buffer = io.BytesIO()
                    mr_image.save(buffer, format='PNG')
                    buffer.seek(0)
                    data_uri = f"data:image/png;base64,{base64.b64encode(buffer.read()).decode('ascii')}"
                    gltf["images"].append({
                        "uri": data_uri,
                        "name": "metallicRoughness"
                    })
                else:
                    mr_path = self.output_dir / "temp_metallic_roughness.png"
                    mr_image.save(str(mr_path))
                    gltf["images"].append({
                        "uri": mr_path.name,
                        "name": "metallicRoughness"
                    })
                
                image_index = len(gltf["images"]) - 1
                gltf["textures"].append({
                    "sampler": 0,
                    "source": image_index,
                    "name": "metallicRoughness"
                })
                material["pbrMetallicRoughness"]["metallicRoughnessTexture"] = {
                    "index": texture_index
                }
                texture_index += 1
        
        gltf["materials"].append(material)
    
    def _add_image(
        self,
        gltf: Dict[str, Any],
        image_path: Path,
        embed: bool
    ) -> int:
        """添加图像到 GLTF"""
        
        if embed:
            # 嵌入为 data URI
            with open(image_path, 'rb') as f:
                data = f.read()
            
            # 确定 MIME 类型
            suffix = image_path.suffix.lower()
            mime_type = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg'
            }.get(suffix, 'image/png')
            
            data_uri = f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"
            gltf["images"].append({
                "uri": data_uri,
                "name": image_path.stem
            })
        else:
            # 使用相对路径
            gltf["images"].append({
                "uri": image_path.name,
                "name": image_path.stem
            })
        
        return len(gltf["images"]) - 1
    
    def _create_metallic_roughness_texture(
        self,
        roughness_path: Path,
        metallic_path: Optional[Path]
    ) -> Optional[Image.Image]:
        """
        创建 GLTF 标准的 metallic-roughness 贴图
        
        GLTF 规范：
        - R 通道：未使用（设为 1.0）
        - G 通道：Roughness
        - B 通道：Metallic
        """
        try:
            # 加载 roughness
            roughness_img = Image.open(roughness_path).convert('L')
            width, height = roughness_img.size
            
            # 加载或创建 metallic
            if metallic_path and metallic_path.exists():
                metallic_img = Image.open(metallic_path).convert('L')
                metallic_img = metallic_img.resize((width, height))
            else:
                # 默认 metallic = 0
                metallic_img = Image.new('L', (width, height), 0)
            
            # 创建合并贴图
            r_channel = Image.new('L', (width, height), 255)  # 未使用
            g_channel = roughness_img  # Roughness
            b_channel = metallic_img   # Metallic
            
            mr_image = Image.merge('RGB', (r_channel, g_channel, b_channel))
            return mr_image
            
        except Exception as e:
            print(f"⚠️ 创建 metallic-roughness 贴图失败: {e}")
            return None
    
    def _export_glb(
        self,
        gltf: Dict[str, Any],
        pbr_textures: Dict[str, Path],
        output_path: Path
    ):
        """
        导出为 GLB 格式（二进制 GLTF）
        
        GLB 文件结构：
        - 12 字节头部
        - JSON chunk
        - BIN chunk（可选）
        """
        # 创建一个新的 GLTF，所有资源都嵌入
        glb_gltf = self._create_gltf_structure(
            plate_number=gltf["asset"]["extras"]["plate_number"],
            plate_type=gltf["asset"]["extras"]["plate_type"],
            width=0.44,
            height=0.14,  # 简化处理
            pbr_textures=pbr_textures,
            embed_textures=True
        )
        
        # 将 GLTF JSON 转换为字节
        json_str = json.dumps(glb_gltf, separators=(',', ':'))
        json_bytes = json_str.encode('utf-8')
        
        # 对齐到 4 字节
        json_padding = (4 - len(json_bytes) % 4) % 4
        json_bytes += b' ' * json_padding
        
        # GLB 头部
        magic = b'glTF'
        version = struct.pack('<I', 2)
        
        # JSON chunk
        json_chunk_length = struct.pack('<I', len(json_bytes))
        json_chunk_type = struct.pack('<I', 0x4E4F534A)  # JSON
        
        # 总长度
        total_length = 12 + 8 + len(json_bytes)
        length = struct.pack('<I', total_length)
        
        # 写入 GLB 文件
        with open(output_path, 'wb') as f:
            f.write(magic)
            f.write(version)
            f.write(length)
            f.write(json_chunk_length)
            f.write(json_chunk_type)
            f.write(json_bytes)


def export_plates_to_gltf(
    input_dir: Path,
    output_dir: Path,
    manifest_path: Optional[Path] = None
) -> List[Tuple[Path, Path]]:
    """
    批量导出车牌为 GLTF/GLB 格式
    
    Args:
        input_dir: 输入目录（包含 PBR 贴图）
        output_dir: 输出目录
        manifest_path: 资产清单文件路径
        
    Returns:
        [(gltf_path, glb_path), ...]
    """
    exporter = GLTFExporter(output_dir)
    results = []
    
    # 如果有清单文件，使用清单
    if manifest_path and manifest_path.exists():
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        for asset in manifest.get("assets", []):
            plate_number = asset["plate_number"]
            plate_type = asset["plate_type"]
            is_double = asset["is_double"]
            
            # 构建贴图路径
            textures = asset.get("textures", {})
            pbr_textures = {}
            for channel, rel_path in textures.items():
                full_path = input_dir.parent / rel_path
                if full_path.exists():
                    pbr_textures[channel] = full_path
            
            # 导出
            output_name = f"{plate_number}_{asset['index']:04d}"
            try:
                gltf_path, glb_path = exporter.export_plate_gltf(
                    plate_number=plate_number,
                    plate_type=plate_type,
                    is_double=is_double,
                    pbr_textures=pbr_textures,
                    output_name=output_name
                )
                results.append((gltf_path, glb_path))
                print(f"✅ 导出: {output_name}")
            except Exception as e:
                print(f"⚠️ 导出失败 {output_name}: {e}")
    
    return results


# ============ 测试代码 ============

if __name__ == "__main__":
    from pathlib import Path
    
    # 测试导出
    project_root = Path(__file__).parent.parent
    input_dir = project_root / "data" / "output" / "pbr" / "usd"
    output_dir = project_root / "data" / "output" / "pbr" / "gltf"
    manifest_path = input_dir / "license_plates_pbr_manifest.json"
    
    if manifest_path.exists():
        results = export_plates_to_gltf(input_dir, output_dir, manifest_path)
        print(f"\n✅ 导出完成: {len(results)} 个文件")
    else:
        print(f"⚠️ 清单文件不存在: {manifest_path}")
