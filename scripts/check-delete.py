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
      const c = await (await fetch('/api/v1/sandboxes',{method:'POST',headers:H,body:JSON.stringify({image:'python:3.12',name:'del-test',cpu:'1',memory:'1Gi',timeout_seconds:300})})).json();
      const sid = c.sandbox_id;
      const d1 = await fetch('/api/v1/sandboxes/'+sid,{method:'DELETE',headers:H});
      const d2 = await fetch('/api/v1/sandboxes/'+sid,{method:'DELETE',headers:H});
      return {sid, first:d1.status, second:d2.status};
    }""")
    print(res)
    b.close()
