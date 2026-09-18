"""Local visual smoke test against the deployed SandboxHub (http://43.135.120.107:8081).

Logs in via Keycloak and screenshots key pages.
Run: python scripts/e2e-smoke.py
"""
from __future__ import annotations

import pathlib
import sys

from playwright.sync_api import sync_playwright

BASE = "http://43.135.120.107:8081"
USER = "dev1"
PWD = "Passw0rd!"
OUT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE, wait_until="networkidle")
        # Keycloak login
        if "realms" in page.url or page.locator("#username").count() > 0:
            page.fill("#username", USER)
            page.fill("#password", PWD)
            page.click("#kc-login")
            page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / "01_dashboard.png"))
        print("url:", page.url)

        # navigate to sandboxes
        page.click("text=沙箱")
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT / "02_sandboxes.png"))

        # create page
        page.click("text=创建沙箱")
        page.wait_for_timeout(1000)
        page.screenshot(path=str(OUT / "03_create.png"))

        browser.close()
    print("SCREENSHOTS_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
