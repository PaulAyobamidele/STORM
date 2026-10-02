#!/usr/bin/env python
"""probe_dom.py -- walk the Spliit screens the System Interface needs and dump
the real DOM (tag, role, id, name, placeholder, type, href, text) for each, so
selectors in concrete_domain.yml are taken from the running app, not guessed.

Also exercises, live, the three nominal-path predictions of the behaviour note:
amount 0 (inline zod message), amount 20,000,000 (server rejection: what does
the UI show?), and a WEEKLY expense dated eight days back (is the materialised
copy logged in Activity?).

    /Users/ayobamidele/text-conc/.venv/bin/python systems/spliit/notes/probe_dom.py
    BASE=http://localhost:3000 (default). Output: systems/spliit/notes/dom/NN_*.txt
"""
import os, sys, time, datetime, json, re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = os.environ.get("BASE", "http://localhost:3000")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dom")
os.makedirs(OUT, exist_ok=True)
STAMP = datetime.datetime.now().strftime("%H%M%S")
TITLE_A = f"Probe once {STAMP}"
TITLE_B = f"Probe weekly {STAMP}"

o = Options()
for a in ("--headless=new", "--no-sandbox", "--disable-gpu", "--window-size=1280,1600"):
    o.add_argument(a)
d = webdriver.Chrome(options=o)
d.set_page_load_timeout(60)
W = lambda t=15: WebDriverWait(d, t)
summary = []

INTERESTING = ("//body//*[self::a or self::button or self::input or self::select or self::textarea "
               "or self::label or self::h1 or self::h2 or self::h3 or self::p or self::li or self::td "
               "or self::th or @role or @data-testid or @data-state]")

def dump(name, note=""):
    path = os.path.join(OUT, f"{name}.txt")
    lines = [f"# {name}  url={d.current_url}  {note}", ""]
    for e in d.find_elements(By.XPATH, INTERESTING):
        try:
            attrs = {k: e.get_attribute(k) for k in ("id", "name", "role", "type", "placeholder", "href",
                                                      "aria-label", "data-testid", "data-state", "inputmode",
                                                      "value", "for", "disabled")}
            attrs = {k: v for k, v in attrs.items() if v not in (None, "", "false")}
            cls = (e.get_attribute("class") or "")[:60]
            txt = (e.get_attribute("innerText") or "").strip().replace("\n", " | ")[:90]
            lines.append(f"<{e.tag_name}> {json.dumps(attrs, ensure_ascii=False)} class='{cls}' :: {txt}")
        except Exception as ex:  # stale etc.
            lines.append(f"<?> {ex.__class__.__name__}")
    with open(path, "w") as fh:
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

def set_native_value(el, value):
    d.execute_script("""
        const el = arguments[0], v = arguments[1];
        const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        s.call(el, v);
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
    """, el, value)

def click_xpath(xp, t=15):
    el = W(t).until(EC.element_to_be_clickable((By.XPATH, xp))); el.click(); return el

# selectors confirmed from the first dump (03_expense_form): two decimal inputs
# (originalAmount first, hidden) and two submit buttons (an empty one in the
# currency block first), so target by name / label / visible text.
X_TITLE   = "//input[@name='title']"
X_AMOUNT  = "//input[@name='amount']"
X_CREATE  = "//button[@type='submit'][normalize-space()='Create']"
X_SAVE    = "//button[@type='submit'][normalize-space()='Save']"
X_PAYER   = "//label[contains(.,'Paid by')]/following::button[@role='combobox'][1]"
X_RECUR   = "//label[contains(.,'Expense Recurrence')]/following::button[@role='combobox'][1]"
X_OPTION  = "//div[@role='option'][normalize-space()='{}']"

def type_xpath(xp, text, t=15):
    el = W(t).until(EC.presence_of_element_located((By.XPATH, xp))); el.clear(); el.send_keys(text); return el

# ---------------------------------------------------------------- 1. group
def create_group():
    d.get(f"{BASE}/groups/create"); W().until(EC.presence_of_element_located((By.XPATH, "//form")))
    dump("01_group_create_form")
    type_xpath("//input[@placeholder='Summer vacations']", f"Probe group {STAMP}")
    click_xpath("//button[@type='submit']")
    W(30).until(lambda x: re.search(r"/groups/([^/]+)", x.current_url) and "/create" not in x.current_url)
    time.sleep(1.5)
    gid = re.search(r"/groups/([^/?#]+)", d.current_url).group(1)
    dump("02_expenses_empty", f"group={gid}")
    return gid
GID = step("create group", create_group)
if not GID:
    print(summary); d.quit(); sys.exit(1)

# ---------------------------------------------------------------- 2. form
def expense_form():
    d.get(f"{BASE}/groups/{GID}/expenses/create")
    W().until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Monday evening restaurant']")))
    time.sleep(1)
    dump("03_expense_form")
    # every combobox / select trigger, opened one at a time
    combos = d.find_elements(By.XPATH, "//button[@role='combobox']")
    print(f"  comboboxes: {len(combos)}")
    for i, c in enumerate(combos):
        try:
            c.click(); time.sleep(0.6); dump(f"04_combo_{i}_open", f"trigger text={c.text!r}")
            d.find_element(By.TAG_NAME, "body").send_keys(u''); time.sleep(0.3)  # ESC
        except Exception as ex:
            print(f"  combo {i}: {ex.__class__.__name__}")
    return len(combos)
