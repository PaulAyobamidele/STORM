#!/usr/bin/env python
"""probe_ui.py -- walk the MedTimer screens the System Interface needs and dump
the real view hierarchy (UiAutomator XML + a compact text listing + a
screenshot) for each, so every selector in properties/concrete_domain.yml is
taken from the running app, not guessed.

Also exercises, live, the nominal-path predictions of notes/observed_behaviour.md:
a medicine with three units of stock and a late reminder shows a scheduled row
today (state "Please wait…"); Taken from the row's popup yields "Taken" and
"2 pills left"; the edit sheet and the delete/re-raise popup exist; an empty
medicine name is accepted; and the database tables read back as predicted.

    source systems/foodyou/env.sh          # adb + emulator on PATH
    .venv/bin/python systems/medtimer/notes/probe_ui.py

    APPIUM_URL   default http://127.0.0.1:4723
    DEVICE       default emulator-5554
    KEEP_STATE=1 skip the `pm clear` (re-probe an app that already has data)

Output: systems/medtimer/notes/ui/NN_<name>.{xml,txt,png}, db_after_probe.txt,
and a summary on stdout. Every step is best-effort: a failure is recorded with
a screenshot and the walk continues, so one wrong guess does not hide the
next screen.
"""
import os, sys, time, subprocess, datetime, re
from xml.etree import ElementTree as ET

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import WebDriverException, NoSuchElementException

PKG = "com.futsch1.medtimer"
ACT = "com.futsch1.medtimer.MainActivity"
APPIUM_URL = os.environ.get("APPIUM_URL", "http://127.0.0.1:4723")
DEVICE = os.environ.get("DEVICE", "emulator-5554")
ADB = os.path.join(os.environ.get("ANDROID_HOME", "/opt/homebrew/share/android-commandlinetools"),
                   "platform-tools", "adb")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
os.makedirs(OUT, exist_ok=True)

MED_NAME = "Vitamin C"          # no digits: the card's first number must be the stock
STOCK, UNIT, DOSE, TIME = "3", "pills", "1", "23:59"
TIME_12H = "11:59 PM"

summary = []
n = int(os.environ.get("START_N", "0"))
FROM = os.environ.get("FROM")          # skip every step before this label
_started = FROM is None


