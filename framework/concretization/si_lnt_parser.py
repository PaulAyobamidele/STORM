# CODEX EDUCATIONAL COMMENTS START
# In the concretization story, si_lnt_parser.py is the translator: it reads the LNT System Interface and builds the element-map shape that algorithm.py and executors.py can execute.
# CODEX EDUCATIONAL COMMENTS END
# This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
"""
si_lnt_parser.py  (v2 — tree-structured SI support)

Parses a STORM LNT System Interface file and builds an in-memory gate map
structurally identical to html_element_map.yml, extended with a
`traversal_paths` field for tree-structured SIs.

Two LNT SI syntaxes are supported:

  Legacy (string literals):
      NAVIGATE_TO ("/register")
      TYPE_INTO   ("#username-input", "name1_at_a_c")
      CLICK       ("#register-submit-btn")

  Formal (enum values — requires concrete_domain.yml):
      NAVIGATE_TO (rt_register)
      TYPE_INTO   (sel_username_input, cv_alice_at_a_c)
      CLICK       (sel_register_btn)

Tree-structured SIs add `case screen in ... end case` traversal blocks
before the gate-firing line. The parser emits these as:

  traversal_paths: {
      "SCR_HOME":     [action, action, ...],
      "SCR_EXPENSES": [],        # null branch = empty list
      ...
  }

The LNTSIExecutorAdapter uses traversal_paths at runtime by looking up
the current screen state and executing the corresponding action list
before the gate's own actions.

The interpretation I(L): enum -> string is loaded from concrete_domain.yml
which must live alongside the LNT file or at
systems/<sut>/properties/concrete_domain.yml.
"""
# `from` chooses a module to read from, `__future__` enables newer Python behavior early, and `import annotations` lets type hints be stored lazily so this file can use modern type syntax.
from __future__ import annotations

# `import` loads a library module so this file can call its functions; the comma-separated names are the helper libraries this line makes available.
import os
# `import` loads a library module so this file can call its functions; the comma-separated names are the helper libraries this line makes available.
import re
# `import` loads a library module so this file can call its functions; the comma-separated names are the helper libraries this line makes available.
import logging
# `import` loads a library module so this file can call its functions; the comma-separated names are the helper libraries this line makes available.
import yaml
# `from ... import ...` means Python opens another module and brings only the named tools into this file, instead of importing the whole module name.
from typing import Optional

# This creates a logger named after this module, so messages from this file can be filtered and traced while the concretization run is happening.
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Gates that the AUT alphabet may contain but that intentionally have no
# element-map entry. Validation must skip these; the graph walker tolerates a
# missing spec for them (it no-ops on an empty entry — see ConcretizationAlgorithm).
#
# Shared by validate_invariants (here) and validate_element_map (algorithm.py)
# so the two checks cannot drift.
# ---------------------------------------------------------------------------

# This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
STRUCTURAL_SKIP_GATES = frozenset({
    # Verdict / control labels
    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
    "PASS", "FAIL", "INCONCLUSIVE", "DISRUPTION_OCCURS",
    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
    "RECEIVE_ZONE_STATUS", "CONFIRMED",
    # Disruption gates — verdicts handled by quiescence / DisruptionExecutor
    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
    "APP_TIMEOUT", "UE1_OFFLINE",
    # FoodYou disruption gates: EXTAPI_FAIL / NETWORK_DEGRADED are the live faults
    # emitted by the SI's composed disruption simulator; the rest are inert
    # placeholders declared in the spec alphabet with no test cases yet.
    "EXTAPI_FAIL", "NETWORK_DEGRADED",
    "UE1_KILL", "UE2_STORAGEFULL", "DISRUPTION_DB", "DB_CORRUPT",
    "CACHE_STALE", "STORAGE_DEGRADED",
    # UI traversal gates — concrete execution lives in each meaningful gate's
    # traversal_paths, run by LNTSIExecutorAdapter, not an element-map entry.
    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
    "NAVIGATE_TO", "NAVIGATE", "TAP", "TYPE_INTO", "ENTER_TEXT", "CLICK", "WAIT_FOR", "OBSERVE",
    # Placeholder gates — no current test cases target these
    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
    "VIEW_ACTIVITY", "VIEW_STATS", "VIEW_INFORMATION",
    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
    "EDIT_GROUP", "EDIT_EXPENSE", "REIMBURSEMENT_CREATE",
    # CADP parallel-composition artefact
    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
    "LOCK",
# This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
})


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

# `class ConcreteActionTree` defines a new kind of object; `(dict)` means it inherits behavior or rules from dict, and the colon starts the indented body of the class.
class ConcreteActionTree(dict):
    # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
    """
    Dict subclass holding one gate's concrete interaction spec.
    Fields mirror html_element_map.yml gate entries, plus one new field:

        url              str | None
        param_types      dict  {param_N: TypeName}
        actions          list  [{selector, by, action, param?}]
                               Common post-gate actions (after traversal).
        wait_for         dict  {selector, by}
        observe          dict  {selector, by, attribute}
        traversal_paths  dict  {SCREEN_NAME: [action, ...]}
                               Per-screen traversal action lists.
                               Empty list = `null` branch (already at anchor).
                               None = gate has no case block (flat/legacy SI).
    """


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

