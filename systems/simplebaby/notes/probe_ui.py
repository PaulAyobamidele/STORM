#!/usr/bin/env python
"""probe_ui.py -- walk the SimpleBaby screens the System Interface needs and
dump the real view hierarchy (UiAutomator XML, a compact listing, a
screenshot) for each, so every selector in properties/concrete_domain.yml is
read off the running app, not guessed. It also exercises the nominal
predictions of observed_behaviour.md live and prints what it saw.

    .venv/bin/python systems/simplebaby/notes/probe_ui.py <step> [<step> ...]

Steps (run in order on a fresh install; each is best-effort and dumps on
failure): welcome signup child feed_form feed_save history invalid delete
sleep overnight timer guest.

    APPIUM_URL  default http://127.0.0.1:4723
    DEVICE      default emulator-5556
Output: systems/simplebaby/notes/ui/NN_<name>.{xml,txt,png}
"""
import os, sys, time, re, json, subprocess, datetime
from xml.etree import ElementTree as ET

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy

PKG = "com.anonymous.bt_sdk53"
APPIUM_URL = os.environ.get("APPIUM_URL", "http://127.0.0.1:4723")
DEVICE = os.environ.get("DEVICE", "emulator-5556")
ADB = os.path.join(os.environ.get("ANDROID_HOME", "/opt/homebrew/share/android-commandlinetools"),
                   "platform-tools", "adb")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
os.makedirs(OUT, exist_ok=True)
STATE = os.path.join(OUT, "probe_state.json")

ITEM, AMOUNT, CHILD = "Apple sauce", "4 oz", "Robin"

state = json.load(open(STATE)) if os.path.exists(STATE) else {"n": 0}


def save_state():
    json.dump(state, open(STATE, "w"), indent=1)


def adb(*args, timeout=60):
    r = subprocess.run([ADB, "-s", DEVICE, *args], capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()


def connect():
    caps = {"platformName": "Android", "automationName": "UiAutomator2",
            "udid": DEVICE, "appPackage": PKG, "appActivity": ".MainActivity",
            "noReset": True, "autoLaunch": False, "newCommandTimeout": 600,
            "uiautomator2ServerLaunchTimeout": 120000}
    return webdriver.Remote(APPIUM_URL, options=UiAutomator2Options().load_capabilities(caps))


d = connect()


def dump(name, note=""):
    state["n"] += 1
    save_state()
    base = os.path.join(OUT, f"{state['n']:02d}_{name}")
    xml = d.page_source
    open(base + ".xml", "w").write(xml)
    lines = [f"# {state['n']:02d}_{name}  {note}", ""]
    try:
        for e in ET.fromstring(xml).iter():
            a = e.attrib
            if not a.get("class"):
                continue
            keep = {k: a.get(k) for k in ("resource-id", "text", "content-desc") if a.get(k)}
            flags = [f for f in ("clickable", "checked", "focused") if a.get(f) == "true"]
            if keep or flags:
                lines.append(f"<{a['class'].split('.')[-1]}> {keep} {' '.join(flags)} bounds={a.get('bounds')}")
    except ET.ParseError as ex:
        lines.append(f"(xml parse error: {ex})")
    open(base + ".txt", "w").write("\n".join(lines) + "\n")
    try:
        d.get_screenshot_as_file(base + ".png")
    except Exception:
        pass
    print(f"  dumped {state['n']:02d}_{name} ({len(lines) - 2} nodes)")


def find(sel, t=10):
    end = time.time() + t
    while time.time() < end:
        els = d.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, sel)
        if els:
            return els[0]
        time.sleep(0.4)
    return None


def rid(x):
    return f'new UiSelector().resourceId("{x}")'


def text(x):
    return f'new UiSelector().text("{x}")'


def dismiss_logbox():
    """The dev build's LogBox banner covers the bottom of the screen; its
    close control is the last clickable child of the banner."""
    b = d.find_elements(AppiumBy.ANDROID_UIAUTOMATOR,
                        'new UiSelector().descriptionContains("Open debugger to view warnings")')
    if b:
        kids = b[0].find_elements(AppiumBy.CLASS_NAME, "android.view.ViewGroup")
        if kids:
            kids[-1].click()
            time.sleep(0.5)


def tap(sel, t=10):
    dismiss_logbox()
    el = find(sel, t)
    if el is None:
        raise RuntimeError(f"not found: {sel}")
    el.click()
    time.sleep(0.6)


def type_into(sel, value, t=10):
    el = find(sel, t)
    if el is None:
        raise RuntimeError(f"not found: {sel}")
    el.click()
    el.clear()
    el.send_keys(value)
    try:
        if d.is_keyboard_shown():
            d.hide_keyboard()
    except Exception:
        pass
    time.sleep(0.4)


