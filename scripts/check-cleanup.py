from playwright.sync_api import sync_playwright
BASE="http://43.135.120.107:8081"
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page()
    pg.goto(BASE, wait_until="networkidle")
    if pg.locator("#username").count()>0:
        pg.fill("#username","admin"); pg.fill("#password","Passw0rd!"); pg.click("#kc-login"); pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(1500)
    res = pg.evaluate("""async () => {
      const t = localStorage.getItem('tenantId');
      const tok = (await (await fetch('/realms/sandboxhub/protocol/openid-connect/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'grant_type=password&client_id=sandboxhub-web&username=admin&password=Passw0rd!'})).json()).access_token;
      const H = {'X-Tenant-Id':t,'Authorization':'Bearer '+tok,'Content-Type':'application/json'};
      const before = await (await fetch('/api/v1/sandboxes?size=100',{headers:H})).json();
      const cleanup = await (await fetch('/api/v1/admin/cleanup',{method:'POST',headers:H})).json();
      const after = await (await fetch('/api/v1/sandboxes?size=100',{headers:H})).json();
      return {
        before_total: before.total,
        before_terminated: before.items.filter(x=>x.state==='Terminated').length,
        cleanup,
        after_total: after.total,
        after_terminated: after.items.filter(x=>x.state==='Terminated').length,
      };
    }""")
    print(res)
    b.close()
