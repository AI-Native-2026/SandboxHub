from playwright.sync_api import sync_playwright
import pathlib
BASE="http://43.135.120.107:8081"; OUT=pathlib.Path("docs/screenshots"); OUT.mkdir(exist_ok=True)
pages=[("u1_cost","/cost"),("u1_quota","/quota"),("u1_approval","/approval"),("u1_vault","/vault"),("u1_policy","/policy"),("u3_recordings","/recordings"),("u3_rbac","/rbac"),("u4_pools","/pools"),("u5_tasks","/tasks"),("u5_artifacts","/artifacts"),("u5_agents","/agents")]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1440,"height":950})
    pg.goto(BASE, wait_until="networkidle")
    if pg.locator("#username").count()>0:
        pg.fill("#username","admin"); pg.fill("#password","Passw0rd!"); pg.click("#kc-login"); pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(1500)
    for name,path in pages:
        pg.goto(BASE+path, wait_until="networkidle"); pg.wait_for_timeout(1800)
        pg.screenshot(path=str(OUT/f"30_{name}.png")); print("shot", name)
    b.close()
print("DONE")
