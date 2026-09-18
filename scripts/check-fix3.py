from playwright.sync_api import sync_playwright
import pathlib
BASE="http://43.135.120.107:8081"; OUT=pathlib.Path("docs/screenshots"); OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1440,"height":950})
    pg.goto(BASE, wait_until="networkidle")
    if pg.locator("#username").count()>0:
        pg.fill("#username","dev1"); pg.fill("#password","Passw0rd!"); pg.click("#kc-login"); pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(1500)
    res = pg.evaluate("""async () => {
      const t = localStorage.getItem('tenantId');
      const tok = (await (await fetch('/realms/sandboxhub/protocol/openid-connect/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'grant_type=password&client_id=sandboxhub-web&username=dev1&password=Passw0rd!'})).json()).access_token;
      const H = {'X-Tenant-Id':t,'Authorization':'Bearer '+tok};
      const r = await (await fetch('/api/v1/sandboxes/db60aff3-41e2-46f6-b853-c0d339cf5979',{headers:H})).json();
      return {status:r.state, lost:r.lost, name:r.name};
    }""")
    print("stale sandbox get:", res)
    pg.goto(BASE+"/sandboxes", wait_until="networkidle"); pg.wait_for_timeout(1500)
    pg.screenshot(path=str(OUT/"60_list_createbtn.png"))
    pg.goto(BASE+"/api-keys", wait_until="networkidle"); pg.wait_for_timeout(1200)
    pg.click("button:has-text('创建新密钥')"); pg.wait_for_timeout(800)
    pg.screenshot(path=str(OUT/"61_apikey_modal.png"))
    b.close()
print("DONE")