step("expense form", expense_form)

# ---------------------------------------------------------------- 3. create ONCE
def create_once():
    d.get(f"{BASE}/groups/{GID}/expenses/create")
    type_xpath(X_TITLE, TITLE_A)
    type_xpath(X_AMOUNT, "12.00")
    click_xpath(X_PAYER); time.sleep(0.5)
    click_xpath(X_OPTION.format("John")); time.sleep(0.3)
    dump("05_expense_form_filled")
    click_xpath(X_CREATE)
    W(30).until(lambda x: "/create" not in x.current_url)
    time.sleep(2.5)
    dump("06_expenses_after_once")
    # the search box: does the list filter to the row?
    box = d.find_element(By.XPATH, "//input[@placeholder='Search for an expense…']")
    box.send_keys(TITLE_A); time.sleep(1.5)
    dump("06b_list_filtered")
    return d.current_url
step("create ONCE expense", create_once)

# ---------------------------------------------------------------- 4. read-backs
def tabs():
    for name, path in (("07_stats", "stats"), ("08_activity", "activity"), ("09_balances", "balances")):
        d.get(f"{BASE}/groups/{GID}/{path}"); time.sleep(2.5); dump(name)
    return True
step("stats/activity/balances", tabs)

# ---------------------------------------------------------------- 5. edit + delete dialog
def edit_and_dialog():
    d.get(f"{BASE}/groups/{GID}/expenses"); time.sleep(2.5)
    row = W(15).until(EC.element_to_be_clickable((By.XPATH, f"//*[contains(text(),'{TITLE_A}')]")))
    row.click()
    W(20).until(lambda x: "/edit" in x.current_url); time.sleep(1.5)
    dump("10_edit_form")
    btn = d.find_elements(By.XPATH, "//button[contains(.,'Delete')]")
    if btn:
        btn[0].click(); time.sleep(0.8); dump("11_delete_dialog")
        d.find_element(By.TAG_NAME, "body").send_keys(u'')
    return len(btn)
step("edit page + delete dialog", edit_and_dialog)

# ---------------------------------------------------------------- 6. INVALID (0)
def invalid_zero():
    d.get(f"{BASE}/groups/{GID}/expenses/create")
    type_xpath(X_TITLE, f"Probe zero {STAMP}")
    type_xpath(X_AMOUNT, "0")
    click_xpath(X_PAYER); time.sleep(0.5); click_xpath(X_OPTION.format("John"))
    click_xpath(X_CREATE); time.sleep(1.5)
    dump("12_invalid_zero", f"url={d.current_url}")
    return d.current_url
step("INVALID amount 0", invalid_zero)

# ---------------------------------------------------------------- 7. OVERLIMIT
def overlimit():
    d.get(f"{BASE}/groups/{GID}/expenses/create")
    type_xpath(X_TITLE, f"Probe overlimit {STAMP}")
    type_xpath(X_AMOUNT, "20000000")
    click_xpath(X_PAYER); time.sleep(0.5); click_xpath(X_OPTION.format("John"))
    click_xpath(X_CREATE); time.sleep(6)
    dump("13_overlimit_after_submit", f"url={d.current_url}")
    d.get(f"{BASE}/groups/{GID}/activity"); time.sleep(2.5); dump("13b_activity_after_overlimit")
    return d.current_url
step("OVERLIMIT amount 20000000", overlimit)

# ---------------------------------------------------------------- 8. WEEKLY dated 8 days back
def weekly():
    d.get(f"{BASE}/groups/{GID}/expenses/create")
    type_xpath(X_TITLE, TITLE_B)
    type_xpath(X_AMOUNT, "25.00")
    date_el = d.find_element(By.XPATH, "//input[@type='date']")
    past = (datetime.date.today() - datetime.timedelta(days=8)).isoformat()
    set_native_value(date_el, past)
    click_xpath(X_PAYER); time.sleep(0.5); click_xpath(X_OPTION.format("John"))
    click_xpath(X_RECUR); time.sleep(0.5); click_xpath(X_OPTION.format("Weekly")); time.sleep(0.3)
    opened = True
    date_now = d.find_element(By.XPATH, "//input[@type='date']").get_attribute("value")
    dump("14_weekly_form_filled", f"date={past} recurrence_opened={opened} date_now={date_now}")
    click_xpath(X_CREATE)
    W(30).until(lambda x: "/create" not in x.current_url); time.sleep(3)
    d.get(f"{BASE}/groups/{GID}/expenses"); time.sleep(3)
    dump("15_weekly_list")
    rows = d.find_elements(By.XPATH, f"//*[contains(text(),'{TITLE_B}')]")
    d.get(f"{BASE}/groups/{GID}/activity"); time.sleep(3)
    dump("16_weekly_activity")
    entries = d.find_elements(By.XPATH, f"//*[contains(text(),'{TITLE_B}')]")
    d.get(f"{BASE}/groups/{GID}/stats"); time.sleep(2.5); dump("17_stats_after_weekly")
    return {"rows_with_title": len(rows), "activity_entries_with_title": len(entries), "date": past}
step("WEEKLY dated 8 days back", weekly)

d.quit()
print("\n==== SUMMARY  group", GID)
for s in summary:
    print(f"  {s[1]:4s} {s[0]:32s} {s[2]}")
