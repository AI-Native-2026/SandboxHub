from playwright.sync_api import sync_playwright
BASE="http://43.135.120.107:8081"
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); errs=[]
    pg.on("pageerror", lambda e: errs.append(str(e)[:300]))
    pg.goto(BASE, wait_until="networkidle")
    if pg.locator("#username").count()>0:
        pg.fill("#username","dev1"); pg.fill("#password","Passw0rd!"); pg.click("#kc-login"); pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(3000)
    print("url:", pg.url)
    print("menu:", pg.locator(".ant-menu").count())
    for e in errs[-10:]: print("ERR", e)
    b.close()
