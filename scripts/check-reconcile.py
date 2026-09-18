from playwright.sync_api import sync_playwright
BASE="http://43.135.120.107:8081"
def tok(pg,u): 
    return pg.evaluate("""async (u) => (await (await fetch('/realms/sandboxhub/protocol/openid-connect/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'grant_type=password&client_id=sandboxhub-web&username='+u+'&password=Passw0rd!'})).json()).access_token""", u)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page()
    pg.goto(BASE, wait_until="networkidle")
    if pg.locator("#username").count()>0:
        pg.fill("#username","dev1"); pg.fill("#password","Passw0rd!"); pg.click("#kc-login"); pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(1500)
    DT = tok(pg,"dev1"); AT = tok(pg,"admin")
    res = pg.evaluate("""async ([DT,AT]) => {
      const t = localStorage.getItem('tenantId');
      const DH = {'X-Tenant-Id':t,'Authorization':'Bearer '+DT,'Content-Type':'application/json'};
      const AH = {'X-Tenant-Id':t,'Authorization':'Bearer '+AT,'Content-Type':'application/json'};
      // create two, delete one
      const a = await (await fetch('/api/v1/sandboxes',{method:'POST',headers:DH,body:JSON.stringify({image:'python:3.12',name:'rec-test',cpu:'1',memory:'1Gi',timeout_seconds:300})})).json();
      await fetch('/api/v1/sandboxes/'+a.sandbox_id,{method:'DELETE',headers:DH});
      const list = await (await fetch('/api/v1/sandboxes?size=100',{headers:DH})).json();
      const cl = await (await fetch('/api/v1/admin/cleanup',{method:'POST',headers:AH})).json();
      const after = await (await fetch('/api/v1/sandboxes?size=100',{headers:DH})).json();
      return {total_before:list.total, cleanup:cl, total_after:after.total};
    }""", [DT, AT])
    print(res)
    b.close()
