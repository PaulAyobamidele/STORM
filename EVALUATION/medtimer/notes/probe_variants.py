#!/usr/bin/env python
"""probe_variants.py -- confirm, live, the three domain variants the behaviour
note predicts from the source, and capture the screens the System Interface
needs for them (the delete dialog, the edit sheet's toggle, the cannot-be-
skipped switch). Each variant starts from a clean app and builds the fixture
the way the SI's prelude will (medicine "Vitamin C", 3 pills, one reminder at
11:59 PM with dose 1), so the read-back is about that fixture only.

    VARIANT=skip_delete  .venv/bin/python EVALUATION/medtimer/notes/probe_variants.py
    VARIANT=skip_edit    ...
    VARIANT=noskip_skip  ...

Output: notes/ui/v_<variant>_NN_<name>.{xml,txt,png} and a database read-back
printed at the end. Observations only; verdicts come from the walk.
"""
import os, sys, time, subprocess, datetime
from xml.etree import ElementTree as ET
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import WebDriverException, NoSuchElementException

PKG, ACT = "com.futsch1.medtimer", "com.futsch1.medtimer.MainActivity"
APPIUM_URL = os.environ.get("APPIUM_URL", "http://127.0.0.1:4723")
DEVICE = os.environ.get("DEVICE", "emulator-5554")
ADB = os.path.join(os.environ.get("ANDROID_HOME", "/opt/homebrew/share/android-commandlinetools"), "platform-tools", "adb")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
VARIANT = os.environ.get("VARIANT", "skip_delete")
MED, STOCK, UNIT, DOSE, TIME12 = "Vitamin C", "3", "pills", "1", "11:59 PM"
n = 0


def adb(*args):
    r = subprocess.run([ADB, "-s", DEVICE, *args], capture_output=True, text=True, timeout=60)
    return (r.stdout + r.stderr).strip()


def rid(name): return f"{PKG}:id/{name}"


def dump(name, note=""):
    global n
    n += 1
    base = os.path.join(OUT, f"v_{VARIANT}_{n:02d}_{name}")
    xml = d.page_source
    open(base + ".xml", "w").write(xml)
    lines = [f"# v_{VARIANT}_{n:02d}_{name}  {note}", ""]
    try:
        for e in ET.fromstring(xml).iter():
            a = e.attrib
            if not a.get("class"):
                continue
            keep = {k: a.get(k) for k in ("resource-id", "text", "content-desc") if a.get(k)}
            flags = [f for f in ("clickable", "checkable", "checked", "focused") if a.get(f) == "true"]
            if keep or flags:
                lines.append(f"<{a['class'].split('.')[-1]}> {keep} {' '.join(flags)} bounds={a.get('bounds')}")
    except ET.ParseError as ex:
        lines.append(f"(xml parse error: {ex})")
    open(base + ".txt", "w").write("\n".join(lines) + "\n")
    try:
        d.get_screenshot_as_file(base + ".png")
    except WebDriverException:
        pass
    print(f"  dumped v_{VARIANT}_{n:02d}_{name} ({len(lines)-2} elements)")


