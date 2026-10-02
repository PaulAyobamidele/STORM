#!/usr/bin/env python
"""probe_faults.py -- what the browser shows when a post is made under each
write-path fault: alert texts and their timing, then a fresh read of the
profile count and the home feed after the fault is restored. One fresh
browser and a seeded fixture per fault. Faults are injected and restored
through the framework's DisruptionExecutor, with their probes.

    MASTODON_PW=... .venv/bin/python systems/mastodon/notes/probe_faults.py [FAULT ...]
Extra pseudo-fault WEB_STOPPED: `docker stop` web instead of pausing it.
"""
import os, subprocess, sys, time
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "framework"))
import logging; logging.basicConfig(level=logging.WARNING)
from concretization.disruptor import DisruptionExecutor  # noqa: E402
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "https://mastodon.localhost"
TEXT = "@alice ioco note C https://example.com"
FAULTS = sys.argv[1:] or ["DB_ABORT", "APP_UNAVAILABLE", "WEB_STOPPED", "INFRA_DB_DOWN",
                          "APP_WRITE_FAIL", "UE_SESSION_EXPIRED", "INFRA_STORAGE_FULL",
                          "INFRA_SIDEKIQ_DEAD"]
de = DisruptionExecutor(os.path.join(ROOT, "systems/mastodon/properties/disruption_mapping.yml"),
                        base_url=BASE, project_root=ROOT)

def sh(c): return subprocess.run(c, shell=True, cwd=ROOT, capture_output=True, text=True)

def browser():
    o = Options()
    for a in ("--headless=new", "--no-sandbox", "--window-size=1280,900", "--ignore-certificate-errors"):
        o.add_argument(a)
    d = webdriver.Chrome(options=o); d.set_page_load_timeout(60); return d

def login(d):
    W = WebDriverWait(d, 30)
    d.get(BASE + "/auth/sign_in")
    W.until(EC.presence_of_element_located((By.NAME, "user[email]"))).send_keys("bob@mastodon.localhost")
    d.find_element(By.NAME, "user[password]").send_keys(os.environ["MASTODON_PW"])
    d.find_element(By.XPATH, "//form//button[@type='submit']").click()
    return W.until(EC.presence_of_element_located((By.XPATH, "//textarea[contains(@class,'autosuggest-textarea__textarea')]")))

def alerts(d):
    try:
        return [e.get_attribute("innerText").strip().replace("\n", " | ")
                for e in d.find_elements(By.XPATH, "//div[contains(@class,'notification-bar')]")]
    except Exception as e:
        return [f"<{e.__class__.__name__}>"]

def readback():
    q = ("docker exec -i mastodon-db-1 psql -U postgres -d mastodon_production -tAc "
         "\"SELECT (SELECT count(*) FROM statuses WHERE account_id=117353415630680785), "
         "(SELECT statuses_count FROM account_stats WHERE account_id=117353415630680785)\"")
    rows_count = sh(q).stdout.strip()
    feed = sh("docker exec mastodon-redis-1 redis-cli ZCARD feed:home:117353415630680785").stdout.strip()
    return f"rows|counter={rows_count} home-feed-size={feed}"

for f in FAULTS:
    print(f"\n=== {f}")
    if sh("sh systems/mastodon/seed.sh").returncode != 0:
        print("  seed failed; stop"); break
    d = browser()
    try:
        ta = login(d); time.sleep(2)
        ta.click(); ta.send_keys(TEXT); time.sleep(0.5)
        if f == "WEB_STOPPED":
            ok = sh("docker stop mastodon-web-1").returncode == 0
        else:
            ok = de.activate_disruption(f)
        print(f"  injected: {ok}")
        t0 = time.time()
        d.find_element(By.XPATH, "//div[contains(@class,'compose-form__submit')]//button[@type='submit']").click()
        seen = []
        while time.time() - t0 < 15:
            a = alerts(d)
            for x in a:
                if x not in [s for _, s in seen]:
                    seen.append((round(time.time() - t0, 1), x))
            time.sleep(0.25)
        btn = d.find_element(By.XPATH, "//div[contains(@class,'compose-form__submit')]//button[@type='submit']")
        ta_val = d.find_element(By.XPATH, "//textarea[contains(@class,'autosuggest-textarea__textarea')]").get_attribute("value")
        print(f"  alerts within 15 s: {seen or 'NONE'}")
        print(f"  form after 15 s: text kept={bool(ta_val)} button disabled={btn.get_attribute('disabled')}")
    except Exception as e:
        print(f"  probe error: {e.__class__.__name__}: {str(e)[:200]}")
    finally:
        if f == "WEB_STOPPED":
            sh("docker start mastodon-web-1")
            for i in range(90):
                if sh("curl -sk --resolve mastodon.localhost:443:127.0.0.1 -o /dev/null -w '%{http_code}' "
                      "https://mastodon.localhost/health").stdout == "200":
                    print(f"  web back after {i*2} s"); break
                time.sleep(2)
        else:
            print(f"  restored: {de.restore([f])}")
            de._poisoned = False
        time.sleep(8)          # let a late write land, and fan-out run
        print(f"  store 8 s after restore: {readback()}")
        try: d.quit()
        except Exception: pass
print("\nfinal seed:", "ok" if sh("sh systems/mastodon/seed.sh").returncode == 0 else "FAILED")