# `class LNTSystemInterface` defines a new kind of object; the colon means the following indented lines belong inside that class.
class LNTSystemInterface:
    # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
    """
    Reads an LNT System Interface (.lnt) text file and extracts every
    [SI_GATE:NAME] branch into a ConcreteActionTree.

    Supports flat (legacy) and tree-structured (case screen in) syntax.
    For tree-structured SIs, `traversal_paths` is populated per gate.
    For flat SIs, `traversal_paths` is None (backward compatible).
    """

    # -- compiled regexes: structural markers ------------------------------
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _GATE_LINE_RE    = re.compile(r'--\s*\[SI_GATE:([A-Z_0-9]+)\](.*)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _KV_PAIRS_RE     = re.compile(r'(\w+):\s*([^:\[]+?)(?=\s+\w+:|$)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _BASE_URL_RE     = re.compile(r'--\s*base_url:\s*(\S+)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _SELECT_RE       = re.compile(r'\balt\b', re.IGNORECASE)
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _END_SEL_RE      = re.compile(r'\bend\s+alt\b', re.IGNORECASE)

    # case screen in ... end case
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _CASE_OPEN_RE    = re.compile(r'^\s*case\s+\w+\s+in\s*$', re.IGNORECASE)
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _CASE_CLOSE_RE   = re.compile(r'^\s*end\s+case\s*;?\s*$', re.IGNORECASE)
    # SCR_FOO -> or | SCR_FOO ->
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _SCREEN_ARM_RE   = re.compile(r'^\s*\|?\s*(SCR_[A-Z_0-9]+)\s*->\s*$')
    # Bare null statement inside a case arm
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _NULL_RE         = re.compile(r'^\s*null\s*;?\s*$', re.IGNORECASE)

    # screen := SCR_XXX assignment (post-case screen update)
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _SCREEN_ASSIGN_RE = re.compile(r'^\s*screen\s*:=\s*(SCR_[A-Z_0-9]+)\s*;?\s*$')

    # observe_attr annotation
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _OBSERVE_ATTR_RE = re.compile(r'--\s*observe_attr:\s*(\S+)')

    # L-value comment annotation
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _L_VALUE_RE      = re.compile(r'L\((\w+)\)\s*=\s*([a-z_][a-z_0-9]*)')

    # -- string-literal forms (legacy) -------------------------------------
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _NAVIGATE_STR_RE   = re.compile(r'NAVIGATE_TO\s*\(\s*"([^"]+)"\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _TYPE_INTO_STR_RE  = re.compile(r'TYPE_INTO\s*\(\s*"([^"]+)"\s*,\s*"([^"]*)"\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _CLICK_STR_RE      = re.compile(r'\bCLICK\s*\(\s*"([^"]+)"\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _WAIT_FOR_STR_RE   = re.compile(r'\bWAIT_FOR\s*\(\s*"([^"]+)"\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _OBSERVE_STR_RE    = re.compile(r'\bOBSERVE\s*\(\s*"([^"]+)"\s*\)')

    # -- formal enum forms -------------------------------------------------
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _NAVIGATE_S_RE     = re.compile(
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        r'NAVIGATE_TO_S\s*\(\s*([a-z_][a-z_0-9]*)\s*,\s*([a-z_][a-z_0-9]*)\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _NAVIGATE_ENUM_RE  = re.compile(r'NAVIGATE_TO\s*\(\s*([a-z_][a-z_0-9]*)\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _TYPE_INTO_L_RE    = re.compile(
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        r'TYPE_INTO\s*\(\s*([a-z_][a-z_0-9]*)\s*,\s*L_\w+\s*\(\s*\w+\s*\)\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _TYPE_INTO_ENUM_RE = re.compile(
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        r'TYPE_INTO\s*\(\s*([a-z_][a-z_0-9]*)\s*,\s*([a-z_][a-z_0-9]*)\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _CLICK_ENUM_RE     = re.compile(r'\bCLICK\s*\(\s*([a-z_][a-z_0-9]*)\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _WAIT_FOR_ENUM_RE  = re.compile(r'\bWAIT_FOR\s*\(\s*([a-z_][a-z_0-9]*)\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _OBSERVE_ENUM_RE   = re.compile(r'\bOBSERVE\s*\(\s*([a-z_][a-z_0-9]*)\s*\)')

    # -- paper-style (marker-less) forms ------------------------------------
    # Lowercase concrete system actions used by paper-style SIs (e.g. MedTimer):
    #   navigate (route)  tap (cv | L_x(var))  wait_for (el)  observe (el)
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _PS_NAVIGATE_RE = re.compile(r'\bnavigate\s*\(\s*([a-z_][a-z_0-9]*)\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _PS_CLICK_RE   = re.compile(r'\bclick\s*\(\s*([a-z_][a-z_0-9]*)\s*\)')
    # click (L_x (var)): the L function maps the variable's abstract value to a
    # selector name, resolved through `selectors:` (web analogue of tap (L_x (var)))
    _PS_CLICK_L_RE = re.compile(r'\bclick\s*\(\s*(L_\w+)\s*\(\s*(\w+)\s*\)\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _PS_TYPE_INTO_L_RE = re.compile(
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        r'\btype_into\s*\(\s*([a-z_][a-z_0-9]*)\s*,\s*(L_\w+)\s*\(\s*(\w+)\s*\)\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _PS_TYPE_INTO_RE = re.compile(
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        r'\btype_into\s*\(\s*([a-z_][a-z_0-9]*)\s*,\s*([a-z_][a-z_0-9]*)\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _PS_TAP_L_RE    = re.compile(r'\btap\s*\(\s*L_\w+\s*\(\s*(\w+)\s*\)\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _PS_TAP_RE      = re.compile(r'\btap\s*\(\s*([a-z_][a-z_0-9]*)\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _PS_WAITFOR_RE  = re.compile(r'\bwait_for\s*\(\s*([a-z_][a-z_0-9]*)\s*\)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _PS_OBSERVE_RE  = re.compile(r'\bobserve\s*\(\s*([a-z_][a-z_0-9]*)\s*\)')
    # An abstract gate call = an UPPERCASE statement head that is not one of the
    # known concrete primitives.
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _PS_ABSTRACT_RE = re.compile(r'^([A-Z][A-Z_0-9]*)\s*(?:\(|;?$)')
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _PS_ALT_OPEN_RE  = re.compile(r'^alt$',          re.IGNORECASE)
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    # Trailing ";" allowed: "end alt;" is valid LNT whenever the alt is followed
    # by another statement. Without the ";?" the close never matches, depth never
    # returns to 0, and every gate after the alt is silently swallowed into its
    # arms -- surfacing far away as "gate X appears in AUT but has no entry in
    # the LNT System Interface". _CASE_CLOSE_RE already tolerates it.
    _PS_ALT_CLOSE_RE = re.compile(r'^end\s+alt\s*;?$', re.IGNORECASE)

    # `if screen == SCR_X then` ... `end if` — a CONDITIONAL traversal block.
    # These used to be invisible to the paper-style parser: only the `if`/`end if`
    # lines were skipped, so the guarded body was appended to the flat action list
    # and executed unconditionally. A gate guarded for two different origin screens
    # (the common "reach SCR_ADD_ENTRY from SCR_HOME, or from SCR_FOOD_SEARCH"
    # shape) therefore ran BOTH bodies on every visit, in every screen state.
    # They are now emitted as ordered `guards`, evaluated against the tracked
    # screen exactly as LNT evaluates them.
    _PS_IF_SCREEN_RE = re.compile(r'^if\s+screen\s*==\s*(SCR_[A-Z_0-9]+)\s+then$',
                                  re.IGNORECASE)
    # Any other `if ... then` — not screen-conditional, so its body stays flat
    # (previous behaviour). Tracked only to find the matching `end if`.
    _PS_IF_ANY_RE    = re.compile(r'^if\s+.*\bthen$', re.IGNORECASE)
    _PS_END_IF_RE    = re.compile(r'^end\s+if\s*;?$', re.IGNORECASE)

    # Uppercase concrete primitives that must NOT be mistaken for abstract gates.
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _CONCRETE_HEADS = frozenset({
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "NAVIGATE_TO", "NAVIGATE_TO_S", "TYPE_INTO", "CLICK", "WAIT_FOR", "OBSERVE",
    # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
    })

    # `def __init__` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def __init__(self, lnt_path: str, concrete_domain_path: Optional[str] = None,
                 extra_skip_gates: Optional[set] = None):
        # Gates this SUT declares as faults, supplied by the caller from the
        # SUT's own disruption_mapping.yml.
        #
        # STRUCTURAL_SKIP_GATES below is a fixed list of FoodYou/Spliit gate
        # names. Any AUT gate missing from both it and the SI raises
        # "SI invariant violated", so a SUT whose faults are named anything
        # else could not generate at all: Moodle declares APP1_WRITE_FAIL,
        # BGJOB_FAIL, SLOW_QUERY, NET_CONGESTION and HIGH_LATENCY, none of
        # which appear there. Adding them to the framework's list would push
        # one more SUT's vocabulary into shared code; taking them from the
        # mapping keeps the framework a template.
        self._extra_skip_gates = frozenset(extra_skip_gates or ())
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.lnt_path       = lnt_path
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        self._gates:        dict[str, ConcreteActionTree] = {}
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        self._base_url:     str = "http://localhost:5000"
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        self._domain:       dict = {"routes": {}, "selectors": {}, "concrete_values": {}}
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        self._var_defaults: dict[str, str] = {}
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        self._l_functions:  dict[str, dict] = {}

        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        self._load_domain(lnt_path, concrete_domain_path)
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        self._load_l_functions(lnt_path)
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        self._parse()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    # `def get_concrete_tree` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> ConcreteActionTree` documents the expected return type.
    def get_concrete_tree(self, abstract_gate: str) -> ConcreteActionTree:
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self._gates.get(abstract_gate, ConcreteActionTree())

    # `def get_abstract_gates` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> list[str]` documents the expected return type.
    def get_abstract_gates(self) -> list[str]:
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return list(self._gates.keys())

    def observed_selectors(self) -> set:
        """
        Selectors the SI actually OBSERVES somewhere — i.e. the ones a verdict is
        read from.

        This is what separates the two jobs `wait_for` does, and it is derived
        from the model rather than hand-listed so it cannot drift:

          observed     -> the wait is an ORACLE. Its absence is a finding about
                          the SUT (el_extapi_warning not appearing IS the
                          EXTAPI_FAIL result), so it may yield FAIL.
          not observed -> the wait is a PRECONDITION on the tester's own
                          progress (el_search_input, el_search_results,
                          el_measure_screen). Its absence means the tester could
                          not proceed, which under ioco leaves nothing to judge:
                          INCONCLUSIVE, never FAIL.
        """
        seen: set = set()
        for tree in self._gates.values():
            for key in ("observe", "observes"):
                spec = tree.get(key)
                if isinstance(spec, dict):
                    spec = [spec]
                for one in (spec or []):
                    sel = (one or {}).get("selector")
                    if sel:
                        seen.add(sel)
        return seen

    def screen_anchors(self) -> dict:
        """
        {SCR_X: selector} — one element per screen that PROVES the SUT is on it.

        Optional: without it the runtime simply cannot verify its screen belief
        and says so. Read from concrete_domain.yml, where element names are
        resolved through the same interpretation I() as everything else.
        """
        raw = (self._domain or {}).get("screen_anchors") or {}
        return {scr: (self._resolve_element(el) or el) for scr, el in raw.items()}

    # `def to_element_map` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> dict` documents the expected return type.
    def to_element_map(self) -> dict:
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return {
            # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
            "base_url": self._base_url,
            # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
            "concrete_domain": self._domain,
            # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
            "gates": {name: dict(tree) for name, tree in self._gates.items()},
        # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
        }

    # `def validate_invariants` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> None` documents the expected return type.
    def validate_invariants(self, aut_path: str) -> None:
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        gates_in_aut: set[str] = set()
        # `with open(...) as f` opens a file and guarantees it will be closed automatically; `f` is the file handle used by the indented block.
        with open(aut_path) as f:
            # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
            for line in f:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                m = re.search(r'"([A-Z_0-9]+)', line)
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if m:
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    gates_in_aut.add(m.group(1))

        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        skip = STRUCTURAL_SKIP_GATES | self._extra_skip_gates
        for gate in sorted(gates_in_aut - skip):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            spec = self._gates.get(gate)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if spec is None:
                # `raise` deliberately throws an error; this code uses it when a required invariant or dependency is missing and continuing would hide the real problem.
                raise ValueError(
                    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
                    f"SI invariant violated: gate '{gate}' appears in AUT "
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    f"but has no entry in the LNT System Interface '{self.lnt_path}'."
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            actions            = spec.get("actions", [])
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            observe            = spec.get("observe")
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            traversal_paths    = spec.get("traversal_paths")
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            has_traversal      = traversal_paths is not None and len(traversal_paths) > 0
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if not actions and observe is None and not has_traversal:
                # `raise` deliberately throws an error; this code uses it when a required invariant or dependency is missing and continuing would hide the real problem.
                raise ValueError(
                    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
                    f"SI invariant violated: gate '{gate}' has neither "
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    f"actions, traversal_paths, nor an observe block."
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            url = spec.get("url", "")
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if "SESSION" in url.upper() and "{{SESSION_ID}}" not in url:
                # `raise` deliberately throws an error; this code uses it when a required invariant or dependency is missing and continuing would hide the real problem.
                raise ValueError(
                    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
                    f"SI invariant violated: gate '{gate}' URL '{url}' "
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    f"references a session but does not use {{{{SESSION_ID}}}}."
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )

        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
        logger.info(f"LNT SI invariants OK for {aut_path}")

    # ------------------------------------------------------------------
    # Interpretation I(L): enum value -> runtime string
    # ------------------------------------------------------------------

    # `def _I` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> Optional[str]` documents the expected return type.
    def _I(self, category: str, enum_val: str) -> Optional[str]:
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self._domain.get(category, {}).get(enum_val)

    # `def _resolve_selector` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> Optional[str]` documents the expected return type.
    def _resolve_selector(self, enum_val: str) -> Optional[str]:
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self._I("selectors", enum_val)

    # `def _resolve_route` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> Optional[str]` documents the expected return type.
    def _resolve_route(self, enum_val: str) -> Optional[str]:
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self._I("routes", enum_val)

    # `def _resolve_value` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> Optional[str]` documents the expected return type.
    def _resolve_value(self, enum_val: str) -> Optional[str]:
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self._I("concrete_values", enum_val)

    # `def _resolve_value_or_self` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> str` documents the expected return type.
    def _resolve_value_or_self(self, enum_val: str) -> str:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        resolved = self._resolve_value(enum_val)
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return resolved if resolved is not None else enum_val

    # `def _resolve_element` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> Optional[str]` documents the expected return type.
    def _resolve_element(self, enum_val: str) -> Optional[str]:
        # Paper-style SIs name UI elements under `elements:`; fall back to the
        # legacy `selectors:` category so both styles resolve.
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self._I("elements", enum_val) or self._I("selectors", enum_val)

    # `def _resolve_l_function` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> str` documents the expected return type.
    def _resolve_l_function(self, func_name: str, var_name: str, l_value_map: dict) -> str:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        abstract_val = l_value_map.get(var_name, var_name)
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        mapped = self._l_functions.get(func_name, {}).get(abstract_val)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if mapped is None:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            mapped = self._l_functions.get(func_name, {}).get("__default__")
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if mapped is None:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return str(abstract_val)
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self._resolve_value_or_self(mapped)

    # ------------------------------------------------------------------
    # Domain loading
    # ------------------------------------------------------------------

    # `def _load_domain` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> None` documents the expected return type.
    def _load_domain(self, lnt_path: str, explicit_path: Optional[str]) -> None:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        candidates = []
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if explicit_path:
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            candidates.append(explicit_path)
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        lnt_dir = os.path.dirname(os.path.abspath(lnt_path))
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        candidates.append(os.path.join(lnt_dir, "concrete_domain.yml"))
        # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
        candidates.append(
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            os.path.join(lnt_dir, "..", "properties", "concrete_domain.yml"))

        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for path in candidates:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            path = os.path.normpath(path)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if os.path.isfile(path):
                # `with open(...) as f` opens a file and guarantees it will be closed automatically; `f` is the file handle used by the indented block.
                with open(path) as f:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    loaded = yaml.safe_load(f)
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if loaded:
                    # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
                    self._domain = loaded
                    # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                    logger.debug(f"Loaded concrete_domain.yml from {path}")
                # `return` exits the current function immediately and gives no explicit value back.
                return

        # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
        logger.warning(
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            "concrete_domain.yml not found — enum values will not be resolved."
        # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
        )

    # `def _load_l_functions` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> None` documents the expected return type.
    def _load_l_functions(self, lnt_path: str) -> None:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """
        Parse simple LNT interpretation functions such as:

            function L_group (grp : GroupId) : InputValue is
                case grp in
                    grp_0 -> return cv_group_0
                end case
            end function

        and constant-return functions such as L_amount. These functions often
        live in a sibling *_types.lnt file rather than the SI file itself.
        """
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        lnt_dir = os.path.dirname(os.path.abspath(lnt_path))
        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for name in os.listdir(lnt_dir):
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if not name.endswith(".lnt"):
                # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                continue
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            path = os.path.join(lnt_dir, name)
            # `try` starts a protected block: Python attempts the indented code and jumps to `except` if an error happens.
            try:
                # `with open(...) as f` opens a file and guarantees it will be closed automatically; `f` is the file handle used by the indented block.
                with open(path) as f:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    text = f.read()
            # `except` catches an error from the matching `try` block so the concretization run can report or recover instead of crashing immediately.
            except OSError:
                # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                continue
            # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
            for fm in re.finditer(
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                r'function\s+(L_\w+)\s*\([^)]*\)\s*:\s*\w+\s+is(.*?)end\s+function',
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                text, re.DOTALL | re.IGNORECASE,
            # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
            ):
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                func_name = fm.group(1)
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                body = fm.group(2)
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                mapping = self._l_functions.setdefault(func_name, {})
                # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
                for src, dst in re.findall(
                    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                    r'([a-z_][a-z_0-9]*)\s*->\s*return\s+([a-z_][a-z_0-9]*)',
                    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                    body,
                    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                    re.IGNORECASE,
                # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
                ):
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    mapping[src] = dst
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                cm = re.search(r'\breturn\s+([a-z_][a-z_0-9]*)', body, re.IGNORECASE)
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if cm and not mapping:
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    mapping["__default__"] = cm.group(1)

    # ------------------------------------------------------------------
    # Top-level parse
    # ------------------------------------------------------------------

    # `def _parse_var_block` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> None` documents the expected return type.
    def _parse_var_block(self, text: str) -> None:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """
        Populate _var_defaults from the initialisation block only.
        The LNT var block declares types (var x : T in); assignments
        (x := val) are in the init block between 'in' and 'loop'.
        Parsing the entire file for := picks up every screen := SCR_XXX
        assignment and gives the wrong initial screen value.
        """
        # Parse only the init block between 'in' and 'loop'. Scan code only, so
        # the words 'in'/'loop' inside header comments don't shift the block.
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        code_text = "\n".join(l.split("--")[0] for l in text.split("\n"))
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        init_m = re.search(
            # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
            r'\bin\b(.*?)\bloop\b',
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            code_text, re.DOTALL | re.IGNORECASE
        # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
        )
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        init_block = init_m.group(1) if init_m else ""
        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for var_name, val in re.findall(r'(\w+)\s*:=\s*([A-Za-z_][A-Za-z_0-9]*)', init_block):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            resolved = self._resolve_value(val)
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            self._var_defaults[var_name] = resolved if resolved else val
        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
        logger.debug(f"var_defaults: {self._var_defaults}")

    # `def _parse` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> None` documents the expected return type.
    def _parse(self) -> None:
        # `with open(...) as f` opens a file and guarantees it will be closed automatically; `f` is the file handle used by the indented block.
        with open(self.lnt_path) as f:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            text = f.read()

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._BASE_URL_RE.search(text)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m:
            # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
            self._base_url = m.group(1).strip()

        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        self._parse_var_block(text)

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        body = self._extract_alt_body(text)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if body is None:
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.warning(f"No 'alt...end alt' block found in LNT SI: {self.lnt_path}")
            # `return` exits the current function immediately and gives no explicit value back.
            return

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        branches = self._split_branches(body)
        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for branch in branches:
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            self._parse_branch(branch.strip())

        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
        logger.info(f"LNT SI parsed: {len(self._gates)} gates from {self.lnt_path}")

    # `def _split_branches` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> list[str]` documents the expected return type.
    def _split_branches(self, body: str) -> list[str]:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """
        Split the alt body on top-level [] separators.
        Tracks depth for nested alt blocks AND for case...end case blocks
        so that [] inside a case arm is not mistaken for a branch separator.
        """
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        branches: list[str] = []
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        current:  list[str] = []
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        alt_depth  = 0
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        case_depth = 0

        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for line in body.split("\n"):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            stripped = line.strip()
            # Detect structure on code only — the words 'alt'/'[]' inside a
            # comment must not affect depth tracking or branch splitting.
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            code = stripped.split("--")[0].strip()

            # Track case depth first — case blocks can contain alt internally
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if self._CASE_OPEN_RE.match(code):
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                case_depth += 1
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if self._CASE_CLOSE_RE.match(code):
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                case_depth = max(0, case_depth - 1)

            # Track alt depth only outside case blocks. Note: 'end alt' also
            # matches \balt\b, so a standalone open = (alt count - end-alt count).
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if case_depth == 0:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                n_end  = len(self._END_SEL_RE.findall(code))
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                n_open = len(self._SELECT_RE.findall(code)) - n_end
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                alt_depth += n_open - n_end

            # A [] at top-level (alt_depth==0, case_depth==0) is a branch separator
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if code == "[]" and alt_depth <= 0 and case_depth == 0:
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                branches.append("\n".join(current))
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                current = []
            # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
            else:
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                current.append(line)

        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if current:
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            branches.append("\n".join(current))

        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return [b for b in branches if b.strip()]

    # ------------------------------------------------------------------
    # Branch parsing — core method
    # ------------------------------------------------------------------

    # `def _parse_branch` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> None` documents the expected return type.
    def _parse_branch(self, branch: str) -> None:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """
        Parse one SI branch into a ConcreteActionTree.

        A branch has one of two structures:

        FLAT (legacy):
            -- [SI_GATE:NAME] ...
            NAVIGATE_TO (rt_x)
            TYPE_INTO (sel_a, cv_b)
            ...
            GATE_NAME (!param)
            OBSERVE (sel_obs)

        TREE-STRUCTURED (new):
            -- [SI_GATE:NAME] ...
            case screen in
                SCR_A ->
                    CLICK (sel_x); ...
              | SCR_B ->
                    null
              | ...
            end case;
            screen := SCR_ANCHOR;
            -- post-case common actions --
            WAIT_FOR (sel_y)
            GATE_NAME (!param)
            OBSERVE (sel_obs)

        The parser emits:
          - `traversal_paths`: dict[screen_name -> [actions]]  for tree branches
          - `actions`:         list of post-gate-firing common actions
          - `wait_for`:        first WAIT_FOR after the case block (or in flat branch)
          - `observe`:         OBSERVE spec
          - `url`:             NAVIGATE_TO route (flat branches only)
        """
        # Paper-style branch (no [SI_GATE:] marker): marker-less abstract gates,
        # lowercase concrete actions, optional nested alt over abstract outputs.
        # Fully additive — [SI_GATE:]-marked branches (Spliit/Moodle) keep
        # the legacy path below untouched.
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if not self._GATE_LINE_RE.search(branch):
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            self._parse_branch_paperstyle(branch)
            # `return` exits the current function immediately and gives no explicit value back.
            return

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        lines = branch.split("\n")

        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        gate_name:            Optional[str]  = None
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        param_types:          dict           = {}
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        url:                  Optional[str]  = None
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        actions:              list           = []          # post-case common actions
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        wait_for:             Optional[dict] = None
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        observe:              Optional[dict] = None
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        traversal_paths:      Optional[dict] = None       # None = flat SI
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        pending_observe_attr: Optional[str]  = None
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        l_value_map:          dict           = dict(self._var_defaults)

        # Pre-scan L-value annotations in comments
        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for line in lines:
            # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
            for lm in self._L_VALUE_RE.finditer(line):
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                var_name = lm.group(1)
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                enum_val = lm.group(2)
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                resolved = self._resolve_value(enum_val)
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                l_value_map[var_name] = resolved if resolved else enum_val

        # ---- State machine --------------------------------------------
        # PHASES:
        #   "header"       : before case block (gate comment, flat navigates)
        #   "case"         : inside case screen in ... end case
        #   "post_case"    : after end case; (screen :=, common actions, gate fire)
        #   "flat"         : no case block, all actions are direct

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        phase = "header"
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        current_screen: Optional[str] = None   # screen arm being collected
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        arm_actions:    list          = []      # actions for current_screen arm

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        i = 0
        # `while` keeps repeating the indented block as long as the condition before the colon stays true.
        while i < len(lines):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            line    = lines[i]
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            stripped = line.strip()
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            i += 1

            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if not stripped:
                # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                continue

            # ── Comments ──────────────────────────────────────────────
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if stripped.startswith("--"):
                # Gate annotation
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                m = self._GATE_LINE_RE.match(stripped)
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if m:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    gate_name = m.group(1)
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    meta_str  = m.group(2)
                    # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
                    for kv in self._KV_PAIRS_RE.finditer(meta_str):
                        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                        key, val = kv.group(1), kv.group(2)
                        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                        if key == "param_types":
                            # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
                            for idx, part in enumerate(val.split(",")):
                                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                                part = part.strip()
                                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                                if not part:
                                    # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                                    continue
                                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                                if "=" in part:
                                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                                    pk, pv = part.split("=", 1)
                                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                                    param_types[pk.strip()] = pv.strip()
                                # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
                                else:
                                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                                    param_types[f"param_{idx}"] = part
                    # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                    continue
                # observe_attr annotation
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                m = self._OBSERVE_ATTR_RE.match(stripped)
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if m:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    pending_observe_attr = m.group(1)
                # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                continue

            # ── Case block open ───────────────────────────────────────
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if self._CASE_OPEN_RE.match(stripped) and phase == "header":
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                phase            = "case"
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                traversal_paths  = {}
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                current_screen   = None
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                arm_actions      = []
                # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                continue

            # ── Inside case block ─────────────────────────────────────
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if phase == "case":
                # Case close
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if self._CASE_CLOSE_RE.match(stripped):
                    # Flush last arm
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if current_screen is not None:
                        # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                        traversal_paths[current_screen] = arm_actions
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    phase          = "post_case"
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    current_screen = None
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    arm_actions    = []
                    # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                    continue

                # New screen arm:  SCR_X ->  or  | SCR_X ->
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                m = self._SCREEN_ARM_RE.match(stripped)
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if m:
                    # Flush previous arm
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if current_screen is not None:
                        # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                        traversal_paths[current_screen] = arm_actions
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    current_screen = m.group(1)
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    arm_actions    = []
                    # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                    continue

                # null arm
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if self._NULL_RE.match(stripped) and current_screen is not None:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    arm_actions = []   # empty list = no traversal needed
                    # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                    continue

                # Action line inside arm
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if current_screen is not None:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    parsed = self._parse_action_line(stripped, l_value_map,
                                                     # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                                                     wait_for_list=[])
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    arm_actions.extend(parsed)
                # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                continue

            # ── Post-case phase ───────────────────────────────────────
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if phase == "post_case":
                # screen := SCR_X  (update current screen — consumed, not emitted)
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if self._SCREEN_ASSIGN_RE.match(stripped):
                    # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                    continue

                # Remaining lines are common post-gate actions, wait_for, observe
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                result = self._parse_post_case_line(
                    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                    stripped, l_value_map,
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    wait_for, observe, pending_observe_attr, actions
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                wait_for, observe, pending_observe_attr = (
                    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                    result["wait_for"], result["observe"],
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    result["pending_observe_attr"]
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
                # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                continue

            # ── Header / flat phase ───────────────────────────────────
            # (no case block encountered yet)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if phase == "header":
                # Detect start of case block (already handled above)
                # Otherwise treat as flat action line
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                result = self._parse_post_case_line(
                    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                    stripped, l_value_map,
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    wait_for, observe, pending_observe_attr, actions
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                wait_for, observe, pending_observe_attr = (
                    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                    result["wait_for"], result["observe"],
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    result["pending_observe_attr"]
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
                # If NAVIGATE_TO was parsed, capture as url
                # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
                for act in result.get("new_actions", []):
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if act.get("action") == "navigate":
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        url = act.get("url")
                # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                continue

        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate_name is None:
            # `return` exits the current function immediately and gives no explicit value back.
            return

        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        spec: dict = {}
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if url:
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            spec["url"] = url
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if param_types:
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            spec["param_types"] = param_types
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if actions:
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            spec["actions"] = actions
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if wait_for:
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            spec["wait_for"] = wait_for
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if observe:
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            spec["observe"] = observe
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if traversal_paths is not None:
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            spec["traversal_paths"] = traversal_paths

        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        self._gates[gate_name] = ConcreteActionTree(spec)
        # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
        logger.debug(
            # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
            f"SI gate parsed: {gate_name} -> keys={list(spec.keys())} "
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            f"screens={list(traversal_paths.keys()) if traversal_paths else 'flat'}"
        # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
        )

    # ------------------------------------------------------------------
    # Action-line parsers (shared between arm and post-case contexts)
    # ------------------------------------------------------------------

    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
    def _parse_action_line(
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        self,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        stripped:     str,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        l_value_map:  dict,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        wait_for_list: list,
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    ) -> list[dict]:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """
        Parse a single LNT statement line into 0..N action dicts.
        Returns a list (usually length 0 or 1, sometimes 2 for NAVIGATE_TO_S).
        """
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        result = []

        # NAVIGATE_TO_S (route_enum, session_var)
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._NAVIGATE_S_RE.search(stripped)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            route_enum = m.group(1)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            resolved   = self._resolve_route(route_enum)
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            result.append({"action": "navigate", "url": resolved or route_enum})
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return result

        # NAVIGATE_TO (route_enum) — formal
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._NAVIGATE_ENUM_RE.search(stripped)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m and not self._NAVIGATE_STR_RE.search(stripped):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            route_enum = m.group(1)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            resolved   = self._resolve_route(route_enum)
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            result.append({"action": "navigate", "url": resolved or route_enum})
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return result

        # NAVIGATE_TO ("url") — legacy
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._NAVIGATE_STR_RE.search(stripped)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m:
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            result.append({"action": "navigate", "url": m.group(1)})
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return result

        # TYPE_INTO (sel_enum, L_func(var)) — formal with L-function
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._TYPE_INTO_L_RE.search(stripped)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m and not self._TYPE_INTO_STR_RE.search(stripped):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel_enum = m.group(1)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel      = self._resolve_selector(sel_enum) or sel_enum
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            func_m   = re.search(r'(L_\w+)\s*\(\s*(\w+)\s*\)', stripped)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            func_name = func_m.group(1) if func_m else ""
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            var_m    = re.search(r'L_\w+\s*\(\s*(\w+)\s*\)', stripped)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            var_name = var_m.group(1) if var_m else ""
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            val      = (self._resolve_l_function(func_name, var_name, l_value_map)
                        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                        if func_name else l_value_map.get(var_name, var_name))
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            result.append(self._make_action(sel, "clear_and_type", param=val))
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return result

        # TYPE_INTO (sel_enum, cv_enum) — formal
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._TYPE_INTO_ENUM_RE.search(stripped)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m and not self._TYPE_INTO_STR_RE.search(stripped):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel_enum = m.group(1)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            val_enum = m.group(2)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel      = self._resolve_selector(sel_enum) or sel_enum
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            val      = self._resolve_value_or_self(val_enum)
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            result.append(self._make_action(sel, "clear_and_type", param=val))
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return result

        # TYPE_INTO ("selector", "param") — legacy
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._TYPE_INTO_STR_RE.search(stripped)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel = m.group(1)
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            result.append(self._make_action(sel, "clear_and_type", param=m.group(2)))
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return result

        # CLICK (sel_enum) — formal
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._CLICK_ENUM_RE.search(stripped)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m and not self._CLICK_STR_RE.search(stripped):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel_enum = m.group(1)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel      = self._resolve_selector(sel_enum) or sel_enum
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            result.append(self._make_action(sel, "click"))
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return result

        # CLICK ("selector") — legacy
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._CLICK_STR_RE.search(stripped)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel = m.group(1)
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            result.append(self._make_action(sel, "click"))
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return result

        # WAIT_FOR (sel_enum) — formal
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._WAIT_FOR_ENUM_RE.search(stripped)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m and not self._WAIT_FOR_STR_RE.search(stripped):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel_enum = m.group(1)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel      = self._resolve_selector(sel_enum) or sel_enum
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            result.append(self._make_action(sel, "wait_for"))
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return result

        # WAIT_FOR ("selector") — legacy
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._WAIT_FOR_STR_RE.search(stripped)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel = m.group(1)
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            result.append(self._make_action(sel, "wait_for"))
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return result

        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return result

    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
    def _parse_post_case_line(
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        self,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        stripped:             str,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        l_value_map:          dict,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        wait_for:             Optional[dict],
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        observe:              Optional[dict],
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        pending_observe_attr: Optional[str],
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        actions:              list,
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    ) -> dict:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """
        Parse one line in the post-case (or flat) section.
        Updates and returns wait_for, observe, pending_observe_attr.
        Also appends to `actions` in-place and returns new_actions for
        navigate detection.
        """
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        new_actions = []

        # screen := SCR_X  — skip silently
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if self._SCREEN_ASSIGN_RE.match(stripped):
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return {
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                "wait_for": wait_for, "observe": observe,
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                "pending_observe_attr": pending_observe_attr,
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                "new_actions": new_actions,
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            }

        # OBSERVE — formal
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._OBSERVE_ENUM_RE.search(stripped)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m and not self._OBSERVE_STR_RE.search(stripped) and observe is None:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel_enum = m.group(1)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel      = self._resolve_element(sel_enum) or self._resolve_selector(sel_enum) or sel_enum
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            attr     = pending_observe_attr or "text"
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            pending_observe_attr = None
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            observe  = self._make_observe(sel, default_attr=attr)
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return {
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                "wait_for": wait_for, "observe": observe,
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                "pending_observe_attr": pending_observe_attr,
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                "new_actions": new_actions,
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            }

        # OBSERVE — legacy
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._OBSERVE_STR_RE.search(stripped)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m and observe is None:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel  = m.group(1)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            attr = pending_observe_attr or "text"
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            pending_observe_attr = None
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            observe = self._make_observe(sel, default_attr=attr)
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return {
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                "wait_for": wait_for, "observe": observe,
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                "pending_observe_attr": pending_observe_attr,
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                "new_actions": new_actions,
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            }

        # WAIT_FOR — promote first occurrence to wait_for, rest to actions
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m_wf = (self._WAIT_FOR_ENUM_RE.search(stripped)
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if not self._WAIT_FOR_STR_RE.search(stripped)
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                else None)
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m_wf_str = self._WAIT_FOR_STR_RE.search(stripped)

        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m_wf or m_wf_str:
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if m_wf:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                sel_enum = m_wf.group(1)
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                sel      = self._resolve_element(sel_enum) or self._resolve_selector(sel_enum) or sel_enum
            # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
            else:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                sel = m_wf_str.group(1)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            wait_action = self._make_action(sel, "wait_for")
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if wait_for is None:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                wait_for = {k: wait_action[k] for k in ("selector", "by") if k in wait_action}
            # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
            else:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                act = wait_action
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                actions.append(act)
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                new_actions.append(act)
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return {
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                "wait_for": wait_for, "observe": observe,
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                "pending_observe_attr": pending_observe_attr,
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                "new_actions": new_actions,
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            }

        # All other action lines
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        parsed = self._parse_action_line(stripped, l_value_map, wait_for_list=[])
        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for act in parsed:
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            actions.append(act)
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            new_actions.append(act)

        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return {
            # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
            "wait_for": wait_for, "observe": observe,
            # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
            "pending_observe_attr": pending_observe_attr,
            # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
            "new_actions": new_actions,
        # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
        }

    # ------------------------------------------------------------------
    # Paper-style (marker-less, nested-alt) parsing — additive
    # ------------------------------------------------------------------

    # `def _extract_alt_body` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> Optional[str]` documents the expected return type.
    def _extract_alt_body(self, text: str) -> Optional[str]:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """
        Return the text BETWEEN the outer `alt` and its matching `end alt`
        (comments preserved), locating the boundaries on code only so the words
        'alt'/'loop' inside comments cannot mislead the scan. Replaces a raw
        regex that would otherwise latch onto an 'alt' mentioned in a header
        comment. Behaviour is identical for comment-free SIs (Spliit and
        Moodle).
        """
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        seen_loop = False
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        started   = False
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        depth     = 0
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        body: list[str] = []

        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for line in text.split("\n"):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            code   = line.split("--")[0]
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            n_end  = len(self._END_SEL_RE.findall(code))
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            n_open = len(self._SELECT_RE.findall(code)) - n_end

            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if not started:
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if not seen_loop and re.search(r'\bloop\b', code, re.IGNORECASE):
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    seen_loop = True
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if seen_loop and n_open > 0:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    started = True
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    depth   = n_open - n_end
                # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                continue

            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            depth += n_open - n_end
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if depth <= 0:
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return "\n".join(body)          # outer 'end alt' reached
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            body.append(line)

        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return "\n".join(body) if body else None

    # `def _parse_branch_paperstyle` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> None` documents the expected return type.
    def _parse_branch_paperstyle(self, branch: str) -> None:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """
        Parse one marker-less (paper-style) outer branch.

        Structure:
            <concrete inputs> ABSTRACT_INPUT [ <concrete outputs> ABSTRACT_OUTPUT ]
        optionally wrapped in `if (guard) then ... end if`, and optionally with a
        nested `alt` immediately after the abstract input — one arm per distinct
        abstract output. Each nested arm becomes its own concrete-observation
        sequence + resulting abstract output (recorded under the output gate's
        `branches`).
        """
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        lines        = branch.split("\n")
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        l_value_map  = dict(self._var_defaults)

        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        prefix, arms = self._split_nested_alt(lines)

        # Linear prefix: concrete inputs + the abstract input gate (+ any inline
        # outputs when there is no nested alt).
        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for gate, spec in self._parse_linear_steps(prefix, l_value_map):
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            self._merge_gate(gate, spec)

        # Nested alt: each arm is its own observation sequence -> abstract output.
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if arms is not None:
            # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
            per_gate: dict[str, list] = {}
            # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
            for arm in arms:
                # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
                for gate, spec in self._parse_linear_steps(arm, l_value_map):
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    per_gate.setdefault(gate, []).append(spec)
            # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
            for gate, specs in per_gate.items():
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                merged = dict(specs[0])
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if len(specs) > 1:
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    merged["branches"] = specs
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                self._merge_gate(gate, merged)

    # `def _merge_gate` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> None` documents the expected return type.
    def _merge_gate(self, gate: str, spec: dict) -> None:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """Insert a gate spec, accumulating nested-alt `branches` if re-seen."""
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate in self._gates:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            existing = self._gates[gate]
            # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
            for k, v in spec.items():
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if k == "branches":
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    existing.setdefault("branches", []).extend(v)
                # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
                else:
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    existing.setdefault(k, v)
        # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
        else:
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            self._gates[gate] = ConcreteActionTree(spec)

    # `def _split_nested_alt` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> tuple` documents the expected return type.
    def _split_nested_alt(self, lines: list) -> tuple:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """
        Split a branch's lines into (prefix_lines, arms). `arms` is None when the
        branch has no nested alt; otherwise it is a list of line-lists, one per
        nested-alt arm. Boundaries are detected on code only (comments ignored).
        """
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        depth       = 0
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        prefix:  list = []
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        arms:    Optional[list] = None
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        current: list = []

        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for line in lines:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            code = line.split("--")[0].strip()

            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if self._PS_ALT_OPEN_RE.match(code):
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if depth == 0:
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    arms, current, depth = [], [], 1
                    # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                    continue
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                depth += 1
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if self._PS_ALT_CLOSE_RE.match(code):
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                depth -= 1
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if depth == 0:
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    arms.append(current)
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    current = []
                    # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                    continue

            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if depth >= 1:
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if code == "[]" and depth == 1:
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    arms.append(current)
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    current = []
                    # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                    continue
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                current.append(line)
            # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
            else:
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                prefix.append(line)

        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return prefix, arms

    # `def _parse_linear_steps` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> list` documents the expected return type.
    def _parse_linear_steps(self, lines: list, l_value_map: dict) -> list:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """
        Walk a linear (no nested alt) line sequence, accumulating concrete
        actions and emitting (abstract_gate, spec) the moment each abstract gate
        call is reached. Non-screen guards and `end`/`null` lines are skipped.

        Two things the model states explicitly are carried through rather than
        discarded, because the runtime otherwise has to guess them:

          `guards`             ordered [{when_screen, actions, destination}] from
                               `if screen == SCR_X then ... end if` blocks. The
                               runtime runs a guard only when it believes it is on
                               that screen, matching LNT's own semantics.
          `destination_screen` where the gate leaves the SUT, from `screen := SCR_X`.
                               Emitted ONLY when the segment names a single
                               destination unambiguously: this parser flattens
                               nested alts, so a segment spanning two arms can
                               carry two conflicting targets and asserting either
                               one would be a fabricated claim about the SUT.
        """
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        steps:    list = []
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        actions:  list = []
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        wait_for: Optional[dict] = None
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        observe:  Optional[dict] = None
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        observes: list = []
        # Screen-guard / destination state for the segment leading to the next gate.
        guards:   list = []
        # Every distinct `screen := SCR_X` seen in this segment, in order. More
        # than one distinct value = ambiguous, see the docstring.
        dests:    list = []
        # Non-None while inside `if screen == ... then`: the guard being collected.
        cur_guard: Optional[dict] = None
        # `end if` nesting depth inside the current guard body.
        guard_depth = 0

        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for line in lines:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            code = line.split("--")[0].strip()
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if not code:
                # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                continue

            # ---- screen guards ------------------------------------------
            gm = self._PS_IF_SCREEN_RE.match(code)
            if gm and cur_guard is None:
                cur_guard   = {"when_screen": gm.group(1), "actions": [],
                               "destination": None}
                guard_depth = 0
                continue

            if cur_guard is not None:
                # Track nested `if ... then` so only the guard's OWN `end if`
                # closes it.
                if self._PS_IF_ANY_RE.match(code):
                    guard_depth += 1
                    continue
                if self._PS_END_IF_RE.match(code):
                    if guard_depth > 0:
                        guard_depth -= 1
                        continue
                    guards.append(cur_guard)
                    cur_guard = None
                    continue

            # ---- `screen := SCR_X` --------------------------------------
            sm = self._SCREEN_ASSIGN_RE.match(code)
            if sm:
                if cur_guard is not None:
                    # A guard's trailing assignment is unambiguous: it is where
                    # THAT body lands, whatever the surrounding alt does.
                    cur_guard["destination"] = sm.group(1)
                elif sm.group(1) not in dests:
                    dests.append(sm.group(1))
                continue

            # Abstract gate call (UPPERCASE head, not a concrete primitive)?
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            am = self._PS_ABSTRACT_RE.match(code)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if am and am.group(1) not in self._CONCRETE_HEADS:
                # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
                spec: dict = {}
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if actions:
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    spec["actions"] = actions
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if wait_for:
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    spec["wait_for"] = wait_for
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if observe:
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    spec["observe"] = observe
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if len(observes) > 1:
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    spec["observes"] = observes
                if guards:
                    spec["guards"] = guards
                if len(dests) == 1:
                    spec["destination_screen"] = dests[0]
                elif len(dests) > 1:
                    # Say so rather than picking: the runtime falls back to
                    # probing the screen anchors instead of asserting a belief.
                    logger.debug(
                        f"{am.group(1)}: ambiguous destination {dests} "
                        f"(flattened alt) — no destination_screen emitted")
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                steps.append((am.group(1), spec))
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                actions, wait_for, observe, observes = [], None, None, []
                guards, dests = [], []
                # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                continue

            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            kind, act = self._parse_concrete_paper(code, l_value_map)

            # Inside a guard everything belongs to that guard's body — including
            # its wait_for. Letting a guard's wait_for become the GATE's wait_for
            # is how SEARCH_FOOD came to wait on el_search_input (the guard's
            # "search screen is up") instead of el_search_results (its own
            # precondition), silently dropping the check it was written to make.
            if cur_guard is not None:
                if kind is not None:
                    cur_guard["actions"].append(act)
                continue

            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if kind in ("navigate", "tap", "click", "type_into"):
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                actions.append(act)
            # `elif` means 'else, if this other condition is true'; Python reaches it only when earlier `if` or `elif` checks in the same chain did not run.
            elif kind == "wait_for":
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if wait_for is None:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    wait_for = {"selector": act["selector"], "by": act["by"]}
                # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
                else:
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    actions.append(act)
            # `elif` means 'else, if this other condition is true'; Python reaches it only when earlier `if` or `elif` checks in the same chain did not run.
            elif kind == "observe":
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                observes.append(act)
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if observe is None:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    observe = act
            # else: assignment / guard / structural line -> skip

        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return steps

    # `def _parse_concrete_paper` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> tuple` documents the expected return type.
    def _parse_concrete_paper(self, code: str, l_value_map: dict) -> tuple:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """Classify one lowercase concrete-action line -> (kind, action_dict)."""
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._PS_NAVIGATE_RE.search(code)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            route = self._resolve_route(m.group(1)) or m.group(1)
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return "navigate", {"action": "navigate", "url": route}

        m = self._PS_CLICK_L_RE.search(code)
        if m:
            target = self._resolve_l_function(m.group(1), m.group(2), l_value_map)
            sel = self._resolve_selector(target) or target
            return "click", self._make_action(sel, "click", param=target)

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._PS_CLICK_RE.search(code)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel = self._resolve_selector(m.group(1)) or m.group(1)
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return "click", self._make_action(sel, "click")

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._PS_TYPE_INTO_L_RE.search(code)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel = self._resolve_selector(m.group(1)) or m.group(1)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            val = self._resolve_l_function(m.group(2), m.group(3), l_value_map)
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return "type_into", self._make_action(sel, "clear_and_type", param=val)

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._PS_TYPE_INTO_RE.search(code)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel = self._resolve_selector(m.group(1)) or m.group(1)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            val = self._resolve_value_or_self(m.group(2))
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return "type_into", self._make_action(sel, "clear_and_type", param=val)

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._PS_TAP_L_RE.search(code)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            var = m.group(1)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            val = l_value_map.get(var, var)
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return "tap", self._make_action(val, "click", param=val)

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._PS_TAP_RE.search(code)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            val = self._resolve_value_or_self(m.group(1))
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return "tap", self._make_action(val, "click")

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._PS_WAITFOR_RE.search(code)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel = self._resolve_element(m.group(1)) or m.group(1)
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return "wait_for", self._make_action(sel, "wait_for")

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        m = self._PS_OBSERVE_RE.search(code)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if m:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            sel = self._resolve_element(m.group(1)) or m.group(1)
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return "observe", self._make_observe(sel)

        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return None, None

    # `def _locator_spec` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> dict` documents the expected return type.
    def _locator_spec(self, locator, default_attr: str | None = None) -> dict:
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if isinstance(locator, dict):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            spec = dict(locator)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            selector = spec.get("selector", "")
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if "by" not in spec:
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                spec["by"] = self._by_for(str(selector))
        # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
        else:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            selector = str(locator)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            spec = {"selector": selector, "by": self._by_for(selector)}
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if default_attr is not None and "attribute" not in spec:
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            spec["attribute"] = default_attr
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return spec

    # `def _make_action` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> dict` documents the expected return type.
    def _make_action(self, locator, action: str, param=None) -> dict:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        spec = self._locator_spec(locator)
        # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
        spec["action"] = action
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if param is not None:
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            spec["param"] = param
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return spec

    # `def _make_observe` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> dict` documents the expected return type.
    def _make_observe(self, locator, default_attr: str = "text") -> dict:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        spec = self._locator_spec(locator, default_attr=default_attr)
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return {
            # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
            "selector": spec.get("selector", ""),
            # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
            "by": spec.get("by", "id"),
            # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
            "attribute": spec.get("attribute", default_attr),
        # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
        }

    # `@staticmethod` means the next function lives on the class but does not receive `self`; it is a helper grouped with the class because it belongs to that idea.
    @staticmethod
    # `def _by_for` creates a reusable function/method; the parentheses list inputs, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> str` documents the expected return type.
    def _by_for(selector: str) -> str:
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if (selector.startswith("//") or selector.startswith(".//")
                # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
                or selector.startswith("(//") or selector.startswith("(/")):
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return "xpath"
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if selector.startswith("#"):
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return "css"
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return "id"
