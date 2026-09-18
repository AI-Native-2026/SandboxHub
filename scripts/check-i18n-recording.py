from playwright.sync_api import sync_playwright
import pathlib

BASE = "http://43.135.120.107:8081"
OUT = pathlib.Path("docs/screenshots")
OUT.mkdir(exist_ok=True)


def wait_app(pg):
    for _ in range(40):
        if pg.locator(".ant-menu").count() > 0:
            return
        pg.wait_for_timeout(1000)
    raise RuntimeError("app menu not found; url=" + pg.url)


def goto_app(pg, path):
    for _ in range(3):
        try:
            pg.goto(BASE + path, wait_until="domcontentloaded", timeout=45000)
            wait_app(pg)
            pg.wait_for_timeout(1200)
            return
        except Exception:
            pg.wait_for_timeout(2000)
    raise RuntimeError("goto failed: " + path)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 950})
    pg.set_default_timeout(60000)
    pg.goto(BASE, wait_until="domcontentloaded")
    if pg.locator("#username").count() > 0:
        pg.fill("#username", "dev1")
        pg.fill("#password", "Passw0rd!")
        pg.click("#kc-login")
    wait_app(pg)
    pg.wait_for_timeout(2000)

    # switch to English
    pg.click("button[aria-label='Toggle language']")
    pg.wait_for_timeout(1000)

    sid = pg.evaluate(
        """async () => {
      const tok = (await (await fetch('/realms/sandboxhub/protocol/openid-connect/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'grant_type=password&client_id=sandboxhub-web&username=dev1&password=Passw0rd!'})).json()).access_token;
      const me = await (await fetch('/api/v1/me',{headers:{'Authorization':'Bearer '+tok}})).json();
      const t = me.tenants[0].id; localStorage.setItem('tenantId', t);
      const H = {'X-Tenant-Id':t,'Authorization':'Bearer '+tok,'Content-Type':'application/json'};
      const c = await (await fetch('/api/v1/sandboxes',{method:'POST',headers:H,body:JSON.stringify({image:'python:3.12',name:'rec-demo',cpu:'1',memory:'1Gi',timeout_seconds:1800})})).json();
      return c.sandbox_id;
    }"""
    )
    print("sandbox:", sid)

    goto_app(pg, "/artifacts")
    pg.screenshot(path=str(OUT / "80_artifacts_en.png"))
    pg.click("button:has-text('Collect Artifact')")
    pg.wait_for_timeout(1500)
    pg.screenshot(path=str(OUT / "81_artifacts_modal_en.png"))
    pg.click(".ant-modal .ant-select-selector")
    pg.wait_for_timeout(1000)
    pg.screenshot(path=str(OUT / "82_artifacts_select.png"))
    pg.keyboard.press("Escape")
    pg.keyboard.press("Escape")

    goto_app(pg, "/agents")
    pg.screenshot(path=str(OUT / "83_agents_en.png"))
    goto_app(pg, "/guide")
    pg.screenshot(path=str(OUT / "84_guide_en.png"))

    goto_app(pg, "/sandboxes")
    pg.click("table tbody tr:first-child a")
    pg.wait_for_selector("div[role='tab']:has-text('Runtime')", timeout=60000)
    pg.click("div[role='tab']:has-text('Runtime')")
    pg.wait_for_timeout(600)
    pg.click("div[role='tab']:has-text('Terminal')")
    pg.wait_for_timeout(7000)
    pg.screenshot(path=str(OUT / "85_terminal_en.png"))
    print("Connected visible:", pg.locator("text=Connected").count() > 0)

    pg.locator(".ant-switch").first.click()
    pg.wait_for_timeout(5000)
    pg.locator(".xterm-screen").first.click()
    pg.keyboard.type("echo rec-test-123\n")
    pg.wait_for_timeout(4000)
    pg.screenshot(path=str(OUT / "86_terminal_recording.png"))

    goto_app(pg, "/")
    pg.wait_for_timeout(2500)
    goto_app(pg, "/recordings")
    pg.wait_for_timeout(1500)
    rows = pg.locator("table tbody tr").count()
    print("recording rows:", rows)
    pg.screenshot(path=str(OUT / "87_recordings_en.png"))
    if rows > 0:
        pg.locator("table tbody tr").first.locator("a:has-text('Replay')").click()
        pg.wait_for_timeout(1000)
        pg.click("button:has-text('Play')")
        pg.wait_for_timeout(4000)
        content = pg.locator("pre.sh-out").last.inner_text()
        print("replay contains rec-test-123:", "rec-test-123" in content)
        pg.screenshot(path=str(OUT / "88_recording_replay.png"))
    b.close()
print("DONE")
