#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨平台工具函数模块

提供Linux/Windows/macOS平台兼容的工具函数。
"""

import os
import sys
import platform
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional


def get_platform_info() -> dict:
    """
    获取当前平台信息
    
    Returns:
        包含平台信息的字典
    """
    return {
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'python_version': platform.python_version(),
        'is_linux': platform.system() == 'Linux',
        'is_windows': platform.system() == 'Windows',
        'is_macos': platform.system() == 'Darwin'
    }


def normalize_path(path: str) -> str:
    """
    规范化路径，确保跨平台兼容
    
    Args:
        path: 原始路径
        
    Returns:
        规范化后的路径
    """
    # 转换为Path对象并解析
    normalized = Path(path).resolve()
    return str(normalized)


def ensure_directory(path: str) -> Path:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        path: 目录路径
        
    Returns:
        Path对象
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def open_browser(url: str) -> bool:
    """
    跨平台打开浏览器
    
    Args:
        url: 要打开的URL
        
    Returns:
        是否成功打开
    """
    try:
        system = platform.system()
        
        if system == 'Linux':
            # Linux平台尝试多种方式
            browsers = ['xdg-open', 'gnome-open', 'kde-open', 'sensible-browser']
            for browser in browsers:
                try:
                    subprocess.Popen([browser, url], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                    return True
                except FileNotFoundError:
                    continue
            # 如果都失败，使用webbrowser模块
            webbrowser.open(url)
            return True
            
        elif system == 'Darwin':
            # macOS
            subprocess.Popen(['open', url])
            return True
            
        elif system == 'Windows':
            # Windows
            os.startfile(url)
            return True
            
        else:
            # 其他系统使用webbrowser
            webbrowser.open(url)
            return True
            
    except Exception as e:
        print(f"⚠️ 无法自动打开浏览器: {e}")
        print(f"📍 请手动访问: {url}")
        return False


def find_available_port(start_port: int = 5000, max_tries: int = 100) -> int:
    """
    查找可用端口
    
    Args:
        start_port: 起始端口
        max_tries: 最大尝试次数
        
    Returns:
        可用端口号
    """
    import socket
    
    for port in range(start_port, start_port + max_tries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    
    raise RuntimeError(f"无法在 {start_port}-{start_port + max_tries} 范围内找到可用端口")


def get_local_ip() -> str:
    """
    获取本机局域网IP地址
    
    Returns:
        IP地址字符串
    """
    import socket
    
    try:
        # 创建一个UDP socket连接到外部地址来获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小
    
    Args:
        size_bytes: 字节数
        
    Returns:
        格式化后的字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def safe_filename(filename: str) -> str:
    """
    生成安全的文件名，移除不合法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        安全的文件名
    """
    # 定义不同平台的非法字符
    if platform.system() == 'Windows':
        illegal_chars = '<>:"/\\|?*'
    else:
        illegal_chars = '/'
    
    # 替换非法字符
    safe_name = filename
    for char in illegal_chars:
        safe_name = safe_name.replace(char, '_')
    
    return safe_name


class ColorPrinter:
    """跨平台彩色输出类"""
    
    # ANSI颜色代码
    COLORS = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'reset': '\033[0m'
    }
    
    @classmethod
    def _supports_color(cls) -> bool:
        """检查终端是否支持颜色"""
        if platform.system() == 'Windows':
            # Windows 10+ 支持ANSI颜色
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
                return True
            except Exception:
                return False
        else:
            # Unix系统检查是否是终端
            return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    
    @classmethod
    def print(cls, text: str, color: str = 'white'):
        """
        彩色打印
        
        Args:
            text: 要打印的文本
            color: 颜色名称
        """
        if cls._supports_color() and color in cls.COLORS:
            print(f"{cls.COLORS[color]}{text}{cls.COLORS['reset']}")
        else:
            print(text)
    
    @classmethod
    def success(cls, text: str):
        """打印成功信息"""
        cls.print(f"✅ {text}", 'green')
    
    @classmethod
    def error(cls, text: str):
        """打印错误信息"""
        cls.print(f"❌ {text}", 'red')
    
    @classmethod
    def warning(cls, text: str):
        """打印警告信息"""
        cls.print(f"⚠️ {text}", 'yellow')
    
    @classmethod
    def info(cls, text: str):
        """打印信息"""
        cls.print(f"📋 {text}", 'blue')
