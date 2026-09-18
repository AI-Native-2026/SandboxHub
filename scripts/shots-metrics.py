from playwright.sync_api import sync_playwright
import pathlib

BASE = "http://43.135.120.107:8081"
OUT = pathlib.Path("docs/screenshots")
OUT.mkdir(exist_ok=True)

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
    pg.wait_for_timeout(2500)

    # create a sandbox via API and record its name
    name = pg.evaluate(
        """async () => {
      const tok = (await (await fetch('/realms/sandboxhub/protocol/openid-connect/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'grant_type=password&client_id=sandboxhub-web&username=dev1&password=Passw0rd!'})).json()).access_token;
      const me = await (await fetch('/api/v1/me',{headers:{'Authorization':'Bearer '+tok}})).json();
      const t = me.tenants[0].id; localStorage.setItem('tenantId', t);
      const H = {'X-Tenant-Id':t,'Authorization':'Bearer '+tok,'Content-Type':'application/json'};
      const list = await (await fetch('/api/v1/sandboxes?size=100',{headers:H})).json();
      for (const s of (list.items||[])) { if (s.state==='Running') { await fetch('/api/v1/sandboxes/'+s.sandbox_id,{method:'DELETE',headers:H}); } }
      const c = await (await fetch('/api/v1/sandboxes',{method:'POST',headers:H,body:JSON.stringify({image:'python:3.12',name:'metrics-demo',cpu:'1',memory:'1Gi',timeout_seconds:1800})})).json();
      return c.name;
    }"""
    )
    print("created:", name)

    # navigate in-app: sidebar -> sandboxes -> first row link
    pg.click(".ant-menu-item:has-text('沙箱')")
    pg.wait_for_timeout(2500)
    pg.click("table tbody tr:first-child a")
    pg.wait_for_selector("div[role='tab']:has-text('观测')", timeout=60000)
    pg.click("div[role='tab']:has-text('观测')")
    pg.wait_for_timeout(16000)
    pg.screenshot(path=str(OUT / "70_metrics_series.png"))
    b.close()
print("DONE")
