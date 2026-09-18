"""Robust E2E: login -> create -> detail tabs (terminal/command/files/metrics).
Run: python scripts/e2e-full.py
"""
from __future__ import annotations

import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

BASE = "http://43.135.120.107:8081"
OUT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)


def step(name, fn):
    try:
        fn()
        print(f"  ok: {name}")
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL: {name}: {type(e).__name__}: {str(e)[:160]}")


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE, wait_until="networkidle")
        if page.locator("#username").count() > 0:
            page.fill("#username", "dev1")
            page.fill("#password", "Passw0rd!")
            page.click("#kc-login")
            page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1200)

        # create
        page.click("text=创建沙箱")
        page.wait_for_timeout(1000)
        page.fill("input[placeholder='my-sandbox']", f"e2e-{int(time.time())%10000}")
        page.fill("input[placeholder='python:3.12']", "python:3.12")
        page.click("button.ant-btn-primary")
        page.wait_for_url("**/sandboxes/**", timeout=90000)
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT / "04_detail_overview.png"))

        step("terminal", lambda: (
            page.click("div[role='tab']:has-text('终端')"),
            page.wait_for_timeout(5000),
            page.screenshot(path=str(OUT / "05_terminal.png")),
        ))
        step("command", lambda: (
            page.click("div[role='tab']:has-text('命令')"),
            page.wait_for_timeout(800),
            page.click("button.ant-btn-primary"),
            page.wait_for_timeout(5000),
            page.screenshot(path=str(OUT / "06_command.png")),
        ))
        step("files", lambda: (
            page.click("div[role='tab']:has-text('文件')"),
            page.wait_for_timeout(3000),
            page.screenshot(path=str(OUT / "07_files.png")),
        ))
        step("metrics", lambda: (
            page.click("div[role='tab']:has-text('指标')"),
            page.wait_for_timeout(4000),
            page.screenshot(path=str(OUT / "08_metrics.png")),
        ))
        print("detail url:", page.url)
        browser.close()
    print("E2E_FULL_DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
