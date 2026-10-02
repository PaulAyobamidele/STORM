# CODEX EDUCATIONAL COMMENTS START
# In the concretization story, executors.py is the hands and eyes: algorithm.py asks it to perform concrete UI actions or wait for visible outputs, while LNTSIExecutorAdapter uses si_lnt_parser.py trees to run screen-specific traversal before the main gate action.
# CODEX EDUCATIONAL COMMENTS END
# This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
"""
executors.py
Platform-specific executors for the concretization algorithm.

Each executor implements:
    perform(action, values) -> bool
    wait(observe_spec, timeout) -> (value, timed_out)
    close()

Executors available:
    MockExecutor          -- scripted responses for unit testing
    HTMLExecutor          -- Selenium WebDriver for web applications
    HTMLExecutorAdapter   -- wraps HTMLExecutor, handles gate navigation
    AndroidExecutor       -- Appium UIAutomator2 for Android
    IOSExecutor           -- Appium XCUITest for iOS
"""

# `from` chooses a module to read from, `__future__` enables newer Python behavior early, and `import annotations` lets type hints be stored lazily so this file can use modern type syntax.
from __future__ import annotations
# `import` loads a library module so this file can call its functions; the comma-separated names are the helper libraries this line makes available.
import logging
# `import` loads a library module so this file can call its functions; the comma-separated names are the helper libraries this line makes available.
import re
# `import` loads a library module so this file can call its functions; the comma-separated names are the helper libraries this line makes available.
import time
# `from ... import ...` means Python opens another module and brings only the named tools into this file, instead of importing the whole module name.
from abc import ABC, abstractmethod

# This creates a logger named after this module, so messages from this file can be filtered and traced while the concretization run is happening.
logger = logging.getLogger(__name__)


# ===========================================================================
# Base interface
# ===========================================================================

# `class BaseExecutor` defines a new kind of object; `(ABC)` means it inherits behavior or rules from ABC, and the colon starts the indented body of the class.
class BaseExecutor(ABC):

    # `@abstractmethod` marks the next method as required; any real executor subclass must implement it before Python will let that subclass be used normally.
    @abstractmethod
    # `def perform` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> bool` documents the expected return type.
    def perform(self, action: dict, values: dict) -> bool:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """Execute one UI action. Returns True on success."""

    # `@abstractmethod` marks the next method as required; any real executor subclass must implement it before Python will let that subclass be used normally.
    @abstractmethod
    # `def wait` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> tuple[str | None, bool]` documents the expected return type.
    def wait(self, observe_spec: dict, timeout: int) -> tuple[str | None, bool]:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """
        Wait for a system output.
        Returns (observed_value, timed_out).
        observed_value is None if unexpected or not found.
        timed_out is True if nothing appeared within timeout.
        """

    # `def close` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def close(self):
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """Release resources."""
        # `pass` is an intentional no-op: it tells Python 'do nothing here' while keeping the syntax valid.
        pass


# ===========================================================================
# MockExecutor
# ===========================================================================

# `class MockExecutor` defines a new kind of object; `(BaseExecutor)` means it inherits behavior or rules from BaseExecutor, and the colon starts the indented body of the class.
class MockExecutor(BaseExecutor):
    # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
    """
    Scripted mock for testing the algorithm without a browser.

    mock_outputs: list of values returned by wait() in order.
    Special tokens:
        "__TIMEOUT__"  ->  (None, True)    quiescence
        "__FAIL__"     ->  (None, False)   unexpected output
    """

    # `def __init__` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def __init__(self, mock_outputs: list[str] = None, fail_at: set = None):
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.mock_outputs = list(mock_outputs or [])
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.output_index = 0
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.fail_at      = fail_at or set()
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.action_log   = []

    # `def perform` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> bool` documents the expected return type.
    def perform(self, action: dict, values: dict) -> bool:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        gate = action.get("gate", action.get("selector", "unknown"))
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        self.action_log.append({"action": action, "values": values})
        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
        logger.debug(f"MockExecutor.perform: {gate} with {values}")
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate in self.fail_at:
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.info(f"MockExecutor: simulating failure at {gate}")
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return False
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return True

    # `def wait` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> tuple[str | None, bool]` documents the expected return type.
    def wait(self, observe_spec: dict, timeout: int) -> tuple[str | None, bool]:
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if self.output_index >= len(self.mock_outputs):
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.debug("MockExecutor: no more outputs — returning None")
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return None, False
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        value = self.mock_outputs[self.output_index]
        # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
        self.output_index += 1
        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
        logger.debug(f"MockExecutor.wait: returning {value!r}")
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if value == "__TIMEOUT__":
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return None, True
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if value == "__FAIL__":
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return None, False
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return value, False


# ===========================================================================
# HTMLExecutor
# ===========================================================================

