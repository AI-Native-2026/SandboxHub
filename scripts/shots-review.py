from playwright.sync_api import sync_playwright
import pathlib
BASE="http://43.135.120.107:8081"; OUT=pathlib.Path("docs/screenshots"); OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1440,"height":950})
    pg.goto(BASE, wait_until="networkidle")
    if pg.locator("#username").count()>0:
        pg.fill("#username","dev1"); pg.fill("#password","Passw0rd!"); pg.click("#kc-login"); pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(1500)
    # sandbox list dark
    pg.goto(BASE+"/sandboxes", wait_until="networkidle"); pg.wait_for_timeout(1500)
    pg.screenshot(path=str(OUT/"40_list_dark.png"))
    # create modal
    pg.click("button:has-text('创建沙箱')"); pg.wait_for_timeout(1000)
    pg.screenshot(path=str(OUT/"41_create_modal.png")); pg.keyboard.press("Escape"); pg.wait_for_timeout(600)
    # api key
    pg.goto(BASE+"/api-keys", wait_until="networkidle"); pg.wait_for_timeout(1200)
    pg.screenshot(path=str(OUT/"42_apikey_dark.png"))
    # switch light (single button: the theme button has aria-label 切换主题)
    pg.click("button[aria-label='切换主题']"); pg.wait_for_timeout(800)
    pg.screenshot(path=str(OUT/"43_apikey_light.png"))
    pg.goto(BASE+"/sandboxes", wait_until="networkidle"); pg.wait_for_timeout(1200)
    pg.screenshot(path=str(OUT/"44_list_light.png"))
    pg.goto(BASE, wait_until="networkidle"); pg.wait_for_timeout(1200)
    pg.screenshot(path=str(OUT/"45_dashboard_light.png"))
    b.close()
print("DONE")