def find(sel, t=8):
    kind, _, val = sel.partition(":")
    if kind == "id":
        by, q = (AppiumBy.ID, val) if ":" in val else (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().resourceIdMatches("(^|.*/){val}$")')
    elif kind == "text":
        by, q = AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{val}")'
    elif kind == "textc":
        by, q = AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().textContains("{val}")'
    elif kind == "desc":
        by, q = AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().description("{val}")'
    else:
        by, q = AppiumBy.ANDROID_UIAUTOMATOR, val
    end = time.time() + t
    while True:
        try:
            return d.find_element(by, q)
        except NoSuchElementException:
            if time.time() > end:
                raise
            time.sleep(0.4)


def present(sel, t=2):
    try:
        find(sel, t); return True
    except NoSuchElementException:
        return False


def tap(sel, t=8):
    find(sel, t).click(); time.sleep(0.7)


def tap_first(*sels):
    for s in sels:
        if present(s, 2):
            tap(s); return s
    raise NoSuchElementException(f"none of {sels}")


def type_into(sel, text):
    el = find(sel); el.click(); time.sleep(0.3); el.clear(); el.send_keys(text); time.sleep(0.3)


def back(): d.press_keycode(4); time.sleep(0.8)


def db():
    q = ("SELECT medicineId, medicineName, amount, unit, cannotBeSkipped FROM Medicine; "
         "SELECT reminderEventId, reminderId, status, stockHandled, stockBefore, stockAfter FROM ReminderEvent;")
    out = adb("shell", f'run-as {PKG} sqlite3 databases/medTimer "{q}"')
    print("  DB:", " | ".join(out.splitlines()))
    return out


# ---------------------------------------------------------------- fresh app
print("adb: pm clear + grant")
adb("shell", "am", "force-stop", PKG); adb("shell", "pm", "clear", PKG)
adb("shell", "pm", "grant", PKG, "android.permission.POST_NOTIFICATIONS")
opts = UiAutomator2Options(); opts.platform_name = "Android"; opts.automation_name = "UiAutomator2"
opts.device_name = DEVICE; opts.udid = DEVICE; opts.app_package = PKG; opts.app_activity = ACT
opts.no_reset = True; opts.auto_grant_permissions = True; opts.new_command_timeout = 600
d = webdriver.Remote(APPIUM_URL, options=opts); d.implicitly_wait(0); time.sleep(3)

# ---------------------------------------------------------------- prelude (as the SI will do it)
print("== prelude")
tap("id:nav_medicines"); tap("id:addMedicine"); type_into("id:medicineName", MED); tap("text:OK"); time.sleep(1.2)
tap("id:openStockTracking"); tap("text:Amount"); time.sleep(0.6)
type_into('ui:new UiSelector().className("android.widget.EditText")', STOCK); tap("text:OK"); time.sleep(0.6)
tap("text:Unit"); time.sleep(0.6)
type_into('ui:new UiSelector().className("android.widget.EditText")', UNIT); tap("text:OK"); time.sleep(0.6)
back(); time.sleep(0.8)
tap("id:addReminder"); time.sleep(0.6); tap("id:timeBasedCard"); time.sleep(0.8)
type_into("id:editAmount", DOSE); type_into("id:editReminderTime", TIME12)
tap("id:createReminder"); time.sleep(1.2)
dump("edit_medicine_ready")

if VARIANT == "noskip_skip":
    print("== set 'Medicine cannot be skipped'")
    tap("id:openMedicineSettings"); time.sleep(0.8)
    tap("text:Medicine cannot be skipped"); time.sleep(0.6)
    dump("settings_after_toggle", "expect the second switch checked")
    back(); time.sleep(0.8)

print("== overview")
tap("id:nav_overview"); time.sleep(1.5)
dump("overview_scheduled")
tap("id:stateButton"); time.sleep(0.8)
dump("popup_scheduled", "does the popup still offer Skipped?" if VARIANT == "noskip_skip" else "")
tap("id:skippedButton"); time.sleep(2.0)
dump("overview_after_skipped", "state 'Skipped', stock text absent (no change)")
db()

if VARIANT == "skip_delete":
    print("== delete the skipped dose")
    tap("id:stateButton"); time.sleep(0.8)
    dump("popup_after_skipped", "expect Taken / Re-raise / Delete")
    tap("id:deleteButton"); time.sleep(0.8)
    dump("delete_dialog", "the confirmation dialog: capture its buttons")
    tap_first("text:Yes", "text:YES", "text:OK", "text:Delete"); time.sleep(2.0)
    dump("overview_after_delete", "row gone?")
    db()
    tap("id:nav_medicines"); time.sleep(1.2)
    dump("medicines_after_delete", "prediction: '4 pills left' (refund of a dose never taken)")
    print("  card:", find(f"textc:{MED}").text)

elif VARIANT == "skip_edit":
    print("== edit the skipped dose to Taken")
    tap("id:reminderText"); time.sleep(1.0)
    dump("edit_sheet_skipped", "Skipped toggle checked")
    tap("id:takenToggleButton"); time.sleep(0.5)
    dump("edit_sheet_toggled")
    back(); time.sleep(1.5)
    dump("overview_after_edit", "prediction: state 'Taken', stock unchanged")
    db()
    tap("id:nav_medicines"); time.sleep(1.2)
    dump("medicines_after_edit", "prediction: still '3 pills left'")
    print("  card:", find(f"textc:{MED}").text)

elif VARIANT == "noskip_skip":
    tap("id:nav_medicines"); time.sleep(1.2)
    dump("medicines_after_noskip_skip")

d.quit()
print("done", VARIANT)