# `class HTMLExecutor` defines a new kind of object; `(BaseExecutor)` means it inherits behavior or rules from BaseExecutor, and the colon starts the indented body of the class.
class HTMLExecutor(BaseExecutor):
    # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
    """
    Drives a web application via Selenium WebDriver.

    Understands the structure of html_element_map.yml:

    Action dict fields:
        selector  : element id or CSS selector
        by        : "id" | "css" | "xpath" | "name"  (default "id")
        action    : "clear_and_type" | "click" | "navigate"
        param     : template like "{{USERNAME}}" resolved from values
        gate      : gate name (injected by run.py inject_gate_keys)

    Observe spec fields:
        selector  : element id or CSS selector
        by        : locator strategy  (default "id")
        attribute : "text" | any HTML attribute name  (default "text")

    Wait-for spec fields:
        selector  : element to wait for after action completes
        by        : locator strategy

    Important: selectors in the element map may include a leading "#"
    (CSS selector style). When by=id, the "#" is stripped automatically
    because Selenium's By.ID expects a bare id without the prefix.
    """

    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    BY_MAP = {
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "id":    "ID",
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "css":   "CSS_SELECTOR",
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "xpath": "XPATH",
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "name":  "NAME",
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "class": "CLASS_NAME",
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "tag":   "TAG_NAME",
    # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
    }

    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
    def __init__(
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        self,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        base_url:     str,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        browser:      str  = "chrome",
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        element_map:  dict = None,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        headless:     bool = True,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        implicit_wait: int = 2,
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    ):
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.base_url      = base_url.rstrip("/")
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.element_map   = element_map or {}
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.headless      = headless
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.implicit_wait = implicit_wait
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.driver        = self._init_driver(browser)
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self._fault_mode   = "none"
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self._ue1_offline  = False

        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if self.base_url:
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            self.driver.get(self.base_url)
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.info(f"HTMLExecutor initialized with base URL: {self.base_url}")

    # ------------------------------------------------------------------
    # Driver initialisation
    # ------------------------------------------------------------------

    def _accept_insecure_certs(self) -> bool:
        """True when the SUT's concrete_domain.yml declares

            browser:
              accept_insecure_certs: true

        for a SUT served behind a locally signed certificate. Off unless a
        SUT asks for it, and logged when on, because it also stops the
        browser from noticing a certificate that is genuinely wrong.
        """
        cd = (self.element_map or {}).get("concrete_domain") or {}
        on = bool((cd.get("browser") or {}).get("accept_insecure_certs"))
        if on:
            logger.warning("browser: accepting untrusted TLS certificates "
                           "(concrete_domain.browser.accept_insecure_certs)")
        return on

    # `def _init_driver` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def _init_driver(self, browser: str):
        # `try` starts a protected block: Python attempts the indented code and jumps to `except` if an error happens.
        try:
            # `from ... import ...` means Python opens another module and brings only the named tools into this file, instead of importing the whole module name.
            from selenium import webdriver
            # `from ... import ...` means Python opens another module and brings only the named tools into this file, instead of importing the whole module name.
            from selenium.webdriver.chrome.options  import Options as ChromeOpts
            # `from ... import ...` means Python opens another module and brings only the named tools into this file, instead of importing the whole module name.
            from selenium.webdriver.firefox.options import Options as FirefoxOpts
        # `except` catches an error from the matching `try` block so the concretization run can report or recover instead of crashing immediately.
        except ImportError:
            # `raise` deliberately throws an error; this code uses it when a required invariant or dependency is missing and continuing would hide the real problem.
            raise RuntimeError("Run: pip install selenium")

        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if browser == "chrome":
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            opts = ChromeOpts()
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if self.headless:
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                opts.add_argument("--headless=new")
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            opts.add_argument("--no-sandbox")
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            opts.add_argument("--disable-dev-shm-usage")
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            opts.add_argument("--disable-gpu")
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            opts.add_argument("--window-size=1280,900")
            if self._accept_insecure_certs():
                opts.set_capability("acceptInsecureCerts", True)
                opts.add_argument("--ignore-certificate-errors")
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            driver = webdriver.Chrome(options=opts)

        # `elif` means 'else, if this other condition is true'; Python reaches it only when earlier `if` or `elif` checks in the same chain did not run.
        elif browser == "firefox":
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            opts = FirefoxOpts()
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if self.headless:
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                opts.add_argument("--headless")
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            if self._accept_insecure_certs():
                opts.set_capability("acceptInsecureCerts", True)
            driver = webdriver.Firefox(options=opts)

        # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
        else:
            # `raise` deliberately throws an error; this code uses it when a required invariant or dependency is missing and continuing would hide the real problem.
            raise ValueError(f"Unknown browser: {browser}")

        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        driver.implicitly_wait(self.implicit_wait)
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return driver

    # ------------------------------------------------------------------
    # perform()
    # ------------------------------------------------------------------

    # `def perform` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> bool` documents the expected return type.
    def perform(self, action: dict, values: dict) -> bool:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """
        Execute one action from the element map actions list.

        The action dict looks like:
            {selector: "username-input", by: "id",
             action: "clear_and_type", param: "{{USERNAME}}",
             gate: "REGISTER"}

        values is the concrete_values dict from the algorithm.
        """
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        action_type = action.get("action", "click")

        # ---- Navigate action ------------------------------------------
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if action_type == "navigate":
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            url_template = action.get("url", "/")
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            url = self._substitute(url_template, values)
            # SESSION RESET. A SUT may declare in concrete_domain.yml:
            #     session_reset_url: "/login/logout.php"
            # Navigating there clears the browser's cookies FIRST, ending the
            # session deterministically.
            #
            # This exists because logging out through the UI is not reliably
            # driveable. Moodle's /login/logout.php renders a CSRF-confirmation
            # page whose Continue button is type="submit" inside a form
            # carrying a VALID sesskey -- and clicking it does NOT end the
            # session (verified repeatedly in a real browser: the user stayed
            # logged in). Only GET /login/logout.php?sesskey=<runtime value>
            # works, and a route cannot carry a runtime value.
            #
            # Without this an SI cannot switch actors, so every gate belonging
            # to a second role is undriveable -- for Moodle that is
            # OPEN_GRADING and GRADE_SUBMISSION, i.e. the entire stale-grade
            # property, which would silently degrade to INCONCLUSIVE. The key
            # is declared PER SUT, so the framework keeps no knowledge of any
            # particular system.
            _cd = (self.element_map or {}).get("concrete_domain") or {}
            _reset = _cd.get("session_reset_url")
            if _reset and url.split("?")[0] == str(_reset).split("?")[0]:
                try:
                    self.driver.delete_all_cookies()
                    logger.info("  session reset: browser cookies cleared")
                except Exception as e:
                    logger.warning(f"  session reset failed: {e}")
            self.driver.get(self.base_url + url)
            logger.debug(f"Navigated to {url}")
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return True

        # ---- Resolve concrete value for this action's param -----------
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        param_template = action.get("param", "")
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        concrete_value = self._resolve_param(param_template, values)

        # ---- Find the element -----------------------------------------
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        selector = action.get("selector", "")
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        by_str   = action.get("by", "id")

        # Strip leading # when using By.ID — YAML may use CSS-style ids
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if by_str.lower() == "id" and selector.startswith("#"):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            selector = selector[1:]

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        element = self._find_element(selector, by_str, timeout=10)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if element is None:
            # `try` starts a protected block: Python attempts the indented code and jumps to `except` if an error happens.
            try:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                url = self.driver.current_url
            # `except` catches an error from the matching `try` block so the concretization run can report or recover instead of crashing immediately.
            except Exception:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                url = "<session closed>"
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.error(f"Element not found: '{selector}' (by={by_str}) on {url}")
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return False

        # ---- Execute the action ---------------------------------------
        # `try` starts a protected block: Python attempts the indented code and jumps to `except` if an error happens.
        try:
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if action_type == "clear_and_type":
                # JS ASSIGNMENT IS THE PRIMARY PATH, for the same reason as
                # click below: native input dispatch does nothing in this
                # environment and reports success while doing it.
                #
                # Measured on Moodle 4.5 / Chrome 151 headless, on a textarea
                # verified displayed=True, enabled=True, readonly=None:
                #     element.clear(); element.send_keys("X")  -> value stays ''
                #     JS value= + input/change events          -> value is "X"
                #
                # The consequence was worse than a visible failure: the typing
                # "succeeded", the form was then submitted, and Moodle stored
                # an EMPTY submission. Every downstream oracle then read an
                # empty page and the run reported a state the tester had
                # created itself.
                #
                # The input and change events are dispatched explicitly because
                # assigning .value does not fire them, and any framework
                # listening for them (mform validation, autosave) would
                # otherwise never see the edit.
                _val = str(concrete_value)
                try:
                    # THE VALUE MUST GO THROUGH THE NATIVE SETTER.
                    #
                    # `e.value = v` looks right and is wrong for any framework
                    # with controlled inputs. React replaces the `value`
                    # property on the element instance with its own tracker; a
                    # direct assignment writes past it, so when the `input`
                    # event fires React compares against its tracked value,
                    # sees no change, and never runs onChange. The field shows
                    # the text and the form's state stays empty.
                    #
                    # Observed on Spliit (React + react-hook-form): the group
                    # name was typed, the DOM read it back correctly, and the
                    # form refused to submit because its own state held "".
                    # Plain server-rendered forms (e.g. Moodle) work either
                    # way, which is why this went unnoticed.
                    #
                    # Calling the prototype's setter writes through the tracker
                    # and is equivalent to a direct assignment everywhere else.
                    self.driver.execute_script(
                        "const e=arguments[0], v=arguments[1];"
                        "e.focus();"
                        "const proto = (window.HTMLTextAreaElement &&"
                        "  e instanceof window.HTMLTextAreaElement)"
                        "  ? window.HTMLTextAreaElement.prototype"
                        "  : window.HTMLInputElement.prototype;"
                        "const d = Object.getOwnPropertyDescriptor(proto,'value');"
                        "if (d && d.set) { d.set.call(e, v); } else { e.value = v; }"
                        "e.dispatchEvent(new Event('input',{bubbles:true}));"
                        "e.dispatchEvent(new Event('change',{bubbles:true}));",
                        element, _val)
                except Exception as e:
                    logger.info(f"  JS typing raised {e.__class__.__name__}; "
                                f"falling back to send_keys")
                    element.clear()
                    element.send_keys(_val)
                logger.debug(f"Typed {concrete_value!r} into {selector}")

            # `elif` means 'else, if this other condition is true'; Python reaches it only when earlier `if` or `elif` checks in the same chain did not run.
            elif action_type in ("click", "tap"):
                # JS CLICK IS THE PRIMARY PATH, NOT A FALLBACK.
                #
                # Selenium's native click is unreliable against this SUT and
                # fails SILENTLY -- no exception, no error, the click simply
                # does nothing and the walk carries on until some later
                # wait_for times out and the verdict blames the wrong step.
                #
                # Measured repeatedly on Moodle 4.5 / Chrome 151 headless:
                #   native element.click()          -> no-op
                #   JS arguments[0].click()         -> works
                #   JS form.submit()                -> works
                # on "Add submission", "Save changes" and the logout
                # confirmation. The element was verified to be visible, inside
                # the viewport, and the TOPMOST node at its own centre
                # (document.elementFromPoint returned the button itself), so
                # this is NOT an overlay intercepting the click -- an
                # explanation I gave earlier and could not substantiate. The
                # login button worked natively, which is what made a systemic
                # problem look like a per-element one.
                #
                # CORRECTION: "Attempt quiz" was in that working list and does
                # NOT belong there. Its form is intercepted by a Moodle AMD
                # module that calls preventDefault() and opens a confirmation
                # modal; in headless the module resolves erratically, so the JS
                # click left the page on view.php with no attempt created and no
                # error -- measured across three runs, the modal appearing once
                # at ~3s and never within 15s on the other two. That is why the
                # submit fallback below exists.
                #
                # THE TRADE-OFF, stated plainly: a JS click bypasses the
                # browser's interactability checks, so it can click something a
                # real user could not reach. That is acceptable here because
                # what is under test is Moodle's SERVER-SIDE behaviour, and
                # because reachability is already asserted separately by the
                # gate's wait_for precondition. It would NOT be acceptable if
                # the properties under test were about UI affordances.
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                        element)
                except Exception:
                    pass
                # Is this a classic form-post submit control? Only those are
                # eligible for the requestSubmit fallback: an AJAX button that
                # legitimately does not navigate must not be force-posted.
                try:
                    _submits = self.driver.execute_script(
                        "const e = arguments[0];"
                        "const f = e.form || (e.closest && e.closest('form'));"
                        "if (!f) return false;"
                        "const t = (e.getAttribute('type') || '').toLowerCase();"
                        "const isSubmit = t === 'submit' ||"
                        "  (e.tagName === 'BUTTON' && t !== 'button' && t !== 'reset');"
                        "return !!(isSubmit && f.getAttribute('action'));",
                        element)
                except Exception:
                    _submits = False

                _href_before = None
                if _submits:
                    try:
                        _href_before = self.driver.execute_script("return location.href;")
                    except Exception:
                        _submits = False

                # SECOND CORRECTION: a bare `arguments[0].click()` is not
                # enough either. It dispatches ONE event, `click`, and
                # component libraries built on pointer events never see it.
                # Measured on Spliit (Radix Tabs, Chrome headless):
                #   native element.click()          -> Stats tab activates, 1s
                #   JS arguments[0].click()         -> nothing, still on the
                #                                      expense list after 8s
                # Radix activates a tab on `mousedown` (button 0, no ctrl), so
                # a click event alone is a no-op for it. The Moodle measurement
                # above says the opposite of the native click. Both hold.
                #
                # Resolution: dispatch what a real click is, the WHOLE
                # sequence -- pointerdown, mousedown, pointerup, mouseup, then
                # the click with its activation behaviour (form submit, link
                # navigation). This is a superset of the JS click Moodle was
                # validated on, and the mousedown carries the activation Radix
                # keys on. Every element gets exactly the events a user's click
                # gives it, so no handler sees something new. The native click
                # stays as the fallback should the script itself raise.
                #
                # DOWN AND UP ARE TWO DRIVER CALLS, NOT ONE. A real pointer's
                # down and up arrive in separate browser tasks, and the page
                # renders in between: a Radix Select opens on pointerdown,
                # mounts its listbox, and arms a one-shot document `pointerup`
                # guard that swallows the up which follows a click-through.
                # Dispatched in one script nothing renders between the events,
                # the guard is armed AFTER the trigger's up and fires on the
                # OPTION's up instead, and the option is never selected: the
                # payer stayed unset and the expense was silently not created
                # (measured, probe_click_seq.py). One driver round-trip between
                # down and up gives React its flush, as the browser would.
                # Shared prologue: the element's centre as the event position,
                # arguments[1] is the phase ('down' | 'up').
                _phase = (
                    "const e = arguments[0], down = arguments[1] === 'down';"
                    "const r = e.getBoundingClientRect();"
                    "const opts = {bubbles: true, cancelable: true, composed: true,"
                    "  button: 0, buttons: down ? 1 : 0, view: window,"
                    "  clientX: r.left + r.width / 2, clientY: r.top + r.height / 2};"
                    "if (window.PointerEvent) {"
                    "  e.dispatchEvent(new PointerEvent(down ? 'pointerdown' : 'pointerup',"
                    "    Object.assign({pointerId: 1, pointerType: 'mouse', isPrimary: true}, opts)));"
                    "}"
                    "e.dispatchEvent(new MouseEvent(down ? 'mousedown' : 'mouseup', opts));"
                    "if (down) { if (e.focus) { try { e.focus(); } catch (err) { } } }"
                    "else { e.click(); }")
                try:
                    self.driver.execute_script(_phase, element, "down")
                    self.driver.execute_script(_phase, element, "up")
                except Exception as e:
                    logger.info(f"  scripted pointer sequence raised "
                                f"{e.__class__.__name__}; falling back to native click")
                    element.click()
                logger.debug(f"Clicked {selector}")

                # A submit button that did not navigate had its default action
                # cancelled by a page script. Re-submit the form directly, which
                # bypasses the handler and performs the post the button stands
                # for. Verified on "Attempt quiz": the JS click leaves the URL
                # on view.php, while requestSubmit reaches startattempt.php and
                # the attempt is created.
                #
                # requestSubmit(element) rather than form.submit(): it carries
                # the submitter's name/value, which Moodle's mforms rely on to
                # tell one submit button from another, and it still runs
                # constraint validation.
                if _submits and _href_before is not None:
                    _deadline = time.time() + 2.0
                    _moved = False
                    while time.time() < _deadline:
                        try:
                            if self.driver.execute_script(
                                    "return location.href;") != _href_before:
                                _moved = True
                                break
                        except Exception:
                            # Mid-navigation the context can be torn down; that
                            # is itself evidence the click took effect.
                            _moved = True
                            break
                        time.sleep(0.15)
                    if not _moved:
                        logger.info(f"  {selector}: JS click did not navigate — "
                                    f"the form's default action was cancelled; "
                                    f"submitting the form directly")
                        try:
                            self.driver.execute_script(
                                "const e = arguments[0];"
                                "const f = e.form || e.closest('form');"
                                "try { if (f.requestSubmit) { f.requestSubmit(e); return; } }"
                                "catch (err) { }"
                                "if (f.requestSubmit) { f.requestSubmit(); } else { f.submit(); }",
                                element)
                        except Exception as e:
                            logger.warning(f"  form submit fallback failed: {e}")

                # After a click, probe the gate's wait_for spec with a short
                # timeout so page redirects can settle before the next action.
                # Short (2s) so intermediate UI clicks (e.g. dropdown selection)
                # fail fast instead of blocking for the full 10-second timeout.
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                gate_name = action.get("gate")
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if gate_name:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    gate_spec = self.element_map.get(
                        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                        "gates", {}).get(gate_name, {})
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    wait_for = gate_spec.get("wait_for")
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if wait_for:
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        wsel = wait_for.get("selector", "")
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        wby  = wait_for.get("by", "id")
                        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                        if wby.lower() == "id" and wsel.startswith("#"):
                            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                            wsel = wsel[1:]
                        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                        self._find_element(wsel, wby, timeout=2)

            # `elif` means 'else, if this other condition is true'; Python reaches it only when earlier `if` or `elif` checks in the same chain did not run.
            elif action_type == "type":
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                element.send_keys(str(concrete_value))
                # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                logger.debug(f"Sent keys {concrete_value!r} to {selector}")

            # `elif` means 'else, if this other condition is true'; Python reaches it only when earlier `if` or `elif` checks in the same chain did not run.
            elif action_type == "select":
                # `from ... import ...` means Python opens another module and brings only the named tools into this file, instead of importing the whole module name.
                from selenium.webdriver.support.ui import Select
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                Select(element).select_by_visible_text(str(concrete_value))

            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return True

        # `except` catches an error from the matching `try` block so the concretization run can report or recover instead of crashing immediately.
        except Exception as e:
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.error(f"perform() failed on {selector}: {e}")
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return False

    # ------------------------------------------------------------------
    # wait()
    # ------------------------------------------------------------------

    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
    def wait(
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        self, observe_spec: dict, timeout: int
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    ) -> tuple[str | None, bool]:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """
        Wait for an element and capture its value.

        observe_spec from element map:
            {selector: "zone-value", by: "id", attribute: "text"}
        """
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        selector  = observe_spec.get("selector", "")
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        by_str    = observe_spec.get("by", "id")
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        attribute = observe_spec.get("attribute", "text")

        # Strip leading # when using By.ID
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if by_str.lower() == "id" and selector.startswith("#"):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            selector = selector[1:]

        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if not selector:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return None, False

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        element = self._find_element(selector, by_str, timeout=timeout)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if element is None:
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            logger.info(
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                f"wait() timed out waiting for #{selector} "
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                f"on {self.driver.current_url}"
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return None, True

        # `try` starts a protected block: Python attempts the indented code and jumps to `except` if an error happens.
        try:
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if attribute == "text":
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                value = element.text.strip()
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if not value:
                    # Fallback to innerText via JS for elements where
                    # .text is empty (e.g. span with only child nodes)
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    value = self.driver.execute_script(
                        # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                        "return arguments[0].innerText;", element
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    ).strip()
            # `elif` means 'else, if this other condition is true'; Python reaches it only when earlier `if` or `elif` checks in the same chain did not run.
            elif attribute == "value":
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                value = element.get_attribute("value") or ""
            # `elif` means 'else, if this other condition is true'; Python reaches it only when earlier `if` or `elif` checks in the same chain did not run.
            elif attribute == "url_group_id":
                # `import` loads a library module so this file can call its functions; the comma-separated names are the helper libraries this line makes available.
                import re as _re
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                current_url = self.driver.current_url
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                m = _re.search(r'/groups/(?!new\b)([a-zA-Z0-9_-]{5,})', current_url)
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                value = m.group(1) if m else ""
            # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
            else:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                value = element.get_attribute(attribute) or ""

            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.debug(f"Observed #{selector} -> {value!r}")
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return value.lower() if value else None, False

        # `except` catches an error from the matching `try` block so the concretization run can report or recover instead of crashing immediately.
        except Exception as e:
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.error(f"wait() capture failed on #{selector}: {e}")
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return None, False

    # ------------------------------------------------------------------
    # Admin helpers
    # ------------------------------------------------------------------

    # `def set_ue1_offline` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def set_ue1_offline(self, offline: bool):
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """Set browser network to offline/online via Chrome DevTools Protocol."""
        # `try` starts a protected block: Python attempts the indented code and jumps to `except` if an error happens.
        try:
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            self.driver.execute_cdp_cmd("Network.emulateNetworkConditions", {
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                "offline":           offline,
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                "latency":           0,
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                "downloadThroughput": -1,
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                "uploadThroughput":   -1,
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            })
            # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
            self._ue1_offline = offline
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            state = "offline" if offline else "online"
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.info(f"Browser network set to {state} via CDP")
        # `except` catches an error from the matching `try` block so the concretization run can report or recover instead of crashing immediately.
        except Exception as e:
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.warning(f"set_ue1_offline({offline}) failed: {e}")

    # `def reset_sut` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def reset_sut(self):
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """
        POST /admin/reset on the SUT to clear server state.
        Also clears browser cookies to reset the Flask session.
        Both are required for clean test isolation between TCs.
        """
        # `import` loads a library module so this file can call its functions; the comma-separated names are the helper libraries this line makes available.
        import urllib.request
        # `try` starts a protected block: Python attempts the indented code and jumps to `except` if an error happens.
        try:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            req = urllib.request.Request(
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                self.base_url + "/admin/reset",
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                data=b"",
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                method="POST"
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            urllib.request.urlopen(req, timeout=5)
            # Clear browser cookies — this resets the Flask session
            # so each TC starts as a genuinely new user
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            self.driver.delete_all_cookies()
            # Restore browser network if a previous TC set it offline
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if self._ue1_offline:
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                self.set_ue1_offline(False)
            # Re-apply the stored fault mode if one was set
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if self._fault_mode and self._fault_mode != "none":
                # `try` starts a protected block: Python attempts the indented code and jumps to `except` if an error happens.
                try:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    req2 = urllib.request.Request(
                        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                        self.base_url + f"/admin/fault/{self._fault_mode}",
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        data=b"",
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        method="POST"
                    # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                    )
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    urllib.request.urlopen(req2, timeout=5)
                    # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                    logger.info(f"SUT fault mode re-applied: {self._fault_mode}")
                # `except` catches an error from the matching `try` block so the concretization run can report or recover instead of crashing immediately.
                except Exception as e2:
                    # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                    logger.warning(f"Re-apply fault mode failed: {e2}")
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.info("SUT state reset via /admin/reset")
        # `except` catches an error from the matching `try` block so the concretization run can report or recover instead of crashing immediately.
        except Exception as e:
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.warning(f"reset_sut() failed: {e}")

    # `def set_fault_mode` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def set_fault_mode(self, mode: str):
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """POST /admin/fault/<mode> to switch fault injection."""
        # `import` loads a library module so this file can call its functions; the comma-separated names are the helper libraries this line makes available.
        import urllib.request
        # `try` starts a protected block: Python attempts the indented code and jumps to `except` if an error happens.
        try:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            req = urllib.request.Request(
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                self.base_url + f"/admin/fault/{mode}",
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                data=b"",
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                method="POST"
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            urllib.request.urlopen(req, timeout=5)
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.info(f"SUT fault mode set to: {mode}")
            # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
            self._fault_mode = mode
        # `except` catches an error from the matching `try` block so the concretization run can report or recover instead of crashing immediately.
        except Exception as e:
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.warning(f"set_fault_mode() failed: {e}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    # `def _find_element` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def _find_element(self, selector: str, by_str: str, timeout: int = 10):
        # `from ... import ...` means Python opens another module and brings only the named tools into this file, instead of importing the whole module name.
        from selenium.webdriver.support.ui import WebDriverWait
        # `from ... import ...` means Python opens another module and brings only the named tools into this file, instead of importing the whole module name.
        from selenium.webdriver.support   import expected_conditions as EC
        # `from ... import ...` means Python opens another module and brings only the named tools into this file, instead of importing the whole module name.
        from selenium.common.exceptions   import TimeoutException
        # `from ... import ...` means Python opens another module and brings only the named tools into this file, instead of importing the whole module name.
        from selenium.webdriver.common.by import By

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        by_const_name = self.BY_MAP.get(by_str.lower(), "ID")
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        by_const      = getattr(By, by_const_name)

        # Strip # prefix for By.ID (defensive — should already be stripped
        # by callers, but guard here too)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if by_const_name == "ID" and selector.startswith("#"):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            selector = selector[1:]

        # `try` starts a protected block: Python attempts the indented code and jumps to `except` if an error happens.
        try:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return WebDriverWait(self.driver, timeout).until(
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                EC.presence_of_element_located((by_const, selector))
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )
        # `except` catches an error from the matching `try` block so the concretization run can report or recover instead of crashing immediately.
        except TimeoutException:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return None
        # `except` catches an error from the matching `try` block so the concretization run can report or recover instead of crashing immediately.
        except Exception as e:
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.error(f"_find_element({selector!r}) error: {e}")
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return None

    # `def _wait_for_element` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def _wait_for_element(self, wait_spec: dict, timeout: int = 10):
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        selector = wait_spec.get("selector", "")
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        by_str   = wait_spec.get("by", "id")
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if by_str.lower() == "id" and selector.startswith("#"):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            selector = selector[1:]
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if selector:
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            self._find_element(selector, by_str, timeout=timeout)

    # `@staticmethod` means the next function lives on the class but does not receive `self`; it is a helper grouped with the class because it belongs to that idea.
    @staticmethod
    # `def _substitute` creates a reusable function/method; the parentheses list inputs, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> str` documents the expected return type.
    def _substitute(template: str, values: dict) -> str:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """
        Replace {{KEY}} tokens in template with concrete values.

        Matching strategy (in order):
        1. Exact key match (case-insensitive)
        2. Partial match — TOKEN contains key or key contains TOKEN
        3. First value in dict as fallback

        Example:
            template = "/nurse/alert/urgent/{{SESSION_ID}}"
            values   = {"sess_0": "3f2a1b4c-..."}
            result   = "/nurse/alert/urgent/3f2a1b4c-..."
        """
        # `def replacer` creates a reusable function/method; the parentheses list inputs, commas separate parameters, and the colon starts the indented instructions that run when it is called.
        def replacer(match):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            token = match.group(1).upper()
            # Exact match
            # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
            for k, v in values.items():
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if k.upper() == token:
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return str(v)
            # Partial match — e.g. SESSION_ID matches sess_0
            # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
            for k, v in values.items():
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                k_clean     = k.upper().replace("_", "")
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                token_clean = token.replace("_", "")
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if token_clean in k_clean or k_clean in token_clean:
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return str(v)
            # Fallback to first value
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if values:
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return str(next(iter(values.values())))
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return match.group(0)  # leave unreplaced

        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return re.sub(r"\{\{([^}]+)\}\}", replacer, template)

    # `@staticmethod` means the next function lives on the class but does not receive `self`; it is a helper grouped with the class because it belongs to that idea.
    @staticmethod
    # `def _resolve_param` creates a reusable function/method; the parentheses list inputs, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> str` documents the expected return type.
    def _resolve_param(param_template: str, values: dict) -> str:
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if not param_template:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return ""
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return HTMLExecutor._substitute(param_template, values)

    # `def close` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def close(self):
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if self.driver:
            # `try` starts a protected block: Python attempts the indented code and jumps to `except` if an error happens.
            try:
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                self.driver.quit()
            # `except` catches an error from the matching `try` block so the concretization run can report or recover instead of crashing immediately.
            except Exception:
                # `pass` is an intentional no-op: it tells Python 'do nothing here' while keeping the syntax valid.
                pass


# ===========================================================================
# HTMLExecutorAdapter
# ===========================================================================

# `class HTMLExecutorAdapter` defines a new kind of object; `(BaseExecutor)` means it inherits behavior or rules from BaseExecutor, and the colon starts the indented body of the class.
class HTMLExecutorAdapter(BaseExecutor):
    # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
    """
    Transparent adapter that injects gate-level navigation.

    The ConcretizationAlgorithm calls perform() once per action in
    a gate's actions list. This adapter:

    1. Detects when the gate name changes between calls
    2. Navigates to the new gate's URL (substituting {{TOKEN}} values
       from the concrete values dict)
    3. Waits for the gate's wait_for element after navigation
    4. Delegates all perform() and wait() calls to HTMLExecutor

    The gate name is injected into each action dict by inject_gate_keys()
    in run.py before the algorithm runs.
    """

    # `def __init__` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def __init__(self, html_executor: HTMLExecutor, element_map: dict):
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.inner      = html_executor
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.gates_spec = element_map.get("gates", {})
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        self._last_gate: str | None = None

    # `def perform` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> bool` documents the expected return type.
    def perform(self, action: dict, values: dict) -> bool:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        gate_name = action.get("gate")

        # Navigate to gate URL on first action of each new gate
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate_name and gate_name != self._last_gate:
            # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
            self._last_gate = gate_name
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            gate_spec    = self.gates_spec.get(gate_name, {})
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            url_template = gate_spec.get("url", "")

            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if url_template:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                url      = HTMLExecutor._substitute(url_template, values)
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                full_url = self.inner.base_url + url
                # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                logger.debug(f"[{gate_name}] Navigating to {full_url}")
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                self.inner.driver.get(full_url)

                # Wait for the gate's wait_for element after navigation
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                wait_for = gate_spec.get("wait_for")
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if wait_for:
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    self.inner._wait_for_element(wait_for, timeout=10)

        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self.inner.perform(action, values)

    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
    def wait(
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        self, observe_spec: dict, timeout: int
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    ) -> tuple[str | None, bool]:
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self.inner.wait(observe_spec, timeout)

    # `def reset_sut` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def reset_sut(self):
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        self.inner.reset_sut()

    # `def set_fault_mode` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def set_fault_mode(self, mode: str):
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        self.inner.set_fault_mode(mode)

    # `def set_ue1_offline` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def set_ue1_offline(self, offline: bool):
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        self.inner.set_ue1_offline(offline)

    # `def close` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def close(self):
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        self.inner.close()


# ============================================================================
# LNTSIExecutorAdapter  (v2 — tree-structured SI, screen tracker)
# ============================================================================
# Drop-in replacement for the adapter in executors.py.
#
# Key change from v1:
#   Maintains a `_current_screen` tracker. Before executing any gate's
#   post-case common actions, it looks up the gate's `traversal_paths`
#   dict, retrieves the action list for `_current_screen`, and executes
#   those traversal actions first. This implements the runtime resolution
#   of `case screen in ... end case` blocks that the LNT SI describes.
#
# Backward compatible:
#   If `traversal_paths` is None (flat/legacy SI), the adapter behaves
#   exactly as v1 — it navigates to the gate's URL and runs actions directly.
# ============================================================================


# ============================================================================
# LNTSIExecutorAdapter  (v2 — tree-structured SI, screen tracker)
# ============================================================================

# This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
_INITIAL_SCREEN = "SCR_HOME"


class HarnessNotReady(RuntimeError):
    """The apparatus could not put the SUT into a state where a test case can
    begin, so the run has no verdict to give about the SUT or the model.

    Distinct from every other failure in this file. An unappliable stimulus is a
    statement about the SUT's screen (INCONCLUSIVE); a rejected observation is a
    statement about the SUT's behaviour (FAIL). This is a statement about the
    TESTER: it never got as far as interacting with the application, so the run
    belongs in neither column and must be excluded from the results rather than
    counted.
    """


# `class LNTSIExecutorAdapter` defines a new kind of object; `(BaseExecutor)` means it inherits behavior or rules from BaseExecutor, and the colon starts the indented body of the class.
class LNTSIExecutorAdapter(BaseExecutor):

    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
    def __init__(self, html_executor, lnt_si, type_description,
                 # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                 initial_screen=_INITIAL_SCREEN, wait_timeout: int = 10):
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self._lnt_si         = lnt_si
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.inner           = html_executor
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self._type_desc      = type_description
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self._current_screen = initial_screen
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self._last_gate      = None
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self._gate_prepared  = False
        # How long a wait_for may take. Was hard-coded to 10s at every call site,
        # so --timeout silently did nothing for waits (it reached only observe()).
        # That made "raise the timeout to tell slow from silent" impossible.
        self.wait_timeout    = wait_timeout
        # Set whenever a step fails because the TESTER could not proceed (a screen
        # precondition, not an observation about the SUT). algorithm.py reads it to
        # return INCONCLUSIVE with this reason instead of a conformance FAIL.
        self.last_precondition_failure = None
        # Selectors the SI observes => oracles; everything else waited on is a
        # precondition. Derived from the model, see LNTSystemInterface.
        self._oracle_selectors = (lnt_si.observed_selectors()
                                  if hasattr(lnt_si, "observed_selectors") else set())
        self._screen_anchors   = (lnt_si.screen_anchors()
                                  if hasattr(lnt_si, "screen_anchors") else {})
        if not self._screen_anchors:
            logger.warning("no screen_anchors in concrete_domain.yml — the screen "
                           "belief cannot be verified against the SUT")

    # ---- screen belief -----------------------------------------------------

    @staticmethod
    def _anchor_by(selector: str) -> str:
        """Which locator strategy an anchor string asks for.

        Anchors arrive from concrete_domain.yml as bare strings, so the
        strategy has to be read off the shape, exactly as si_lnt_parser._by_for
        and algorithm._by_for do for every other selector. This used to be
        hard-coded to "id", which is right for an Android UiSelector and wrong
        for every web SUT: an XPath anchor was passed to By.ID, Selenium turned
        it into `[id="//input[...]"]`, and the anchor could never be found. The
        screen belief was therefore unverifiable on the web path, and the
        initial-screen check refused to start runs that were perfectly fine.
        """
        s = (selector or "").strip()
        if s.startswith(("//", "(//", ".//", "(/")):
            return "xpath"
        if s.startswith("#") or s.startswith("."):
            return "css"
        return "id"          # Android UiSelector / resource-id, or a web id

    def _anchor_present(self, screen, timeout=2):
        """Is the anchor proving we are on `screen` on the display right now?"""
        sel = self._screen_anchors.get(screen)
        if not sel:
            return None                      # unanchored screen: cannot tell
        return self.inner._find_element(sel, self._anchor_by(sel),
                                        timeout=timeout) is not None

    def _observed_screen(self, timeout=2):
        """Probe every anchor and return the screen we are demonstrably on, or
        None if no anchor matches (or none are configured)."""
        for screen in self._screen_anchors:
            if self._anchor_present(screen, timeout=timeout):
                return screen
        return None

    def _resolve_screen_belief(self):
        """Before running a gate's traversal: confirm the believed screen, and if
        it is wrong, correct it from what the SUT actually shows.

        Correcting rather than failing is deliberate — landing somewhere the model
        did not predict is only a finding once the model HAS predicted something,
        and that check is `_confirm_destination`. Here we only refuse to act on a
        belief we can see is false."""
        if not self._screen_anchors:
            return True
        if self._anchor_present(self._current_screen):
            return True
        actual = self._observed_screen()
        if actual is None:
            self.last_precondition_failure = (
                f"tester lost track of the SUT: believed {self._current_screen}, "
                f"but no known screen anchor is present")
            logger.error(f"  {self.last_precondition_failure}")
            self._capture(f"screen_unknown_{self._current_screen}")
            return False
        logger.warning(f"  screen belief corrected: {self._current_screen} -> "
                       f"{actual} (anchor evidence)")
        self._current_screen = actual
        return True

    def _confirm_destination(self, declared, gate_name):
        """After a gate: the model SAID where this leaves the SUT, so check it.

        A mismatch means model and SUT have diverged in a way that invalidates
        every step after it — that is not evidence about the gate under test, so
        it is INCONCLUSIVE with a named reason, never FAIL."""
        if not declared or not self._screen_anchors:
            return True
        if self._anchor_present(declared, timeout=self.wait_timeout):
            self._current_screen = declared
            return True
        actual = self._observed_screen()
        self.last_precondition_failure = (
            f"{gate_name} declared it lands on {declared}, but the SUT shows "
            f"{actual or 'no known screen'}")
        logger.error(f"  {self.last_precondition_failure}")
        self._capture(f"screen_mismatch_{gate_name}_{declared}")
        return False

    def _capture(self, tag):
        """Dump the screen behind a failure, if the inner executor can."""
        cap = getattr(self.inner, "_capture_failure", None)
        if cap is None:
            return
        base = cap(tag)
        if base:
            logger.error(f"  screen state captured: {base}.png / {base}.xml")

    # `def perform` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def perform(self, action, values):
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        gate_name = action.get("gate")
        # Structural steps the walker issues directly (WAIT_FOR/TAP taken straight
        # from the AUT) carry no "gate" key, which made every message about them
        # read "(gate=None)" -- unplaceable in a 2000-line log. The walker is still
        # somewhere, so name that gate in messages. Kept separate from `gate_name`
        # on purpose: gate_name drives gate-change detection and _prepare_gate, and
        # feeding it a fallback would prepare gates for steps that never asked.
        log_gate = gate_name or self._last_gate or "(structural step)"
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate_name and gate_name != self._last_gate:
            # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
            self._last_gate     = gate_name
            # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
            self._gate_prepared = False
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if not self._gate_prepared and gate_name:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            ok = self._prepare_gate(gate_name, values)
            # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
            self._gate_prepared = True
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if not ok:
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return False
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        action_type = action.get("action", "")
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if action_type == "wait_for":
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel = action.get("selector", "")
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            by  = action.get("by", "xpath")
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if sel:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                el = self._find_or_scroll(sel, by)
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if el is None:
                    # This branch resolves wait_for itself rather than delegating to
                    # inner.perform(), so the inner executor's failure capture never
                    # runs. Without the dump here, a wait_for timeout is reported as
                    # a bare verdict with no record of the screen that caused it --
                    # and the state is gone by the time anyone looks.
                    logger.error(f"wait_for timed out: {sel!r} (gate={log_gate})")
                    # Same oracle-vs-precondition split as the traversal path.
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return self._wait_failed(sel, log_gate)
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return True
        # Bare gate-prep trigger ({"gate": ...} with no concrete payload): the
        # gate's real actions already ran in _prepare_gate. Don't fall through to
        # a phantom empty-selector click.
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if not action.get("selector") and not action_type:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return True
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self.inner.perform(action, values)

    # `def wait` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def wait(self, observe_spec, timeout):
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self.inner.wait(observe_spec, timeout)

    # `def _prepare_gate` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def _prepare_gate(self, gate_name, values):
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        tree = self._lnt_si.get_concrete_tree(gate_name)
        self.last_precondition_failure = None

        # Never traverse on a belief the SUT contradicts.
        if not self._resolve_screen_belief():
            return False

        # `if screen == SCR_X then ... end if` traversal, in model order. Each
        # guard runs only when we are on its screen, and the screen it declares
        # it lands on updates the belief for the guards after it — which is what
        # makes a chain like "leave add-entry -> search, then home -> search"
        # behave as LNT specifies. These bodies used to be flattened into the
        # unconditional action list, so EVERY guard ran on every visit regardless
        # of the screen state.
        for guard in tree.get("guards", []):
            if guard.get("when_screen") != self._current_screen:
                continue
            logger.debug(f"  guard {guard['when_screen']} taken for {gate_name}")
            for act in guard.get("actions", []):
                resolved = self._resolve_action(act, values)
                if not self._execute_action(resolved, values, gate_name):
                    return False
            dest = guard.get("destination")
            if dest:
                if not self._confirm_destination(dest, gate_name):
                    return False
                self._current_screen = dest

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        tp   = tree.get("traversal_paths")
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if tp is not None:
            # A believed screen that is not an arm of this gate's case block means
            # the tracker has drifted from the device. Previously `or []` turned
            # that into an empty action list: the gate ran NOTHING, reported
            # success, and the walk continued believing it had navigated. The next
            # step then failed and was blamed on the SUT. Drift is a tester fault,
            # so say so here rather than let it surface as a conformance verdict.
            if self._current_screen not in tp:
                logger.error(
                    f"screen tracker drift at {gate_name}: believed "
                    f"{self._current_screen!r}, but this gate only has arms for "
                    f"{sorted(tp)} — refusing to run an empty traversal")
                return False
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            path_actions = tp.get(self._current_screen) or []
            # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
            for act in path_actions:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                resolved = self._resolve_action(act, values)
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if not self._execute_action(resolved, values, gate_name):
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return False
        # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
        else:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            url_template = tree.get("url", "")
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if url_template:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                url = HTMLExecutor._substitute(url_template, values)
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                self.inner.driver.get(self.inner.base_url + url)
        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for act in tree.get("actions", []):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            resolved = self._resolve_action(act, values)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if not self._execute_action(resolved, values, gate_name):
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return False
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        wait_for = tree.get("wait_for")
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if wait_for:
            # The result used to be discarded, so a gate whose anchor never
            # appeared carried on regardless — the walk proceeded on a screen that
            # was not there. This wait is a PRECONDITION ("the gate's screen is
            # up"), so failing it means the tester is not in control, not that the
            # SUT broke a promise.
            if self.inner._wait_for_element(wait_for, timeout=self.wait_timeout) is None:
                logger.error(
                    f"precondition not met at {gate_name}: anchor "
                    f"{wait_for.get('selector')!r} never appeared")
                return False
        # Where does this gate leave the SUT? The model SAYS -- `screen := SCR_X`,
        # now carried through the parser as destination_screen -- so use that and
        # verify it against an anchor.
        declared = tree.get("destination_screen")
        if declared:
            if not self._confirm_destination(declared, gate_name):
                return False
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        elif tp is not None:
            # Fallback for gates whose SI records no destination: infer it as "the
            # case arm that needed no work must be where we are". A guess, kept
            # only because it is better than leaving the belief stale -- and now
            # anchor-checked on the next gate rather than trusted outright.
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            null_screens = [s for s, a in tp.items() if not a]
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if null_screens:
                # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
                self._current_screen = null_screens[0]
                logger.debug(f"  {gate_name} declares no destination; guessed "
                             f"{self._current_screen} from the empty case arm")
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return True

    # `def _resolve_action` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def _find_or_scroll(self, sel: str, by: str):
        """Locate an element, scrolling the view if it is merely below the fold.

        UiAutomator matches only rendered nodes, so a `wait_for` cannot tell "absent"
        from "further down the list". The action path already scrolls; waits did not,
        which showed up live: after scrolling down to reach a meal's Add button, the
        daily-total card sat above the viewport and the wait for it failed -- and
        because that selector is an oracle, the miss was on course to be reported as
        a conformance FAIL. Scrolling is the tester's job, not the SUT's fault.
        """
        el = self.inner._find_element(sel, by, timeout=self.wait_timeout)
        if el is not None:
            return el
        scroll = getattr(self.inner, "_scroll_into_view", None)
        return scroll(sel, by) if scroll is not None else None

    def _wait_failed(self, sel: str, gate_name) -> bool:
        """A wait_for did not find its element. Decide which of the TWO jobs
        wait_for does was being performed, and record it accordingly.

        `wait_for (el_calories); observe (el_calories)` checks a promise -- the
        SUT owes that value, so its absence is evidence about the SUT.
        `wait_for (el_search_input)` only establishes context; its absence means
        the tester never got where it was going, which is evidence about the
        TESTER. The SI writes both identically, so the split is derived from the
        model: a selector the SI observes somewhere is an oracle, everything else
        waited on is a precondition. Derived, not hand-listed, so it cannot drift
        as the SI changes.

        Always returns False (the wait did fail); the difference is whether a
        precondition reason is recorded for the verdict layer to pick up.
        """
        if sel in self._oracle_selectors:
            # An oracle wait that fails is a CANDIDATE COUNTER-EXAMPLE, so it is the
            # case that most needs evidence. Capturing only on the precondition path
            # (as this did when first written) had it exactly backwards: the runs
            # worth investigating were the ones leaving no trace behind.
            logger.error(f"expected observable never appeared at {gate_name}: {sel!r}")
            self._capture(f"oracle_{gate_name}_{sel}")
            return False
        self.last_precondition_failure = (
            f"precondition for {gate_name} not met: {sel!r} never appeared, so the "
            f"step after it was never reached")
        logger.error(f"  {self.last_precondition_failure}")
        self._capture(f"precondition_{gate_name}")
        return False

    def _resolve_action(self, action, values):
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        resolved = dict(action)
        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for key in ("param", "url"):
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if key in resolved and isinstance(resolved[key], str):
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                resolved[key] = HTMLExecutor._substitute(resolved[key], values)
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return resolved

    # `def _execute_action` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def _execute_action(self, action, values, gate_name):
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        action_type = action.get("action", "click")
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if action_type == "navigate":
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            url = HTMLExecutor._substitute(action.get("url", "/"), values)
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            self.inner.driver.get(self.inner.base_url + url)
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return True
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if action_type == "wait_for":
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel = action.get("selector", "")
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            by  = action.get("by", "xpath")
            if sel == "":
                return True
            if self._find_or_scroll(sel, by) is not None:
                return True
            return self._wait_failed(sel, gate_name)
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        injected = dict(action)
        # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
        injected["gate"] = gate_name
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self.inner.perform(injected, values)

    # `def set_screen` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def set_screen(self, screen_name):
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self._current_screen = screen_name

    # `def get_screen` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def get_screen(self):
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self._current_screen

    # `def reset_sut` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def reset_sut(self):
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        self.inner.reset_sut()
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self._current_screen = _INITIAL_SCREEN
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self._last_gate      = None
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self._gate_prepared  = False
        self.last_precondition_failure = None
        # A relaunched app paints skeleton placeholders before its real content,
        # and the first tap of the walk used to fire into them -- observed live:
        # the meal controls had not rendered, the tap found nothing, and the run
        # was recorded as a conformance FAIL on step one. Waiting for the initial
        # screen's own anchor is the app telling us it is ready, which beats any
        # fixed sleep. Best effort: an unanchored SUT just proceeds as before.
        anchor = self._screen_anchors.get(_INITIAL_SCREEN)
        if not anchor:
            return
        # ESCALATING RECOVERY, then REFUSE TO START.
        #
        # This used to log a warning and carry on. On 2026-08-24 the emulator's
        # system process hung and put an "isn't responding" dialog over
        # everything; the anchor was absent, the warning fired, and the walk
        # started anyway. It then failed on its first element -- 138 times in a
        # row, one per remaining test case in the purpose, each reported
        # INCONCLUSIVE for a reason that had nothing to do with the fault under
        # test. The reset was not missing; the refusal to proceed was.
        #
        # A test case that cannot reach its own starting screen has no verdict to
        # give. Raising is the honest outcome: the caller records a harness
        # failure rather than a statement about the SUT.
        for attempt in (1, 2, 3):
            if self.inner._find_element(anchor, self._anchor_by(anchor),
                                        timeout=self.wait_timeout) is not None:
                if attempt > 1:
                    logger.info(f"  {_INITIAL_SCREEN} ready after recovery "
                                f"(attempt {attempt})")
                else:
                    logger.info(f"  {_INITIAL_SCREEN} ready (anchor present)")
                return
            dismissed = self._dismiss_system_dialog()
            logger.warning(
                f"  {_INITIAL_SCREEN} anchor {anchor!r} absent "
                f"(attempt {attempt}/3)"
                f"{f' — {dismissed}' if dismissed else ''}")
            if attempt < 3:
                try:
                    self.inner.reset_sut()
                except Exception as e:
                    logger.warning(f"  relaunch during recovery failed: {e}")

        # Capture the screen BEFORE raising -- this failure previously had no
        # evidence attached at all, so the only way to know why the device
        # would not come up was to be watching the emulator live when it
        # happened. Confirmed 2026-09-01: without this, "the device is stuck
        # somewhere" was a fact only a human at the keyboard could report.
        cap = getattr(self.inner, "_capture_failure", None)
        base = ""
        if callable(cap):
            try:
                base = cap("harness_not_ready")
            except Exception as e:
                logger.debug(f"harness-failure capture skipped: {e}")
        if base:
            logger.error(f"  screen state captured: {base}.png / {base}.xml")

        raise HarnessNotReady(
            f"{_INITIAL_SCREEN} anchor {anchor!r} never appeared after 3 "
            f"relaunch attempts. The device is not in a state where this test "
            f"case can start, so it has no verdict to give. Check for a system "
            f"'isn't responding' dialog, a crashed app, or an exhausted disk.")

    def _dismiss_system_dialog(self) -> str:
        """Clear whatever is sitting over the app under test and blocking the
        SUT's own screen anchor, then report what was done.

        Two DISTINCT failure modes look identical from here (anchor absent,
        relaunch not enough) and need different recovery:

          * An ANR / 'process isn't responding' dialog, drawn by the system,
            not the SUT -- every selector the tester owns misses it.
          * A stuck SYSTEM PANEL (notification shade / Quick Settings), also
            system-drawn. Confirmed live 2026-09-01: `reset_sut()`'s relaunch
            (force-stop + start) cannot touch this -- it restarts the APP, and
            the panel is drawn by SystemUI, a different process entirely. Left
            unhandled, this fault is NOT self-limiting: it does not clear on
            its own, so every subsequent variant starts from the same stuck
            state and reports the identical HARNESS failure -- a human had to
            swipe it closed by hand to keep a sweep moving at all.

        ANR dialogs are dismissed by tapping their own button. The stuck-panel
        case (and anything else not recognized) is handled by KEYCODE_HOME,
        which Android guarantees returns to the launcher and collapses any
        open system panel -- unconditional recovery that does not depend on
        first diagnosing which system-drawn thing is in the way.

        Returns a short description of what was done, or "" if nothing was.

        ANDROID ONLY. Every recovery below is a device action -- UiAutomator
        text selectors and KEYCODE_HOME -- and neither means anything to a
        browser. Run against a web SUT they produced three rounds of invalid
        CSS (`[id="new UiSelector().text(\"Close\")"]`) and a wall of driver
        stack traces before the real problem surfaced. A browser has no system
        dialog to dismiss, so there is nothing to do here.
        """
        if not callable(getattr(self.inner, "_press_keycode", None)):
            return ""
        for label in ("Close app", "OK", "Wait", "Close"):
            try:
                el = self.inner._find_element(
                    f'new UiSelector().text("{label}")', "id", timeout=1)
                if el is not None:
                    el.click()
                    logger.warning(f"  dismissed a system dialog via {label!r} — "
                                   f"this was NOT the app under test")
                    return f"dismissed a system dialog via {label!r}"
            except Exception:
                continue
        try:
            press = getattr(self.inner, "_press_keycode", None)
            if callable(press) and press("KEYCODE_HOME"):
                return "pressed KEYCODE_HOME (no known dialog matched; " \
                       "clears a stuck system panel unconditionally)"
        except Exception as e:
            logger.debug(f"  KEYCODE_HOME recovery failed: {e}")
        return ""

    # `def set_fault_mode` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def set_fault_mode(self, mode):
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        self.inner.set_fault_mode(mode)

    # `def set_ue1_offline` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def set_ue1_offline(self, offline):
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        self.inner.set_ue1_offline(offline)

    # `def close` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def close(self):
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        self.inner.close()


# ===========================================================================
# AndroidExecutor
# ===========================================================================

class AndroidExecutor(BaseExecutor):
    """
    Drives a native Android app via Appium (UiAutomator2).

    Mirrors HTMLExecutor's interface so it can be wrapped by the same
    adapters used for web SUTs:
        perform(action, values)         -> bool
        wait(observe_spec, timeout)     -> (value, timed_out)
        _find_element(selector, by, t)  -> element | None
        _wait_for_element(wait_spec, t)
        reset_sut(), set_fault_mode(mode), set_ue1_offline(offline), close()

    Selector interpretation of the element-map `selector` string
    (the element map's `by` field is advisory — UiAutomator2 has no single
    web-style "id", so selector *shape* decides the locator strategy):

      * starts with 'new UiSelector('  -> ANDROID_UIAUTOMATOR, verbatim
      * looks like a resource id
        ('pkg:id/name' / 'android:id/name') -> AppiumBy.ID
      * bare text token (e.g. "Breakfast") -> tried in order as
        UiSelector().text(t) / .textContains(t) /
        .description(t) / .descriptionContains(t), then accessibility id.

    device_config (JSON passed via --device-config) supplies Appium
    capabilities, e.g.:
        {"appPackage": "com.maksimowiczm.foodyou",
         "appActivity": ".MainActivity",
         "deviceName": "emulator-5554",
         "server_url": "http://127.0.0.1:4723"}
    Any key other than `server_url` is forwarded verbatim as a capability,
    so callers can override or extend the defaults freely.
    """

    DEFAULT_SERVER     = "http://127.0.0.1:4723"
    _UISELECTOR_PREFIX = "new UiSelector("
    _RESOURCE_ID_RE    = re.compile(r'^[\w.]+:id/\w+$')

    def __init__(self, device_config: dict = None, element_map: dict = None,
                 wait_timeout: int = 10):
        self.config       = dict(device_config or {})
        self.element_map  = element_map or {}
        self.server_url   = self.config.pop("server_url", self.DEFAULT_SERVER)
        self.base_url     = ""            # adapter compat: native has no URL
        self.app_package  = self.config.get("appPackage")
        self._fault_mode  = "none"
        self._ue1_offline = False
        # How long to keep looking for an element before calling it absent. Was a
        # literal 10 at every call site, so --timeout could not reach the find that
        # precedes every tap -- which is exactly the wait that decides whether a
        # slow-rendering screen is a missing control.
        self.wait_timeout = wait_timeout
        self.driver       = self._init_driver()

    # ------------------------------------------------------------------
    # Driver initialisation
    # ------------------------------------------------------------------

    def _init_driver(self):
        try:
            from appium import webdriver
            from appium.options.android import UiAutomator2Options
        except ImportError:
            raise RuntimeError("Run: pip install Appium-Python-Client")

        caps = {
            "platformName":      "Android",
            "automationName":    "UiAutomator2",
            "newCommandTimeout": 300,
            "noReset":           True,
            # Appium's default is 30 s, which is not enough on a host under
            # memory pressure: the emulator falls back to software rendering and
            # installing and starting the UiAutomator2 server on the device takes
            # longer than that. On 2026-08-25 every one of 144 runs died with
            # "instrumentation process cannot be initialized within 30000ms" --
            # 144 failures in six minutes, none of which touched the app.
            "uiautomator2ServerLaunchTimeout": 120000,
            "uiautomator2ServerInstallTimeout": 120000,
        }
        caps.update(self.config)          # user caps override the defaults
        options = UiAutomator2Options().load_capabilities(caps)
        try:
            driver = webdriver.Remote(self.server_url, options=options)
        except Exception as e:
            # A session that never opens is an APPARATUS failure, not a verdict.
            # Raising the driver's own exception let it propagate as an ordinary
            # error, so the sweep recorded ERROR rows and the
            # three-consecutive-failure abort never fired -- 144 doomed runs.
            if self.session_is_dead(e):
                raise HarnessNotReady(
                    f"Appium could not create a session: {e}. The device or the "
                    f"Appium server is not in a usable state. Restart the Appium "
                    f"server after an emulator reboot, and check host memory."
                ) from e
            raise
        logger.info(
            f"AndroidExecutor connected to {self.server_url} "
            f"(app={caps.get('appPackage', '?')})"
        )
        return driver

    # Message fragments meaning the SESSION died, as opposed to an element being
    # absent. Matched as substrings because the wording varies by Appium version.
    _SESSION_DEAD = (
        "Appium Settings app is not running",
        "instrumentation process cannot be initialized",
        "A session is either terminated or not started",
        "invalid session id",
        "Could not proxy command to the remote server",
    )

    def session_is_dead(self, exc: Exception) -> bool:
        return any(m.lower() in str(exc).lower() for m in self._SESSION_DEAD)

    def reconnect(self) -> bool:
        """Rebuild the Appium session after it dies mid-run.

        A dead session says nothing about the SUT -- the tester lost its
        connection to the device. Previously the exception propagated and ended
        the run, which then classified as UNCLASSIFIED, because the recorded
        error string was whatever happened to be in flight when the session went.
        Three runs in the 2026-08-23 sweep ended that way and had to be
        reconstructed by grepping 748 logs.

        Returns True if a usable session was rebuilt. Deliberately does NOT
        decide whether the test case can continue: a mid-walk reconnect loses the
        tester's place in the model, and only the caller knows whether that is
        recoverable or whether the run must be recorded as a harness failure.
        """
        try:
            self.driver.quit()
        except Exception:
            pass                       # already dead; nothing to close
        try:
            self.driver = self._init_driver()
            logger.warning("  Appium session rebuilt after dying mid-run")
            return True
        except Exception as e:
            logger.error(f"  Appium session could not be rebuilt: {e}")
            return False

    # ------------------------------------------------------------------
    # Locator resolution
    # ------------------------------------------------------------------

    def _scroll_up_once(self) -> bool:
        """One screenful backwards. True if the gesture was issued.

        UiScrollable has no usable 'search upwards' form -- flingToBeginning and
        friends return a boolean, not an element, so they cannot terminate a
        selector chain. An explicit gesture states the direction plainly and lets
        the caller re-find between steps, which is what makes 'absent' and 'above
        the fold' separable at all.
        """
        try:
            size = self.driver.get_window_size()
            self.driver.execute_script("mobile: scrollGesture", {
                "left": int(size["width"] * 0.1),
                "top": int(size["height"] * 0.2),
                "width": int(size["width"] * 0.8),
                "height": int(size["height"] * 0.6),
                "direction": "up",
                "percent": 1.0,
            })
            return True
        except Exception as e:
            logger.debug(f"  scroll-up gesture unavailable: {e}")
            return False

    def _scroll_into_view(self, selector: str, by_str: str = ""):
        """Scroll a scrollable container until `selector` is on screen, then return
        THE ELEMENT THAT SELECTOR MATCHES. None if nothing scrolls, or it is
        genuinely absent.

        UiAutomator matches only what is currently rendered, so "not found" and
        "further down the list" are indistinguishable to _find_element. Without
        this the two look identical to the walker and the second is reported as a
        missing control -- i.e. as the SUT's fault.

        CRITICAL: `scrollIntoView` is a SCROLL ACTION, and what it returns is the
        scrollable CONTAINER, not the target. An earlier version returned that
        container directly, so callers received an element that did not satisfy
        their own selector -- an observe of `\\d+ / \\d+ kcal` came back holding
        "155 kcal" (a food row), and the oracle dutifully compared it against the
        daily total and reported a counter-example that did not exist. So: scroll
        first, then locate with the caller's selector, and hand back only that.
        """
        sel = (selector or "").strip()
        # UiScrollable takes a UiSelector argument, so only selectors already in
        # that form can be delegated. Text/resource-id shorthands are wrapped.
        if sel.startswith(self._UISELECTOR_PREFIX):
            inner = sel
        elif self._RESOURCE_ID_RE.match(sel):
            inner = f'new UiSelector().resourceId("{sel}")'
        else:
            inner = f'new UiSelector().text("{sel.replace(chr(34), chr(92) + chr(34))}")'
        scroll = (f'new UiScrollable(new UiSelector().scrollable(true))'
                  f'.setMaxSearchSwipes(6).scrollIntoView({inner})')
        try:
            from appium.webdriver.common.appiumby import AppiumBy
            # Fire it for the SCROLLING SIDE EFFECT only; the return value is the
            # container and must never be handed back as the match.
            self.driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, scroll)
            # Now ask the normal way. If the scroll worked, the target is on
            # screen and this finds it; if it did not, this returns None and the
            # caller correctly sees "absent" rather than a wrong element.
            el = self._find_element(sel, by_str, timeout=2)
            if el is not None:
                logger.info(f"  scrolled into view: {sel!r}")
                return el
            # scrollIntoView only searches FORWARD, so anything above the current
            # position stays invisible. That is not a corner case here: the daily
            # summary sits at the TOP of a list that grows with every entry, so a
            # scroll-assisted tap on a meal's Add button leaves it behind, and the
            # next observation of the total finds nothing. Confirmed live -- the
            # captured screen showed the meal rows and no "N / N kcal" anywhere.
            # So rewind and look again.
            for _ in range(4):
                if not self._scroll_up_once():
                    break
                el = self._find_element(sel, by_str, timeout=1)
                if el is not None:
                    logger.info(f"  scrolled back up into view: {sel!r}")
                    return el
        except Exception as e:
            # No scrollable container, or the selector form is not scrollable --
            # both mean "cannot help here", not an error worth failing on.
            logger.debug(f"  scrollIntoView({sel!r}) not applicable: {e}")
        return None

    def _locator_candidates(self, selector: str, by_str: str = ""):
        """Ordered list of (AppiumBy, value) locators to try for a selector."""
        from appium.webdriver.common.appiumby import AppiumBy

        sel = (selector or "").strip()
        by  = (by_str or "").strip().lower()

        # Explicit strategies (honoured if an SI ever emits them).
        if by in ("uiautomator", "android_uiautomator", "-android uiautomator"):
            return [(AppiumBy.ANDROID_UIAUTOMATOR, sel)]
        if by in ("accessibility_id", "accessibility id", "a11y"):
            return [(AppiumBy.ACCESSIBILITY_ID, sel)]
        if by == "xpath":
            return [(AppiumBy.XPATH, sel)]

        # Shape detection.
        if sel.startswith(self._UISELECTOR_PREFIX):
            return [(AppiumBy.ANDROID_UIAUTOMATOR, sel)]
        if self._RESOURCE_ID_RE.match(sel):
            return [(AppiumBy.ID, sel)]

        # Bare token -> best-effort text / content-description match.
        esc = sel.replace('"', '\\"')
        return [
            (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{esc}")'),
            (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().textContains("{esc}")'),
            (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().description("{esc}")'),
            (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().descriptionContains("{esc}")'),
            (AppiumBy.ACCESSIBILITY_ID, sel),
        ]

    def _find_element(self, selector: str, by_str: str = "id", timeout: int = 10):
        from selenium.common.exceptions import WebDriverException

        if not selector:
            return None
        candidates = self._locator_candidates(selector, by_str)
        deadline   = time.time() + max(0, timeout)
        drift_recovery_tried = False
        while True:
            for by_const, value in candidates:
                try:
                    els = self.driver.find_elements(by_const, value)
                    if els:
                        return els[0]
                except WebDriverException:
                    continue
            if time.time() >= deadline:
                return None
            # Focus-drift recovery, tried once per wait, halfway through the
            # budget. Confirmed 2026-09-16 on storage_media: `am force-stop ;
            # am start` (the STORAGE_MEDIA/UE1_KILL relaunch, used to force the
            # app to re-open its now-broken resource) sometimes loses the race
            # against SystemUI -- the emulator ends up showing the Quick
            # Settings panel instead of the app, and every poll in THIS loop
            # then legitimately finds nothing, because there is nothing of
            # the app's to find. 55/144 storage_media variants timed out this
            # way, every one confirmed post hoc by `current_package ==
            # com.android.systemui` in the captured page source -- not one
            # genuine ioco observation, an apparatus artifact.
            #
            # This is NOT the sticky-panel case `_dismiss_system_dialog`
            # already handles (that one does not self-clear and needs a human
            # swipe). This one clears itself by the very next variant every
            # time -- confirmed live, the PASS immediately before and after
            # each affected variant observes the identical oracle text within
            # a single poll. So it is a one-shot focus race, not a persistent
            # state, and pressing HOME + re-activating the SUT mid-poll is
            # enough: it does not change what a genuine timeout means for any
            # other selector, since current_package only diverges from
            # app_package when focus has actually left the app. This is an
            # apparatus-recovery step, not a verdict decision -- orthogonal to
            # however _step_failure_verdict / _inconclusive_reason classify
            # whatever timeout (if any) still happens after it.
            if (not drift_recovery_tried and self.app_package
                    and time.time() >= deadline - max(0, timeout) / 2):
                drift_recovery_tried = True
                try:
                    cur = self.driver.current_package
                except Exception:
                    cur = None
                if cur and cur != self.app_package:
                    # An ANR dialog ("<app> isn't responding": Close app / Wait)
                    # is drawn by the system over a hung app, so it shows up
                    # here as the foreground package not being the SUT. Seen
                    # 2026-09-25 (storage_media v38, ~4h into a sweep): the
                    # search screen behind it had in fact finished. HOME +
                    # relaunch would discard that screen; "Wait" keeps it and
                    # lets the app catch up, which is what a user would do.
                    # Only when no such dialog is present is it a genuine focus
                    # drift, handled by the HOME + re-activate below.
                    # One raw query, NOT _find_element: that would re-enter
                    # this recovery block from inside itself and recurse.
                    anr = None
                    try:
                        from appium.webdriver.common.appiumby import AppiumBy
                        hits = self.driver.find_elements(
                            AppiumBy.ANDROID_UIAUTOMATOR,
                            'new UiSelector().text("Wait")')
                        anr = hits[0] if hits else None
                    except Exception:
                        anr = None
                    if anr is not None:
                        logger.warning(
                            f"  ANR dialog over the SUT mid-wait (current_package="
                            f"{cur!r}) -- tapping 'Wait' and continuing to poll")
                        try:
                            anr.click()
                        except Exception as e:
                            logger.debug(f"  ANR 'Wait' tap failed: {e}")
                        time.sleep(1.0)
                        continue
                    logger.warning(
                        f"  focus drift detected mid-wait: current_package="
                        f"{cur!r} != app_package={self.app_package!r} -- "
                        f"pressing HOME and re-activating the SUT")
                    try:
                        self._press_keycode("KEYCODE_HOME")
                        self.driver.activate_app(self.app_package)
                    except Exception as e:
                        logger.debug(f"  focus-drift recovery failed: {e}")
            time.sleep(0.4)

    def _wait_for_element(self, wait_spec: dict, timeout: int = 10):
        selector = wait_spec.get("selector", "")
        by_str   = wait_spec.get("by", "id")
        if selector:
            return self._find_element(selector, by_str, timeout=timeout)
        return None

    # ------------------------------------------------------------------
    # perform()
    # ------------------------------------------------------------------

    def perform(self, action: dict, values: dict) -> bool:
        action_type = action.get("action", "click")

        # Native apps have no URL to GET; ordinary screen moves are done by taps.
        # The SI issues navigate() only in the UE1_KILL branch (navigate(rt_diary)),
        # which models "the app was killed and relaunched" — so faithfully relaunch
        # (terminate + activate), which also returns to the Home/diary screen where
        # the daily total is displayed.
        if action_type == "navigate":
            pkg = self.app_package or self.config.get("appPackage")
            try:
                if pkg:
                    self.driver.terminate_app(pkg)
                    self.driver.activate_app(pkg)
                    self._dismiss_interstitials()
                    logger.info(f"navigate -> relaunched {pkg} (UE1_KILL: kill + relaunch to Home)")
                else:
                    logger.debug("navigate: no appPackage; treating as no-op")
            except Exception as e:
                logger.warning(f"navigate relaunch failed: {e}")
            return True

        selector = action.get("selector", "")
        by_str   = action.get("by", "id")

        if action_type == "wait_for":
            if self._find_element(selector, by_str,
                                  timeout=self.wait_timeout) is not None:
                return True
            logger.error(f"wait_for timed out: {selector!r}")
            base = self._capture_failure(f"wait_for_{selector}")
            if base:
                logger.error(f"  screen state captured: {base}.png / {base}.xml")
            return False

        concrete_value = HTMLExecutor._resolve_param(action.get("param", ""), values)

        # ENTER_TEXT carries no selector: type into the focused field.
        if action_type == "enter_text":
            return self._enter_text(str(concrete_value))

        # A keycode pseudo-selector (e.g. "KEYCODE_ENTER") is a key event, not
        # an element to locate.
        if selector.upper().startswith("KEYCODE_") and action_type in ("click", "tap"):
            return self._press_keycode(selector.upper())

        element = self._find_element(selector, by_str, timeout=self.wait_timeout)
        if element is None:
            # A raised keyboard hides the nodes it covers; drop it and retry once
            # before declaring the element absent.
            self._hide_keyboard()
            element = self._find_element(selector, by_str,
                                         timeout=max(2, self.wait_timeout // 2))
        if element is None:
            # Still missing: it may simply be below the fold. UiAutomator only
            # matches nodes in the current view, so a list that has grown pushes
            # its controls out of reach -- observed live when a meal accumulated
            # five entries and its "Add" button left the viewport, which was then
            # reported as the SUT failing. Scrolling is the tester's job, so do it
            # here rather than let an off-screen control become a verdict.
            element = self._scroll_into_view(selector, by_str)
        if element is None:
            logger.error(f"Element not found: {selector!r} (by={by_str}, strategy="
                         f"{self._locator_candidates(selector, by_str)[0][0]})")
            base = self._capture_failure(f"{action_type}_{selector}")
            if base:
                logger.error(f"  screen state captured: {base}.png / {base}.xml")
            return False

        try:
            if action_type in ("click", "tap"):
                element.click()
                logger.debug(f"Tapped {selector}")
            elif action_type == "clear_and_type":
                element.clear()
                element.send_keys(str(concrete_value))
                logger.debug(f"Typed {concrete_value!r} into {selector}")
            elif action_type == "type":
                element.send_keys(str(concrete_value))
                logger.debug(f"Sent keys {concrete_value!r} to {selector}")
            else:
                logger.warning(f"Unknown action {action_type!r} on {selector}; tapping")
                element.click()
            return True
        except Exception as e:
            logger.error(f"perform() failed on {selector}: {e}")
            return False

    # ------------------------------------------------------------------
    # wait()
    # ------------------------------------------------------------------

    def wait(self, observe_spec: dict, timeout: int) -> tuple[str | None, bool]:
        selector  = observe_spec.get("selector", "")
        by_str    = observe_spec.get("by", "id")
        attribute = observe_spec.get("attribute", "text")

        if not selector:
            return None, False

        element = self._find_element(selector, by_str, timeout=timeout)
        if element is None:
            # Same two failure modes as wait_for, and they were both unhandled here:
            #
            #  1. The value may simply be below the fold. UiAutomator matches only
            #     rendered nodes, and the daily-total card sits at the TOP of a list
            #     that grows with every entry -- so once a scroll-assisted tap has
            #     moved the viewport down, observing the total finds nothing.
            #  2. Whatever the cause, this leaves no evidence. An observe timeout is
            #     a candidate counter-example ("the SUT owed a value and did not
            #     produce it"), so it is precisely the case that must be
            #     reconstructable afterwards -- and until now it was the only
            #     failure path that captured nothing at all.
            element = self._scroll_into_view(selector, by_str)
            if element is None:
                logger.info(f"wait() timed out waiting for {selector!r}")
                base = self._capture_failure(f"observe_{selector}")
                if base:
                    logger.error(f"  screen state captured: {base}.png / {base}.xml")
                return None, True
            logger.info(f"  observed after scrolling into view: {selector!r}")

        try:
            if attribute == "text":
                value = (element.text or "").strip()
            elif attribute in ("content-desc", "contentDescription", "desc"):
                value = (element.get_attribute("content-desc") or "").strip()
            else:
                value = (element.get_attribute(attribute) or "").strip()
            logger.debug(f"Observed {selector} -> {value!r}")
            # Lower-cased to match verdict/observation comparisons, as HTMLExecutor does.
            return (value.lower() if value else None), False
        except Exception as e:
            logger.error(f"wait() capture failed on {selector}: {e}")
            return None, False

    def _enter_text(self, text: str) -> bool:
        """Type text into the on-screen text field (the sole EditText, focused by
        click); falls back to the currently active element."""
        from appium.webdriver.common.appiumby import AppiumBy

        def _first_edit():
            els = self.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
            return els[0] if els else None

        try:
            el = _first_edit()
            if el is None:
                try:
                    el = self.driver.switch_to.active_element
                except Exception:
                    el = None
            if el is None:
                logger.error("enter_text: no EditText or focused field found")
                return False
            # Focus first (may trigger the keyboard / a Compose re-render).
            try:
                el.click()
            except Exception:
                pass
            time.sleep(0.5)   # let the view settle before typing
            # Compose churns the tree during the keyboard animation, staling
            # element handles — re-find and retry send_keys until it sticks.
            last_err = None
            for _ in range(4):
                try:
                    target = _first_edit() or el
                    # Always clear first: the field may be pre-filled (the
                    # add-entry form opens at 100 g) or hold a previous query,
                    # and send_keys APPENDS — so without this an "invalid
                    # amount" is never actually invalid and a second search
                    # types "TestAppleTestRice".
                    try:
                        target.clear()
                    except Exception:
                        pass
                    if text:
                        target.send_keys(text)
                    # Commit the entry (IME action) so live/remote search fires;
                    # harmless on single-line fields that ignore Enter.
                    try:
                        self.driver.press_keycode(66)   # KEYCODE_ENTER
                    except Exception:
                        pass
                    # Drop the soft keyboard: while it is up it covers the
                    # bottom of the screen (the Save FAB, the source headers),
                    # and those nodes leave the UiAutomator tree — a later
                    # tap(cv_save) / tap(cv_search_submit) then cannot find them.
                    self._hide_keyboard()
                    logger.debug(f"Entered text {text!r} and submitted")
                    return True
                except Exception as e:
                    last_err = e
                    time.sleep(0.4)
            logger.error(f"enter_text({text!r}) failed after retries: {last_err}")
            return False
        except Exception as e:
            logger.error(f"enter_text({text!r}) failed: {e}")
            return False

    def _capture_failure(self, tag: str) -> str:
        """Dump the screen and UI tree when a step fails, so the state that caused
        it is recoverable afterwards.

        Without this, diagnosing a missing element means re-driving the app by
        hand and hoping to land in the same state -- which is not reliable, since
        the manual sequence differs from what the executor did (it clears fields,
        presses IME actions and dismisses the keyboard). Artifacts go to
        $CONCRETIZATION_DEBUG_DIR, default ./tmp/failure_artifacts.
        """
        import os
        d = os.environ.get("CONCRETIZATION_DEBUG_DIR", "tmp/failure_artifacts")
        try:
            os.makedirs(d, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            safe = re.sub(r'[^A-Za-z0-9_.-]+', '_', tag)[:60]
            base = os.path.join(d, f"{stamp}_{safe}")
            try:
                self.driver.get_screenshot_as_file(base + ".png")
            except Exception as e:
                logger.debug(f"screenshot failed: {e}")
            try:
                with open(base + ".xml", "w") as fh:
                    fh.write(self.driver.page_source)
            except Exception as e:
                logger.debug(f"page_source failed: {e}")
            return base
        except Exception as e:
            logger.debug(f"failure capture skipped: {e}")
            return ""

    def _hide_keyboard(self) -> None:
        """Dismiss the soft keyboard if it is up (best effort, never raises)."""
        try:
            if self.driver.is_keyboard_shown():
                self.driver.hide_keyboard()
                time.sleep(0.4)     # let the layout settle before the next find
        except Exception as e:
            logger.debug(f"hide_keyboard skipped: {e}")

    # Android key events addressable by name (extend as gates require).
    _KEYCODES = {"KEYCODE_ENTER": 66, "KEYCODE_BACK": 4,
                 "KEYCODE_TAB": 61, "KEYCODE_SEARCH": 84, "KEYCODE_HOME": 3}

    def _press_keycode(self, keycode_name: str) -> bool:
        """Send an Android key event named like 'KEYCODE_ENTER'."""
        code = self._KEYCODES.get(keycode_name)
        if code is None:
            logger.error(f"Unknown keycode: {keycode_name}")
            return False
        try:
            self.driver.press_keycode(code)
            logger.debug(f"Pressed {keycode_name} ({code})")
            return True
        except Exception as e:
            logger.error(f"press_keycode({keycode_name}) failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Admin helpers
    # ------------------------------------------------------------------

    def reset_sut(self):
        """Return the app to a clean initial state by relaunching it, then
        clearing the non-alphabet onboarding interstitials so the test starts
        on the home screen."""
        pkg = self.app_package or self.config.get("appPackage")
        try:
            if pkg:
                self.driver.terminate_app(pkg)
                self.driver.activate_app(pkg)
                logger.info(f"Relaunched {pkg} for clean test isolation")
                self._dismiss_interstitials()
            else:
                logger.warning("reset_sut(): no appPackage configured; skipping relaunch")
        except Exception as e:
            logger.warning(f"reset_sut() failed: {e}")

    def _dismiss_interstitials(self):
        """Best-effort dismissal of FoodYou's onboarding screens that block the
        home screen after a cold start (`pm clear`): the welcome "Agree &
        Continue" page, the food-database "Agree & Continue" page, and the
        "What's new" sheet (dismissed with BACK). Each step is best-effort: tap
        if present, skip if not — so this is a no-op on a warm start that
        already resumes on home."""
        # The two "Agree & Continue" pages appear in sequence; loop a few passes
        # so the second is dismissed once the first goes away. Short lookups keep
        # absence cheap on a warm start.
        for _ in range(3):
            btn = self._find_element("Agree & Continue", "text", timeout=3)
            if btn is None:
                break
            try:
                btn.click()
                logger.info("Interstitial dismissed: 'Agree & Continue'")
                time.sleep(0.6)   # let the next screen settle
            except Exception as e:
                logger.warning(f"Failed tapping 'Agree & Continue': {e}")
                break

        # "What's new" sheet has no confirm button; BACK dismisses it.
        whats_new = self._find_element("What's new", "text", timeout=3)
        if whats_new is not None:
            try:
                self._press_keycode("KEYCODE_BACK")
                logger.info("Interstitial dismissed: 'What's new' (BACK)")
                time.sleep(0.6)
            except Exception as e:
                logger.warning(f"Failed dismissing 'What's new': {e}")

    def set_fault_mode(self, mode: str):
        # Fault injection on Android is delivered out-of-band (disruptor / adb /
        # the app's own disruption simulator), not by the UI executor. Record
        # intent so callers can introspect it.
        self._fault_mode = mode
        logger.info(f"AndroidExecutor fault mode recorded: {mode} (injection handled out-of-band)")

    def set_ue1_offline(self, offline: bool):
        """Best-effort device connectivity toggle via adb shell; else record intent."""
        try:
            self.driver.execute_script("mobile: shell", {
                "command": "svc",
                "args":    ["data", "disable" if offline else "enable"],
            })
            logger.info(f"Device data {'disabled' if offline else 'enabled'} via adb")
        except Exception as e:
            logger.warning(f"set_ue1_offline({offline}) not applied: {e}")
        self._ue1_offline = offline

    def close(self):
        if getattr(self, "driver", None):
            try:
                self.driver.quit()
            except Exception:
                pass
