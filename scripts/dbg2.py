from playwright.sync_api import sync_playwright
import pathlib

BASE = "http://43.135.120.107:8081"
OUT = pathlib.Path("docs/screenshots")

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 950})
    pg.set_default_timeout(60000)
    pg.goto(BASE, wait_until="domcontentloaded")
    if pg.locator("#username").count() > 0:
        pg.fill("#username", "dev1")
        pg.fill("#password", "Passw0rd!")
        pg.click("#kc-login")
        pg.wait_for_load_state("domcontentloaded")
    pg.wait_for_timeout(3000)
    info = pg.evaluate(
        """async () => {
      const tok = (await (await fetch('/realms/sandboxhub/protocol/openid-connect/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'grant_type=password&client_id=sandboxhub-web&username=dev1&password=Passw0rd!'})).json()).access_token;
      const me = await (await fetch('/api/v1/me',{headers:{'Authorization':'Bearer '+tok}})).json();
      const t = me.tenants[0].id; localStorage.setItem('tenantId', t);
      const H = {'X-Tenant-Id':t,'Authorization':'Bearer '+tok,'Content-Type':'application/json'};
      const list = await (await fetch('/api/v1/sandboxes?size=100',{headers:H})).json();
      const running = (list.items||[]).filter(x=>x.state==='Running');
      return {lang: localStorage.getItem('sh-lang'), tenant: t, running: running.length, sid: running[0] && running[0].sandbox_id};
    }"""
    )
    print(info)
    sid = info["sid"]
    pg.goto(BASE + "/sandboxes/" + sid, wait_until="domcontentloaded")
    pg.wait_for_timeout(9000)
    print("url:", pg.url)
    print("tabs:", pg.locator("div[role='tab']").all_inner_texts())
    pg.screenshot(path=str(OUT / "debug_detail.png"))
    b.close()
