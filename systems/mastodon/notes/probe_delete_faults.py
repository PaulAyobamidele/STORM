#!/usr/bin/env python
"""probe_delete_faults.py -- what the browser shows when the DELETE of post C
(the happy path's last step) meets each fault: alert texts and timing, then
the store after the fault is restored. Posts A, B, C are made through
PostStatusService; one fresh browser and a seeded fixture per fault.

    MASTODON_PW=... .venv/bin/python systems/mastodon/notes/probe_delete_faults.py [FAULT ...]
INFRA_SIDEKIQ_DEAD is armed before the delete starts; the others just before
the modal's Delete click, where the System Interface places them.
"""
import os, subprocess, sys, time
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "framework"))
import logging; logging.basicConfig(level=logging.WARNING)
from concretization.disruptor import DisruptionExecutor  # noqa: E402
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "https://mastodon.localhost"
BOB = 117353415630680785
FAULTS = sys.argv[1:] or ["DB_ABORT", "INFRA_STORAGE_FULL", "UE_SESSION_EXPIRED",
                          "APP_UNAVAILABLE", "INFRA_DB_DOWN", "INFRA_SIDEKIQ_DEAD"]
de = DisruptionExecutor(os.path.join(ROOT, "systems/mastodon/properties/disruption_mapping.yml"),
                        base_url=BASE, project_root=ROOT)
sh = lambda c: subprocess.run(c, shell=True, cwd=ROOT, capture_output=True, text=True)
MENU_C = "//div[@aria-label='Home']//article[.//div[contains(@class,'status__content__text')][contains(.,'ioco note C')]]//button[@aria-label='More']"


def posts():
    r = sh("docker exec mastodon-web-1 bin/rails runner '"
           "b = Account.find_local(\"bob\"); "
           "%w[A B C].each { |x| PostStatusService.new.call(b, text: \"@alice ioco note #{x} https://example.com\"); sleep 1 }' 2>&1")
    time.sleep(4)
    return r.returncode == 0


def store():
    q = sh("docker exec -i mastodon-db-1 psql -U postgres -d mastodon_production -tAc "
           f"\"SELECT (SELECT count(*) FROM statuses WHERE account_id={BOB} AND deleted_at IS NULL), "
           f"(SELECT count(*) FROM statuses WHERE account_id={BOB} AND deleted_at IS NULL AND text LIKE '%note C%'), "
           f"(SELECT statuses_count FROM account_stats WHERE account_id={BOB})\"").stdout.strip()
    return f"live rows|C live|counter = {q}"


for f in FAULTS:
    print(f"\n=== {f}")
    if sh("sh systems/mastodon/seed.sh").returncode != 0 or not posts():
        print("  seed or posts failed; stop"); break
    print(f"  before: {store()}")
    o = Options()
    for a in ("--headless=new", "--no-sandbox", "--window-size=1280,900", "--ignore-certificate-errors"):
        o.add_argument(a)
    d = webdriver.Chrome(options=o); W = WebDriverWait(d, 30)
    try:
        d.get(BASE + "/auth/sign_in")
        W.until(EC.presence_of_element_located((By.NAME, "user[email]"))).send_keys("bob@mastodon.localhost")
        d.find_element(By.NAME, "user[password]").send_keys(os.environ["MASTODON_PW"])
        d.find_element(By.XPATH, "//form//button[@type='submit']").click()
        W.until(EC.presence_of_element_located((By.XPATH, MENU_C))); time.sleep(1.5)
        if f == "INFRA_SIDEKIQ_DEAD":
            print(f"  injected: {de.activate_disruption(f)}")
        W.until(EC.element_to_be_clickable((By.XPATH, MENU_C))).click(); time.sleep(0.6)
        W.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(@class,'dropdown-menu__item')][normalize-space()='Delete']"))).click()
        W.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'safety-action-modal')]")))
        if f != "INFRA_SIDEKIQ_DEAD":
            print(f"  injected: {de.activate_disruption(f)}")
        t0 = time.time()
        d.find_element(By.XPATH, "//div[contains(@class,'safety-action-modal')]//button[@type='submit'][normalize-space()='Delete']").click()
        seen = []
        while time.time() - t0 < 15:
            try:
                for e in d.find_elements(By.XPATH, "//div[contains(@class,'notification-bar')]"):
                    x = e.get_attribute("innerText").strip().replace("\n", " | ")
                    if x and x not in [s for _, s in seen]:
                        seen.append((round(time.time() - t0, 1), x))
            except Exception:
                pass
            time.sleep(0.25)
        still = len(d.find_elements(By.XPATH, MENU_C))
        print(f"  alerts within 15 s: {seen or 'NONE'}")
        print(f"  post C still in the open column after 15 s: {bool(still)}")
    except Exception as e:
        print(f"  probe error: {e.__class__.__name__}: {str(e)[:200]}")
    finally:
        print(f"  restored: {de.restore([f])}"); de._poisoned = False
        time.sleep(8)
        print(f"  store 8 s after restore: {store()}")
        try: d.quit()
        except Exception: pass
print("\nfinal seed:", "ok" if sh("sh systems/mastodon/seed.sh").returncode == 0 else "FAILED")