def alert_text():
    parts = []
    for r in (f"{PKG}:id/alert_title", "android:id/alertTitle", "android:id/message"):
        els = d.find_elements(AppiumBy.ID, r)
        if els:
            parts.append(els[0].text)
    return " | ".join(parts)


def close_alert(label="OK"):
    b = find(f'new UiSelector().resourceId("android:id/button1")', 3)
    if b is not None:
        b.click()
        time.sleep(0.6)


# ---------------------------------------------------------------- steps
def welcome():
    d.activate_app(PKG)
    time.sleep(4)
    dump("welcome", f"current package {d.current_package}")


def signup():
    if find(rid("sign-up-first-name"), 2) is None:
        tap(rid("sign-up-button"))
    dump("signup_form")
    email = f"probe{datetime.datetime.now():%H%M%S}@example.com"
    state["email"] = email
    save_state()
    type_into(rid("sign-up-first-name"), "Probe")
    type_into(rid("sign-up-last-name"), "Tester")
    type_into(rid("sign-up-email"), email)
    type_into(rid("sign-up-password-initial"), "probe-pass-1")
    type_into(rid("sign-up-password-confirm"), "probe-pass-1")
    tap(rid("sign-up-sign-up-button"))
    time.sleep(5)
    dump("after_signup", f"email {email}; alert: {alert_text()!r}")


def child():
    dump("child_popup")
    type_into(rid("add-child-name"), CHILD)
    tap(rid("add-child-save-button"))
    time.sleep(3)
    dump("home_after_child", f"alert: {alert_text()!r}")
    close_alert()


def feed_form():
    tap(rid("feeding-button"))
    time.sleep(2)
    dump("feeding_form")


def feed_save():
    type_into(rid("feeding-item-name"), ITEM)
    type_into(rid("feeding-amount"), AMOUNT)
    dump("feeding_filled")
    tap(rid("feeding-save-log-button"))
    time.sleep(3)
    dump("feeding_saved_alert", f"alert: {alert_text()!r}")
    close_alert()
    dump("home_after_save")


def history():
    tap(text("Logs"))
    time.sleep(1.5)
    dump("logs_tab")
    tap(rid("logs-feeding-button"))
    time.sleep(3)
    dump("feeding_history")


def invalid():
    d.back()
    time.sleep(1)
    tap(text("Trackers"))
    tap(rid("feeding-button"))
    type_into(rid("feeding-item-name"), ITEM)
    tap(rid("feeding-save-log-button"))
    time.sleep(2)
    dump("invalid_alert", f"alert: {alert_text()!r}")
    close_alert()
    d.back()
    time.sleep(1)


def delete():
    tap(text("Logs"))
    tap(rid("logs-feeding-button"))
    time.sleep(3)
    tap(rid("log-item-delete-button"))
    time.sleep(1)
    dump("delete_dialog", f"alert: {alert_text()!r}")
    tap(text("DELETE") if find(text("DELETE"), 2) else text("Delete"))
    time.sleep(3)
    dump("history_after_delete")
    d.back()
    time.sleep(1)


def sleep_screen():
    tap(text("Trackers"))
    tap(rid("sleep-button"))
    time.sleep(2)
    dump("sleep_form")
    tap(rid("sleep-manual-start-time"))
    time.sleep(1.5)
    dump("sleep_time_picker")
    d.back()
    time.sleep(1)


def timer():
    tap(rid("sleep-stopwatch-start"))
    time.sleep(3)
    dump("stopwatch_running")
    tap(rid("sleep-stopwatch-stop"))
    dump("stopwatch_stopped")


STEPS = {"welcome": welcome, "signup": signup, "child": child, "feed_form": feed_form,
         "feed_save": feed_save, "history": history, "invalid": invalid, "delete": delete,
         "sleep": sleep_screen, "timer": timer}

def set_time(button_rid, hour, minute, ampm):
    """Open a native time picker, switch it to text input, type the time."""
    tap(rid(button_rid))
    time.sleep(1)
    tap(rid("android:id/toggle_mode"))
    time.sleep(0.8)
    if state.get("dumped_text_picker") is None:
        dump("time_picker_text_mode")
        state["dumped_text_picker"] = True
        save_state()
    for r, v in (("android:id/input_hour", hour), ("android:id/input_minute", minute)):
        el = find(rid(r), 5)
        if el is None:
            raise RuntimeError(f"not found: {r}")
        el.click()
        el.clear()
        el.send_keys(v)
        time.sleep(0.3)
    tap(rid("android:id/am_pm_spinner"))
    tap(text(ampm))
    tap(rid("android:id/button1"))
    time.sleep(0.8)


def overnight():
    if find(rid("sleep-manual-start-time"), 2) is None:
        tap(text("Trackers"))
        tap(rid("sleep-button"))
        time.sleep(2)
    tap(rid("sleep-reset-form-button"))
    set_time("sleep-manual-start-time", "10", "00", "PM")
    set_time("sleep-manual-end-time", "6", "00", "AM")
    dump("overnight_filled")
    tap(rid("sleep-save-log-button"))
    time.sleep(3)
    dump("overnight_after_save", f"alert: {alert_text()!r}")
    close_alert()


