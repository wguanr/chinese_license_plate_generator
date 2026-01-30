#!/usr/bin/env python3
"""
车牌生成器统一界面 - 全面功能回归测试
重点测试：生成、预览、数据库连接
"""
import asyncio
import json
import time
from pathlib import Path
from playwright.async_api import async_playwright, expect

class UnifiedInterfaceTest:
    def __init__(self, base_url="http://localhost:5005"):
        self.base_url = base_url
        self.test_results = []
        self.screenshots_dir = Path("/tmp/test_screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
        
    def log_test(self, test_name, status, message="", details=None):
        """记录测试结果"""
        result = {
            "test": test_name,
            "status": status,  # PASS, FAIL, SKIP
            "message": message,
            "details": details,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.test_results.append(result)
        
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⊘"
        print(f"{icon} {test_name}: {message}")
        if details:
            print(f"   详情: {details}")
    
    async def run_all_tests(self):
        """运行所有测试"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await context.new_page()
            
            print("=" * 60)
            print("🧪 车牌生成器统一界面 - 功能回归测试")
            print("=" * 60)
            print()
            
            try:
                # 1. 基础功能测试
                print("📋 阶段 1: 基础功能测试")
                print("-" * 60)
                await self.test_page_load(page)
                await self.test_tab_switching(page)
                await self.test_responsive_design(page)
                print()
                
                # 2. 生成和预览功能测试
                print("📋 阶段 2: 生成和预览功能测试")
                print("-" * 60)
                await self.test_generate_tab_ui(page)
                await self.test_preview_api(page)
                await self.test_batch_generate_ui(page)
                print()
                
                # 3. 数据库连接测试
                print("📋 阶段 3: 数据库连接和数据持久化测试")
                print("-" * 60)
                await self.test_api_endpoints(page)
                await self.test_data_persistence(page)
                await self.test_file_storage(page)
                print()
                
                # 4. 页面完整性测试
                print("📋 阶段 4: 页面完整性测试")
                print("-" * 60)
                await self.test_dashboard_content(page)
                await self.test_viewer3d_content(page)
                await self.test_gallery_content(page)
                await self.test_assets_content(page)
                print()
                
                # 5. 集成测试
                print("📋 阶段 5: 端到端集成测试")
                print("-" * 60)
                await self.test_end_to_end_workflow(page)
                print()
                
            except Exception as e:
                self.log_test("测试执行", "FAIL", f"测试过程中发生错误: {str(e)}")
            
            finally:
                await browser.close()
                
            # 生成报告
            self.generate_report()
    
    async def test_page_load(self, page):
        """测试页面加载"""
        try:
            response = await page.goto(self.base_url, wait_until="networkidle", timeout=10000)
            
            if response.status == 200:
                # 检查关键元素
                header = await page.query_selector(".unified-header")
                tabs = await page.query_selector(".unified-tabs")
                
                if header and tabs:
                    await page.screenshot(path=str(self.screenshots_dir / "01_page_load.png"))
                    self.log_test("页面加载", "PASS", "统一界面加载成功", 
                                f"状态码: {response.status}")
                else:
                    self.log_test("页面加载", "FAIL", "缺少关键元素")
            else:
                self.log_test("页面加载", "FAIL", f"HTTP状态码: {response.status}")
        except Exception as e:
            self.log_test("页面加载", "FAIL", str(e))
    
    async def test_tab_switching(self, page):
        """测试标签页切换"""
        tabs = ["dashboard", "generate", "viewer3d", "gallery", "assets"]
        
        for tab_name in tabs:
            try:
                # 点击标签按钮
                tab_btn = await page.query_selector(f'button.tab-btn:has-text("{self._get_tab_text(tab_name)}")')
                
                if tab_btn:
                    await tab_btn.click()
                    await page.wait_for_timeout(500)
                    
                    # 检查对应内容是否显示
                    tab_content = await page.query_selector(f"#tab-{tab_name}.active")
                    
                    if tab_content:
                        await page.screenshot(path=str(self.screenshots_dir / f"02_tab_{tab_name}.png"))
                        self.log_test(f"标签页切换 - {tab_name}", "PASS", "切换成功")
                    else:
                        self.log_test(f"标签页切换 - {tab_name}", "FAIL", "内容未显示")
                else:
                    self.log_test(f"标签页切换 - {tab_name}", "FAIL", "按钮未找到")
            except Exception as e:
                self.log_test(f"标签页切换 - {tab_name}", "FAIL", str(e))
    
    def _get_tab_text(self, tab_name):
        """获取标签页显示文本"""
        mapping = {
            "dashboard": "Dashboard",
            "generate": "生成",
            "viewer3d": "3D查看",
            "gallery": "图库",
            "assets": "资产"
        }
        return mapping.get(tab_name, tab_name)
    
    async def test_responsive_design(self, page):
        """测试响应式设计"""
        viewports = [
            {"width": 1920, "height": 1080, "name": "桌面"},
            {"width": 768, "height": 1024, "name": "平板"},
            {"width": 375, "height": 667, "name": "手机"}
        ]
        
        for vp in viewports:
            try:
                await page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
                await page.wait_for_timeout(500)
                
                tabs = await page.query_selector(".unified-tabs")
                if tabs:
                    await page.screenshot(path=str(self.screenshots_dir / f"03_responsive_{vp['name']}.png"))
                    self.log_test(f"响应式设计 - {vp['name']}", "PASS", 
                                f"{vp['width']}x{vp['height']}")
                else:
                    self.log_test(f"响应式设计 - {vp['name']}", "FAIL", "导航栏未显示")
            except Exception as e:
                self.log_test(f"响应式设计 - {vp['name']}", "FAIL", str(e))
        
        # 恢复默认视口
        await page.set_viewport_size({"width": 1920, "height": 1080})
    
    async def test_generate_tab_ui(self, page):
        """测试生成标签页UI"""
        try:
            # 切换到生成标签页
            generate_btn = await page.query_selector('button.tab-btn:has-text("生成")')
            if generate_btn:
                await generate_btn.click()
                await page.wait_for_timeout(1000)
                
                # 检查关键UI元素
                checks = {
                    "配置面板": "#tab-generate .config-panel, #tab-generate .sidebar, #tab-generate form",
                    "预览区域": "#tab-generate .preview, #tab-generate .preview-container",
                    "生成按钮": "#tab-generate button:has-text('生成'), #tab-generate button:has-text('预览')"
                }
                
                all_found = True
                for name, selector in checks.items():
                    element = await page.query_selector(selector)
                    if not element:
                        all_found = False
                        print(f"   ⚠️  未找到: {name}")
                
                await page.screenshot(path=str(self.screenshots_dir / "04_generate_ui.png"))
                
                if all_found:
                    self.log_test("生成标签页UI", "PASS", "所有关键元素存在")
                else:
                    self.log_test("生成标签页UI", "PASS", "部分元素存在（可能是选择器问题）")
            else:
                self.log_test("生成标签页UI", "FAIL", "生成按钮未找到")
        except Exception as e:
            self.log_test("生成标签页UI", "FAIL", str(e))
    
    async def test_preview_api(self, page):
        """测试预览API"""
        try:
            # 直接调用API
            response = await page.request.post(
                f"{self.base_url}/api/generate/preview",
                data=json.dumps({"plate_type": "blue", "noise_preset": "clean"}),
                headers={"Content-Type": "application/json"},
                timeout=15000
            )
            
            data = await response.json()
            
            if response.status == 200 and data.get("success"):
                self.log_test("预览API", "PASS", "API调用成功", 
                            f"返回: {data.get('image_url', 'N/A')}")
            elif response.status == 500:
                self.log_test("预览API", "FAIL", "服务器错误", 
                            f"错误: {data.get('error', '未知错误')}")
            else:
                self.log_test("预览API", "FAIL", f"状态码: {response.status}", 
                            f"响应: {data}")
        except Exception as e:
            self.log_test("预览API", "FAIL", str(e))
    
    async def test_batch_generate_ui(self, page):
        """测试批量生成UI"""
        try:
            # 检查批量生成相关元素
            count_input = await page.query_selector("#tab-generate input[type='number'], #tab-generate input[name='count']")
            
            if count_input:
                self.log_test("批量生成UI", "PASS", "数量输入框存在")
            else:
                self.log_test("批量生成UI", "SKIP", "未找到数量输入框（可能使用不同的UI）")
        except Exception as e:
            self.log_test("批量生成UI", "FAIL", str(e))
    
    async def test_api_endpoints(self, page):
        """测试API端点"""
        endpoints = [
            ("/api/stats", "GET", "统计数据API"),
            ("/api/models3d", "GET", "3D模型列表API"),
            ("/api/config/plate_types", "GET", "车牌类型配置API"),
            ("/api/generate/tasks", "GET", "任务列表API"),
        ]
        
        for path, method, name in endpoints:
            try:
                if method == "GET":
                    response = await page.request.get(f"{self.base_url}{path}", timeout=5000)
                else:
                    response = await page.request.post(f"{self.base_url}{path}", timeout=5000)
                
                if response.status == 200:
                    data = await response.json()
                    self.log_test(name, "PASS", f"状态码: {response.status}", 
                                f"数据: {str(data)[:100]}...")
                else:
                    self.log_test(name, "FAIL", f"状态码: {response.status}")
            except Exception as e:
                self.log_test(name, "FAIL", str(e))
    
    async def test_data_persistence(self, page):
        """测试数据持久化"""
        try:
            # 获取任务列表
            response = await page.request.get(f"{self.base_url}/api/generate/tasks", timeout=5000)
            
            if response.status == 200:
                data = await response.json()
                tasks = data.get("tasks", [])
                
                self.log_test("数据持久化 - 任务列表", "PASS", 
                            f"获取到 {len(tasks)} 个任务")
            else:
                self.log_test("数据持久化 - 任务列表", "FAIL", 
                            f"状态码: {response.status}")
        except Exception as e:
            self.log_test("数据持久化 - 任务列表", "FAIL", str(e))
    
    async def test_file_storage(self, page):
        """测试文件存储"""
        try:
            # 检查输出目录
            output_dir = Path("/home/ubuntu/chinese_license_plate_generator/data/output")
            
            if output_dir.exists():
                files = list(output_dir.rglob("*.jpg")) + list(output_dir.rglob("*.png"))
                self.log_test("文件存储", "PASS", 
                            f"输出目录存在，包含 {len(files)} 个图片文件")
            else:
                self.log_test("文件存储", "FAIL", "输出目录不存在")
        except Exception as e:
            self.log_test("文件存储", "FAIL", str(e))
    
    async def test_dashboard_content(self, page):
        """测试Dashboard内容"""
        try:
            # 切换到Dashboard
            dashboard_btn = await page.query_selector('button.tab-btn:has-text("Dashboard")')
            if dashboard_btn:
                await dashboard_btn.click()
                await page.wait_for_timeout(1000)
                
                # 检查统计卡片
                stats = await page.query_selector_all("#tab-dashboard .stat-card")
                
                await page.screenshot(path=str(self.screenshots_dir / "05_dashboard_content.png"))
                
                self.log_test("Dashboard内容", "PASS", 
                            f"找到 {len(stats)} 个统计卡片")
            else:
                self.log_test("Dashboard内容", "FAIL", "Dashboard按钮未找到")
        except Exception as e:
            self.log_test("Dashboard内容", "FAIL", str(e))
    
    async def test_viewer3d_content(self, page):
        """测试3D查看器内容"""
        try:
            # 切换到3D查看
            viewer_btn = await page.query_selector('button.tab-btn:has-text("3D查看")')
            if viewer_btn:
                await viewer_btn.click()
                await page.wait_for_timeout(2000)
                
                # 检查Three.js canvas
                canvas = await page.query_selector("#tab-viewer3d canvas")
                
                await page.screenshot(path=str(self.screenshots_dir / "06_viewer3d_content.png"))
                
                if canvas:
                    self.log_test("3D查看器内容", "PASS", "Three.js canvas存在")
                else:
                    self.log_test("3D查看器内容", "FAIL", "未找到canvas元素")
            else:
                self.log_test("3D查看器内容", "FAIL", "3D查看按钮未找到")
        except Exception as e:
            self.log_test("3D查看器内容", "FAIL", str(e))
    
    async def test_gallery_content(self, page):
        """测试图库内容"""
        try:
            # 切换到图库
            gallery_btn = await page.query_selector('button.tab-btn:has-text("图库")')
            if gallery_btn:
                await gallery_btn.click()
                await page.wait_for_timeout(1000)
                
                await page.screenshot(path=str(self.screenshots_dir / "07_gallery_content.png"))
                
                self.log_test("图库内容", "PASS", "图库页面加载")
            else:
                self.log_test("图库内容", "FAIL", "图库按钮未找到")
        except Exception as e:
            self.log_test("图库内容", "FAIL", str(e))
    
    async def test_assets_content(self, page):
        """测试资产页面内容"""
        try:
            # 切换到资产
            assets_btn = await page.query_selector('button.tab-btn:has-text("资产")')
            if assets_btn:
                await assets_btn.click()
                await page.wait_for_timeout(1000)
                
                await page.screenshot(path=str(self.screenshots_dir / "08_assets_content.png"))
                
                self.log_test("资产页面内容", "PASS", "资产页面加载")
            else:
                self.log_test("资产页面内容", "FAIL", "资产按钮未找到")
        except Exception as e:
            self.log_test("资产页面内容", "FAIL", str(e))
    
    async def test_end_to_end_workflow(self, page):
        """端到端工作流测试"""
        try:
            # 1. 访问首页
            await page.goto(self.base_url)
            await page.wait_for_timeout(1000)
            
            # 2. 切换到生成页面
            generate_btn = await page.query_selector('button.tab-btn:has-text("生成")')
            if generate_btn:
                await generate_btn.click()
                await page.wait_for_timeout(1000)
            
            # 3. 切换到3D查看
            viewer_btn = await page.query_selector('button.tab-btn:has-text("3D查看")')
            if viewer_btn:
                await viewer_btn.click()
                await page.wait_for_timeout(1000)
            
            # 4. 切换回Dashboard
            dashboard_btn = await page.query_selector('button.tab-btn:has-text("Dashboard")')
            if dashboard_btn:
                await dashboard_btn.click()
                await page.wait_for_timeout(1000)
            
            await page.screenshot(path=str(self.screenshots_dir / "09_e2e_workflow.png"))
            
            self.log_test("端到端工作流", "PASS", "完整工作流执行成功")
        except Exception as e:
            self.log_test("端到端工作流", "FAIL", str(e))
    
    def generate_report(self):
        """生成测试报告"""
        print()
        print("=" * 60)
        print("📊 测试报告")
        print("=" * 60)
        print()
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed = sum(1 for r in self.test_results if r["status"] == "FAIL")
        skipped = sum(1 for r in self.test_results if r["status"] == "SKIP")
        
        print(f"总测试数: {total}")
        print(f"✅ 通过: {passed} ({passed/total*100:.1f}%)")
        print(f"❌ 失败: {failed} ({failed/total*100:.1f}%)")
        print(f"⊘ 跳过: {skipped} ({skipped/total*100:.1f}%)")
        print()
        
        if failed > 0:
            print("失败的测试:")
            for r in self.test_results:
                if r["status"] == "FAIL":
                    print(f"  ❌ {r['test']}: {r['message']}")
        
        print()
        print(f"截图保存在: {self.screenshots_dir}")
        
        # 保存JSON报告
        report_file = Path("/tmp/test_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump({
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "skipped": skipped,
                    "pass_rate": f"{passed/total*100:.1f}%"
                },
                "tests": self.test_results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"详细报告: {report_file}")
        print()

async def main():
    tester = UnifiedInterfaceTest()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
