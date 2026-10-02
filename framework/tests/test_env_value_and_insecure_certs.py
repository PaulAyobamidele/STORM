"""Self-test for two opt-in, SUT-agnostic hooks:

  * "@env:NAME" in a concrete value is typed as the environment variable's
    value; the placeholder is returned unchanged (and an error logged) when
    the variable is not set; "@date" and plain values behave as before.
  * concrete_domain.browser.accept_insecure_certs turns on certificate
    acceptance in Chrome and Firefox; absent or false, the options are the
    same as before.

    .venv/bin/python -m pytest framework/tests/test_env_value_and_insecure_certs.py -q
"""
import datetime
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from concretization.algorithm import ConcretizationAlgorithm  # noqa: E402
from concretization import executors  # noqa: E402

A = ConcretizationAlgorithm.__new__(ConcretizationAlgorithm)


def test_env_value_is_read_from_the_environment(monkeypatch):
    monkeypatch.setenv("IOCO_TEST_SECRET", "s3cret")
    assert A._materialise_value("@env:IOCO_TEST_SECRET") == "s3cret"


def test_env_value_missing_is_left_as_is(monkeypatch):
    monkeypatch.delenv("IOCO_TEST_ABSENT", raising=False)
    assert A._materialise_value("@env:IOCO_TEST_ABSENT") == "@env:IOCO_TEST_ABSENT"


def test_other_values_unchanged():
    assert A._materialise_value("hello") == "hello"
    assert A._materialise_value("") == ""
    assert A._materialise_value(None) is None
    assert A._materialise_value("@env:") == "@env:"          # not a valid name
    want = (datetime.date.today() - datetime.timedelta(days=8)).isoformat()
    assert A._materialise_value("@date-8") == want


class _FakeDriver:
    def __init__(self, options=None):
        self.options = options

    def implicitly_wait(self, _):
        pass


def _driver_for(browser, element_map, monkeypatch):
    import selenium.webdriver as wd
    monkeypatch.setattr(wd, "Chrome", _FakeDriver)
    monkeypatch.setattr(wd, "Firefox", _FakeDriver)
    ex = executors.HTMLExecutor.__new__(executors.HTMLExecutor)
    ex.element_map = element_map
    ex.headless = True
    ex.implicit_wait = 0
    return ex._init_driver(browser).options


def _flags(opts):
    caps = opts.to_capabilities()
    args = list(getattr(opts, "arguments", []))
    return bool(caps.get("acceptInsecureCerts")), "--ignore-certificate-errors" in args


def test_chrome_default_is_unchanged(monkeypatch):
    assert _flags(_driver_for("chrome", {}, monkeypatch)) == (False, False)
    off = {"concrete_domain": {"browser": {"accept_insecure_certs": False}}}
    assert _flags(_driver_for("chrome", off, monkeypatch)) == (False, False)


def test_chrome_opt_in(monkeypatch):
    on = {"concrete_domain": {"browser": {"accept_insecure_certs": True}}}
    assert _flags(_driver_for("chrome", on, monkeypatch)) == (True, True)


def test_firefox_opt_in(monkeypatch):
    on = {"concrete_domain": {"browser": {"accept_insecure_certs": True}}}
    accept, _ = _flags(_driver_for("firefox", on, monkeypatch))
    assert accept
    # off: exactly Selenium's own Firefox default, whatever that is (it
    # already accepts insecure certificates), i.e. the hook changes nothing
    from selenium.webdriver.firefox.options import Options as FirefoxOpts
    default = bool(FirefoxOpts().to_capabilities().get("acceptInsecureCerts"))
    accept, _ = _flags(_driver_for("firefox", {}, monkeypatch))
    assert accept == default
