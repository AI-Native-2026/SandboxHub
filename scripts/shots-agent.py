from playwright.sync_api import sync_playwright
import os
import pathlib
import time

BASE = "http://43.135.120.107:8081"
OUT = pathlib.Path("imgs")
OUT.mkdir(exist_ok=True)


def login(pg, user):
    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_timeout(1500)
    if pg.locator("#username").count() > 0:
        pg.fill("#username", user)
        pg.fill("#password", "Passw0rd!")
        pg.click("#kc-login")
        pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(2000)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.set_default_timeout(120000)
    login(pg, "admin")

    sid = os.environ.get("SID")
    if not sid:
        sid = pg.evaluate(
            """async () => {
          const tok = (await (await fetch('/realms/sandboxhub/protocol/openid-connect/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'grant_type=password&client_id=sandboxhub-web&username=admin&password=Passw0rd!'})).json()).access_token;
          const me = await (await fetch('/api/v1/me',{headers:{'Authorization':'Bearer '+tok}})).json();
          const t = me.tenants[0].id; localStorage.setItem('tenantId', t);
          const H = {'X-Tenant-Id':t,'Authorization':'Bearer '+tok,'Content-Type':'application/json'};
          const c = await (await fetch('/api/v1/sandboxes',{method:'POST',headers:H,body:JSON.stringify({image:'opensandbox/code-interpreter:v1.1.0',name:'agent-opencode',cpu:'1',memory:'1Gi',timeout_seconds:3600})})).json();
          return c.sandbox_id;
        }"""
        )
    print("sandbox:", sid)

    pg.goto(BASE + "/sandboxes/" + sid, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    pg.click("div[role='tab']:has-text('运行')")
    pg.wait_for_timeout(800)
    pg.click("div[role='tab']:has-text('终端')")
    for _ in range(30):
        if pg.locator("text=已连接").count() > 0:
            break
        pg.wait_for_timeout(1000)
    pg.wait_for_timeout(3000)

    screen = pg.locator(".xterm-screen").first
    screen.click()
    pg.keyboard.type("npm install -g opencode-ai@latest\n")
    print("installing opencode...")
    pg.wait_for_timeout(45000)

    pg.keyboard.type("opencode\n")
    pg.wait_for_timeout(6000)
    pg.keyboard.type("Create /tmp/greeting.py that prints a time-based greeting, then run it\n")
    print("waiting for agent...")
    pg.wait_for_timeout(60000)
    pg.screenshot(path=str(OUT / "Agent.png"))
    print("saved", OUT / "Agent.png")
    b.close()
