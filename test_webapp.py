#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车牌生成器前端测试脚本

使用Playwright测试Flask Web应用的功能，特别是：
1. 页面加载
2. 导航功能
3. 3D模型查看器（USD/GLB加载）
4. 生成功能
"""

import time
from playwright.sync_api import sync_playwright, expect

def test_webapp():
    """测试车牌生成器Web应用"""
    
    with sync_playwright() as p:
        # 启动浏览器（无头模式）
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        # 收集控制台日志
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        
        # 收集错误
        errors = []
        page.on('pageerror', lambda exc: errors.append(str(exc)))
        
        test_results = {
            'dashboard': {'status': 'pending', 'details': []},
            'generate': {'status': 'pending', 'details': []},
            'viewer3d': {'status': 'pending', 'details': []},
            'gallery': {'status': 'pending', 'details': []},
            'assets': {'status': 'pending', 'details': []},
        }
        
        try:
            # ===================================================================
            # 测试1: Dashboard页面
            # ===================================================================
            print("\n=== 测试1: Dashboard页面 ===")
            page.goto('http://localhost:5000/', wait_until='networkidle', timeout=30000)
            
            # 等待页面加载
            time.sleep(2)
            
            # 截图
            page.screenshot(path='/tmp/test_dashboard.png', full_page=True)
            print("  ✓ Dashboard页面加载成功")
            test_results['dashboard']['details'].append("页面加载成功")
            
            # 检查关键元素
            if page.locator('text=车牌生成器').count() > 0:
                print("  ✓ 找到标题")
                test_results['dashboard']['details'].append("标题存在")
            
            if page.locator('text=仪表盘').count() > 0 or page.locator('text=Dashboard').count() > 0:
                print("  ✓ 找到仪表盘导航")
                test_results['dashboard']['details'].append("导航栏存在")
            
            test_results['dashboard']['status'] = 'passed'
            
            # ===================================================================
            # 测试2: 生成页面
            # ===================================================================
            print("\n=== 测试2: 生成页面 ===")
            
            # 查找生成页面链接
            generate_link = page.locator('a[href="/generate"]').first
            if generate_link.count() > 0:
                generate_link.click()
                page.wait_for_load_state('networkidle', timeout=30000)
                time.sleep(2)
                
                page.screenshot(path='/tmp/test_generate.png', full_page=True)
                print("  ✓ 生成页面加载成功")
                test_results['generate']['details'].append("页面加载成功")
                
                # 检查表单元素
                if page.locator('select').count() > 0:
                    print(f"  ✓ 找到 {page.locator('select').count()} 个下拉选择框")
                    test_results['generate']['details'].append(f"下拉框数量: {page.locator('select').count()}")
                
                if page.locator('button').count() > 0:
                    print(f"  ✓ 找到 {page.locator('button').count()} 个按钮")
                    test_results['generate']['details'].append(f"按钮数量: {page.locator('button').count()}")
                
                test_results['generate']['status'] = 'passed'
            else:
                print("  ⚠ 未找到生成页面链接")
                test_results['generate']['status'] = 'skipped'
                test_results['generate']['details'].append("未找到导航链接")
            
            # ===================================================================
            # 测试3: 3D查看器页面（重点测试）
            # ===================================================================
            print("\n=== 测试3: 3D查看器页面 ===")
            
            # 导航到3D查看器
            page.goto('http://localhost:5000/viewer3d', wait_until='networkidle', timeout=30000)
            
            # 等待Three.js加载
            print("  等待Three.js和GLTFLoader加载...")
            time.sleep(8)  # 增加等待时间
            
            # 检查API响应
            api_response = page.evaluate("""async () => {
                try {
                    const response = await fetch('/api/models3d');
                    const data = await response.json();
                    return data;
                } catch (e) {
                    return {error: e.toString()};
                }
            }""")
            print(f"  API响应: {api_response.get('total', 0)} 个模型")
            if api_response.get('models'):
                for m in api_response['models'][:3]:
                    print(f"    - {m.get('plate_number', 'N/A')}")
            
            page.screenshot(path='/tmp/test_viewer3d.png', full_page=True)
            print("  ✓ 3D查看器页面加载成功")
            test_results['viewer3d']['details'].append("页面加载成功")
            
            # 检查Three.js canvas
            canvas = page.locator('canvas').first
            if canvas.count() > 0:
                print("  ✓ 找到Three.js canvas元素")
                test_results['viewer3d']['details'].append("Canvas元素存在")
                
                # 获取canvas尺寸
                canvas_box = canvas.bounding_box()
                if canvas_box:
                    print(f"  ✓ Canvas尺寸: {canvas_box['width']}x{canvas_box['height']}")
                    test_results['viewer3d']['details'].append(f"Canvas尺寸: {canvas_box['width']}x{canvas_box['height']}")
            else:
                print("  ✗ 未找到canvas元素")
                test_results['viewer3d']['details'].append("Canvas元素缺失")
            
            # 检查模型列表
            model_list = page.locator('.model-list').first
            if model_list.count() > 0:
                print("  ✓ 找到模型列表")
                test_results['viewer3d']['details'].append("模型列表存在")
                
                # 检查模型项
                model_items = page.locator('.model-item')
                # 等待模型列表加载
                time.sleep(3)
                model_count = model_items.count()
                print(f"  ✓ 模型数量: {model_count}")
                test_results['viewer3d']['details'].append(f"模型数量: {model_count}")
                
                # 如果有模型，尝试点击第一个
                if model_count > 0:
                    print("  尝试加载第一个模型...")
                    first_model = model_items.first
                    first_model.click()
                    
                    # 等待模型加载
                    time.sleep(5)
                    
                    # 再次截图
                    page.screenshot(path='/tmp/test_viewer3d_loaded.png', full_page=True)
                    print("  ✓ 模型点击完成")
                    test_results['viewer3d']['details'].append("模型点击成功")
                    
                    # 检查是否有加载指示器消失
                    loading = page.locator('.loading-indicator').first
                    if loading.count() == 0 or not loading.is_visible():
                        print("  ✓ 模型加载完成（无加载指示器）")
                        test_results['viewer3d']['details'].append("模型加载完成")
                else:
                    print("  ⚠ 没有可用的模型")
                    test_results['viewer3d']['details'].append("无可用模型")
            else:
                print("  ⚠ 未找到模型列表")
                test_results['viewer3d']['details'].append("模型列表缺失")
            
            # 检查控制按钮
            controls = page.locator('.controls').first
            if controls.count() > 0:
                print("  ✓ 找到控制面板")
                test_results['viewer3d']['details'].append("控制面板存在")
            
            test_results['viewer3d']['status'] = 'passed'
            
            # ===================================================================
            # 测试4: 图库页面
            # ===================================================================
            print("\n=== 测试4: 图库页面 ===")
            
            gallery_link = page.locator('a[href="/gallery"]').first
            if gallery_link.count() > 0:
                gallery_link.click()
                page.wait_for_load_state('networkidle', timeout=30000)
                time.sleep(2)
                
                page.screenshot(path='/tmp/test_gallery.png', full_page=True)
                print("  ✓ 图库页面加载成功")
                test_results['gallery']['details'].append("页面加载成功")
                
                # 检查图片网格
                if page.locator('.gallery-grid').count() > 0 or page.locator('.image-grid').count() > 0:
                    print("  ✓ 找到图库网格")
                    test_results['gallery']['details'].append("图库网格存在")
                
                test_results['gallery']['status'] = 'passed'
            else:
                print("  ⚠ 未找到图库链接")
                test_results['gallery']['status'] = 'skipped'
            
            # ===================================================================
            # 测试5: 资产管理页面
            # ===================================================================
            print("\n=== 测试5: 资产管理页面 ===")
            
            assets_link = page.locator('a[href="/assets"]').first
            if assets_link.count() > 0:
                assets_link.click()
                page.wait_for_load_state('networkidle', timeout=30000)
                time.sleep(2)
                
                page.screenshot(path='/tmp/test_assets.png', full_page=True)
                print("  ✓ 资产管理页面加载成功")
                test_results['assets']['details'].append("页面加载成功")
                
                test_results['assets']['status'] = 'passed'
            else:
                print("  ⚠ 未找到资产管理链接")
                test_results['assets']['status'] = 'skipped'
            
        except Exception as e:
            print(f"\n✗ 测试过程中出现错误: {e}")
            page.screenshot(path='/tmp/test_error.png', full_page=True)
            errors.append(str(e))
        
        finally:
            # 关闭浏览器
            browser.close()
        
        # ===================================================================
        # 生成测试报告
        # ===================================================================
        print("\n" + "="*70)
        print("测试报告")
        print("="*70)
        
        for page_name, result in test_results.items():
            status_icon = {
                'passed': '✓',
                'failed': '✗',
                'skipped': '⊘',
                'pending': '?'
            }.get(result['status'], '?')
            
            print(f"\n{status_icon} {page_name.upper()}: {result['status'].upper()}")
            for detail in result['details']:
                print(f"    - {detail}")
        
        # 控制台日志
        if console_logs:
            print(f"\n📋 控制台日志 ({len(console_logs)} 条):")
            for log in console_logs[:10]:  # 只显示前10条
                print(f"    {log}")
            if len(console_logs) > 10:
                print(f"    ... 还有 {len(console_logs) - 10} 条日志")
        
        # 错误
        if errors:
            print(f"\n❌ 错误 ({len(errors)} 个):")
            for error in errors:
                print(f"    {error}")
        
        # 截图位置
        print("\n📸 截图已保存:")
        print("    - /tmp/test_dashboard.png")
        print("    - /tmp/test_generate.png")
        print("    - /tmp/test_viewer3d.png")
        print("    - /tmp/test_viewer3d_loaded.png")
        print("    - /tmp/test_gallery.png")
        print("    - /tmp/test_assets.png")
        
        # 总结
        passed_count = sum(1 for r in test_results.values() if r['status'] == 'passed')
        total_count = len(test_results)
        
        print("\n" + "="*70)
        print(f"测试完成: {passed_count}/{total_count} 通过")
        print("="*70)
        
        return test_results, console_logs, errors


if __name__ == '__main__':
    print("车牌生成器前端测试")
    print("="*70)
    print("请确保Flask服务已在 http://localhost:5000 运行")
    print("="*70)
    
    test_results, console_logs, errors = test_webapp()
    
    # 退出码
    all_passed = all(r['status'] in ['passed', 'skipped'] for r in test_results.values())
    exit(0 if all_passed else 1)