def same_day():
    if find(rid("sleep-manual-start-time"), 2) is None:
        tap(text("Trackers"))
        tap(rid("sleep-button"))
        time.sleep(2)
    tap(rid("sleep-reset-form-button"))
    set_time("sleep-manual-start-time", "1", "00", "PM")
    set_time("sleep-manual-end-time", "2", "00", "PM")
    tap(rid("sleep-save-log-button"))
    time.sleep(3)
    dump("same_day_after_save", f"alert: {alert_text()!r}")
    close_alert()


STEPS.update({"overnight": overnight, "same_day": same_day})


def doze():
    """Stopwatch started, app backgrounded, Doze forced for 60 s, app back."""
    if find(rid("sleep-stopwatch-start"), 2) is None:
        tap(text("Trackers"))
        tap(rid("sleep-button"))
        time.sleep(2)
    tap(rid("sleep-stopwatch-reset"))
    tap(rid("sleep-stopwatch-start"))
    t0 = time.time()
    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    print("  force-idle:", adb("shell", "dumpsys", "deviceidle", "force-idle"))
    time.sleep(60)
    print("  unforce:", adb("shell", "dumpsys", "deviceidle", "unforce"))
    d.activate_app(PKG)
    time.sleep(2)
    wall = int(time.time() - t0)
    clocks = [e.text for e in d.find_elements(AppiumBy.ANDROID_UIAUTOMATOR,
              'new UiSelector().resourceId("sleep-stopwatch").childSelector(new UiSelector().textMatches("[0-9][0-9]"))')]
    dump("doze_after_return", f"wall {wall}s, stopwatch {clocks}")
    print(f"  wall clock {wall} s, stopwatch reads {clocks}")
    tap(rid("sleep-stopwatch-stop"))


def background():
    """The same without Doze: backgrounded 60 s."""
    if find(rid("sleep-stopwatch-start"), 2) is None:
        tap(text("Trackers"))
        tap(rid("sleep-button"))
        time.sleep(2)
    tap(rid("sleep-stopwatch-reset"))
    tap(rid("sleep-stopwatch-start"))
    t0 = time.time()
    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    time.sleep(60)
    d.activate_app(PKG)
    time.sleep(2)
    wall = int(time.time() - t0)
    clocks = [e.text for e in d.find_elements(AppiumBy.ANDROID_UIAUTOMATOR,
              'new UiSelector().resourceId("sleep-stopwatch").childSelector(new UiSelector().textMatches("[0-9][0-9]"))')]
    dump("background_after_return", f"wall {wall}s, stopwatch {clocks}")
    print(f"  wall clock {wall} s, stopwatch reads {clocks}")
    tap(rid("sleep-stopwatch-stop"))


STEPS.update({"doze": doze, "background": background})


def to_home():
    for _ in range(4):
        if find(rid("feeding-button"), 2) is not None:
            return
        back = find('new UiSelector().descriptionContains("Back")', 1)
        if back is not None:
            back.click()
        else:
            d.back()
        time.sleep(1)
    tap(text("Trackers"))


def guest():
    to_home()
    tap(rid("header-link"))
    time.sleep(2)
    dump("profile_signed_in")
    tap(rid("profile-sign-out-button"))
    time.sleep(3)
    dump("after_sign_out")
    tap(rid("guest-button"))
    time.sleep(1.5)
    dump("guest_screen")
    tap(rid("guest-continue-button"))
    time.sleep(3)
    dump("guest_child_popup")
    type_into(rid("add-child-name"), CHILD)
    tap(rid("add-child-save-button"))
    time.sleep(2)
    tap(rid("feeding-button"))
    type_into(rid("feeding-item-name"), ITEM)
    type_into(rid("feeding-amount"), AMOUNT)
    tap(rid("feeding-save-log-button"))
    time.sleep(2)
    dump("guest_saved_alert", f"alert: {alert_text()!r}")
    close_alert()
    tap(text("Logs"))
    tap(rid("logs-feeding-button"))
    time.sleep(2)
    dump("guest_history")


def guest_relaunch():
    d.terminate_app(PKG)
    d.activate_app(PKG)
    time.sleep(5)
    dump("guest_after_relaunch")


STEPS.update({"guest": guest, "guest_relaunch": guest_relaunch})


if __name__ == "__main__":
    for s in sys.argv[1:]:
        print(f"== {s}")
        try:
            STEPS[s]()
        except Exception as ex:
            print(f"  !! {s}: {ex.__class__.__name__}: {str(ex)[:200]}")
            dump(f"fail_{s}")
            break
    d.quit()
