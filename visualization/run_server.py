#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化服务器启动脚本

提供简便的服务器启动方式，支持自动打开浏览器。
"""

import sys
import time
import argparse
import threading
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from visualization.app import PlateGeneratorApp
from visualization.utils import open_browser, find_available_port, get_local_ip, ColorPrinter


def delayed_open_browser(url: str, delay: float = 1.5):
    """
    延迟打开浏览器
    
    Args:
        url: 要打开的URL
        delay: 延迟秒数
    """
    time.sleep(delay)
    open_browser(url)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='车牌生成器可视化Dashboard服务器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python run_server.py                    # 默认启动
  python run_server.py --port 8080        # 指定端口
  python run_server.py --no-browser       # 不自动打开浏览器
  python run_server.py --debug            # 调试模式
        '''
    )
    
    parser.add_argument(
        '--host', 
        type=str, 
        default='0.0.0.0', 
        help='主机地址 (默认: 0.0.0.0)'
    )
    parser.add_argument(
        '--port', 
        type=int, 
        default=5000, 
        help='端口号 (默认: 5000)'
    )
    parser.add_argument(
        '--debug', 
        action='store_true', 
        help='开启调试模式'
    )
    parser.add_argument(
        '--no-browser', 
        action='store_true', 
        help='不自动打开浏览器'
    )
    parser.add_argument(
        '--output-dir', 
        type=str, 
        default=None, 
        help='输出目录路径'
    )
    
    args = parser.parse_args()
    
    # 打印启动信息
    ColorPrinter.info("正在启动车牌生成器可视化Dashboard...")
    
    # 查找可用端口
    try:
        port = find_available_port(args.port)
        if port != args.port:
            ColorPrinter.warning(f"端口 {args.port} 已被占用，使用端口 {port}")
    except RuntimeError as e:
        ColorPrinter.error(str(e))
        sys.exit(1)
    
    # 创建应用
    app = PlateGeneratorApp(output_dir=args.output_dir)
    
    # 获取访问地址
    local_ip = get_local_ip()
    local_url = f"http://localhost:{port}"
    network_url = f"http://{local_ip}:{port}"
    
    # 打印访问信息
    print("\n" + "=" * 50)
    ColorPrinter.success("服务器启动成功!")
    print("=" * 50)
    print(f"\n📍 本地访问:   {local_url}")
    print(f"📍 局域网访问: {network_url}")
    print(f"\n💡 按 Ctrl+C 停止服务器\n")
    
    # 自动打开浏览器
    if not args.no_browser:
        ColorPrinter.info("正在打开浏览器...")
        browser_thread = threading.Thread(
            target=delayed_open_browser, 
            args=(local_url,)
        )
        browser_thread.daemon = True
        browser_thread.start()
    
    # 启动服务器
    try:
        app.run(host=args.host, port=port, debug=args.debug)
    except KeyboardInterrupt:
        print("\n")
        ColorPrinter.info("服务器已停止")


if __name__ == '__main__':
    main()
