#!/usr/bin/env python
"""probe_dom.py -- walk the Mastodon screens the System Interface needs and dump
the real DOM (tag, role, id, name, class, aria-label, text) for each, so the
selectors in concrete_domain.yml come from the running app, not from a guess.

Stage "read" (default) writes nothing but the login session: sign-in page,
home, compose form, a status menu opened on an existing post, the profile, the
blank-post alert and the over-limit state (the client sends neither).
Stage "write" posts, edits and deletes one fixture post and dumps each step.

    MASTODON_PW=... .venv/bin/python EVALUATION/mastodon/notes/probe_dom.py [read|write]
    BASE=https://mastodon.localhost (default). Output: EVALUATION/mastodon/notes/dom/
The password is read from the environment only and never written to disk.
"""
import os, sys, time, json, datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = os.environ.get("BASE", "https://mastodon.localhost")
EMAIL = os.environ.get("MASTODON_EMAIL", "bob@mastodon.localhost")
PW = os.environ["MASTODON_PW"]
STAGE = (sys.argv[1] if len(sys.argv) > 1 else "read")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dom")
os.makedirs(OUT, exist_ok=True)
STAMP = datetime.datetime.now().strftime("%H%M%S")
TEXT = f"@alice ioco probe {STAMP} https://example.com"
EDITED = f"@alice ioco probe {STAMP} revised https://example.com"

o = Options()
for a in ("--headless=new", "--no-sandbox", "--disable-gpu", "--window-size=1280,900",
          "--ignore-certificate-errors"):          # Caddy's internal CA; probe only
    o.add_argument(a)
d = webdriver.Chrome(options=o)
d.set_page_load_timeout(60)
W = lambda t=15: WebDriverWait(d, t)
summary = []

INTERESTING = ("//body//*[self::a or self::button or self::input or self::textarea or self::label "
               "or self::h1 or self::h2 or self::h3 or self::p or self::li or self::article "
               "or @role or @aria-label or @data-id or @data-testid "
               "or contains(@class,'notification') or contains(@class,'counter') "
               "or contains(@class,'status__content') or contains(@class,'account__header')]")

