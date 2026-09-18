from playwright.sync_api import sync_playwright
import pathlib
BASE="http://43.135.120.107:8081"; OUT=pathlib.Path("docs/screenshots"); OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1440,"height":950})
    pg.goto(BASE, wait_until="networkidle")
    if pg.locator("#username").count()>0:
        pg.fill("#username","admin"); pg.fill("#password","Passw0rd!"); pg.click("#kc-login"); pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(1500)
    # english mode
    pg.click("button[aria-label='切换语言']"); pg.wait_for_timeout(900)
    pg.goto(BASE+"/sandboxes", wait_until="networkidle"); pg.wait_for_timeout(1200)
    pg.screenshot(path=str(OUT/"50_en_list.png"))
    pg.goto(BASE+"/pools", wait_until="networkidle"); pg.wait_for_timeout(1800)
    pg.screenshot(path=str(OUT/"51_pools_en.png"))
    pg.goto(BASE+"/rbac", wait_until="networkidle"); pg.wait_for_timeout(1200)
    pg.click("button:has-text('New role')"); pg.wait_for_timeout(900)
    pg.screenshot(path=str(OUT/"52_rbac_modal.png")); pg.keyboard.press("Escape")
    # back to zh
    pg.click("button[aria-label='切换语言']"); pg.wait_for_timeout(700)
    pg.goto(BASE+"/cost", wait_until="networkidle"); pg.wait_for_timeout(2000)
    pg.screenshot(path=str(OUT/"53_usage_chart.png"))
    b.close()
print("DONE")