def adb(*args, timeout=60):
    r = subprocess.run([ADB, "-s", DEVICE, *args], capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()


def rid(name):
    return f"{PKG}:id/{name}"


# ---------------------------------------------------------------- dumping
def dump(name, note=""):
    """XML hierarchy, compact listing, screenshot."""
    global n
    n += 1
    base = os.path.join(OUT, f"{n:02d}_{name}")
    xml = d.page_source
    with open(base + ".xml", "w") as fh:
        fh.write(xml)
    lines = [f"# {n:02d}_{name}  {note}", ""]
    try:
        root = ET.fromstring(xml)
        for e in root.iter():
            a = e.attrib
            if not a.get("class"):
                continue
            keep = {k: a.get(k) for k in ("resource-id", "text", "content-desc") if a.get(k)}
            flags = [f for f in ("clickable", "checkable", "checked", "focused", "enabled")
                     if a.get(f) == "true" and f != "enabled"]
            if not keep and not flags:
                continue
            lines.append(f"<{a['class'].split('.')[-1]}> {keep} {' '.join(flags)} bounds={a.get('bounds')}")
    except ET.ParseError as ex:
        lines.append(f"(xml parse error: {ex})")
    with open(base + ".txt", "w") as fh:
        fh.write("\n".join(lines) + "\n")
    try:
        d.get_screenshot_as_file(base + ".png")
    except WebDriverException:
        pass
    print(f"  dumped {n:02d}_{name} ({len(lines) - 2} elements)")


def step(label, fn):
    global _started
    if not _started:
        if label == FROM:
            _started = True
        else:
            print(f"-- {label} (skipped)")
            return None
    print(f"== {label}")
    try:
        r = fn()
        summary.append((label, "ok", r))
        return r
    except Exception as ex:
        try:
            d.get_screenshot_as_file(os.path.join(OUT, f"fail_{label.replace(' ', '_')}.png"))
        except Exception:
            pass
        summary.append((label, "FAIL", f"{ex.__class__.__name__}: {str(ex)[:160]}"))
        print(f"  !! {ex.__class__.__name__}: {str(ex)[:200]}")
        return None


# ---------------------------------------------------------------- finding
def find(sel, t=8):
    """sel: 'id:name' | 'text:...' | 'desc:...' | 'ui:new UiSelector()...'"""
    kind, _, val = sel.partition(":")
    if kind == "id":
        # View ids are "pkg:id/name"; Compose test tags exposed as resource-ids
        # are bare ("nav_medicines"). Try the prefixed form, then the bare one.
        if ":" in val:
            by, q = AppiumBy.ID, val
        else:
            by, q = AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().resourceIdMatches("(^|.*/){val}$")'
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
        find(sel, t)
        return True
    except NoSuchElementException:
        return False


def tap(sel, t=8):
    find(sel, t).click()
    time.sleep(0.6)


def tap_first(*sels):
    """Try several selectors in order; the first present is tapped."""
    for s in sels:
        if present(s, 2):
            tap(s)
            return s
    raise NoSuchElementException(f"none of {sels}")


def type_into(sel, text, t=8):
    el = find(sel, t)
    el.click()
    time.sleep(0.3)
    el.clear()
    el.send_keys(text)
    time.sleep(0.3)
    return el


def back():
    d.press_keycode(4)
    time.sleep(0.8)


def dismiss_permission_dialog():
    for s in ("text:Allow", "text:ALLOW", "id:com.android.permissioncontroller:id/permission_allow_button"):
        if present(s, 1):
            tap(s)
            return s
    return None


# ---------------------------------------------------------------- session
if os.environ.get("KEEP_STATE") != "1":
    print("adb: pm clear + grant POST_NOTIFICATIONS")
    print(" ", adb("shell", "pm", "clear", PKG))
    print(" ", adb("shell", "pm", "grant", PKG, "android.permission.POST_NOTIFICATIONS"))

opts = UiAutomator2Options()
opts.platform_name = "Android"
opts.automation_name = "UiAutomator2"
opts.device_name = DEVICE
opts.udid = DEVICE
opts.app_package = PKG
opts.app_activity = ACT
opts.no_reset = True
opts.auto_grant_permissions = True
opts.new_command_timeout = 600
d = webdriver.Remote(APPIUM_URL, options=opts)
d.implicitly_wait(0)
time.sleep(3)

# ---------------------------------------------------------------- 0. resume
def resume():
    for _ in range(2):
        if present("text:Cancel", 1):
            tap("text:Cancel")
    back()
    tap_first("id:nav_medicines", "text:Medicine")
    time.sleep(1.0)
    tap(f"textc:{MED_NAME}")
    time.sleep(1.2)
    dump("resume_edit_medicine")
if FROM:
    print(f"== resume at {FROM!r}")
    resume()

# ---------------------------------------------------------------- 1. first launch
def first_launch():
    dlg = dismiss_permission_dialog()
    dump("overview_empty", f"permission_dialog={dlg}")
    return dlg
step("first launch", first_launch)

# ---------------------------------------------------------------- 2. medicine list, add medicine
def medicines_empty():
    tap_first("id:nav_medicines", "text:Medicine", "desc:Medicines tab")
    dump("medicines_empty")
step("medicine tab", medicines_empty)

def add_medicine():
    tap_first("id:addMedicine", "text:Add medicine")
    dump("add_dialog")
    type_into("id:medicineName", MED_NAME)
    dump("add_dialog_filled")
    tap("text:OK")
    time.sleep(1.5)
    dump("edit_medicine", f"after creating {MED_NAME!r}")
step("add medicine", add_medicine)

# ---------------------------------------------------------------- 3. stock settings
def stock_settings():
    tap_first("id:openStockTracking", "desc:Medicine stock")
    dump("stock_settings")
    tap("text:Amount")
    time.sleep(0.8)
    dump("amount_dialog")
    type_into("ui:new UiSelector().className(\"android.widget.EditText\")", STOCK)
    tap("text:OK")
    time.sleep(0.8)
    tap("text:Unit")
    time.sleep(0.8)
    dump("unit_dialog")
    type_into("ui:new UiSelector().className(\"android.widget.EditText\")", UNIT)
    tap("text:OK")
    time.sleep(0.8)
    dump("stock_settings_set", f"amount={STOCK} unit={UNIT}")
    back()
    time.sleep(1.0)
    dump("edit_medicine_after_stock")
step("stock settings", stock_settings)

# ---------------------------------------------------------------- 4. add a time-based reminder
def add_reminder():
    tap_first("id:addReminder", "text:Add reminder")
    time.sleep(0.8)
    dump("reminder_type_dialog")
    tap_first("id:timeBasedCard", "text:Time based reminder")
    time.sleep(0.8)
    dump("new_reminder_dialog")
    type_into("id:editAmount", DOSE)
    # The time field: TimeEditor.kt:46-60 opens a Material picker on focus /
    # click, but the first probe saw no picker a second after a click and the
    # field itself holds a plain time string ("8:00 AM", 12-hour locale). Try
    # typing the locale form first; if a picker did open, drive it instead.
    typed = TIME_12H if present("text:8:00 AM", 1) else TIME
    el = find("id:editReminderTime")
    el.click()
    time.sleep(2.0)
    dump("time_field_after_click")
    picker = present("id:material_timepicker_ok_button", 1) or present("desc:Switch to text input mode", 1)
    if picker:
        dump("time_picker")
        tap_first("id:material_timepicker_mode_button", "desc:Switch to text input mode")
        time.sleep(0.6)
        twelve_hour = present("id:material_clock_period_pm_button", 1)
        hour = "11" if twelve_hour else "23"
        type_into("ui:new UiSelector().resourceIdMatches(\".*material_hour_text_input\").childSelector(new UiSelector().className(\"android.widget.EditText\"))", hour)
        type_into("ui:new UiSelector().resourceIdMatches(\".*material_minute_text_input\").childSelector(new UiSelector().className(\"android.widget.EditText\"))", "59")
        if twelve_hour:
            tap("id:material_clock_period_pm_button")
        dump("time_picker_filled", f"hour={hour} minute=59 twelve_hour={twelve_hour}")
        tap_first("id:material_timepicker_ok_button", "text:OK")
    else:
        el = find("id:editReminderTime")
        el.clear()
        el.send_keys(typed)
        time.sleep(0.5)
        if present("id:material_timepicker_ok_button", 1):
            dump("time_picker_opened_by_typing")
            tap_first("text:Cancel", "text:CANCEL")
    time.sleep(0.5)
    dump("new_reminder_dialog_filled", f"dose={DOSE} time={TIME}")
    tap_first("id:createReminder", "text:Create")
    time.sleep(1.2)
    dump("edit_medicine_with_reminder")
step("add reminder", add_reminder)

# ---------------------------------------------------------------- 5. medicine settings (cannot be skipped)
def medicine_settings():
    tap_first("id:openMedicineSettings", "desc:Medicine settings")
    time.sleep(0.8)
    dump("medicine_settings", "the 'Medicine cannot be skipped' switch")
    back()
    time.sleep(0.8)
step("medicine settings", medicine_settings)

# ---------------------------------------------------------------- 6. overview: the scheduled row, then Taken
def overview_scheduled():
    tap_first("id:nav_overview", "text:Overview", "desc:Overview tab")
    time.sleep(1.5)
    dump("overview_scheduled", f"expect a row for {MED_NAME!r} with state 'Please wait…'")
    row = find(f"textc:{MED_NAME}", 8)
    return row.text
step("overview scheduled row", overview_scheduled)

def take_dose():
    tap("id:stateButton")
    time.sleep(0.8)
    dump("popup_scheduled", "expect Taken / Skipped / Reschedule")
    tap_first("id:takenButton", "text:Taken")
    time.sleep(2.0)
    dump("overview_after_taken", "expect state 'Taken' and a stock fragment")
    return find(f"textc:{MED_NAME}", 8).text
step("take the dose", take_dose)

def medicines_after_taken():
    tap_first("id:nav_medicines", "text:Medicine", "desc:Medicines tab")
    time.sleep(1.2)
    dump("medicines_after_taken", "expect '2 pills left'")
    return find(f"textc:{MED_NAME}", 8).text
step("medicine tab after taken", medicines_after_taken)

# ---------------------------------------------------------------- 7. edit sheet and the post-take popup
def edit_sheet():
    tap_first("id:nav_overview", "text:Overview", "desc:Overview tab")
    time.sleep(1.2)
    tap("id:reminderText")
    time.sleep(1.0)
    dump("edit_sheet", "expect the Taken/Skipped toggle")
    back()
    time.sleep(1.0)
    dump("overview_after_sheet", "the sheet's dismissal writes the event back")
step("edit sheet", edit_sheet)

def popup_after_taken():
    tap("id:stateButton")
    time.sleep(0.8)
    dump("popup_after_taken", "expect Skipped / Re-raise / Delete")
    back()
    time.sleep(0.6)
step("popup after taken", popup_after_taken)

# ---------------------------------------------------------------- 8. empty medicine name
def empty_name():
    tap_first("id:nav_medicines", "text:Medicine", "desc:Medicines tab")
    time.sleep(1.0)
    tap_first("id:addMedicine", "text:Add medicine")
    time.sleep(0.6)
    tap("text:OK")
    time.sleep(1.5)
    dump("after_empty_name", "prediction: accepted, edit screen with an empty title")
    back()
    time.sleep(1.0)
    dump("medicines_after_empty_name")
step("empty medicine name", empty_name)

# ---------------------------------------------------------------- 9. database read-back
def db_readback():
    q = ("PRAGMA journal_mode; "
         "SELECT medicineId, medicineName, amount, unit, cannotBeSkipped FROM Medicine; "
         "SELECT reminderId, medicineRelId, timeInMinutes, amount, createdTimestamp, active FROM Reminder; "
         "SELECT reminderEventId, reminderId, status, remindedTimestamp, processedTimestamp, "
         "stockHandled, stockBefore, stockAfter, stockUnit FROM ReminderEvent;")
    out = adb("shell", f'run-as {PKG} sqlite3 databases/medTimer "{q}"')
    ls = adb("shell", f"run-as {PKG} ls -l databases/")
    with open(os.path.join(OUT, "db_after_probe.txt"), "w") as fh:
        fh.write(f"# {datetime.datetime.now().isoformat()}\n# {q}\n{out}\n\n# ls -l databases/\n{ls}\n")
    print(out)
    print(ls)
    return out.splitlines()[:1]
step("database read-back", db_readback)

d.quit()
print("\n==== SUMMARY")
for s in summary:
    print(f"  {s[1]:4s} {s[0]:28s} {s[2]}")
