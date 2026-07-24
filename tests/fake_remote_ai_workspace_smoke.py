import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = os.environ.get("FAKE_REMOTE_BASE_URL", "http://localhost:51080")
USERNAME = os.environ.get("FAKE_REMOTE_USERNAME", "admin")
PASSWORD = os.environ.get("FAKE_REMOTE_PASSWORD", "admin123")
OUTPUT_PATH = Path(os.environ.get("FAKE_REMOTE_SMOKE_OUTPUT", "logs/fake-remote-ai-workspace-smoke.json"))


def normalize_text(text: str) -> str:
    return " ".join((text or "").split())


def body_preview(page) -> str:
    return normalize_text(page.locator("body").inner_text(timeout=15000))[:1600]


def login(page) -> None:
    page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")
    page.locator("input").nth(0).fill(USERNAME)
    page.locator("input").nth(1).fill(PASSWORD)
    page.locator(".login-button").click()
    page.wait_for_url("**/home", timeout=30000)


def pick_select_option(page, label_text: str, option_text: str) -> None:
    form_item = page.locator(".el-form-item").filter(has_text=label_text).first
    form_item.locator(".el-select").click()
    dropdown = page.locator(".el-select-dropdown:visible").last
    dropdown.wait_for(timeout=15000)
    option = dropdown.locator(".el-select-dropdown__item").filter(has_text=option_text).first
    option.wait_for(timeout=15000)
    option.click()


def collect_page(page, key: str, url: str) -> dict:
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    return {
        "key": key,
        "url": url,
        "preview": body_preview(page),
    }


def validate_ai_environment_linkage(page) -> dict:
    page.goto(f"{BASE_URL}/ai-generation/list?tab=ai-conversations", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="新建 AI 开发环境").click()
    page.get_by_text("新建 AI 开发环境").last.wait_for(timeout=15000)

    pick_select_option(page, "所属项目", "AIOps")
    pick_select_option(page, "AI开发环境配置", "AIOps-testhub-fake-remote开发环境")
    pick_select_option(page, "AI开发项目配置", "AIOps-本地路径项目配置")
    page.get_by_placeholder("请输入新环境名称").fill("AIOps-fake-remote-联调校验")
    page.get_by_role("button", name="校验链路").click()

    page.get_by_text("联动校验结果").wait_for(timeout=30000)
    page.get_by_text("可继续").wait_for(timeout=30000)

    dialog_preview = body_preview(page)
    page.get_by_role("button", name="取消").click()
    return {
        "dialog_preview": dialog_preview,
        "checks": {
            "validation_card_visible": "联动校验结果" in dialog_preview,
            "validation_ready": "可继续" in dialog_preview,
            "ops_ready": "AI运维：就绪" in dialog_preview,
            "conversation_ready": "AI会话：就绪" in dialog_preview,
            "requirement_ready": "需求联动：就绪" in dialog_preview,
            "testing_ready": "测试联动：就绪" in dialog_preview,
            "defect_ready": "AI缺陷联动：就绪" in dialog_preview,
            "build_ready": "构建命令：就绪" in dialog_preview,
        },
    }


def main() -> int:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 960})

        login(page)

        results = {
            "base_url": BASE_URL,
            "pages": [],
            "checks": {},
        }

        pages = [
            ("ai_conversations", f"{BASE_URL}/ai-generation/list?tab=ai-conversations"),
            ("ai_dev_runtime_configs", f"{BASE_URL}/ai-generation/list?tab=ai-dev-runtime-configs"),
            ("ai_dev_configs", f"{BASE_URL}/ai-generation/list?tab=ai-dev-configs"),
        ]

        for key, url in pages:
            results["pages"].append(collect_page(page, key, url))

        runtime_preview = next(item["preview"] for item in results["pages"] if item["key"] == "ai_dev_runtime_configs")
        config_preview = next(item["preview"] for item in results["pages"] if item["key"] == "ai_dev_configs")
        conversation_preview = next(item["preview"] for item in results["pages"] if item["key"] == "ai_conversations")
        linkage_validation = validate_ai_environment_linkage(page)
        results["linkage_validation"] = linkage_validation

        results["checks"] = {
            "conversation_page_loaded": "AI会话" in conversation_preview,
            "conversation_launch_button_visible": "新建 AI 开发环境" in conversation_preview,
            "runtime_seed_visible": "AIOps-testhub-fake-remote开发环境" in runtime_preview,
            "runtime_launch_action_visible": "启动环境" in runtime_preview,
            "project_seed_local_visible": "AIOps-本地路径项目配置" in config_preview,
            "project_seed_remote_visible": "AIOps-远程仓库项目配置" in config_preview,
            **linkage_validation["checks"],
        }

        browser.close()

    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    failed = [name for name, ok in results["checks"].items() if not ok]
    if failed:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        raise SystemExit(f"Fake remote AI workspace smoke failed: {', '.join(failed)}")

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
