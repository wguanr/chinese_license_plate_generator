#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车牌生成器管理系统 - Flask Web应用

提供完整的管理界面，支持：
- 自定义生成配置
- 实时预览
- 批量生成任务
- 资产管理
- 数据集导出

兼容Linux/Windows/macOS平台。
"""

import os
import sys
import json
import platform
import shutil
import uuid
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from collections import defaultdict
from queue import Queue

from flask import Flask, render_template, jsonify, request, send_from_directory, send_file

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 导入核心模块
from core.dataset_exporter import DatasetExporter
from core.noise_module import (
    CompositeNoiseApplicator, CompositeNoiseConfig, NoiseConfig,
    NoiseType, NoiseIntensity,
    StainConfig, ShadowConfig, PaintPeelingConfig, OcclusionConfig
)

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
    plate_type: str = "blue"  # blue, yellow, green_car, green_truck, white, black, black_shi
    count: int = 1
    noise_preset: str = "medium"  # clean, light, medium, heavy, extreme, random
    custom_noise: Dict = field(default_factory=dict)
    province: str = ""  # 空表示随机
    custom_number: str = ""  # 空表示随机生成


@dataclass
class GenerationTask:
    """生成任务"""
    task_id: str
    config: PlateConfig
    status: str = "pending"  # pending, running, completed, failed
    progress: int = 0
    total: int = 0
    created_at: str = ""
    completed_at: str = ""
    results: List[str] = field(default_factory=list)
    error: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class PlateAsset:
    """车牌资产"""
    asset_id: str
    filename: str
    filepath: str
    plate_number: str
    plate_type: str
    color: str
    is_double: bool
    noise_level: str
    file_size: int
    width: int
    height: int
    created_at: str
    image_url: str
    tags: List[str] = field(default_factory=list)


# ============ 任务管理器 ============

class TaskManager:
    """任务管理器"""
    
    def __init__(self, generator, noise_generator, output_dir: Path):
        self.generator = generator
        self.noise_generator = noise_generator
        self.output_dir = output_dir
        self.tasks: Dict[str, GenerationTask] = {}
        self.task_queue = Queue()
        self.is_running = False
        self._worker_thread = None
    
    def start(self):
        """启动任务处理器"""
        if not self.is_running:
            self.is_running = True
            self._worker_thread = threading.Thread(target=self._process_tasks, daemon=True)
            self._worker_thread.start()
    
    def stop(self):
        """停止任务处理器"""
        self.is_running = False
    
    def create_task(self, config: PlateConfig) -> GenerationTask:
        """创建新任务"""
        task = GenerationTask(
            task_id=str(uuid.uuid4())[:8],
            config=config,
            total=config.count
        )
        self.tasks[task.task_id] = task
        self.task_queue.put(task.task_id)
        return task
    
    def get_task(self, task_id: str) -> Optional[GenerationTask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[GenerationTask]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def _process_tasks(self):
        """处理任务队列"""
        while self.is_running:
            try:
                if not self.task_queue.empty():
                    task_id = self.task_queue.get(timeout=1)
                    self._execute_task(task_id)
                else:
                    time.sleep(0.5)
            except Exception as e:
                print(f"任务处理错误: {e}")
    
    def _execute_task(self, task_id: str):
        """执行单个任务"""
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
                # 生成车牌
                plate_img, plate_number = self._generate_single_plate(config)
                
                if plate_img is not None:
                    # 应用噪声
                    if config.noise_preset != "clean":
                        plate_img = self._apply_noise(plate_img, config)
                    
                    # 保存图片
                    filename = f"{plate_number}_{config.plate_type}_{config.noise_preset}_{i:04d}.jpg"
                    filepath = task_output_dir / filename
                    plate_img.save(str(filepath), quality=95)
                    results.append(str(filepath))
                
                task.progress = i + 1
            
            task.results = results
            task.status = "completed"
            task.completed_at = datetime.now().isoformat()
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.now().isoformat()
    
    def _generate_single_plate(self, config: PlateConfig):
        """生成单个车牌"""
        if not self.generator:
            return None, "UNKNOWN"
        
        try:
            # 映射类型
            type_mapping = {
                "blue": ("blue", False),
                "yellow": ("yellow", False),
                "yellow_double": ("yellow", True),
                "green_car": ("green_car", False),
                "green_truck": ("green_truck", False),
                "white": ("white", False),
                "white_double": ("white", True),
                "black": ("black", False),
                "black_shi": ("black_shi", False),
            }
            
            plate_type, is_double = type_mapping.get(config.plate_type, ("blue", False))
            
            # 调用生成器
            img, number = self.generator.generate_plate_by_type(plate_type, is_double)
            return img, number
            
        except Exception as e:
            print(f"生成车牌失败: {e}")
            return None, "ERROR"
    
    def _apply_noise(self, img, config: PlateConfig):
        """应用噪声"""
        if not self.noise_generator:
            return img
        
        try:
            import numpy as np
            from PIL import Image
            
            # 转换为numpy数组
            img_array = np.array(img)
            
            # 根据预设创建噪声配置
            intensity_map = {
                "clean": NoiseIntensity.NONE,
                "light": NoiseIntensity.LIGHT,
                "medium": NoiseIntensity.MEDIUM,
                "heavy": NoiseIntensity.HEAVY,
                "extreme": NoiseIntensity.EXTREME,
                "random": NoiseIntensity.MEDIUM
            }
            
            intensity = intensity_map.get(config.noise_preset, NoiseIntensity.MEDIUM)
            
            if intensity == NoiseIntensity.NONE:
                return img
            
            # 创建复合噪声配置
            noise_config = CompositeNoiseConfig(
                stain=StainConfig(intensity=intensity),
                shadow=ShadowConfig(intensity=intensity),
                paint_peeling=PaintPeelingConfig(intensity=intensity) if intensity.value >= 2 else None,
                occlusion=OcclusionConfig(intensity=intensity) if intensity.value >= 3 else None
            )
            
            # 应用噪声
            noisy_array = self.noise_generator.apply(img_array, noise_config)
            
            return Image.fromarray(noisy_array)
            
        except Exception as e:
            print(f"应用噪声失败: {e}")
            return img


# ============ 主应用类 ============

class PlateGeneratorApp:
    """车牌生成器管理应用"""
    
    def __init__(self, output_dir: str = None):
        self.project_root = PROJECT_ROOT
        
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.project_root / "data" / "output"
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir = self.project_root / "data" / "export"
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化生成器
        self._init_generators()
        
        # 初始化任务管理器
        self.task_manager = TaskManager(
            self.plate_generator,
            self.noise_generator,
            self.output_dir
        )
        self.task_manager.start()
        
        # 创建Flask应用
        self.app = Flask(
            __name__,
            template_folder=str(Path(__file__).parent / "templates"),
            static_folder=str(Path(__file__).parent / "static")
        )
        
        # 注册路由
        self._register_routes()
        
        # 资产缓存
        self._assets_cache: List[PlateAsset] = []
        self._cache_time: Optional[datetime] = None
        
        print(f"✅ 车牌生成器管理系统初始化完成")
        print(f"📁 输出目录: {self.output_dir}")
        print(f"📁 导出目录: {self.export_dir}")
    
    def _init_generators(self):
        """初始化生成器"""
        self.plate_generator = None
        self.noise_generator = None
        
        # 初始化车牌生成器
        if GENERATOR_AVAILABLE:
            try:
                plate_model_dir = self.project_root / "assets" / "plate_model"
                font_model_dir = self.project_root / "assets" / "font_model"
                
                if plate_model_dir.exists() and font_model_dir.exists():
                    self.plate_generator = MultiPlateGenerator(
                        str(plate_model_dir),
                        str(font_model_dir)
                    )
                    print("✅ 车牌生成器初始化成功")
                else:
                    print("⚠️ 资源目录不存在")
            except Exception as e:
                print(f"⚠️ 车牌生成器初始化失败: {e}")
        
        # 初始化噪声生成器
        try:
            self.noise_generator = CompositeNoiseApplicator()
            print("✅ 噪声生成器初始化成功")
        except Exception as e:
            print(f"⚠️ 噪声生成器初始化失败: {e}")
    
    def _register_routes(self):
        """注册Flask路由"""
        
        # ============ 页面路由 ============
        
        @self.app.route('/')
        def index():
            """主页 - 管理面板"""
            return render_template('admin.html')
        
        @self.app.route('/generate')
        def generate_page():
            """生成页面"""
            return render_template('generate.html')
        
        @self.app.route('/assets')
        def assets_page():
            """资产管理页面"""
            return render_template('assets.html')
        
        @self.app.route('/export')
        def export_page():
            """导出页面"""
            return render_template('export.html')
        
        @self.app.route('/viewer3d')
        def viewer3d_page():
            """3D模型查看器页面"""
            return render_template('viewer3d.html')
        
        # ============ 系统API ============
        
        @self.app.route('/api/system/status')
        def api_system_status():
            """获取系统状态"""
            return jsonify({
                'platform': platform.system(),
                'python_version': platform.python_version(),
                'generator_available': self.plate_generator is not None,
                'noise_generator_available': self.noise_generator is not None,
                'output_dir': str(self.output_dir),
                'export_dir': str(self.export_dir)
            })
        
        # ============ 配置API ============
        
        @self.app.route('/api/config/plate_types')
        def api_plate_types():
            """获取支持的车牌类型"""
            return jsonify({
                'types': [
                    {'id': 'blue', 'name': '蓝色车牌', 'description': '普通民用车牌', 'color': '#1890ff'},
                    {'id': 'yellow', 'name': '黄色车牌', 'description': '大型车辆车牌', 'color': '#faad14'},
                    {'id': 'yellow_double', 'name': '黄色双层车牌', 'description': '挂车/货车车牌', 'color': '#faad14'},
                    {'id': 'green_car', 'name': '绿色小型新能源', 'description': '新能源小型车', 'color': '#52c41a'},
                    {'id': 'green_truck', 'name': '绿色大型新能源', 'description': '新能源大型车', 'color': '#52c41a'},
                    {'id': 'white', 'name': '白色车牌', 'description': '警车/军车车牌', 'color': '#ffffff'},
                    {'id': 'white_double', 'name': '白色双层车牌', 'description': '武警车牌', 'color': '#ffffff'},
                    {'id': 'black', 'name': '黑色车牌', 'description': '港澳车牌', 'color': '#262626'},
                    {'id': 'black_shi', 'name': '黑色使领馆车牌', 'description': '使领馆车辆', 'color': '#262626'},
                ]
            })
        
        @self.app.route('/api/config/noise_presets')
        def api_noise_presets():
            """获取噪声预设"""
            return jsonify({
                'presets': [
                    {'id': 'clean', 'name': '无噪声', 'description': '干净的车牌图像'},
                    {'id': 'light', 'name': '轻度噪声', 'description': '少量污渍和轻微磨损'},
                    {'id': 'medium', 'name': '中度噪声', 'description': '适中的污渍、阴影和磨损'},
                    {'id': 'heavy', 'name': '重度噪声', 'description': '明显的污渍、掉漆和遮挡'},
                    {'id': 'extreme', 'name': '极端噪声', 'description': '严重的污损和遮挡'},
                    {'id': 'random', 'name': '随机噪声', 'description': '随机组合各种噪声效果'},
                ]
            })
        
        @self.app.route('/api/config/provinces')
        def api_provinces():
            """获取省份列表"""
            provinces = [
                '京', '津', '沪', '渝', '冀', '豫', '云', '辽', '黑', '湘',
                '皖', '鲁', '新', '苏', '浙', '赣', '鄂', '桂', '甘', '晋',
                '蒙', '陕', '吉', '闽', '贵', '粤', '川', '青', '藏', '琼', '宁'
            ]
            return jsonify({'provinces': provinces})
        
        # ============ 生成API ============
        
        @self.app.route('/api/generate/preview', methods=['POST'])
        def api_generate_preview():
            """生成预览（单张）"""
            try:
                data = request.get_json()
                config = PlateConfig(
                    plate_type=data.get('plate_type', 'blue'),
                    count=1,
                    noise_preset=data.get('noise_preset', 'clean'),
                    province=data.get('province', ''),
                    custom_number=data.get('custom_number', '')
                )
                
                if not self.plate_generator:
                    return jsonify({'success': False, 'error': '生成器未初始化'}), 500
                
                # 生成单张预览
                task = self.task_manager.create_task(config)
                
                # 等待完成（预览是同步的）
                timeout = 10
                start = time.time()
                while task.status not in ['completed', 'failed'] and time.time() - start < timeout:
                    time.sleep(0.1)
                
                if task.status == 'completed' and task.results:
                    # 返回图片URL
                    filepath = Path(task.results[0])
                    relative_path = filepath.relative_to(self.output_dir)
                    return jsonify({
                        'success': True,
                        'image_url': f'/output/{relative_path}',
                        'filename': filepath.name
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': task.error or '生成超时'
                    }), 500
                    
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/generate/batch', methods=['POST'])
        def api_generate_batch():
            """批量生成"""
            try:
                data = request.get_json()
                config = PlateConfig(
                    plate_type=data.get('plate_type', 'blue'),
                    count=min(data.get('count', 10), 100),  # 限制最大100
                    noise_preset=data.get('noise_preset', 'medium'),
                    province=data.get('province', ''),
                    custom_number=data.get('custom_number', '')
                )
                
                if not self.plate_generator:
                    return jsonify({'success': False, 'error': '生成器未初始化'}), 500
                
                # 创建任务
                task = self.task_manager.create_task(config)
                
                return jsonify({
                    'success': True,
                    'task_id': task.task_id,
                    'message': f'已创建生成任务，共 {config.count} 张'
                })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/generate/task/<task_id>')
        def api_task_status(task_id):
            """获取任务状态"""
            task = self.task_manager.get_task(task_id)
            if not task:
                return jsonify({'error': '任务不存在'}), 404
            
            result = {
                'task_id': task.task_id,
                'status': task.status,
                'progress': task.progress,
                'total': task.total,
                'created_at': task.created_at,
                'completed_at': task.completed_at,
                'error': task.error
            }
            
            if task.status == 'completed':
                result['results'] = [
                    f'/output/generated/{task.task_id}/{Path(p).name}'
                    for p in task.results
                ]
            
            return jsonify(result)
        
        @self.app.route('/api/generate/tasks')
        def api_all_tasks():
            """获取所有任务"""
            tasks = self.task_manager.get_all_tasks()
            return jsonify({
                'tasks': [
                    {
                        'task_id': t.task_id,
                        'status': t.status,
                        'progress': t.progress,
                        'total': t.total,
                        'plate_type': t.config.plate_type,
                        'noise_preset': t.config.noise_preset,
                        'created_at': t.created_at,
                        'completed_at': t.completed_at
                    }
                    for t in sorted(tasks, key=lambda x: x.created_at, reverse=True)
                ]
            })
        
        # ============ 资产API ============
        
        @self.app.route('/api/assets')
        def api_assets():
            """获取资产列表"""
            assets = self._scan_assets()
            
            # 筛选参数
            plate_type = request.args.get('type')
            color = request.args.get('color')
            noise = request.args.get('noise')
            search = request.args.get('search', '').lower()
            
            filtered = assets
            
            if plate_type:
                filtered = [a for a in filtered if a.plate_type == plate_type]
            if color:
                filtered = [a for a in filtered if a.color == color]
            if noise:
                filtered = [a for a in filtered if a.noise_level == noise]
            if search:
                filtered = [a for a in filtered if search in a.plate_number.lower() or search in a.filename.lower()]
            
            # 分页
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))
            start = (page - 1) * per_page
            end = start + per_page
            
            return jsonify({
                'total': len(filtered),
                'page': page,
                'per_page': per_page,
                'assets': [asdict(a) for a in filtered[start:end]]
            })
        
        @self.app.route('/api/assets/stats')
        def api_assets_stats():
            """获取资产统计"""
            assets = self._scan_assets()
            
            stats = {
                'total': len(assets),
                'by_type': defaultdict(int),
                'by_color': defaultdict(int),
                'by_noise': defaultdict(int),
                'total_size_mb': 0
            }
            
            for asset in assets:
                stats['by_type'][asset.plate_type] += 1
                stats['by_color'][asset.color] += 1
                stats['by_noise'][asset.noise_level] += 1
                stats['total_size_mb'] += asset.file_size
            
            stats['by_type'] = dict(stats['by_type'])
            stats['by_color'] = dict(stats['by_color'])
            stats['by_noise'] = dict(stats['by_noise'])
            stats['total_size_mb'] = round(stats['total_size_mb'] / (1024 * 1024), 2)
            
            return jsonify(stats)
        
        @self.app.route('/api/assets/delete', methods=['POST'])
        def api_assets_delete():
            """删除资产"""
            try:
                data = request.get_json()
                asset_ids = data.get('asset_ids', [])
                
                deleted = 0
                for asset_id in asset_ids:
                    # 查找资产
                    assets = self._scan_assets()
                    for asset in assets:
                        if asset.asset_id == asset_id:
                            filepath = Path(asset.filepath)
                            if filepath.exists():
                                filepath.unlink()
                                deleted += 1
                            break
                
                # 清除缓存
                self._assets_cache = []
                self._cache_time = None
                
                return jsonify({
                    'success': True,
                    'deleted': deleted
                })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # ============ 导出API ============
        
        @self.app.route('/api/export/formats')
        def api_export_formats():
            """获取支持的导出格式"""
            return jsonify({
                'formats': [
                    {'id': 'dino', 'name': 'DINO', 'description': 'DINO格式数据集'},
                    {'id': 'kitti', 'name': 'KITTI', 'description': 'KITTI格式数据集'},
                    {'id': 'usd', 'name': 'USD', 'description': 'Universal Scene Description'},
                    {'id': 'json', 'name': 'JSON', 'description': 'JSON元数据文件'},
                ]
            })
        
        @self.app.route('/api/export/start', methods=['POST'])
        def api_export_start():
            """开始导出"""
            try:
                data = request.get_json()
                format_type = data.get('format', 'all')
                dataset_name = data.get('name', 'license_plates')
                source_dir = data.get('source', 'all')  # all, noisy, generated
                
                # 确定输入目录
                if source_dir == 'noisy':
                    input_dir = self.output_dir / "noisy" / "img"
                elif source_dir == 'generated':
                    input_dir = self.output_dir / "generated"
                elif source_dir == 'texture_noisy':
                    input_dir = self.output_dir / "texture_noisy" / "img"
                else:
                    # 默认使用贴图噪声目录
                    input_dir = self.output_dir / "texture_noisy" / "img"
                
                if not input_dir.exists():
                    return jsonify({'success': False, 'error': '输入目录不存在'}), 400
                
                exporter = DatasetExporter(input_dir, self.export_dir)
                images = exporter.scan_images()
                
                if not images:
                    return jsonify({'success': False, 'error': '未找到任何图像'}), 400
                
                results = {}
                
                if format_type in ['json', 'all']:
                    results['json'] = str(exporter.export_json(images, f"{dataset_name}_info.json"))
                
                if format_type in ['usd', 'all']:
                    results['usd'] = str(exporter.export_usd(images, dataset_name))
                
                if format_type in ['dino', 'all']:
                    results['dino'] = str(exporter.export_dino(images, f"{dataset_name}_dino"))
                
                if format_type in ['kitti', 'all']:
                    results['kitti'] = str(exporter.export_kitti(images, f"{dataset_name}_kitti"))
                
                return jsonify({
                    'success': True,
                    'message': f'成功导出 {len(images)} 张图像',
                    'total_images': len(images),
                    'results': results
                })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/export/download/<format_type>')
        def api_export_download(format_type):
            """下载导出的数据集"""
            try:
                dataset_name = request.args.get('name', 'license_plates')
                
                if format_type == 'dino':
                    export_path = self.export_dir / f"{dataset_name}_dino"
                elif format_type == 'kitti':
                    export_path = self.export_dir / f"{dataset_name}_kitti"
                elif format_type == 'usd':
                    export_path = self.export_dir / "usd"
                elif format_type == 'json':
                    json_path = self.export_dir / f"{dataset_name}_info.json"
                    if json_path.exists():
                        return send_file(json_path, as_attachment=True)
                    return jsonify({'error': 'JSON文件不存在'}), 404
                else:
                    return jsonify({'error': '不支持的格式'}), 400
                
                if not export_path.exists():
                    return jsonify({'error': '导出目录不存在'}), 404
                
                zip_filename = f"{dataset_name}_{format_type}.zip"
                zip_path = self.export_dir / zip_filename
                
                if zip_path.exists():
                    zip_path.unlink()
                
                shutil.make_archive(str(zip_path.with_suffix('')), 'zip', export_path)
                
                return send_file(zip_path, as_attachment=True, download_name=zip_filename)
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/export/status')
        def api_export_status():
            """获取导出状态"""
            exports = []
            
            for format_type in ['dino', 'kitti', 'usd', 'json']:
                if format_type == 'json':
                    path = self.export_dir / "license_plates_info.json"
                elif format_type == 'usd':
                    path = self.export_dir / "usd"
                else:
                    path = self.export_dir / f"license_plates_{format_type}"
                
                if path.exists():
                    if path.is_file():
                        size = path.stat().st_size
                        modified = datetime.fromtimestamp(path.stat().st_mtime).isoformat()
                    else:
                        size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                        modified = datetime.fromtimestamp(path.stat().st_mtime).isoformat()
                    
                    exports.append({
                        'format': format_type,
                        'exists': True,
                        'size_mb': round(size / (1024 * 1024), 2),
                        'modified': modified
                    })
                else:
                    exports.append({'format': format_type, 'exists': False})
            
            return jsonify({'exports': exports})
        
        # ============ 3D模型API ============
        
        @self.app.route('/api/models3d')
        def api_models3d():
            """获取3D模型列表"""
            models = []
            
            # 读取PBR清单文件
            manifest_path = self.output_dir / "pbr" / "usd" / "license_plates_pbr_manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                    
                    for asset in manifest.get('assets', []):
                        # 检查GLB文件是否存在
                        glb_name = f"{asset['plate_number']}_{asset['index']:04d}.glb"
                        glb_path = self.output_dir / "pbr" / "gltf" / glb_name
                        
                        # 获取尺寸信息
                        dimensions = asset.get('dimensions', {})
                        width_meters = dimensions.get('width_meters', 0.44)
                        height_meters = dimensions.get('height_meters', 0.14)
                        
                        if glb_path.exists():
                            models.append({
                                'plate_number': asset['plate_number'],
                                'plate_type': asset['plate_type'],
                                'is_double': asset.get('is_double', False),
                                'noise_preset': asset.get('noise_preset', 'medium'),
                                'index': asset['index'],
                                'width_meters': width_meters,
                                'height_meters': height_meters,
                                'glb_url': f"/output/pbr/gltf/{glb_name}",
                                'gltf_url': f"/output/pbr/gltf/{asset['plate_number']}_{asset['index']:04d}.gltf",
                                'textures': asset.get('textures', {}),
                                'thumbnail': f"/output/pbr/img/{asset['plate_number']}_{asset['plate_type']}_{asset.get('noise_preset', 'medium')}_{asset['index']:04d}.jpg"
                            })
                except Exception as e:
                    print(f"读取清单文件失败: {e}")
            
            return jsonify({
                'models': models,
                'total': len(models)
            })
        
        @self.app.route('/api/models3d/export', methods=['POST'])
        def api_models3d_export():
            """导出3D模型（USD + GLTF）"""
            try:
                from core.gltf_exporter import export_plates_to_gltf
                
                input_dir = self.output_dir / "pbr" / "usd"
                output_dir = self.output_dir / "pbr" / "gltf"
                manifest_path = input_dir / "license_plates_pbr_manifest.json"
                
                if not manifest_path.exists():
                    return jsonify({'success': False, 'error': 'PBR资产清单不存在，请先生成PBR车牌'}), 400
                
                results = export_plates_to_gltf(input_dir, output_dir, manifest_path)
                
                return jsonify({
                    'success': True,
                    'message': f'成功导出 {len(results)} 个3D模型',
                    'total': len(results)
                })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # ============ 文件服务 ============
        
        @self.app.route('/output/<path:filepath>')
        def serve_output(filepath):
            """提供输出文件服务"""
            return send_from_directory(str(self.output_dir), filepath)
        
        @self.app.route('/plates/<path:filepath>')
        def serve_plates(filepath):
            """提供车牌图片服务（兼容旧路由）"""
            # 尝试多个目录
            for subdir in ['noisy/img', 'generated', '']:
                full_path = self.output_dir / subdir / filepath
                if full_path.exists():
                    return send_from_directory(str(full_path.parent), full_path.name)
            return "Not Found", 404
    
    def _scan_assets(self, force_refresh: bool = False) -> List[PlateAsset]:
        """扫描资产"""
        if not force_refresh and self._cache_time:
            if (datetime.now() - self._cache_time).seconds < 5:
                return self._assets_cache
        
        assets = []
        
        # 扫描所有输出目录
        scan_dirs = [
            self.output_dir / "texture_noisy" / "img",
            self.output_dir / "noisy" / "img",
            self.output_dir / "generated",
        ]
        
        for scan_dir in scan_dirs:
            if scan_dir.exists():
                for img_file in scan_dir.rglob('*.jpg'):
                    asset = self._parse_asset(img_file)
                    if asset:
                        assets.append(asset)
                for img_file in scan_dir.rglob('*.png'):
                    asset = self._parse_asset(img_file)
                    if asset:
                        assets.append(asset)
        
        self._assets_cache = assets
        self._cache_time = datetime.now()
        
        return assets
    
    def _parse_asset(self, filepath: Path) -> Optional[PlateAsset]:
        """解析资产文件"""
        try:
            from PIL import Image
            
            filename = filepath.name
            stem = filepath.stem
            parts = stem.split('_')
            
            plate_number = parts[0] if parts else stem
            plate_type = parts[1] if len(parts) > 1 else 'unknown'
            noise_level = parts[2] if len(parts) > 2 else 'unknown'
            
            # 颜色映射
            color_map = {
                'blue': 'blue', 'yellow': 'yellow', 'green': 'green',
                'white': 'white', 'black': 'black', 'car': 'green', 'truck': 'green'
            }
            color = 'unknown'
            for key, val in color_map.items():
                if key in plate_type.lower():
                    color = val
                    break
            
            # 获取图片尺寸
            with Image.open(filepath) as img:
                width, height = img.size
            
            is_double = height > 180
            
            stat = filepath.stat()
            
            # 构建URL
            relative_path = filepath.relative_to(self.output_dir)
            image_url = f"/output/{relative_path}"
            
            return PlateAsset(
                asset_id=str(uuid.uuid4())[:8],
                filename=filename,
                filepath=str(filepath),
                plate_number=plate_number,
                plate_type=plate_type,
                color=color,
                is_double=is_double,
                noise_level=noise_level,
                file_size=stat.st_size,
                width=width,
                height=height,
                created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                image_url=image_url,
                tags=[plate_type, color, noise_level]
            )
            
        except Exception as e:
            print(f"解析资产失败 {filepath}: {e}")
            return None
    
    def run(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
        """启动服务器"""
        print(f"🚀 启动车牌生成器管理系统...")
        print(f"📍 访问地址: http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug, threaded=True)


def create_app(output_dir: str = None) -> Flask:
    """创建Flask应用实例"""
    app = PlateGeneratorApp(output_dir)
    return app.app


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='车牌生成器管理系统')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='主机地址')
    parser.add_argument('--port', type=int, default=5000, help='端口号')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    parser.add_argument('--output-dir', type=str, default=None, help='输出目录')
    
    args = parser.parse_args()
    
    app = PlateGeneratorApp(output_dir=args.output_dir)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
