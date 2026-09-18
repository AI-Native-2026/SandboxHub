"""Focused check: run a command in the UI and read the rendered output."""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

BASE = "http://43.135.120.107:8081"


def main() -> int:
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE, wait_until="networkidle")
        if page.locator("#username").count() > 0:
            page.fill("#username", "dev1")
            page.fill("#password", "Passw0rd!")
            page.click("#kc-login")
            page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        # open first sandbox
        page.goto(BASE + "/sandboxes", wait_until="networkidle")
        page.wait_for_timeout(1500)
        page.click("table tbody tr:first-child a:has-text('详情')")
        page.wait_for_timeout(2000)
        page.click("div[role='tab']:has-text('命令')")
        page.wait_for_timeout(800)
        page.click("button.ant-btn-primary")
        page.wait_for_timeout(6000)
        text = page.locator("pre.sh-out").inner_text()
        print("OUTPUT_START>>>")
        print(text)
        print("<<<OUTPUT_END")
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
