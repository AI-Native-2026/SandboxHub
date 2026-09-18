from playwright.sync_api import sync_playwright
import pathlib
url = pathlib.Path("docs/design/ui-spec.html").resolve().as_uri()
out = pathlib.Path("docs/design"); 
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":1440,"height":1000})
    pg.goto(url); pg.add_style_tag(content="html{scroll-behavior:auto !important}"); pg.wait_for_timeout(600)
    pg.screenshot(path=str(out/"_preview_hero.png"))
    for name, sel in [("ia","#ia"),("tokens","#tokens"),("wf_list","#wf-list"),("wf_detail","#wf-detail"),("roadmap","#roadmap")]:
        pg.eval_on_selector(sel, "el=>el.scrollIntoView({behavior:'instant',block:'start'})"); pg.wait_for_timeout(300)
        pg.screenshot(path=str(out/f"_preview_{name}.png"))
    b.close()
print("ok")
