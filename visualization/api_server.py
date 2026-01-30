#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车牌生成器 API 服务器 - Flask (无头模式)
专为 React 前端提供 RESTful API 服务
"""

import os
import sys
import json
import uuid
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from queue import Queue

from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 导入核心模块
from core.noise_module import (
    CompositeNoiseApplicator, CompositeNoiseConfig, NoiseConfig,
    NoiseType, NoiseIntensity,
    StainConfig, ShadowConfig, PaintPeelingConfig, OcclusionConfig
)

# 导入GLTF导出器
try:
    from core.gltf_exporter import GLTFExporter
    GLTF_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ GLTF导出器导入失败: {e}")
    GLTF_AVAILABLE = False

# 尝试导入车牌生成器
try:
    sys.path.insert(0, str(PROJECT_ROOT / "assets"))
    from generate_multi_plate import MultiPlateGenerator
    GENERATOR_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 车牌生成器导入失败: {e}")
    GENERATOR_AVAILABLE = False

# ============ 数据类定义 ============

@dataclass
class PlateConfig:
    """车牌生成配置"""
    plate_type: str = "blue"
    count: int = 1
    noise_preset: str = "medium"
    custom_noise: Dict = field(default_factory=dict)
    province: str = ""
    custom_number: str = ""
    double_row: bool = False
    thickness: int = 3  # mm

@dataclass
class GenerationTask:
    """生成任务"""
    task_id: str
    config: PlateConfig
    status: str = "pending"
    progress: int = 0
    total: int = 0
    created_at: str = ""
    completed_at: str = ""
    results: List[str] = field(default_factory=list)
    error: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self):
        data = asdict(self)
        # 转换config对象为字典
        if hasattr(self.config, '__dict__'):
            data['config'] = asdict(self.config)
        return data

# ============ 任务管理器 ============

class TaskManager:
    """任务管理器"""
    
    def __init__(self, generator, noise_generator, gltf_exporter, output_dir: Path):
        self.generator = generator
        self.noise_generator = noise_generator
        self.gltf_exporter = gltf_exporter
        self.output_dir = output_dir
        self.tasks: Dict[str, GenerationTask] = {}
        self.task_queue = Queue()
        self.is_running = False
        self._worker_thread = None
    
    def start(self):
        if not self.is_running:
            self.is_running = True
            self._worker_thread = threading.Thread(target=self._process_tasks, daemon=True)
            self._worker_thread.start()
    
    def stop(self):
        self.is_running = False
    
    def create_task(self, config: PlateConfig) -> GenerationTask:
        # 清理已完成的旧任务，防止内存泄漏（保留最近100个）
        if len(self.tasks) > 100:
            completed_tasks = [tid for tid, t in self.tasks.items() if t.status in ["completed", "failed"]]
            for tid in completed_tasks[:-20]: # 保留最近20个完成的任务
                del self.tasks[tid]

        task = GenerationTask(
            task_id=str(uuid.uuid4())[:8],
            config=config,
            total=config.count
        )
        self.tasks[task.task_id] = task
        self.task_queue.put(task.task_id)
        return task
    
    def get_task(self, task_id: str) -> Optional[GenerationTask]:
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[GenerationTask]:
        return list(self.tasks.values())
    
    def _process_tasks(self):
        print("[API] Worker线程已启动")
        while self.is_running:
            try:
                if not self.task_queue.empty():
                    task_id = self.task_queue.get(timeout=1)
                    self._execute_task(task_id)
                else:
                    time.sleep(0.5)
            except Exception as e:
                print(f"[API] 任务处理错误: {e}")
    
    def _execute_task(self, task_id: str):
        task = self.tasks.get(task_id)
        if not task:
            return
        
        task.status = "running"
        task.progress = 0
        
        try:
            results = []
            config = task.config
            
            # 确定输出目录
            task_output_dir = self.output_dir / "generated" / task_id
            task_output_dir.mkdir(parents=True, exist_ok=True)
            
            for i in range(config.count):
                # 模拟生成延迟
                time.sleep(0.1) 
                
                try:
                    # 实际生成逻辑会在这里调用 self.generator
                    if self.generator:
                        import cv2
                        
                        # 生成车牌
                        # 注意：generate_plate返回 (img, mask, xy, number, color, is_double)
                        plate_img, _, plate_xy, plate_number, plate_color, plate_is_double = self.generator.generate_plate()
                        
                        filename = f"{plate_number}_{i:04d}.jpg"
                        filepath = task_output_dir / filename
                        
                        # 保存图片
                        cv2.imwrite(str(filepath), plate_img)
                        
                        # 保存训练用JSON元数据
                        json_filename = f"{plate_number}_{i:04d}.json"
                        json_filepath = task_output_dir / json_filename
                        
                        # 构建字符位置信息
                        char_bboxes = []
                        if plate_xy is not None:
                            # xy 是 numpy array: [[x1, y1, x2, y2], ...]
                            for bbox in plate_xy:
                                char_bboxes.append({
                                    "x1": int(bbox[0]),
                                    "y1": int(bbox[1]),
                                    "x2": int(bbox[2]),
                                    "y2": int(bbox[3])
                                })
                                
                        metadata = {
                            "plate_number": plate_number,
                            "plate_color": plate_color,
                            "is_double": bool(plate_is_double),
                            "image_width": plate_img.shape[1],
                            "image_height": plate_img.shape[0],
                            "char_bboxes": char_bboxes,
                            "chars": list(plate_number),
                            "generated_at": datetime.now().isoformat(),
                            "task_id": task_id,
                            "config": task.config.to_dict() if hasattr(task.config, 'to_dict') else asdict(task.config)
                        }
                        
                        with open(json_filepath, 'w', encoding='utf-8') as f:
                            json.dump(metadata, f, ensure_ascii=False, indent=2)
                        
                        # 生成GLTF模型
                        model_path = None
                        if self.gltf_exporter:
                            try:
                                # 准备贴图字典 (这里简化处理，直接使用生成的图片作为basecolor)
                                # 在真实场景中，应该有法线贴图、粗糙度贴图等
                                pbr_textures = {
                                    "basecolor": filepath
                                }
                                
                                model_filename = f"{plate_number}_{i:04d}"
                                # 获取厚度参数，默认为3mm
                                thickness = getattr(config, 'thickness', 3) / 1000.0  # mm to meter
                                
                                _, glb_path = self.gltf_exporter.export_plate_gltf(
                                    plate_number=plate_number,
                                    plate_type=config.plate_type,
                                    is_double=config.double_row,
                                    pbr_textures=pbr_textures,
                                    output_name=model_filename,
                                    embed_textures=True,
                                    thickness=thickness
                                )
                                
                                # 复制GLB到任务目录
                                task_glb_path = task_output_dir / f"{model_filename}.glb"
                                import shutil
                                shutil.copy(glb_path, task_glb_path)
                                model_path = f"/api/results/{task_id}/{model_filename}.glb"
                                
                            except Exception as e:
                                print(f"⚠️ 模型导出失败: {e}")

                        result_item = {
                            "image": f"/api/results/{task_id}/{filename}",
                            "model": model_path,
                            "plate_number": plate_number
                        }
                        results.append(result_item)
                    else:
                        # 仅在没有生成器时使用占位符
                        filename = f"placeholder_{i:04d}.jpg"
                        filepath = task_output_dir / filename
                        with open(filepath, 'w') as f:
                            f.write("placeholder")
                        
                        results.append({
                            "image": f"/api/results/{task_id}/{filename}",
                            "model": None,
                            "plate_number": "PLACEHOLDER"
                        })
                except Exception as e:
                    print(f"⚠️ 单个车牌生成失败: {e}")
                    # 即使单个失败，也继续执行后续任务，或者记录错误
                    # 这里选择继续，但进度+1
                
                task.progress = i + 1
            
            task.results = results
            task.status = "completed"
            task.completed_at = datetime.now().isoformat()
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.now().isoformat()

# ============ API 服务器类 ============

class APIServer:
    def __init__(self, output_dir: str = None):
        self.project_root = PROJECT_ROOT
        
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.project_root / "data" / "output"
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化生成器 (占位)
        self.plate_generator = None
        self.noise_generator = None
        self.gltf_exporter = None
        
        if GENERATOR_AVAILABLE:
            try:
                self.plate_generator = MultiPlateGenerator(
                    adr_plate_model=str(self.project_root / "assets" / "plate_model"),
                    adr_font=str(self.project_root / "assets" / "font_model")
                )
                print("✅ 车牌生成器初始化成功")
            except Exception as e:
                print(f"⚠️ 车牌生成器初始化失败: {e}")
                
        if GLTF_AVAILABLE:
            try:
                self.gltf_exporter = GLTFExporter(self.output_dir / "models")
                print("✅ GLTF导出器初始化成功")
            except Exception as e:
                print(f"⚠️ GLTF导出器初始化失败: {e}")

        # 初始化任务管理器
        self.task_manager = TaskManager(
            self.plate_generator,
            self.noise_generator,
            self.gltf_exporter,
            self.output_dir
        )
        self.task_manager.start()
        
        # 创建Flask应用
        self.app = Flask(__name__)
        CORS(self.app) # 启用CORS以支持跨域请求
        
        self._register_routes()
        
    def _register_routes(self):
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            return jsonify({
                "status": "ok", 
                "timestamp": datetime.now().isoformat(),
                "version": "2.0.0-API"
            })
            
        @self.app.route('/api/stats', methods=['GET'])
        def get_stats():
            # 模拟统计数据
            return jsonify({
                "total_generated": 12450,
                "storage_used": "4.2 GB",
                "api_latency": "45ms",
                "active_nodes": "3/3"
            })
            
        @self.app.route('/api/generate', methods=['POST'])
        def create_generation_task():
            data = request.json
            if not data:
                return jsonify({"error": "No data provided"}), 400
                
            config = PlateConfig(
                plate_type=data.get('plateType', 'blue'),
                count=int(data.get('count', 1)),
                noise_preset=data.get('noisePreset', 'medium'),
                province=data.get('province', ''),
                custom_number=data.get('customNumber', ''),
                double_row=data.get('doubleRow', False),
                thickness=int(data.get('thickness', 3))
            )
            
            task = self.task_manager.create_task(config)
            return jsonify({
                "task_id": task.task_id,
                "status": task.status,
                "message": "Task created successfully"
            })
            
        @self.app.route('/api/tasks/<task_id>', methods=['GET'])
        def get_task_status(task_id):
            task = self.task_manager.get_task(task_id)
            if not task:
                return jsonify({"error": "Task not found"}), 404
            return jsonify(task.to_dict())
            
        @self.app.route('/api/tasks', methods=['GET'])
        def list_tasks():
            tasks = self.task_manager.get_all_tasks()
            return jsonify([t.to_dict() for t in tasks])
            
        @self.app.route('/api/assets', methods=['GET'])
        def list_assets():
            # 模拟资产列表
            return jsonify([
                {"name": "Font_LicensePlate_V2.ttf", "type": "FONT", "size": "2.4 MB", "status": "Active"},
                {"name": "Noise_Texture_Pack_01.zip", "type": "TEXTURE", "size": "45.2 MB", "status": "Active"},
                {"name": "Plate_Base_Blue.png", "type": "IMAGE", "size": "1.2 MB", "status": "Active"}
            ])
            
        @self.app.route('/api/results/<task_id>/<filename>', methods=['GET'])
        def get_result_file(task_id, filename):
            directory = self.output_dir / "generated" / task_id
            return send_from_directory(directory, filename)

        @self.app.route('/api/gallery', methods=['GET'])
        def get_gallery():
            """获取所有生成的车牌历史记录"""
            gallery_items = []
            generated_dir = self.output_dir / "generated"
            
            if generated_dir.exists():
                # 遍历所有任务目录
                for task_dir in sorted(generated_dir.iterdir(), key=os.path.getmtime, reverse=True):
                    if task_dir.is_dir():
                        task_id = task_dir.name
                        # 查找该任务下的所有图片和模型
                        for img_file in task_dir.glob("*.jpg"):
                            if "placeholder" in img_file.name:
                                continue
                                
                            plate_number = img_file.stem.split('_')[0]
                            model_file = task_dir / f"{img_file.stem}.glb"
                            
                            item = {
                                "id": f"{task_id}_{img_file.stem}",
                                "task_id": task_id,
                                "plate_number": plate_number,
                                "image": f"/api/results/{task_id}/{img_file.name}",
                                "model": f"/api/results/{task_id}/{model_file.name}" if model_file.exists() else None,
                                "created_at": datetime.fromtimestamp(img_file.stat().st_mtime).isoformat(),
                                "type": "Blue" # 暂时硬编码，实际应从文件名或元数据读取
                            }
                            gallery_items.append(item)
                            
            return jsonify(gallery_items)

    def run(self, host='0.0.0.0', port=5000, debug=False):
        self.app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    server = APIServer()
    server.run(port=5000, debug=True)
