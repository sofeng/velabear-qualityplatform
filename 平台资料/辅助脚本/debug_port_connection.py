"""
调试可视化流程编辑器的端口连线问题
"""
import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context()
        page = await context.new_page()

        # 监听控制台日志
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        # 访问可视化流程编辑器
        print("访问可视化流程编辑器...")
        await page.goto("http://127.0.0.1:3000/manual-testcases/visual-flow")
        await page.wait_for_timeout(3000)

        # 检查页面是否加载成功
        title = await page.title()
        print(f"页面标题: {title}")

        # 添加页面节点
        print("\n添加页面节点...")
        try:
            # 查找"页面节点"按钮
            page_node_btn = page.locator('text=页面节点').first
            await page_node_btn.click()
            await page.wait_for_timeout(2000)
            print("✓ 页面节点已添加")
        except Exception as e:
            print(f"✗ 添加页面节点失败: {e}")

        # 获取页面节点列表
        print("\n获取页面节点ID...")
        node_ids = await page.evaluate("""
            () => {
                if (window.listPageNodes) {
                    return window.listPageNodes();
                }
                return [];
            }
        """)
        print(f"页面节点: {node_ids}")

        if node_ids and len(node_ids) > 0:
            node_id = node_ids[0]

            # 检查节点的 SVG 结构
            print(f"\n检查节点 {node_id} 的SVG结构...")
            structure = await page.evaluate(f"""
                () => {{
                    if (window.inspectNodeStructure) {{
                        return window.inspectNodeStructure('{node_id}');
                    }}
                    return null;
                }}
            """)

            # 获取节点的端口信息
            print(f"\n获取节点 {node_id} 的端口信息...")
            await page.evaluate(f"""
                () => {{
                    if (window.debugPorts) {{
                        window.debugPorts('{node_id}');
                    }}
                }}
            """)
            await page.wait_for_timeout(1000)

            # 选择页面节点（点击它）
            print("\n点击页面节点...")
            await page.evaluate(f"""
                () => {{
                    const nodeEl = document.querySelector('[data-cell-id="{node_id}"]');
                    if (nodeEl) {{
                        const rect = nodeEl.getBoundingClientRect();
                        const clickEvent = new MouseEvent('click', {{
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            clientX: rect.left + rect.width / 2,
                            clientY: rect.top + rect.height / 2
                        }});
                        nodeEl.dispatchEvent(clickEvent);
                    }}
                }}
            """)
            await page.wait_for_timeout(1000)

            # 检查是否弹出了节点详情
            try:
                detail_panel = page.locator('.node-detail-drawer, .el-drawer').first
                is_visible = await detail_panel.is_visible(timeout=2000)
                if is_visible:
                    print("✓ 节点详情面板已弹出")
                else:
                    print("✗ 节点详情面板未弹出")
            except:
                print("✗ 节点详情面板未找到")

            # 在页面节点内添加组件（如果有添加组件的功能）
            print("\n尝试添加组件...")
            # 这里需要根据实际UI操作

        # 打印所有控制台日志
        print("\n=== 控制台日志 ===")
        for log in console_logs[-50:]:  # 只显示最后50条
            print(log)

        # 检查页面上的端口元素
        print("\n=== 检查端口DOM元素 ===")
        port_info = await page.evaluate("""
            () => {
                const ports = document.querySelectorAll('[port]');
                return Array.from(ports).map(port => ({
                    id: port.getAttribute('port'),
                    group: port.getAttribute('port-group'),
                    magnet: port.getAttribute('magnet'),
                    tagName: port.tagName,
                    visible: port.getBoundingClientRect().width > 0,
                    pointerEvents: window.getComputedStyle(port).pointerEvents,
                    zIndex: window.getComputedStyle(port).zIndex
                }));
            }
        """)
        print(f"找到 {len(port_info)} 个端口:")
        for i, port in enumerate(port_info[:10]):  # 只显示前10个
            print(f"  [{i}] {port['id']}: group={port['group']}, magnet={port['magnet']}, "
                  f"visible={port['visible']}, pointerEvents={port['pointerEvents']}")

        # 保持浏览器打开以便手动检查
        print("\n浏览器保持打开，按 Ctrl+C 退出...")
        try:
            await page.wait_for_timeout(300000)  # 保持5分钟
        except KeyboardInterrupt:
            print("退出...")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
