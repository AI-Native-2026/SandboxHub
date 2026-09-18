from playwright.sync_api import sync_playwright
BASE="http://43.135.120.107:8081"
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page()
    pg.goto(BASE, wait_until="networkidle")
    if pg.locator("#username").count()>0:
        pg.fill("#username","dev1"); pg.fill("#password","Passw0rd!"); pg.click("#kc-login"); pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(1500)
    res = pg.evaluate("""async () => {
      const t = localStorage.getItem('tenantId');
      const H = {'Content-Type':'application/json','X-Tenant-Id':t};
      const tok = (await (await fetch('/realms/sandboxhub/protocol/openid-connect/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'grant_type=password&client_id=sandboxhub-web&username=dev1&password=Passw0rd!'})).json()).access_token;
      H['Authorization']='Bearer '+tok;
      const list = await (await fetch('/api/v1/sandboxes?size=100',{headers:H})).json();
      const running = list.items.filter(x=>x.state==='Running').slice(0,5);
      const out=[];
      for (const s of running) {
        const d1 = await fetch('/api/v1/sandboxes/'+s.sandbox_id,{method:'DELETE',headers:H});
        const d2 = await fetch('/api/v1/sandboxes/'+s.sandbox_id,{method:'DELETE',headers:H});
        out.push({id:s.sandbox_id.slice(0,8), first:d1.status, second:d2.status});
      }
      return out;
    }""")
    for r in res: print(r)
    b.close()
