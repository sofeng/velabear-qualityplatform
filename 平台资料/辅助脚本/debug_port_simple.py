"""
简化版调试脚本 - 检查DOM结构
"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context()
        page = await context.new_page()

        # 访问页面
        print("Accessing visual flow editor...")
        await page.goto("http://127.0.0.1:3000/manual-testcases/visual-flow")
        await page.wait_for_timeout(5000)

        # 截图
        await page.screenshot(path="visual_flow_page.png")
        print("Screenshot saved")

        # 获取页面上所有可点击按钮
        buttons = await page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('button, .el-button'));
                return btns.map(btn => btn.textContent.trim()).filter(t => t).slice(0, 20);
            }
        """)
        print(f"Buttons found: {buttons}")

        # 检查是否有画布
        canvas_exists = await page.evaluate("""
            () => {
                return !!document.querySelector('.x6-graph, canvas, svg[class*=graph]');
            }
        """)
        print(f"Canvas exists: {canvas_exists}")

        # 检查是否有节点工具栏或侧边栏
        toolbar = await page.evaluate("""
            () => {
                const selectors = ['.node-toolbar', '.stencil', '.dnd-panel', '[class*=stencil]', '[class*=palette]'];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) return {selector: sel, text: el.textContent.substring(0, 100)};
                }
                return null;
            }
        """)
        print(f"Toolbar: {toolbar}")

        # 保持打开
        print("Browser will stay open for 60 seconds...")
        await page.wait_for_timeout(60000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
