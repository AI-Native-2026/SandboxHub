"""SandboxHub E2E suite (aligned with docs/user-journeys.md).

Run: python scripts/e2e-suite.py
"""
from __future__ import annotations

import pathlib
import sys
import time

from playwright.sync_api import Page, sync_playwright

BASE = "http://43.135.120.107:8081"
PWD = "Passw0rd!"
OUT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

RESULTS: list[tuple[str, str, str]] = []


def record(journey: str, ok: bool, note: str = "") -> None:
    RESULTS.append((journey, "PASS" if ok else "FAIL", note))
    print(f"  [{'PASS' if ok else 'FAIL'}] {journey} {note}")


def login(page: Page, user: str) -> None:
    page.goto(BASE, wait_until="networkidle")
    if page.locator("#username").count() > 0:
        page.fill("#username", user)
        page.fill("#password", PWD)
        page.click("#kc-login")
        page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)


def logout(page: Page) -> None:
    try:
        page.goto(BASE, wait_until="networkidle")
        page.click(".ant-dropdown-trigger")
        page.wait_for_timeout(500)
        page.click("text=退出")
        page.wait_for_timeout(2500)
    except Exception:
        pass


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.set_default_timeout(60000)
        page.set_default_navigation_timeout(60000)

        try:
            login(page, "dev1")
            assert page.locator("text=AI智能体沙箱平台").count() > 0
            assert page.locator(".ant-select").count() > 0
            record("E2E-D1 登录/租户", True)
        except Exception as e:
            record("E2E-D1 登录/租户", False, str(e)[:80])

        sid = None
        try:
            page.click(".ant-menu-item:has-text('沙箱')")
            page.wait_for_timeout(1200)
            page.click("button:has-text('创建沙箱')")
            page.wait_for_timeout(900)
            page.fill("input[placeholder='my-sandbox']", f"suite-{int(time.time()) % 100000}")
            page.fill("input[placeholder='python:3.12']", "python:3.12")
            page.click(".ant-modal-footer button.ant-btn-primary")
            page.wait_for_url("**/sandboxes/**", timeout=90000)
            page.wait_for_timeout(2500)
            sid = page.url.rstrip("/").split("/")[-1]
            assert "/sandboxes/" in page.url
            record("E2E-D2 创建沙箱（弹窗）", True, sid[:8])
        except Exception as e:
            record("E2E-D2 创建沙箱（弹窗）", False, str(e)[:80])

        try:
            page.click("div[role='tab']:has-text('运行')")
            page.wait_for_timeout(500)
            page.click("div[role='tab']:has-text('终端')")
            page.wait_for_timeout(5000)
            assert page.locator("text=已连接").count() > 0
            page.click("div[role='tab']:has-text('命令')")
            page.wait_for_timeout(700)
            page.click("button.ant-btn-primary")
            page.wait_for_timeout(6000)
            out = page.locator("pre.sh-out").inner_text()
            assert "Python" in out, out[:80]
            record("E2E-D3 终端/命令", True)
        except Exception as e:
            record("E2E-D3 终端/命令", False, str(e)[:80])

        try:
            page.click("div[role='tab']:has-text('数据')")
            page.wait_for_timeout(2500)
            assert page.locator("text=名称").count() > 0
            record("E2E-D4 文件浏览", True)
        except Exception as e:
            record("E2E-D4 文件浏览", False, str(e)[:80])

        try:
            page.click("div[role='tab']:has-text('观测')")
            page.wait_for_timeout(8000)
            assert page.locator("text=CPU %").count() > 0
            assert page.locator("text=Memory %").count() > 0
            page.screenshot(path=str(OUT / "70_metrics_series.png"))
            record("E2E-D6 指标时序图", True)
        except Exception as e:
            record("E2E-D6 指标时序图", False, str(e)[:80])

        try:
            page.click(".ant-menu-item:has-text('API Key')")
            page.wait_for_timeout(1200)
            page.click("button:has-text('创建新密钥')")
            page.wait_for_timeout(700)
            page.fill("input[placeholder='ci-runner / local-dev']", "suite-key")
            page.click(".ant-modal-footer button.ant-btn-primary")
            page.wait_for_selector("text=密钥已生成", timeout=15000)
            record("E2E-D10 个人 API Key", True)
        except Exception as e:
            record("E2E-D10 个人 API Key", False, str(e)[:80])

        try:
            page.click(".ant-menu-item:has-text('模板市场')")
            page.wait_for_timeout(1500)
            assert page.locator("text=Python 3.12").count() > 0
            record("E2E-D7 模板市场", True)
        except Exception as e:
            record("E2E-D7 模板市场", False, str(e)[:80])

        # theme toggle (single control)
        try:
            page.click("button.sh-theme-toggle")
            page.wait_for_timeout(700)
            assert page.locator("html[data-theme]").count() > 0
            record("E2E-U2 主题切换", True)
        except Exception as e:
            record("E2E-U2 主题切换", False, str(e)[:80])

        # i18n toggle (single control)
        try:
            page.click("button.sh-lang-toggle")
            page.wait_for_timeout(800)
            assert page.locator(".ant-menu-item:has-text('Sandboxes')").count() > 0
            page.click("button.sh-lang-toggle")
            page.wait_for_timeout(600)
            record("E2E-U2 中英切换", True)
        except Exception as e:
            record("E2E-U2 中英切换", False, str(e)[:80])

        page.screenshot(path=str(OUT / "20_workbench.png"))

        logout(page)
        try:
            login(page, "admin")
            page.goto(BASE + "/admin", wait_until="networkidle")
            page.wait_for_timeout(2500)
            assert page.locator("text=租户管理").count() > 0
            page.screenshot(path=str(OUT / "21_admin.png"))
            record("E2E-P1 管理端", True)
        except Exception as e:
            record("E2E-P1 管理端", False, str(e)[:80])

        logout(page)
        try:
            login(page, "viewer")
            assert page.locator(".ant-menu-item:has-text('创建沙箱')").count() == 0
            record("E2E-A1 只读无写入口", True)
        except Exception as e:
            record("E2E-A1 只读无写入口", False, str(e)[:80])

        browser.close()


def main() -> int:
    run()
    print("\n===== E2E RESULT =====")
    passed = sum(1 for _, s, _ in RESULTS if s == "PASS")
    for j, s, n in RESULTS:
        print(f"{s:4}  {j}  {n}")
    print(f"PASS={passed} FAIL={len(RESULTS) - passed}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
