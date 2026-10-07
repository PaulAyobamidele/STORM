#!/usr/bin/env python3
"""Verify EVERY concrete_domain selector through a real browser.

Why not urllib: the previous checker fetched raw HTML, which proves an element
is in the MARKUP but not that a browser renders it. TinyMCE replaces the
submission textarea with an iframe and hides the original, so a selector that
"verified" perfectly was never visible at run time and wait_for timed out. Any
selector JavaScript touches has to be checked here instead.

Reports, per selector, on the page where the SI actually uses it:
    present   in the DOM at all
    visible   what wait_for requires
    text      what observe would capture
"""
import sys, time, yaml
sys.path.insert(0, "/Users/ayobamidele/text-conc/framework")
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

BASE = "http://localhost:8080"
CD = "/Users/ayobamidele/text-conc/EVALUATION/moodle/properties/concrete_domain.yml"
G, R, Y, D, X = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"

cd = yaml.safe_load(open(CD))
B = cd["bindings"]
SEL = cd["selectors"]

def route(name):
    u = cd["routes"][name]
    for k, v in B.items():
        u = u.replace("{{" + k + "}}", str(v))
    return BASE + u

opts = Options()
for a in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
          "--disable-gpu", "--window-size=1280,900"):
    opts.add_argument(a)
d = webdriver.Chrome(options=opts)
d.implicitly_wait(0)


def login(user, pw):
    # ALWAYS log out first. Moodle redirects /login/index.php to the dashboard
    # when a session exists, so the form is absent and the switch to the other
    # actor silently fails -- which is exactly what the SI's own guard has to
    # handle when swapping student for teacher.
    d.get(f"{BASE}/login/logout.php")
    for b in d.find_elements(By.XPATH, "//form[contains(@action,'logout.php')]//button"):
        b.click(); time.sleep(1); break
    d.get(f"{BASE}/login/index.php")
    if not d.find_elements(By.ID, "username"):
        raise RuntimeError("login form absent after logout — still authenticated?")
    d.find_element(By.ID, "username").send_keys(user)
    d.find_element(By.ID, "password").send_keys(pw)
    d.find_element(By.ID, "loginbtn").click()
    time.sleep(1)


def check(page, names):
    print(f"\n{D}{page}{X}")
    for n in names:
        xp = SEL[n]
        els = d.find_elements(By.XPATH, xp)
        if not els:
            print(f"  {R}absent {X} {n}")
            continue
        vis = [e for e in els if e.is_displayed()]
        txt = " ".join((vis[0] if vis else els[0]).text.split())[:44]
        if vis:
            print(f"  {G}visible{X} {n:28} ({len(els)} match) {txt!r}")
        else:
            print(f"  {Y}HIDDEN {X} {n:28} ({len(els)} match) — in the DOM but "
                  f"wait_for requires VISIBLE")


try:
    login("student1", "Student1!")

    d.get(route("rt_course"));       check("rt_course", ["sel_course_heading"])
    d.get(route("rt_quiz_view"));    check("rt_quiz_view",
        ["sel_attempt_quiz_btn", "sel_attempt_state_cell", "sel_quiz_grade_value"])
    d.get(route("rt_assign_view"));  check("rt_assign_view",
        ["sel_submission_status", "sel_submission_text", "sel_add_submission_btn",
         "sel_edit_submission_btn", "sel_submit_for_grading_btn", "sel_assign_grade_cell"])
    d.get(route("rt_assign_edit"));  check("rt_assign_edit",
        ["sel_online_text_editor", "sel_save_changes_btn"])

    print(f"\n{D}rt_assign_edit — EVERY textarea/input actually on the page{X}")
    for e in d.find_elements(By.XPATH, "//textarea|//input[@type='text']|//div[@contenteditable='true']|//iframe"):
        print(f"   <{e.tag_name}> id={e.get_attribute('id')!r} "
              f"name={e.get_attribute('name')!r} displayed={e.is_displayed()}")

    d.get(route("rt_course_total")); check("rt_course_total", ["sel_course_total_cell"])

    login("teacher1", "Teacher1!")
    d.get(route("rt_assign_grader")); check("rt_assign_grader",
        ["sel_grade_input", "sel_grade_save_btn", "sel_grading_submission_text",
         "sel_stale_warning"])
finally:
    d.quit()
