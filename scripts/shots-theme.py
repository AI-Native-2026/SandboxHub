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
    pg.wait_for_timeout(2000)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 950})
    pg.set_default_timeout(60000)
    login(pg, "admin")

    for theme in ("light", "dark"):
        pg.evaluate(f"localStorage.setItem('sh-theme','{theme}')")
        pg.goto(BASE + "/", wait_until="domcontentloaded")
        pg.wait_for_timeout(3500)
        pg.screenshot(path=str(OUT / f"95_overview_{theme}.png"))
        pg.goto(BASE + "/sandboxes", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        pg.screenshot(path=str(OUT / f"96_sandboxes_{theme}.png"))
        pg.goto(BASE + "/agents", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        pg.screenshot(path=str(OUT / f"97_agents_{theme}.png"))
        pg.goto(BASE + "/pools", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        pg.screenshot(path=str(OUT / f"98_pools_{theme}.png"))
    b.close()
print("DONE")
