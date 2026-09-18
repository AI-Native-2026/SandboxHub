from playwright.sync_api import sync_playwright
import pathlib

BASE = "http://43.135.120.107:8081"
OUT = pathlib.Path("docs/screenshots")
OUT.mkdir(exist_ok=True)


def login(pg, user):
    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_timeout(1500)
    if pg.locator("#username").count() > 0:
        pg.fill("#username", user)
        pg.fill("#password", "Passw0rd!")
        pg.click("#kc-login")
        pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(1500)
    for _ in range(30):
        if pg.locator(".ant-menu").count() > 0:
            return
        pg.wait_for_timeout(1000)
    raise RuntimeError("menu not found")


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 950})
    pg.set_default_timeout(60000)
    login(pg, "admin")
    pg.wait_for_timeout(2500)

    pg.goto(BASE + "/policy", wait_until="domcontentloaded")
    pg.wait_for_timeout(2000)
    pg.screenshot(path=str(OUT / "90_policy_templates.png"))
    pg.click("button:has-text('新建模板')")
    pg.wait_for_timeout(1200)
    pg.screenshot(path=str(OUT / "91_policy_new_dropdown.png"))
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(500)

    pg.goto(BASE + "/sandboxes", wait_until="domcontentloaded")
    pg.wait_for_timeout(2000)
    pg.click("button:has-text('创建沙箱')")
    pg.wait_for_timeout(1500)
    pg.screenshot(path=str(OUT / "92_create_policy_select.png"))
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(500)

    pg.goto(BASE + "/pools", wait_until="domcontentloaded")
    pg.wait_for_timeout(2500)
    pg.screenshot(path=str(OUT / "93_pools_usage.png"))
    b.close()
print("DONE")
