#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数单元测试

测试跨平台工具函数的功能。
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from visualization.utils import (
    get_platform_info,
    normalize_path,
    ensure_directory,
    find_available_port,
    get_local_ip,
    format_file_size,
    safe_filename,
    ColorPrinter
)


class TestGetPlatformInfo(unittest.TestCase):
    """测试get_platform_info函数"""
    
    def test_returns_dict(self):
        """测试返回字典类型"""
        info = get_platform_info()
        self.assertIsInstance(info, dict)
    
    def test_contains_required_keys(self):
        """测试包含必要的键"""
        info = get_platform_info()
        required_keys = ['system', 'release', 'version', 'machine', 
                        'python_version', 'is_linux', 'is_windows', 'is_macos']
        for key in required_keys:
            self.assertIn(key, info)
    
    def test_boolean_flags(self):
        """测试布尔标志"""
        info = get_platform_info()
        self.assertIsInstance(info['is_linux'], bool)
        self.assertIsInstance(info['is_windows'], bool)
        self.assertIsInstance(info['is_macos'], bool)
        
        # 只有一个平台标志应该为True
        platform_flags = [info['is_linux'], info['is_windows'], info['is_macos']]
        self.assertEqual(sum(platform_flags), 1)


class TestNormalizePath(unittest.TestCase):
    """测试normalize_path函数"""
    
    def test_normalize_relative_path(self):
        """测试相对路径规范化"""
        result = normalize_path('./test')
        self.assertTrue(os.path.isabs(result))
    
    def test_normalize_absolute_path(self):
        """测试绝对路径规范化"""
        result = normalize_path('/tmp/test')
        self.assertEqual(result, '/tmp/test')
    
    def test_returns_string(self):
        """测试返回字符串类型"""
        result = normalize_path('.')
        self.assertIsInstance(result, str)


class TestEnsureDirectory(unittest.TestCase):
    """测试ensure_directory函数"""
    
    def test_create_new_directory(self):
        """测试创建新目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = os.path.join(temp_dir, 'new_subdir')
            result = ensure_directory(new_dir)
            
            self.assertTrue(os.path.exists(new_dir))
            self.assertTrue(os.path.isdir(new_dir))
            self.assertIsInstance(result, Path)
    
    def test_existing_directory(self):
        """测试已存在的目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = ensure_directory(temp_dir)
            
            self.assertTrue(os.path.exists(temp_dir))
            self.assertIsInstance(result, Path)
    
    def test_nested_directory(self):
        """测试嵌套目录创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_dir = os.path.join(temp_dir, 'a', 'b', 'c')
            result = ensure_directory(nested_dir)
            
            self.assertTrue(os.path.exists(nested_dir))


class TestFindAvailablePort(unittest.TestCase):
    """测试find_available_port函数"""
    
    def test_returns_integer(self):
        """测试返回整数类型"""
        port = find_available_port(50000)
        self.assertIsInstance(port, int)
    
    def test_port_in_range(self):
        """测试端口在有效范围内"""
        port = find_available_port(50000, max_tries=10)
        self.assertGreaterEqual(port, 50000)
        self.assertLess(port, 50010)
    
    def test_port_is_available(self):
        """测试返回的端口可用"""
        import socket
        
        port = find_available_port(50000)
        
        # 尝试绑定该端口
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                # 如果能绑定，说明端口可用
                self.assertTrue(True)
        except OSError:
            self.fail(f"Port {port} is not available")


class TestGetLocalIp(unittest.TestCase):
    """测试get_local_ip函数"""
    
    def test_returns_string(self):
        """测试返回字符串类型"""
        ip = get_local_ip()
        self.assertIsInstance(ip, str)
    
    def test_valid_ip_format(self):
        """测试返回有效的IP格式"""
        ip = get_local_ip()
        parts = ip.split('.')
        
        # 应该有4个部分
        self.assertEqual(len(parts), 4)
        
        # 每个部分应该是0-255之间的数字
        for part in parts:
            self.assertTrue(part.isdigit())
            self.assertGreaterEqual(int(part), 0)
            self.assertLessEqual(int(part), 255)


class TestFormatFileSize(unittest.TestCase):
    """测试format_file_size函数"""
    
    def test_bytes(self):
        """测试字节格式化"""
        result = format_file_size(100)
        self.assertIn('B', result)
        self.assertIn('100', result)
    
    def test_kilobytes(self):
        """测试KB格式化"""
        result = format_file_size(1024)
        self.assertIn('KB', result)
    
    def test_megabytes(self):
        """测试MB格式化"""
        result = format_file_size(1024 * 1024)
        self.assertIn('MB', result)
    
    def test_gigabytes(self):
        """测试GB格式化"""
        result = format_file_size(1024 * 1024 * 1024)
        self.assertIn('GB', result)
    
    def test_zero_bytes(self):
        """测试零字节"""
        result = format_file_size(0)
        self.assertIn('0', result)
        self.assertIn('B', result)


class TestSafeFilename(unittest.TestCase):
    """测试safe_filename函数"""
    
    def test_normal_filename(self):
        """测试正常文件名"""
        result = safe_filename('test.txt')
        self.assertEqual(result, 'test.txt')
    
    def test_filename_with_slash(self):
        """测试包含斜杠的文件名"""
        result = safe_filename('test/file.txt')
        self.assertNotIn('/', result)
    
    def test_chinese_filename(self):
        """测试中文文件名"""
        result = safe_filename('测试文件.txt')
        self.assertEqual(result, '测试文件.txt')
    
    def test_returns_string(self):
        """测试返回字符串类型"""
        result = safe_filename('test.txt')
        self.assertIsInstance(result, str)


class TestColorPrinter(unittest.TestCase):
    """测试ColorPrinter类"""
    
    def test_success_method(self):
        """测试success方法"""
        # 不应该抛出异常
        try:
            ColorPrinter.success('Test success message')
        except Exception as e:
            self.fail(f"ColorPrinter.success raised exception: {e}")
    
    def test_error_method(self):
        """测试error方法"""
        try:
            ColorPrinter.error('Test error message')
        except Exception as e:
            self.fail(f"ColorPrinter.error raised exception: {e}")
    
    def test_warning_method(self):
        """测试warning方法"""
        try:
            ColorPrinter.warning('Test warning message')
        except Exception as e:
            self.fail(f"ColorPrinter.warning raised exception: {e}")
    
    def test_info_method(self):
        """测试info方法"""
        try:
            ColorPrinter.info('Test info message')
        except Exception as e:
            self.fail(f"ColorPrinter.info raised exception: {e}")
    
    def test_print_with_color(self):
        """测试带颜色的打印"""
        try:
            ColorPrinter.print('Test message', 'green')
        except Exception as e:
            self.fail(f"ColorPrinter.print raised exception: {e}")
    
    def test_print_with_invalid_color(self):
        """测试无效颜色"""
        try:
            ColorPrinter.print('Test message', 'invalid_color')
        except Exception as e:
            self.fail(f"ColorPrinter.print raised exception with invalid color: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
