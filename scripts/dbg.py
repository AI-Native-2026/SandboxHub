from playwright.sync_api import sync_playwright
BASE="http://43.135.120.107:8081"
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page()
    pg.goto(BASE, wait_until="domcontentloaded")
    if pg.locator("#username").count()>0:
        pg.fill("#username","dev1"); pg.fill("#password","Passw0rd!"); pg.click("#kc-login"); pg.wait_for_load_state("domcontentloaded")
    pg.wait_for_timeout(1500)
    out = pg.evaluate("""async () => {
      const t = localStorage.getItem('tenantId');
      const tok = (await (await fetch('/realms/sandboxhub/protocol/openid-connect/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'grant_type=password&client_id=sandboxhub-web&username=dev1&password=Passw0rd!'})).json()).access_token;
      const r = await fetch('/api/v1/sandboxes?size=100',{headers:{'X-Tenant-Id':t,'Authorization':'Bearer '+tok}});
      const txt = await r.text();
      return {status:r.status, tenant:t, body: txt.slice(0,300)};
    }""")
    print(out)
    b.close()
