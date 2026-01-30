#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化应用单元测试

测试Flask应用的各个API端点和功能。
"""

import os
import sys
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from visualization.app import PlateVisualizationApp, PlateAsset, DashboardStats


class TestPlateVisualizationApp(unittest.TestCase):
    """测试PlateVisualizationApp类"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        # 创建临时输出目录
        cls.temp_dir = tempfile.mkdtemp()
        cls.app_instance = PlateVisualizationApp(output_dir=cls.temp_dir)
        cls.client = cls.app_instance.app.test_client()
        cls.app_instance.app.config['TESTING'] = True
    
    @classmethod
    def tearDownClass(cls):
        """清理测试环境"""
        import shutil
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)
    
    def test_index_route(self):
        """测试主页路由"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)
    
    def test_gallery_route(self):
        """测试图库页面路由"""
        response = self.client.get('/gallery')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'gallery', response.data.lower())
    
    def test_api_stats(self):
        """测试统计数据API"""
        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('total_plates', data)
        self.assertIn('categories', data)
        self.assertIn('colors', data)
        self.assertIn('single_layer', data)
        self.assertIn('double_layer', data)
        self.assertIn('total_size_mb', data)
    
    def test_api_plates(self):
        """测试车牌列表API"""
        response = self.client.get('/api/plates')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
    
    def test_api_plates_with_filters(self):
        """测试带筛选参数的车牌列表API"""
        # 测试分类筛选
        response = self.client.get('/api/plates?category=civilian')
        self.assertEqual(response.status_code, 200)
        
        # 测试颜色筛选
        response = self.client.get('/api/plates?color=blue')
        self.assertEqual(response.status_code, 200)
        
        # 测试搜索
        response = self.client.get('/api/plates?search=京')
        self.assertEqual(response.status_code, 200)
    
    def test_api_categories(self):
        """测试分类列表API"""
        response = self.client.get('/api/categories')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
    
    def test_api_colors(self):
        """测试颜色列表API"""
        response = self.client.get('/api/colors')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
    
    def test_api_system(self):
        """测试系统信息API"""
        response = self.client.get('/api/system')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('platform', data)
        self.assertIn('python_version', data)
        self.assertIn('project_root', data)
        self.assertIn('output_dir', data)
    
    def test_serve_plate_image_not_found(self):
        """测试图片服务 - 文件不存在"""
        response = self.client.get('/plates/nonexistent.jpg')
        self.assertEqual(response.status_code, 404)


class TestPlateAsset(unittest.TestCase):
    """测试PlateAsset数据类"""
    
    def test_plate_asset_creation(self):
        """测试PlateAsset创建"""
        asset = PlateAsset(
            filename='test.jpg',
            filepath='/path/to/test.jpg',
            category='civilian',
            plate_number='京A12345',
            color='blue',
            is_double=False,
            file_size=1024,
            created_time='2024-01-01 00:00:00',
            image_url='/plates/test.jpg'
        )
        
        self.assertEqual(asset.filename, 'test.jpg')
        self.assertEqual(asset.category, 'civilian')
        self.assertEqual(asset.plate_number, '京A12345')
        self.assertEqual(asset.color, 'blue')
        self.assertFalse(asset.is_double)


class TestDashboardStats(unittest.TestCase):
    """测试DashboardStats数据类"""
    
    def test_dashboard_stats_creation(self):
        """测试DashboardStats创建"""
        stats = DashboardStats(
            total_plates=100,
            categories={'civilian': 50, 'new_energy': 50},
            colors={'blue': 60, 'green': 40},
            single_layer=80,
            double_layer=20,
            total_size_mb=10.5,
            last_generated='2024-01-01 00:00:00'
        )
        
        self.assertEqual(stats.total_plates, 100)
        self.assertEqual(stats.single_layer, 80)
        self.assertEqual(stats.double_layer, 20)
        self.assertEqual(stats.total_size_mb, 10.5)


class TestParseFilename(unittest.TestCase):
    """测试文件名解析功能"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        cls.temp_dir = tempfile.mkdtemp()
        cls.app_instance = PlateVisualizationApp(output_dir=cls.temp_dir)
    
    @classmethod
    def tearDownClass(cls):
        """清理测试环境"""
        import shutil
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)
    
    def test_parse_standard_filename(self):
        """测试标准文件名解析"""
        # 创建临时测试文件
        test_file = Path(self.temp_dir) / "京A12345_blue_false.jpg"
        test_file.write_bytes(b'test')
        
        result = self.app_instance._parse_plate_file(test_file, 'test')
        
        self.assertIsNotNone(result)
        self.assertEqual(result.plate_number, '京A12345')
        self.assertEqual(result.color, 'blue')
        self.assertFalse(result.is_double)
    
    def test_parse_double_layer_filename(self):
        """测试双层车牌文件名解析"""
        test_file = Path(self.temp_dir) / "京A12345_yellow_true.jpg"
        test_file.write_bytes(b'test')
        
        result = self.app_instance._parse_plate_file(test_file, 'test')
        
        self.assertIsNotNone(result)
        self.assertTrue(result.is_double)
    
    def test_parse_green_car_filename(self):
        """测试新能源车牌文件名解析"""
        test_file = Path(self.temp_dir) / "京AD12345_green_car_false.jpg"
        test_file.write_bytes(b'test')
        
        result = self.app_instance._parse_plate_file(test_file, 'test')
        
        self.assertIsNotNone(result)
        self.assertEqual(result.color, 'green')


if __name__ == '__main__':
    unittest.main(verbosity=2)
