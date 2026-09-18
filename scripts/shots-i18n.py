from playwright.sync_api import sync_playwright
import pathlib

BASE = "http://43.135.120.107:8081"
OUT = pathlib.Path("docs/screenshots")
OUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 950})
    pg.set_default_timeout(60000)
    pg.goto(BASE, wait_until="networkidle")
    if pg.locator("#username").count() > 0:
        pg.fill("#username", "dev1")
        pg.fill("#password", "Passw0rd!")
        pg.click("#kc-login")
        pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(2500)

    # switch to English
    pg.click("button[aria-label='切换语言']")
    pg.wait_for_timeout(1200)

    def nav(label):
        pg.click(f".ant-menu-item:has-text('{label}')")
        pg.wait_for_timeout(1800)

    nav("Artifacts")
    pg.screenshot(path=str(OUT / "80_artifacts_en.png"))
    pg.click("button:has-text('Collect Artifact')")
    pg.wait_for_timeout(1200)
    pg.click(".ant-modal .ant-select-selector")
    pg.wait_for_timeout(1000)
    pg.screenshot(path=str(OUT / "81_artifacts_modal_en.png"))
    pg.keyboard.press("Escape")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(500)

    nav("Agent Hosting")
    pg.screenshot(path=str(OUT / "82_agents_en.png"))

    nav("Getting Started")
    pg.screenshot(path=str(OUT / "83_guide_en.png"))

    nav("Sandboxes")
    pg.wait_for_timeout(1200)
    pg.click("table tbody tr:first-child a")
    pg.wait_for_selector("div[role='tab']:has-text('Runtime')", timeout=60000)
    pg.click("div[role='tab']:has-text('Runtime')")
    pg.wait_for_timeout(500)
    pg.click("div[role='tab']:has-text('Terminal')")
    pg.wait_for_timeout(7000)
    pg.screenshot(path=str(OUT / "84_terminal_en.png"))
    print("Connected visible:", pg.locator("text=Connected").count() > 0)
    b.close()
print("DONE")

