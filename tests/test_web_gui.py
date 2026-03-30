"""
Web GUI 自动化测试

使用 Playwright 对 Web 图形界面进行端到端测试。
"""

import pytest
import time
import subprocess
import sys
import os

# 检查 Playwright 是否可用，不可用时跳过整个模块
pytest.importorskip("playwright")

# 设置项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(scope="module")
def server():
    """启动Web服务器"""
    # 启动Flask服务器
    process = subprocess.Popen(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, '.'); from web_gui.app import app; app.run(host='127.0.0.1', port=5001, debug=False)"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # 等待服务器启动
    time.sleep(3)

    yield "http://127.0.0.1:5001"

    # 清理
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


class TestWebGUI:
    """Web GUI 测试类"""

    def test_page_load(self, playwright, server):
        """测试页面加载"""
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # 访问首页
            page.goto(server)
            page.wait_for_load_state("networkidle")

            # 验证页面标题
            assert "合成计算器" in page.title()

            # 验证导航栏存在
            assert page.locator(".navbar").is_visible()
            assert page.locator(".navbar-brand").is_visible()

            # 验证侧边栏导航存在
            assert page.locator(".sidebar").is_visible()

            # 验证主内容区域存在
            assert page.locator(".main-content").is_visible()

        finally:
            browser.close()

    def test_navigation(self, playwright, server):
        """测试导航功能"""
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(server)
            page.wait_for_load_state("networkidle")

            # 测试导航到选择配方页面
            page.click("text=选择配方")
            page.wait_for_load_state("networkidle")
            assert "/select-game" in page.url

            # 测试导航到计算页面
            page.click("text=计算生产链")
            page.wait_for_load_state("networkidle")
            assert "/calculate" in page.url

            # 测试导航到配方管理页面
            page.click("text=配方管理")
            page.wait_for_load_state("networkidle")
            assert "/recipe-management" in page.url

            # 测试返回首页
            page.click("text=首页")
            page.wait_for_load_state("networkidle")
            assert page.url == server + "/" or page.url == server

        finally:
            browser.close()

    def test_select_game_page(self, playwright, server):
        """测试配方选择页面"""
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(f"{server}/select-game")
            page.wait_for_load_state("networkidle")

            # 验证页面标题
            assert "选择配方" in page.title()

            # 验证搜索框存在
            assert page.locator("#gameSearch").is_visible()

            # 验证配方卡片网格存在
            assert page.locator("#gamesGrid").is_visible()

        finally:
            browser.close()

    def test_calculate_page_structure(self, playwright, server):
        """测试计算页面结构"""
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(f"{server}/calculate")
            page.wait_for_load_state("networkidle")

            # 验证页面标题
            assert "计算生产链" in page.title()

            # 验证表单元素存在（如果已选择配方文件）
            if page.locator("#calculateForm").is_visible():
                assert page.locator("#targetItem").is_visible()
                assert page.locator("#targetRate").is_visible()

                # 验证计算按钮存在
                assert page.locator("button[type='submit']").is_visible()

        finally:
            browser.close()

    def test_recipe_management_page_structure(self, playwright, server):
        """测试配方管理页面结构"""
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(f"{server}/recipe-management")
            page.wait_for_load_state("networkidle")

            # 验证页面标题
            assert "配方管理" in page.title()

            # 验证搜索框存在
            assert page.locator("#recipeSearch").is_visible()

            # 验证添加配方按钮存在
            assert page.locator("#addRecipeBtn").is_visible()

            # 验证表格存在（如果已选择配方文件）
            if page.locator("#recipeTable").is_visible():
                assert page.locator("#recipeTable thead").is_visible()

        finally:
            browser.close()

    def test_responsive_design(self, playwright, server):
        """测试响应式设计"""
        browser = playwright.chromium.launch(headless=True)

        viewports = [
            {"width": 1920, "height": 1080, "name": "desktop"},
            {"width": 1024, "height": 768, "name": "tablet"},
            {"width": 375, "height": 667, "name": "mobile"},
        ]

        for viewport in viewports:
            page = browser.new_page(
                viewport={"width": viewport["width"], "height": viewport["height"]})

            try:
                page.goto(server)
                page.wait_for_load_state("networkidle")

                # 验证页面可以正常加载
                assert page.locator(".navbar").is_visible()
                assert page.locator(".main-content").is_visible()

                # 移动端验证底部导航
                if viewport["width"] < 768:
                    assert page.locator(".bottom-nav").is_visible()

            finally:
                page.close()

        browser.close()

    def test_api_endpoints(self, playwright, server):
        """测试API端点"""
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # 测试获取配方文件列表
            response = page.evaluate("""
                async () => {
                    const res = await fetch('/api/games');
                    return res.json();
                }
            """)
            assert response["success"] is True
            assert "games" in response

            # 测试获取物品列表（可能失败如果没有选择配方文件）
            response = page.evaluate("""
                async () => {
                    const res = await fetch('/api/items');
                    return res.json();
                }
            """)
            # 这个请求可能成功也可能失败，取决于是否有选择配方文件
            assert "success" in response

        finally:
            browser.close()

    def test_ui_interactions(self, playwright, server):
        """测试UI交互"""
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(server)
            page.wait_for_load_state("networkidle")

            # 测试Toast通知系统（通过JavaScript触发）
            page.evaluate("""
                showToast('测试标题', '测试消息', 'info');
            """)

            # 验证Toast出现
            assert page.locator(".toast").is_visible()
            assert "测试标题" in page.locator(".toast-title").text_content()

            # 测试加载遮罩
            page.evaluate("""
                showLoading();
            """)
            assert page.locator("#loadingOverlay").is_visible()

            page.evaluate("""
                hideLoading();
            """)
            # 给一点时间让动画完成
            page.wait_for_timeout(500)
            assert not page.locator("#loadingOverlay").is_visible()

        finally:
            browser.close()


class TestAccessibility:
    """可访问性测试"""

    def test_keyboard_navigation(self, playwright, server):
        """测试键盘导航"""
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(server)
            page.wait_for_load_state("networkidle")

            # 测试Tab键导航
            page.keyboard.press("Tab")

            # 验证某个元素获得了焦点
            active_element = page.evaluate(
                "() => document.activeElement.tagName")
            assert active_element != "BODY"  # 焦点应该不在body上

        finally:
            browser.close()

    def test_aria_labels(self, playwright, server):
        """测试ARIA标签"""
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(server)
            page.wait_for_load_state("networkidle")

            # 验证导航按钮有正确的aria-label
            navbar_toggle = page.locator("#navbarToggle")
            if navbar_toggle.is_visible():
                aria_label = navbar_toggle.get_attribute("aria-label")
                assert aria_label is not None
                assert len(aria_label) > 0

        finally:
            browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