def dump(name, note=""):
    lines = [f"# {name}  url={d.current_url}  {note}", ""]
    for e in d.find_elements(By.XPATH, INTERESTING):
        try:
            attrs = {k: e.get_attribute(k) for k in ("id", "name", "role", "type", "href", "aria-label",
                                                      "aria-disabled", "aria-expanded", "data-id",
                                                      "placeholder", "value", "disabled")}
            attrs = {k: v for k, v in attrs.items() if v not in (None, "", "false")}
            cls = (e.get_attribute("class") or "")[:70]
            txt = (e.get_attribute("innerText") or "").strip().replace("\n", " | ")[:100]
            lines.append(f"<{e.tag_name}> {json.dumps(attrs, ensure_ascii=False)} class='{cls}' :: {txt}")
        except Exception as ex:
            lines.append(f"<?> {ex.__class__.__name__}")
    with open(os.path.join(OUT, f"{name}.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.join(OUT, f"{name}.html"), "w") as fh:
        fh.write(d.page_source)
    print(f"  dumped {name} ({len(lines)-2} elements)")

def step(label, fn):
    print(f"== {label}")
    try:
        r = fn(); summary.append((label, "ok", r)); return r
    except Exception as ex:
        d.save_screenshot(os.path.join(OUT, f"fail_{label.replace(' ', '_')}.png"))
        summary.append((label, "FAIL", f"{ex.__class__.__name__}: {str(ex)[:160]}"))
        print(f"  !! {ex.__class__.__name__}: {str(ex)[:200]}")
        return None

X = lambda xp, t=15: W(t).until(EC.presence_of_element_located((By.XPATH, xp)))
C = lambda xp, t=15: W(t).until(EC.element_to_be_clickable((By.XPATH, xp)))
X_TEXTAREA = "//textarea[contains(@class,'autosuggest-textarea__textarea')] | //form[contains(@class,'compose-form')]//textarea"
X_POST = "//div[contains(@class,'compose-form__submit')]//button[@type='submit']"

def set_text(xp, text):
    el = X(xp); el.click()
    el.send_keys(Keys.COMMAND, "a"); el.send_keys(Keys.DELETE)
    if text:
        el.send_keys(text)
    return el

def login():
    d.get(f"{BASE}/auth/sign_in"); X("//form")
    dump("01_sign_in")
    X("//input[@name='user[email]']").send_keys(EMAIL)
    X("//input[@name='user[password]']").send_keys(PW)
    C("//form//button[@type='submit']").click()
    W(30).until(lambda x: "/home" in x.current_url or "/auth" not in x.current_url)
    X(X_TEXTAREA, 30); time.sleep(2.5)
    dump("02_home")
    return d.current_url

def open_menu_on_first():
    btn = C("(//article//button[@aria-label='More'] | //div[contains(@class,'status__action-bar')]//button[@title='More'])[1]")
    btn.click(); time.sleep(0.8)
    dump("03_status_menu_other")
    d.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE); time.sleep(0.4)
    return True

def profile():
    d.get(f"{BASE}/@bob"); time.sleep(3)
    dump("04_profile")
    return d.current_url

def blank_post():
    d.get(f"{BASE}/home"); X(X_TEXTAREA, 30); time.sleep(1.5)
    set_text(X_TEXTAREA, "")
    C(X_POST).click(); time.sleep(1.2)
    dump("05_blank_post")
    return True

def overlimit():
    set_text(X_TEXTAREA, "x" * 501); time.sleep(0.8)
    dump("06_overlimit")
    b = X(X_POST)
    r = {"disabled": b.get_attribute("disabled"), "aria-disabled": b.get_attribute("aria-disabled")}
    set_text(X_TEXTAREA, ""); time.sleep(0.4)
    return r

def post_it():
    d.get(f"{BASE}/home"); X(X_TEXTAREA, 30); time.sleep(1.5)
    set_text(X_TEXTAREA, TEXT); time.sleep(0.5)
    dump("10_compose_filled")
    C(X_POST).click(); time.sleep(1.5)
    dump("11_after_post")
    d.get(f"{BASE}/@bob"); time.sleep(3); dump("12_profile_after_post")
    d.get(f"{BASE}/home"); X(X_TEXTAREA, 30); time.sleep(3); dump("13_home_after_post_reload")
    return len(d.find_elements(By.XPATH, f"//*[contains(text(),'ioco probe {STAMP}')]"))

def edit_it():
    art = X(f"//article[.//*[contains(text(),'ioco probe {STAMP}')]]")
    art.find_element(By.XPATH, ".//button[@aria-label='More' or @title='More']").click(); time.sleep(0.8)
    dump("14_status_menu_own")
    C("//*[@role='menuitem' or contains(@class,'dropdown-menu__item')][.//*[normalize-space()='Edit'] or normalize-space()='Edit']").click()
    time.sleep(1.2); dump("15_edit_mode")
    set_text(X_TEXTAREA, EDITED); time.sleep(0.5)
    C(X_POST).click(); time.sleep(1.5); dump("16_after_update")
    d.get(f"{BASE}/home"); X(X_TEXTAREA, 30); time.sleep(3); dump("17_home_after_edit_reload")
    return len(d.find_elements(By.XPATH, f"//*[contains(.,'ioco probe {STAMP} revised')]"))

def delete_it():
    art = X(f"//article[.//*[contains(text(),'ioco probe {STAMP}')]]")
    art.find_element(By.XPATH, ".//button[@aria-label='More' or @title='More']").click(); time.sleep(0.8)
    C("//*[@role='menuitem' or contains(@class,'dropdown-menu__item')][.//*[normalize-space()='Delete'] or normalize-space()='Delete']").click()
    time.sleep(1); dump("18_delete_modal")
    C("//div[contains(@class,'modal')]//button[normalize-space()='Delete']").click(); time.sleep(2)
    dump("19_after_delete")
    d.get(f"{BASE}/@bob"); time.sleep(3); dump("20_profile_after_delete")
    return True

step("login", login)
if STAGE == "read":
    step("status menu on another's post", open_menu_on_first)
    step("profile", profile)
    step("blank post", blank_post)
    step("over limit", overlimit)
else:
    step("post", post_it)
    step("edit", edit_it)
    step("delete", delete_it)
d.quit()
print("\n==== SUMMARY", STAGE, STAMP)
for s in summary:
    print(f"  {s[1]:4s} {s[0]:32s} {s[2]}")
