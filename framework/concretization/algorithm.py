# In the concretization story, algorithm.py is the test walker: it reads AUT/BCG transitions, 
# chooses whether to perform an input or wait for an output, resolves abstract values into concrete values, 
# calls executors.py to touch the real UI, calls si_lnt_parser.py data through the element map, 
# and optionally calls disruptor.py when a fault gate appears.

"""
algorithm.py  (v3 — flat + graph, ioco correct, all fixes applied)
"""
# `from` chooses a module to read from, `__future__` enables newer Python behavior early, 
# and `import annotations` lets type hints be stored lazily so this file can use modern type syntax.
from __future__ import annotations
# `import` loads a library module so this file can call its functions; 
# the comma-separated names are the helper libraries this line makes available.
import logging, re, subprocess, time
# `from ... import ...` means Python opens another module and brings only the named tools into this file, 
# instead of importing the whole module name.
from collections import defaultdict
# `from ... import ...` means Python opens another module and brings only the named tools into this file, 
# instead of importing the whole module name.
from dataclasses import dataclass, field
# `from ... import ...` means Python opens another module and brings only the named tools into this file, 
# instead of importing the whole module name.
from enum import Enum, auto
# This imports DisruptionExecutor from disruptor.py, connecting the graph-walking algorithm to the fault-injection helper used when a 
# DISRUPTION_OCCURS gate is reached.
from .disruptor import DisruptionExecutor
# This imports STRUCTURAL_SKIP_GATES from si_lnt_parser.py so algorithm.py validates the same structural gates that the LNT parser 
# intentionally leaves without executable UI entries.
from .si_lnt_parser import STRUCTURAL_SKIP_GATES

# This creates a logger named after this module, so messages from this file can be filtered and traced 
# while the concretization run is happening.
logger = logging.getLogger(__name__)


# `class Verdict` defines a new kind of object; `(Enum)` means it inherits behavior or rules from Enum, 
# and the colon starts the indented body of the class.
class Verdict(Enum):
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    PASS = auto()
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    FAIL = auto()
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    INCONC = auto()
    # NOT A VERDICT. The walk could not be carried out, so the SUT was never put
    # to the question and no ioco statement about it is available.
    #
    # PASS/FAIL/INCONC are the three outcomes of walking the test case: they are
    # read off the AUT's trap states, or reached when an observed output is not
    # in the expected set. UNEXECUTABLE is what remains when the apparatus --
    # not the SUT -- prevented the walk: a stimulus that could not be applied,
    # a parameter with no concrete interpretation, a step budget exhausted, an
    # abstract value this deployment cannot produce.
    #
    # It is deliberately OUTSIDE the verdict lattice. Reporting such a run as
    # INCONCLUSIVE would file a harness defect under a genuine ioco outcome
    # (a refuse state, or no accepting state reachable), and reporting it as
    # FAIL would claim the SUT contradicted its specification on evidence that
    # was never gathered. Both have happened here; this exists so neither can.
    #
    # An UNEXECUTABLE run is a bug with an owner: fix it and run again. It must
    # never be counted in a verdict total.
    UNEXECUTABLE = auto()

# `class Direction` defines a new kind of object; `(Enum)` means it inherits behavior or rules from Enum, and the colon starts the indented body of the class.
class Direction(Enum):
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    INPUT  = auto()
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    OUTPUT = auto()
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    BOTH   = auto()


# `@dataclass` is a decorator: Python applies it to the next class so the class automatically gets a useful constructor and readable stored fields.
@dataclass
# `class ParsedStep` defines a new kind of object; the colon means the following indented lines belong inside that class.
class ParsedStep:
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    gate_name:  str
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    direction:  Direction
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    params:     list
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    raw_label:  str = ""

# `@dataclass` is a decorator: Python applies it to the next class so the class automatically gets a useful constructor and readable stored fields.
@dataclass
# `class StepResult` defines a new kind of object; the colon means the following indented lines belong inside that class.
class StepResult:
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    verdict:         object
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    gate_name:       str
    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
    concrete_values: dict = field(default_factory=dict)
    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
    captured:        dict = field(default_factory=dict)
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    error:           str  = ""
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    duration_ms:     float = 0.0

# `@dataclass` is a decorator: Python applies it to the next class so the class automatically gets a useful constructor and readable stored fields.
@dataclass
# `class AUTTransition` defines a new kind of object; the colon means the following indented lines belong inside that class.
class AUTTransition:
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    source: int
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    label:  str
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    target: int

# `@dataclass` is a decorator: Python applies it to the next class so the class automatically gets a useful constructor and readable stored fields.
@dataclass
# `class AUTGraph` defines a new kind of object; the colon means the following indented lines belong inside that class.
class AUTGraph:
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    initial:     int
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    transitions: list[AUTTransition]
    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
    adjacency:   dict = field(default_factory=dict)

    # `def __post_init__` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def __post_init__(self):
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        adj = defaultdict(list)
        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for t in self.transitions:
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            adj[t.source].append(t)
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.adjacency = dict(adj)

    # `def outgoing` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> list[AUTTransition]` documents the expected return type.
    def outgoing(self, state: int) -> list[AUTTransition]:
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self.adjacency.get(state, [])


# `class BCGReader` defines a new kind of object; the colon means the following indented lines belong inside that class.
class BCGReader:
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    INPUT_GATES   = {"REGISTER", "LOGIN", "RECORD_SPO2", "RECORD_HEARTRATE",
                     # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                     "PASSWORD", "NURSE_OUTREACH", "ACKNOWLEDGE_ALERT", "DISRUPTION_OCCURS",
                     # Spliit case study
                     # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                     "CREATE_GROUP", "CREATE_EXPENSE", "VIEW_BALANCES", "CONFIRM_SPLIT",
                     # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                     "UE1_OFFLINE",
                     # FoodYou case study (abstract tester stimuli)
                     # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                     "SEARCH_FOOD", "ADD_ENTRY",
                     # Quiescence-as-input: represents the tester injecting a timeout observation
                     # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                     "APP_TIMEOUT"}
    # Gates whose (PASS) label suffix means "quiescence is acceptable" rather than
    # "fire this immediately to get PASS".  In mixed states these are deferred until
    # all expected outputs have been tried; in pure-input states they are terminal.
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    QUIESCENCE_GATES = {"APP_TIMEOUT"}
    # TGV's quiescence / deadlock sentinel.  It carries no observable spec, so it
    # can never be "matched" against the SUT; instead it is the branch the tester
    # takes when it observes *nothing* (a timeout).  Its verdict suffix is taken
    # when an observation times out and no real output matched.
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    QUIESCENCE_SENTINELS = {"LOCK", ":DELTA:"}   # LOCK = TGV, :DELTA: = TESTOR
    # Low-level UI gates whose concrete steps are bundled into each meaningful
    # gate's traversal_paths (run by LNTSIExecutorAdapter). They carry no action
    # or observation of their own, so the walker advances past them like taus.
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    STRUCTURAL_UI_GATES = {
        # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
        "NAVIGATE_TO", "NAVIGATE", "TAP", "TYPE_INTO", "ENTER_TEXT", "CLICK", "WAIT_FOR", "OBSERVE"
    # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
    }
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    BOTH_GATES    = {"SUBMIT_CHECKIN", "CONFIRMED"}
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    SKIP_GATES    = {
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "I", "T_ACCEPT", "T_REFUSE", "OTHERWISE", "LOCK",
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "NAVIGATE_TO", "NAVIGATE", "TAP", "CLICK", "WAIT_FOR", "TYPE_INTO", "ENTER_TEXT", "OBSERVE",
    # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
    }
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    VERDICT_GATES = {"PASS", "FAIL", ":PASS:", ":FAIL:", ":INCONCLUSIVE:"}
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    ATTACK_GATES  = {"ATTACK_DATA_ACCESS", "ATTACK_NO_ALERT"}
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    FAILURE_GATES = {"FAILURE"}


    # `def read_aut_file` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> AUTGraph` documents the expected return type.
    def read_aut_file(self, path: str) -> AUTGraph:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        transitions = []
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        initial = 0
        # `with open(...) as f` opens a file and guarantees it will be closed automatically; `f` is the file handle used by the indented block.
        with open(path) as f:
            # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
            for line in f:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                line = line.strip()
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if not line:
                    # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                    continue
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if line.startswith("des"):
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    m = re.match(r"des\s*\(\s*(\d+)\s*,", line)
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if m:
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        initial = int(m.group(1))
                    # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                    continue
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                m = re.match(
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    r'\(\s*(\d+)\s*,\s*"([^"]+)"\s*,\s*(\d+)\s*\)', line
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if not m:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    m = re.match(
                        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
                        r'\(\s*(\d+)\s*,\s*([A-Z_:][^,]*?)\s*,\s*(\d+)\s*\)', line
                    # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                    )
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if m:
                        # unquoted label — remap group indices
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        src   = int(m.group(1))
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        label = m.group(2).strip()
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        tgt   = int(m.group(3))
                        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                        transitions.append(AUTTransition(src, label, tgt))
                        # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                        continue
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if m:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    src   = int(m.group(1))
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    label = m.group(2).strip().strip('"')
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    tgt   = int(m.group(3))
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    transitions.append(AUTTransition(src, label, tgt))
        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
        logger.debug(f"AUT parsed: {len(transitions)} transitions, initial={initial}")
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return AUTGraph(initial=initial, transitions=transitions)

    # `def bcg_to_aut` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> str | None` documents the expected return type.
    def bcg_to_aut(self, bcg_path: str) -> str | None:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        aut_path = bcg_path.replace(".bcg", ".aut")
        # `try` starts a protected block: Python attempts the indented code and jumps to `except` if an error happens.
        try:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            result = subprocess.run(
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                ["bcg_io", bcg_path, aut_path],
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                capture_output=True, text=True, timeout=30
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if result.returncode != 0:
                # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                logger.error(f"bcg_io failed: {result.stderr}")
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return None
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return aut_path
        # `except` catches an error from the matching `try` block so the concretization run can report or recover instead of crashing immediately.
        except Exception as e:
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.error(f"bcg_io unavailable: {e}")
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return None

    # `def read_bcg_file` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> AUTGraph | None` documents the expected return type.
    def read_bcg_file(self, bcg_path: str) -> AUTGraph | None:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        aut_path = self.bcg_to_aut(bcg_path)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if aut_path is None:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return None
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self.read_aut_file(aut_path)


    # `def classify_label` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> Direction` documents the expected return type.
    def classify_label(self, label: str) -> Direction:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        gate = label.split()[0].upper().rstrip(";")
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate in self.VERDICT_GATES: return Direction.OUTPUT
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate in self.ATTACK_GATES:  return Direction.OUTPUT
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate in self.FAILURE_GATES: return Direction.OUTPUT
        # TGV-generated AUTs (bcg_io with an .io file) tag each transition with
        # its IOCO direction, written from the TESTER's perspective:
        #   "; OUTPUT" -> tester stimulus (input to the SUT)  -> perform -> Direction.INPUT
        #   "; INPUT"  -> tester observation (SUT output)      -> observe -> Direction.OUTPUT
        # Honor it when present; legacy AUTs (from the early mock app) carry no suffix and
        # fall through to the gate-name sets below.
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        up = label.upper()
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if "; OUTPUT" in up: return Direction.INPUT
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if "; INPUT"  in up: return Direction.OUTPUT
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate in self.INPUT_GATES:   return Direction.INPUT
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate in self.BOTH_GATES:    return Direction.BOTH
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return Direction.OUTPUT

    # `def is_verdict_label` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> bool` documents the expected return type.
    def is_verdict_label(self, label: str) -> bool:
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return label.strip().split()[0].upper() in self.VERDICT_GATES

    # `def is_attack_label` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> bool` documents the expected return type.
    def is_attack_label(self, label: str) -> bool:
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return label.strip().split()[0].upper() in self.ATTACK_GATES

    # `def is_failure_label` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> bool` documents the expected return type.
    def is_failure_label(self, label: str) -> bool:
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return label.strip().split()[0].upper() in self.FAILURE_GATES

    # `def is_internal_label` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> bool` documents the expected return type.
    def is_internal_label(self, label: str) -> bool:
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return label.strip().lower() == "i"

    # `def is_quiescence_sentinel` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> bool` documents the expected return type.
    def is_quiescence_sentinel(self, label: str) -> bool:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """True for TGV's quiescence/deadlock branch (e.g. ``LOCK; INPUT (...)``)."""
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return label.strip().split()[0].upper().rstrip(";") in self.QUIESCENCE_SENTINELS

    # `def is_structural_ui_label` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> bool` documents the expected return type.
    def is_structural_ui_label(self, label: str) -> bool:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """True for low-level UI gates bundled into traversal_paths (NAVIGATE_TO, …)."""
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return label.strip().split()[0].upper().rstrip(";") in self.STRUCTURAL_UI_GATES

    # `def verdict_from_suffix` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> Verdict | None` documents the expected return type.
    def verdict_from_suffix(self, label: str) -> Verdict | None:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """Extract a TGV ``(PASS)``/``(FAIL)``/``(INCONCLUSIVE)`` suffix verdict."""
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        up = label.upper()
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if "(PASS)" in up:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return Verdict.PASS
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if "(FAIL)" in up:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return Verdict.FAIL
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if "(INCONCLUSIVE)" in up:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return Verdict.INCONC
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return None

    # `def map_verdict` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> Verdict` documents the expected return type.
    def map_verdict(self, label: str) -> Verdict:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        gate = label.strip().split()[0].upper()
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate in (":INCONCLUSIVE:", "INCONCLUSIVE"):
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return Verdict.INCONC
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate in ("PASS", ":PASS:"):
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return Verdict.PASS
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return Verdict.FAIL

    # `def parse_gate_and_params` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def parse_gate_and_params(self, label: str):
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        tokens = label.split()
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if not tokens:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return None, []
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        gate = tokens[0].upper().rstrip(";")
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        params = []
        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for i, t in enumerate(tokens[1:]):
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if t.startswith("!"):
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                params.append((f"param_{i}", t[1:].rstrip(";").lower()))
            # `elif` means 'else, if this other condition is true'; Python reaches it only when earlier `if` or `elif` checks in the same chain did not run.
            elif t.startswith("?"):
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                params.append((f"param_{i}", t[1:].rstrip(";").lower()))
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return gate, params


    # Flat label list parsing (backward compatibility)

    # `def parse_labels` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> list[ParsedStep]` documents the expected return type.
    def parse_labels(self, labels: list[str]) -> list[ParsedStep]:
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return [s for s in (self._parse_one(r.strip()) for r in labels
                            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                            if r.strip() and not r.strip().isdigit()) if s]

    # `def _parse_one` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> ParsedStep | None` documents the expected return type.
    def _parse_one(self, raw: str) -> ParsedStep | None:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        tokens = raw.split()
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if not tokens:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return None
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if tokens[0] in self.SKIP_GATES or tokens[0].upper() in self.SKIP_GATES:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return None
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        gate = tokens[0].upper()
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate in self.VERDICT_GATES:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            direction = Direction.OUTPUT
        # `elif` means 'else, if this other condition is true'; Python reaches it only when earlier `if` or `elif` checks in the same chain did not run.
        elif gate in self.INPUT_GATES:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            direction = Direction.INPUT
        # `elif` means 'else, if this other condition is true'; Python reaches it only when earlier `if` or `elif` checks in the same chain did not run.
        elif gate in self.BOTH_GATES:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            direction = Direction.BOTH
        # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
        else:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            direction = Direction.OUTPUT
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        params = [(f"param_{i}", t[1:].lower())
                  # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
                  for i, t in enumerate(tokens[1:]) if t.startswith(("!", "?"))]
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return ParsedStep(gate_name=gate, direction=direction, params=params, raw_label=raw)


# `class Sampler` defines a new kind of object; the colon means the following indented lines belong inside that class.
class Sampler:
    # `def __init__` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def __init__(self, td):
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.td = td

    # `def sample` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def sample(self, type_name: str, abstract_value: str):
        
        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
        logger.debug(f"[SAMPLER] type_name={type_name!r}  abstract_value={abstract_value!r}")
        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
        logger.debug(f"[SAMPLER] spec keys={list(self.td.keys())}")
        
        
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        spec = self.td.get(type_name)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if type_name in ("SPO2_RED", "HR_RED"):
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.debug(f"[SAMPLER] spec for {type_name}: {spec!r}")        
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if spec is None:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return abstract_value
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if spec.get("origin") == "system_generated":
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return None
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        av = spec.get("abstract_values", {})
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if abstract_value in av:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            c = av[abstract_value]
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return None if c == "captured_at_runtime" else str(c)
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        base = spec.get("base", "String")
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if base == "String":
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            regex = spec.get("regex")
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if regex:
                # `try` starts a protected block: Python attempts the indented code and jumps to `except` if an error happens.
                try:
                    # `import` loads a library module so this file can call its functions; the comma-separated names are the helper libraries this line makes available.
                    import exrex
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return exrex.getone(regex)
                # `except` catches an error from the matching `try` block so the concretization run can report or recover instead of crashing immediately.
                except ImportError:
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return "test_value_001"
        # `elif` means 'else, if this other condition is true'; Python reaches it only when earlier `if` or `elif` checks in the same chain did not run.
        elif base == "Enum":
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            vals = spec.get("values", [])
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if vals:
                # `import` loads a library module so this file can call its functions; the comma-separated names are the helper libraries this line makes available.
                import random
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return str(random.choice(vals))
        # `elif` means 'else, if this other condition is true'; Python reaches it only when earlier `if` or `elif` checks in the same chain did not run.
        elif base == "Integer":
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            lo, hi = 0, 1000
            # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
            for c in spec.get("constraints", []):
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if isinstance(c, dict):
                    # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
                    for op, v in c.items():
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        v = int(v)
                        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                        if op == ">=":
                            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                            lo = max(lo, v)
                        # `elif` means 'else, if this other condition is true'; Python reaches it only when earlier `if` or `elif` checks in the same chain did not run.
                        elif op == "<=":
                            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                            hi = min(hi, v)
                        # `elif` means 'else, if this other condition is true'; Python reaches it only when earlier `if` or `elif` checks in the same chain did not run.
                        elif op == ">":
                            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                            lo = max(lo, v + 1)
                        # `elif` means 'else, if this other condition is true'; Python reaches it only when earlier `if` or `elif` checks in the same chain did not run.
                        elif op == "<":
                            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                            hi = min(hi, v - 1)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if lo > hi:
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return None
            # `import` loads a library module so this file can call its functions; the comma-separated names are the helper libraries this line makes available.
            import random
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return str(random.randint(lo, hi))
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return None


# `class Resolver` defines a new kind of object; the colon means the following indented lines belong inside that class.
class Resolver:
    # `def __init__` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def __init__(self, sampler: Sampler, element_map: dict, g_dict: dict):
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.sampler = sampler
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.em_gates = element_map.get("gates", {})
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.g = g_dict

    # `def resolve_params` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def resolve_params(self, gate: str, params: list, l_dict: dict):
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        resolved = {}
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        gate_def = self.em_gates.get(gate, {})
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        pt = gate_def.get("param_types", {})
        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for pname, aval in params:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            c = (self.g.get(aval)
                 # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                 or l_dict.get(aval)
                 # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                 or self.sampler.sample(pt.get(pname, pname), aval))
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if c is None:
                # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                logger.error(f"Cannot resolve {aval} for {gate}")
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return None
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            resolved[aval] = c
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            l_dict[aval]   = c
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return resolved



# `def validate_element_map` creates a reusable function/method; the parentheses list inputs, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> None` documents the expected return type.
def validate_element_map(element_map: dict, aut_path: str) -> None:
    # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
    """
    Checks the four structural invariants of the System Interface
    against the AUT gate alphabet. Raises ValueError on any violation.
    """
    # `import` loads a library module so this file can call its functions; the comma-separated names are the helper libraries this line makes available.
    import re as _re
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    gates_in_map = set(element_map.get("gates", {}).keys())
    # Collect every gate name that appears in the AUT
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    gates_in_aut = set()
    # `with open(...) as f` opens a file and guarantees it will be closed automatically; `f` is the file handle used by the indented block.
    with open(aut_path) as f:
        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for line in f:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            m = _re.search(r'"([A-Z_0-9]+)', line)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if m:
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                gates_in_aut.add(m.group(1))
    # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
    for gate in gates_in_aut - STRUCTURAL_SKIP_GATES:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        spec = element_map.get("gates", {}).get(gate)
        # Invariant 1: every AUT gate has an element map entry
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if spec is None:
            # `raise` deliberately throws an error; this code uses it when a required invariant or dependency is missing and continuing would hide the real problem.
            raise ValueError(
                # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
                f"SI invariant violated: gate '{gate}' appears in AUT "
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                f"but has no entry in the element map.")
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        actions  = spec.get("actions",  [])
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        observe  = spec.get("observe")
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        wait_for = spec.get("wait_for")
        # Invariant 2: every entry has at least one action or observe block
        # Invariant 2: gate must have actions, observe, OR traversal_paths
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        traversal_paths = spec.get("traversal_paths")
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        has_traversal   = bool(traversal_paths)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if not actions and observe is None and not has_traversal:
            # `raise` deliberately throws an error; this code uses it when a required invariant or dependency is missing and continuing would hide the real problem.
            raise ValueError(
                # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
                f"SI invariant violated: gate '{gate}' has neither "
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                f"actions, an observe block, nor traversal_paths.")

        # Invariant 3: observe block must use 'selector', not legacy 'element'
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if observe is not None and "element" in observe:
            # `raise` deliberately throws an error; this code uses it when a required invariant or dependency is missing and continuing would hide the real problem.
            raise ValueError(
                # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
                f"SI invariant violated: gate '{gate}' observe block uses "
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                f"legacy 'element' key — use 'selector' instead.")
        # Invariant 4: URL templates that reference session must use correct key
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        url = spec.get("url", "")
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if "SESSION" in url.upper() and "{{SESSION_ID}}" not in url:
            # `raise` deliberately throws an error; this code uses it when a required invariant or dependency is missing and continuing would hide the real problem.
            raise ValueError(
                # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
                f"SI invariant violated: gate '{gate}' URL '{url}' "
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                f"references a session but does not use {{{{SESSION_ID}}}}.")

# `class ConcretizationAlgorithm` defines a new kind of object; the colon means the following indented lines belong inside that class.
class ConcretizationAlgorithm:

    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    VMAP = {
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "PASS": Verdict.PASS, ":PASS:": Verdict.PASS,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "FAIL": Verdict.FAIL, ":FAIL:": Verdict.FAIL,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        ":INCONCLUSIVE:": Verdict.INCONC,
    # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
    }


    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _INPUT_PRIORITY = {
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, 
        # function call, or argument list that continues across multiple lines.
        "REGISTER": 0,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, 
        # function call, or argument list that continues across multiple lines.
        "LOGIN": 1,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, 
        # function call, or argument list that continues across multiple lines.
        "SUBMIT_CHECKIN": 2,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, 
        # or argument list that continues across multiple lines.
        "RECORD_SPO2": 3,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "RECORD_HEARTRATE": 4,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "GENERATE_ALERT_URGENT": 5,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "GENERATE_ALERT_ROUTINE": 6,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "ACCESS_PATIENT_DATA": 7,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "NURSE_OUTREACH": 8,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "ACKNOWLEDGE_ALERT": 9,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "SEND_MESSAGE": 50,
        # Quiescence gate — always sort last so real actions run first
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "APP_TIMEOUT": 99,
    # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
    }
    
    
    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _OUTPUT_PRIORITY = {
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "RECEIVE_ZONE_STATUS": 0,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "GENERATE_ALERT_URGENT": 1,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "GENERATE_ALERT_ROUTINE": 2,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "ACCESS_PATIENT_DATA": 3,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "NURSE_OUTREACH": 4,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "ACKNOWLEDGE_ALERT": 5,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "CONFIRMED": 10,
        # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
        "SUBMIT_CHECKIN": 10,
    # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
    }

    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
    def __init__(self, element_map: dict, type_description: dict,
             # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
             executor, timeout_seconds: int = 10,
             # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
             mapping_path: str | None = None,
             # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
             base_url: str | None = None,
             # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
             forced_disruption_key: str | None = None):
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.em        = element_map
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.td        = type_description
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.executor  = executor
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.timeout   = timeout_seconds
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.forced_disruption_key = forced_disruption_key
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.sampler   = Sampler(type_description)
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.reader    = BCGReader()
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        self.g_dict:   dict = {}
        self._seed_static_bindings()
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        self.l_dict:   dict = {}
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        self.execution_log: list[StepResult] = []
        # Faults injected during THIS walk, so they can be released afterwards,
        # and whether any injection could not be confirmed -- a run with an
        # unconfirmed fault must not be reported as a conformance result.
        self._active_disruptions = set()
        self._injection_failed = False
        # Observations the structural OBSERVE steps captured since the last
        # checkpoint, as (element key, text). The checkpoint oracle reads the
        # label's offers out of them (observation_oracle.py) and then clears
        # the list, so each checkpoint sees only its own segment of the walk.
        self._pending_observations: list = []
        self._obs_oracle = None

        # --- Disruption executor (optional) ---
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if mapping_path is not None:
            # This imports DisruptionExecutor from disruptor.py, connecting the graph-walking algorithm to the fault-injection helper used when a DISRUPTION_OCCURS gate is reached.
            from .disruptor import DisruptionExecutor
            # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
            self.disruption_executor = DisruptionExecutor(
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                mapping_path=mapping_path,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                base_url=base_url or "http://localhost:5000"
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )
        # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
        else:
            # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
            self.disruption_executor = None

        # --- Android out-of-band fault injector (adb/sqlite) ---
        # Built from the same disruption_mapping.yml when an Android executor is
        # present; injects UE1_KILL / DISRUPTION_DB / DB_CORRUPT / STORAGE_* /
        # CACHE_STALE at the fault gate (or before the walk for `pre` faults).
        self._fault_injector = None
        if mapping_path is not None:
            try:
                import yaml as _yaml
                _m = _yaml.safe_load(open(mapping_path))
                inner = getattr(self.executor, "inner", self.executor)
                cfg   = getattr(inner, "config", None)
                dev   = cfg.get("deviceName") if isinstance(cfg, dict) else None
                pkg   = getattr(inner, "app_package", None)
                if isinstance(_m, dict) and _m.get("faults") and (dev or pkg):
                    from .fault_injector import AndroidFaultInjector
                    self._fault_injector = AndroidFaultInjector(_m, device=dev, package=pkg)
                    logger.info(f"Android fault injector ready (device={dev}, pkg={pkg})")
            except Exception as _e:
                logger.warning(f"fault injector not built: {_e}")

        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self._pending_aut_validation = None   # set by run_aut before walk

    # `def run` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> Verdict` documents the expected return type.
    def run(self, labels: list[str]) -> Verdict:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """Flat‑label runner (backward compatible)."""
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.g_dict = {}
        self._seed_static_bindings()
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.execution_log = []
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        steps = self.reader.parse_labels(labels)
        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
        logger.info(f"Parsed {len(steps)} steps (flat mode)")
        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for step in steps:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            r = self._execute_step_flat(step)
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            self.execution_log.append(r)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if r.verdict is not None:
                # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                logger.info(f"Verdict: {r.verdict.name}")
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return r.verdict
        # Every step ran and none carried a verdict, so no trap state was ever
        # reached. That is the walk failing to complete, not an ioco outcome.
        return Verdict.UNEXECUTABLE

    # `def run_aut` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> Verdict` documents the expected return type.
    def run_aut(self, aut_path: str) -> Verdict:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """Walk an AUT graph."""
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if self.em.get("gates"):
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            validate_element_map(self.em, aut_path)
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        graph = self.reader.read_aut_file(aut_path)
        # Derive this tc's TARGET fault from the filename (tc_<fault>.aut) so the
        # injector and the walker act only on it — the fault AUTs are multi-fault
        # graphs and must not be steered by some other fault's gate.
        if getattr(self, "_fault_injector", None) is not None:
            import os as _os
            base = _os.path.basename(aut_path)
            for _pre, _suf in (("tc_", ".aut"), ("tc_", ".bcg")):
                if base.startswith(_pre) and base.endswith(_suf):
                    cand = base[len(_pre):-len(_suf)].upper()
                    if cand in self._fault_injector.faults:
                        self._fault_injector.target = cand
                    break
            self._fault_target = self._fault_injector.target
            logger.info(f"tc target fault: {self._fault_injector.target or '(none / happy)'}")
        try:
            return self._attributable(self.run_graph(graph))
        finally:
            self._restore_network()

    # `def run_bcg` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> Verdict` documents the expected return type.
    def run_bcg(self, bcg_path: str) -> Verdict:
        # This begins or ends a docstring, which is normal English text Python keeps as documentation for this module, class, or function.
        """Convert BCG to AUT then walk."""
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        graph = self.reader.read_bcg_file(bcg_path)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if graph is None:
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            # The test case could not even be loaded, so nothing was walked.
            logger.error(f"Could not read BCG: {bcg_path}")
            return Verdict.UNEXECUTABLE
        try:
            return self._attributable(self.run_graph(graph))
        finally:
            self._restore_network()

    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
    _VITAL_ORDER = {"abnormal": 0, "borderline": 1, "normal": 2}

    # `def _sort_inputs` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> list` documents the expected return type.
    def _sort_inputs(self, transitions: list) -> list:
        # `def key` creates a reusable function/method; the parentheses list inputs, commas separate parameters, and the colon starts the indented instructions that run when it is called.
        def key(t):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            gate = t.label.split()[0].upper()
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            primary = self._INPUT_PRIORITY.get(gate, 25)
            # Secondary: prefer parameters that trigger the red zone.
            # Default 1 (neutral) — NOT 0, so parameter-less gates like
            # UE1_OFFLINE don't accidentally outrank parameter-bearing gates.
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            secondary = 1
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            tokens = t.label.split()
            # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
            for tok in tokens[1:]:
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if tok.startswith("!"):
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    param_val = tok[1:].lower()
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    secondary = self._VITAL_ORDER.get(param_val, 1)
                    # `break` exits the nearest loop immediately.
                    break
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return (primary, secondary)
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return sorted(transitions, key=key)

    # `def _has_typed_structural_params` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> bool` documents the expected return type.
    def _has_typed_structural_params(self, label: str) -> bool:
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        gate, params = self.reader.parse_gate_and_params(label)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate not in {"NAVIGATE", "TAP", "CLICK", "TYPE_INTO", "ENTER_TEXT", "WAIT_FOR", "OBSERVE"}:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return False
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return bool(params)

    # `def _domain` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> dict` documents the expected return type.
    def _domain(self) -> dict:
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self.em.get("concrete_domain", self.em)

    # `def _domain_value` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def _domain_value(self, category: str, key: str):
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return self._domain().get(category, {}).get(key)

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

    # `def _locator_spec` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> dict` documents the expected return type.
    def _locator_spec(self, locator) -> dict:
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if isinstance(locator, dict):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            spec = dict(locator)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            selector = spec.get("selector", "")
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            spec.setdefault("by", self._by_for(str(selector)))
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return spec
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        selector = str(locator)
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return {"selector": selector, "by": self._by_for(selector)}

    # Concrete values a SUT can only state relative to the run. Written in
    # concrete_domain.yml as "@date", "@date-8", "@date+30": the day of the run
    # offset by that many days, in ISO form, which is what a native date input
    # accepts through the value setter. Anything else is returned unchanged.
    _RELATIVE_DATE_RE = re.compile(r"^@date(?:([+-])(\d+))?$")
    # "@env:NAME": a value the SUT keeps out of its repository (a password),
    # read from the environment when it is typed. Never logged.
    _ENV_VALUE_RE = re.compile(r"^@env:([A-Za-z_][A-Za-z0-9_]*)$")

    def _materialise_value(self, value):
        e = self._ENV_VALUE_RE.match(str(value).strip()) if value is not None else None
        if e:
            import os as _os
            got = _os.environ.get(e.group(1))
            if got is None:
                # Typing the placeholder itself would fail later, at a step
                # that has nothing to do with the cause. Say it here.
                logger.error(f"  {value}: environment variable {e.group(1)} is not set")
                return value
            logger.info(f"  {value} -> (value from the environment, not logged)")
            return got
        m = self._RELATIVE_DATE_RE.match(str(value).strip()) if value is not None else None
        if not m:
            return value
        import datetime as _dt
        days = int(m.group(2) or 0) * (-1 if m.group(1) == "-" else 1)
        out = (_dt.date.today() + _dt.timedelta(days=days)).isoformat()
        logger.info(f"  {value} -> {out}")
        return out

    # `def _resolve_structural_action` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def _resolve_structural_action(self, gate: str, params: list):
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        values = self.g_dict
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate == "NAVIGATE":
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            route_key = params[0][1]
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            route = self._domain_value("routes", route_key) or route_key
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return {"action": "navigate", "url": route}, "perform"

        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate == "CLICK":
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            selector_key = params[0][1]
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            locator = self._domain_value("selectors", selector_key)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if locator is None:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                locator = self._domain_value("elements", selector_key) or selector_key
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            action = self._locator_spec(locator)
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            action["action"] = "click"
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return action, "perform"

        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate == "TAP":
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            value_key = params[0][1]
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            locator = self._domain_value("concrete_values", value_key)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if locator is None:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                locator = self._domain_value("selectors", value_key)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if locator is None:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                locator = self._domain_value("elements", value_key) or value_key
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            action = self._locator_spec(locator)
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            action["action"] = "click"
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return action, "perform"

        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate == "TYPE_INTO":
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if len(params) < 2:
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return None, "perform"
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            selector_key = params[0][1]
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            value_key = params[1][1]
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            locator = self._domain_value("selectors", selector_key)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if locator is None:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                locator = self._domain_value("elements", selector_key) or selector_key
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            resolved_value = self._domain_value("concrete_values", value_key)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if resolved_value is None:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                resolved_value = values.get(value_key)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            value = self._materialise_value(
                resolved_value if resolved_value is not None else value_key)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            action = self._locator_spec(locator)
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            action.update({"action": "clear_and_type", "param": value})
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return action, "perform"

        if gate == "ENTER_TEXT":
            # Single-param type primitive (ENTER_TEXT !CV_X): type the resolved
            # value into the currently focused field. Unlike TYPE_INTO it carries
            # no selector — the field is the one just tapped/waited for.
            if not params:
                return None, "perform"
            value_key = params[0][1]
            resolved_value = self._domain_value("concrete_values", value_key)
            if resolved_value is None:
                resolved_value = values.get(value_key)
            value = self._materialise_value(
                resolved_value if resolved_value is not None else value_key)
            return {"action": "enter_text", "param": value}, "perform"

        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate == "WAIT_FOR":
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            element_key = params[0][1]
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            locator = (self._domain_value("elements", element_key)
                       # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                       or self._domain_value("selectors", element_key)
                       # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                       or element_key)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            action = self._locator_spec(locator)
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            action["action"] = "wait_for"
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return action, "perform"

        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate == "OBSERVE":
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            element_key = params[0][1]
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            locator = (self._domain_value("elements", element_key)
                       # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                       or self._domain_value("selectors", element_key)
                       # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                       or element_key)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            spec = self._locator_spec(locator)
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            spec.setdefault("attribute", "text")
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return spec, "wait"

        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return None, "perform"

    # `def _perform_typed_structural_transition` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> StepResult` documents the expected return type.
    def _perform_typed_structural_transition(self, t: AUTTransition) -> StepResult:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        start = time.time()
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        gate, params = self.reader.parse_gate_and_params(t.label)
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        action, mode = self._resolve_structural_action(gate, params)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if action is None:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return StepResult(
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                verdict=Verdict.FAIL,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                gate_name=gate,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                error=f"Cannot resolve typed structural label: {t.label}",
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                duration_ms=(time.time() - start) * 1000,
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        concrete = dict(self.g_dict)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if mode == "wait":
            # This calls an executor `wait` method from executors.py, which means the algorithm is watching the SUT for an expected concrete output.
            observed, timed_out = self.executor.wait(action, self.timeout)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if timed_out:
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return StepResult(
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    verdict=Verdict.FAIL,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    gate_name=gate,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    error=f"Typed observe timed out: {action}",
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    duration_ms=(time.time() - start) * 1000,
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            captured = {}
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if observed is not None:
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                captured[gate.lower()] = str(observed)
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                self.g_dict["_last_observed"] = str(observed)
                # Keep every OBSERVE, by element, for the checkpoint that
                # follows: a label with several offers (band, log, id) is
                # read from several elements, and _last_observed holds one.
                if gate.upper() == "OBSERVE":
                    _el = str(params[0][1]).lower() if params else gate.lower()
                    self._pending_observations.append((_el, str(observed)))
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return StepResult(
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                verdict=None,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                gate_name=gate,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                concrete_values=concrete,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                captured=captured,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                duration_ms=(time.time() - start) * 1000,
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )

        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if not self.executor.perform(action, concrete):
            # A UI step failed. Dynamically classify FAIL vs INCONCLUSIVE: if the
            # targeted fault never manifested, or the walk is inside an external
            # source the fixture cannot populate, the SUT was never challenged.
            _v = self._step_failure_verdict(action, gate)
            _reason = self._inconclusive_reason(action, gate) or "not challenged"
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return StepResult(
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                verdict=_v,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                gate_name=gate,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                error=f"{f'INCONCLUSIVE ({_reason}): ' if _v == Verdict.INCONC else ''}Typed UI action failed: {action}",
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                concrete_values=concrete,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                duration_ms=(time.time() - start) * 1000,
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )
        # The step succeeded — record whether it entered or left an external
        # data source, so a later failure can be judged in that context.
        self._note_action(action)
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return StepResult(
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            verdict=None,
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            gate_name=gate,
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            concrete_values=concrete,
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            duration_ms=(time.time() - start) * 1000,
        # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
        )

    # --------------------------------------------------------------
    # Graph walker (ioco)
    # --------------------------------------------------------------
    def _compute_pass_reachable(self, graph: AUTGraph) -> set:
        """Set of states from which a :PASS: verdict transition is still reachable.

        Also records, in self._pass_distance, how many transitions each such
        state is from a :PASS: — the backward BFS visits in distance order, so
        the first time a state is seen is its shortest distance. The walker uses
        that distance (not mere reachability) to choose branches: the SI loops
        back to its start screen, so nearly EVERY branch "can eventually" reach
        :PASS: and reachability alone leaves the choice to AUT ordering, which
        sends the walk down arbitrary loops instead of to the verdict.
        """
        from collections import deque
        reverse = defaultdict(list)
        seed = set()
        for t in graph.transitions:
            reverse[t.target].append(t.source)
            if self.reader.is_verdict_label(t.label) and \
               self._map_transition_verdict(t.label) == Verdict.PASS:
                seed.add(t.source)
        seen = set(seed)
        dist = {s: 0 for s in seed}
        dq = deque(seed)
        while dq:
            s = dq.popleft()
            for p in reverse[s]:
                if p not in seen:
                    seen.add(p)
                    dist[p] = dist[s] + 1
                    dq.append(p)
        self._pass_distance = dist
        return seen

    # Seconds to probe ONE candidate observation when a state offers several.
    # Short on purpose: this is a presence check across every alternative, not
    # the oracle's own read, and the full self.timeout multiplied by the number
    # of branches would dominate the walk.
    _PRESENCE_PROBE_TIMEOUT = 2

    def _choose_by_observed_presence(self, transitions: list):
        """At a state offering several OBSERVE branches, let the SUT pick one.

        WHY THIS EXISTS
        ---------------
        A state whose alternatives are observations on DIFFERENT selectors is
        asking "which output did the SUT produce?". That is the SUT's decision,
        never the tester's. _choose_toward_pass answers it by graph distance to
        :PASS:, which is the tester choosing the answer and then testing it.

        Measured on the 2026-08-27 Moodle sweep: after OPEN_GRADING the case
        offered five observations (connection error, course total, session
        error, stale warning, write error). The walker took the session-error
        branch because it was nearest :PASS:, that element was of course absent,
        and the run reported FAIL -- a conformance verdict produced by the
        tester picking a branch, with the fault correctly injected and the SUT
        never actually consulted about which output it had produced.

        Returns
          a transition  -- the observation that is actually present
          False         -- alternatives existed and NONE was present
          None          -- not an observation choice; caller decides as before
        """
        obs = []
        for t in transitions:
            gate, params = self.reader.parse_gate_and_params(t.label)
            action, mode = self._resolve_structural_action(gate, params)
            if action is None or mode != "wait":
                return None
            obs.append((t, action))
        if len(obs) < 2:
            return None
        if len({a.get("selector") for _, a in obs}) < 2:
            return None

        present = []
        for t, action in obs:
            try:
                _, timed_out = self.executor.wait(
                    action, self._PRESENCE_PROBE_TIMEOUT)
            except Exception:
                timed_out = True
            if not timed_out:
                present.append(t)

        if not present:
            # Nothing this state can observe is on screen. Whether that is a
            # counter-example is NOT decided here -- it depends on whether the
            # test case permits quiescence at this state, which only the caller
            # can see. Say "none present" and let it decide.
            return False

        # Several outputs genuinely present: keep the existing preference so
        # behaviour is unchanged whenever the observation does not disambiguate.
        return self._choose_toward_pass(present)

    def _choose_toward_pass(self, transitions: list) -> AUTTransition:
        """Prefer the transition whose target is CLOSEST to a :PASS: verdict.

        Ties (and states with no recorded distance) keep the AUT's own ordering,
        so this only ever refines the previous first-reachable behaviour.
        """
        reachable = getattr(self, "_pass_reachable", None)
        if reachable:
            preferred = [t for t in transitions if t.target in reachable]
            if preferred:
                dist = getattr(self, "_pass_distance", None) or {}
                # min() is stable: equal distances fall back to AUT order.
                return min(preferred, key=lambda t: dist.get(t.target, 1 << 30))
        return transitions[0]

    # Fault gates injected by cutting device/browser connectivity via the
    # executor's set_ue1_offline().
    #
    # These names are a FALLBACK ONLY, kept so a SUT whose mapping predates the
    # `network: true' flag keeps working. They are FoodYou's gate names, and
    # hard-coding them here was a framework/SUT leak: a SUT whose connectivity
    # fault is called anything else (Moodle's is UE1_LOSE_CONN) matched nothing
    # and silently got no injection while the log still said a fault had fired.
    #
    # The authority is now the SUT's own disruption mapping — see
    # _network_fault_gates(), which prefers whatever the mapping marks with
    # `network: true'.
    DEFAULT_NETWORK_FAULT_GATES = {"EXTAPI_FAIL", "NETWORK_DEGRADED", "UE1_OFFLINE"}

    @property
    def NETWORK_FAULT_GATES(self) -> set:
        """Connectivity gates for THIS SUT, taken from its disruption mapping."""
        de = getattr(self, "disruption_executor", None)
        if de is not None:
            try:
                declared = de.network_fault_gates()
                if declared:
                    return declared
            except AttributeError:
                pass                      # legacy executor without the accessor
        return self.DEFAULT_NETWORK_FAULT_GATES

    def _attributable(self, verdict: "Verdict") -> "Verdict":
        """A verdict is a statement about the SUT under the fault the case
        names. If that fault was never confirmed in place, the walk measured
        something else, and PASS / FAIL / INCONCLUSIVE would all be claims
        nothing supports. `_injection_failed` was set at the injection and
        read by nobody, so INFRA_DB_DOWN reported FAIL with the database
        never paused. Downgrade here, once, where every walk returns.
        """
        if not getattr(self, "_injection_failed", False):
            return verdict
        if verdict is Verdict.UNEXECUTABLE:
            return verdict
        logger.error(f"  verdict {verdict.name} discarded: the case's fault was not "
                     f"confirmed active, so the walk did not test what the case names "
                     f"-> UNEXECUTABLE (not a verdict)")
        self.execution_log.append(StepResult(
            verdict=Verdict.UNEXECUTABLE, gate_name="(attribution)",
            error=f"fault not confirmed active; {verdict.name} discarded"))
        return Verdict.UNEXECUTABLE

    def _restore_network(self):
        """Re-enable connectivity if a fault left it disabled during the walk."""
        if getattr(self, "_fault_active", False):
            set_offline = getattr(self.executor, "set_ue1_offline", None)
            if set_offline:
                try:
                    set_offline(False)
                    logger.info("  fault restored — device connectivity re-enabled")
                except Exception as e:
                    logger.warning(f"  fault restore failed: {e}")
            self._fault_active = False
        # Undo any adb/sqlite fault injections (chmod back, reseed, re-enable data).
        if getattr(self, "_fault_injector", None) is not None:
            try:
                self._fault_injector.restore()
            except Exception as e:
                logger.warning(f"  fault-injector restore failed: {e}")
        # Undo what the mapping-driven executor installed during THIS walk.
        # This was missing: `_active_disruptions` was filled at injection
        # and read by nobody, so a Postgres trigger installed for DB_ABORT
        # stayed in place and aborted every write of the five cases that
        # followed -- each of which then reported a verdict about a fault
        # it never asked for. restore() verifies each removal and poisons
        # the executor if one cannot be confirmed.
        de = getattr(self, "disruption_executor", None)
        if de is not None and (self._active_disruptions
                               or getattr(de, "active_disruption", None)
                               or getattr(de, "_pre_injected", None)):
            try:
                if not de.restore(self._active_disruptions):
                    logger.error("  a fault could not be restored or confirmed gone; "
                                 "every later verdict on this SUT is untrustworthy "
                                 "until it is cleared by hand")
            except Exception as e:
                logger.error(f"  disruption restore failed: {e}")
            self._active_disruptions = set()

    _TOTAL_BUCKETS = {"EMPTY", "LOW", "MODERATE", "HIGH", "OVER"}

    def _check_total_arithmetic(self, gate: str, observed: str, resolver) -> None:
        """Sanity-check the total the bucket oracle just accepted.

        WHY THIS EXISTS: the bucket oracle classifies with
        `rung = round(total / unit)` clamped to the last bucket, so with a 155 kcal
        unit EVERY total from 543 kcal upward classifies as OVER. Past that point
        the conformance check confirms nothing at all -- 620, 775 and 5000 are
        indistinguishable -- and below it the tolerance is still +/- half a unit.

        Every entry in this model is one reference portion of the same food, so a
        correct total is an exact multiple of the unit. That holds regardless of
        how many entries there are, which is why it needs no bookkeeping and stays
        valid across adds and removes alike.

        Deliberately NOT a verdict. The model specifies buckets, so the bucket
        comparison remains the ioco result; this is reported alongside it as a
        separate finding. Turning it into a FAIL would claim a conformance
        violation the specification never asked for.
        """
        unit = getattr(resolver, "unit", None)
        if not unit or unit <= 0:
            return
        from .quantity_resolver import parse_total
        cur, _goal = parse_total(observed)
        if cur is None or cur <= 0:
            return
        rem  = cur % unit
        off  = min(rem, unit - rem)          # distance to the nearest multiple
        if off <= 0.5:                        # allow the SUT's own rounding
            return
        rungs = cur / unit
        logger.error(
            f"ARITHMETIC INCONSISTENCY at {gate}: total {cur:g} kcal is not a "
            f"multiple of the {unit:g} kcal reference portion "
            f"({rungs:.3f} portions, off by {off:g}) — the bucket oracle cannot "
            f"see this")
        self.execution_log.append(StepResult(
            verdict=None, gate_name=gate,
            error=(f"ARITHMETIC INCONSISTENCY: total {cur:g} is not a multiple of "
                   f"{unit:g} ({rungs:.3f} portions)")))

    def _food_kcal(self, label: str) -> tuple[str | None, float | None]:
        """The food named on a label, and its authoritative energy.

        Reads FoodId.values and Calorie.abstract_values from the type
        description, so no food name appears in this file.
        """
        foods = {str(v).strip().lower()
                 for v in ((self.td.get("FoodId") or {}).get("values") or [])}
        if not foods:
            return None, None
        _gate, params = self.reader.parse_gate_and_params(label)
        energies = (self.td.get("Calorie") or {}).get("abstract_values") or {}
        for _pname, aval in params:
            if aval in foods:
                # Same correction as _validate_food_info, and it has to be here
                # too. CACHE_STALE rewrites the energy in the app's own catalogue,
                # so the declared fixture value stops being authoritative the
                # moment it is injected. Fixing only the FOOD_INFO oracle left the
                # LEDGER staging 900 per add while the app correctly showed 999 --
                # eight TOTAL MISMATCH findings riding inside a PASS, every one of
                # them the tester's arithmetic rather than the app's.
                live = self._authoritative_now(aval)
                if live is not None:
                    return aval, live
                raw = energies.get(aval)
                try:
                    return aval, float(raw)
                except (TypeError, ValueError):
                    return aval, None
        return None, None


    def _concrete_for_abstract(self, token: str):
        """The rendered string an abstract value maps to, from type_description.

        Searched across every declared type rather than a named one, because the
        caller has a bare label token and not the parameter's type. Abstract
        value names are unique across this domain by construction; if two types
        ever shared one, the ambiguity would show up as the "matches several"
        warning above rather than as a wrong verdict.
        """
        for _tname, spec in (self.td or {}).items():
            if not isinstance(spec, dict):
                continue
            av = spec.get("abstract_values") or {}
            if token in av:
                c = av[token]
                if c in (None, "captured_at_runtime"):
                    return None
                return str(c)
        return None

    @staticmethod
    def _observation_matches(observed, concrete) -> bool:
        """Does the rendered text carry this abstract value?

        Substring, case-insensitive, whitespace-collapsed: Moodle renders
        "Draft (not submitted)" inside markup with padding, and the executor
        returns the element's whole text. Exact equality would fail on every
        real page.
        """
        import re as _re
        o = _re.sub(r"\s+", " ", str(observed)).strip().lower()
        c = _re.sub(r"\s+", " ", str(concrete)).strip().lower()
        return bool(c) and c in o

    def _select_by_observation(self, expected: dict, observed: str,
                               default: str) -> str:
        """Let the OBSERVATION pick the branch when a state allows several outputs.

        A specification may permit more than one output after a trace — here,
        dropping out of OVER is modelled as `alt total := HIGH [] total := OVER`,
        so both are legal. Which one occurs is the SUT's decision, never the
        tester's: choosing one and then failing the run because the other
        appeared is not an ioco verdict, it is the tester marking its own
        homework.

        So read the value and follow the branch whose abstract value it
        satisfies, using the same interpretation function the gate oracle uses.

        Returns `default` unchanged when there is nothing to disambiguate, when
        the bands overlap, or when NO allowed value fits. That last case is a
        genuine counter-example and is left to the gate oracle to report, which
        it does with the exact-sum and delta evidence attached — but it is
        logged here too, naming every value the spec allowed, because the
        oracle's message can only name the one branch it happened to be given.
        """
        head = default.split()[0].rstrip(";")
        labels = [lbl for lbl in expected
                  if lbl.split()[0].rstrip(";") == head]
        if len(labels) < 2:
            return default

        # Types declared with `role:` at this gate decide first, from the same
        # observations the checkpoint oracle will check; the bucket and enum
        # matchers below stay for systems that declare none.
        try:
            oracle = self._declared_oracle()
            if oracle.declared_at(head):
                from .observation_oracle import Observation
                obs = [Observation(e, t) for e, t in self._pending_observations]
                if not obs and observed:
                    obs = [Observation("_last_observed", str(observed))]
                fits_ = oracle.fits(head, labels, obs)
                if len(fits_) == 1:
                    if fits_[0] != default:
                        logger.info(f"  observation selects {fits_[0]!r} from "
                                    f"{[(e, t) for e, t in self._pending_observations]}")
                    return fits_[0]
                if len(fits_) > 1:
                    logger.warning(f"  the observations fit several allowed outputs "
                                   f"({len(fits_)}) — keeping {default}")
                    return default
                # nothing fits: hand it to the checkpoint oracle, which reports
                # the mismatch against `default` with the evidence attached
                return default
        except Exception as e:
            logger.warning(f"  declared-type selection skipped: {e}")

        def buckets(lbl: str) -> list[str]:
            return [t.upper() for t in lbl.replace("!", " ").split()[1:]
                    if t.upper() in self._TOTAL_BUCKETS]

        try:
            from .quantity_resolver import QuantityResolver
            r = getattr(self, "_qty_resolver", None)
            if r is None:
                r = QuantityResolver.from_type_description(self.td)
                self._qty_resolver = r
            fits = [(lbl, b) for lbl in labels for b in buckets(lbl)
                    if r.matches_total(b, observed)]
        except Exception as e:
            logger.warning(f"  output selection skipped: {e}")
            return default

        if len(fits) == 1:
            chosen, bucket = fits[0]
            if chosen != default:
                logger.info(f"  observation selects {bucket}: {observed!r} "
                            f"(spec also allowed "
                            f"{', '.join(b for l in labels for b in buckets(l) if b != bucket)})")
            return chosen
        if len(fits) > 1:
            logger.warning(f"  {observed!r} fits several allowed outputs "
                           f"({', '.join(b for _, b in fits)}) — the bands "
                           f"overlap, which is a model defect; keeping {default}")
            return default

        # GENERIC FALLBACK — enumerated abstract values.
        #
        # The band matcher above only understands NUMERIC buckets declared with
        # a quantity range, so for any SUT whose outputs are plain enumerations
        # `fits' is empty and this function used to return `default': THE FIRST
        # ALTERNATIVE, regardless of what the SUT actually showed. That is the
        # D1 defect -- the tester choosing among the SUT's outputs -- and it
        # would have made every multi-valued oracle in an enumerated domain
        # silently vacuous.
        #
        # Here the observation picks the branch by matching it against
        # type_description.abstract_values, the same interpretation the gate
        # oracle uses. Substring and case-insensitive because the SUT wraps
        # values in markup and whitespace.
        #
        # Returning `default` when NOTHING fits is deliberate and is not a
        # silent pass: it hands an unmatched observation to the gate oracle,
        # which reports it as a counter-example with the evidence attached.
        enum_fits = []
        for lbl in labels:
            for tok in [t for t in lbl.replace("!", " ").split()[1:]]:
                concrete = self._concrete_for_abstract(tok)
                if concrete and self._observation_matches(observed, concrete):
                    enum_fits.append((lbl, tok, concrete))
        if len(enum_fits) == 1:
            chosen, tok, concrete = enum_fits[0]
            if chosen != default:
                logger.info(f"  observation selects {tok}: {observed!r} "
                            f"matches {concrete!r}")
            return chosen
        if len(enum_fits) > 1:
            logger.warning(
                f"  {observed!r} matches several allowed outputs "
                f"({', '.join(t for _, t, _ in enum_fits)}) — the abstract "
                f"values are not distinguishable by observation, which is a "
                f"model defect; keeping {default}")
            return default
        logger.warning(
            f"  {observed!r} matches NONE of the allowed outputs "
            f"({', '.join(sorted({t for l in labels for t in l.replace('!',' ').split()[1:]}))}) "
            f"— leaving it to the gate oracle to report")
        return default

        allowed = sorted({b for lbl in labels for b in buckets(lbl)})
        if allowed:
            logger.error(f"  no allowed output matches {observed!r} — the spec "
                         f"permits {', '.join(allowed)} here")
        return default

    def _capture_oracle_failure(self, tag: str) -> str:
        """Screenshot + UI tree when an ORACLE rejects an observation.

        Capture already fires when a WAIT fails -- when the tester could not find
        something. But the case that most needs a picture is the opposite one:
        the tester found the value, read it, and the oracle rejected it. That is
        a candidate counter-example, and the screen behind it is the evidence for
        or against it.

        Without it, attributing a mismatch to the app or to the tester's own
        bookkeeping costs a re-run -- and the re-run overwrites the log that
        raised the question in the first place.
        """
        inner = getattr(self.executor, "inner", self.executor)
        cap = getattr(inner, "_capture_failure", None)
        if not callable(cap):
            return ""
        try:
            base = cap(tag)
        except Exception as e:
            logger.debug(f"oracle capture skipped: {e}")
            return ""
        if base:
            logger.info(f"  evidence: {base}.png / .xml")
        return base

    # Atwater factors: kcal per gram of protein, fat, carbohydrate. Universal
    # nutrition arithmetic, not a FoodYou constant, which is why they live here
    # rather than in the concrete domain.
    _ATWATER = {"protein": 4.0, "fat": 9.0, "carbs": 4.0}

    def _check_macro_consistency(self, gate: str, observed: str) -> None:
        """Cross-check the displayed ENERGY against the displayed MACROS.

        The specification constrains one number: the daily energy total. The same
        screen shows protein, fat and carbohydrate, computed by the same code from
        the same rows, and the model says nothing about them -- so nothing checks
        them, and a defect there is free.

        This is not a header-versus-entries check. Those already agree. It asks a
        different question: are the two figures the application shows CONSISTENT
        WITH EACH OTHER? Energy and macros are related by fixed factors, so a day
        holding 100 g of fat cannot also hold 0 kcal. When the app reports both,
        it is contradicting itself, and no external reference is needed to see it.

        FOUND THIS WAY, 2026-08-23 (EVALUATION/foodyou/TODO.md): under DB_CORRUPT the
        app correctly flagged a record "missing required fields" and refused to
        show its energy -- then counted that same record's 100 g of fat into the
        daily total, so the header read "0 / 2000 kcal, 2000 calories left"
        alongside "Fats 100 / 67 g". It trusted one field of a record it had
        declared untrustworthy.

        Reported as a FINDING, never as a verdict. The specification does not
        mention macros, so a discrepancy here violates nothing it asserts and is
        not an ioco counter-example. Making it one requires putting the macros in
        the model -- see TODO.md.

        The tolerance is wide on purpose. Atwater factors are approximate, foods
        carry fibre and alcohol the factors treat differently, and every figure on
        screen is rounded. Only a contradiction the rounding cannot explain is
        worth reporting.
        """
        from .quantity_resolver import parse_total
        cur, _goal = parse_total(observed)
        if cur is None:
            return

        def _grams(elem: str):
            sel = (self.em.get("concrete_domain", {}).get("elements", {}) or {}).get(elem)
            if not sel:
                return None
            try:
                val, timed_out = self.executor.wait({"selector": sel, "by": "id"}, 3)
            except Exception:
                return None
            if timed_out or val is None:
                return None
            m = re.search(r"(\d+(?:\.\d+)?)\s*/", str(val))
            return float(m.group(1)) if m else None

        p = _grams("el_daily_protein")
        f = _grams("el_daily_fat")
        c = _grams("el_daily_carbs")
        if p is None or f is None or c is None:
            logger.debug("  macro check skipped: macros not readable on this screen")
            return

        implied = (p * self._ATWATER["protein"] + f * self._ATWATER["fat"]
                   + c * self._ATWATER["carbs"])
        # Absolute floor of 100 kcal so a near-empty diary cannot trip on rounding,
        # and 25% above that so large totals are judged proportionally.
        tolerance = max(100.0, 0.25 * implied)
        if abs(implied - cur) <= tolerance:
            logger.info(f"  macros consistent: {p:g}P {f:g}F {c:g}C implies "
                        f"~{implied:g} kcal, screen shows {cur:g}")
            return

        logger.error(
            f"MACRO INCONSISTENCY at {gate}: the screen shows {cur:g} kcal but its "
            f"own macros ({p:g}g protein, {f:g}g fat, {c:g}g carbohydrate) imply "
            f"~{implied:g} kcal -- a gap of {implied - cur:+g}. The app is "
            f"contradicting itself; the model constrains only the kcal figure, so "
            f"this is a FINDING, not a conformance verdict.")
        self._capture_oracle_failure(f"macro_inconsistency_{gate}")
        self.execution_log.append(StepResult(
            verdict=None, gate_name=gate,
            error=(f"MACRO INCONSISTENCY: screen shows {cur:g} kcal, its macros "
                   f"imply {implied:g} ({p:g}P {f:g}F {c:g}C)")))

    def _stage_exact_op(self, op: str) -> None:
        """Stage a ledger movement for the next CONFIRM_TOTAL to apply.

        ADD_ENTRY and REMOVE_ENTRY cannot check anything themselves — no total is
        on screen at that point — so they hand the movement to the next gate that
        can see one. One slot, one producer, one consumer.

        If a movement is ALREADY staged when the next one arrives, the
        CONFIRM_TOTAL that should have consumed it never reached the oracle.
        Overwriting it silently is exactly what produced a confident -900 kcal
        error against a total the app had computed correctly: the ledger went on
        reporting with total assurance while sitting one removal above reality.

        So the ledger declares itself unusable instead. An oracle that abstains
        costs one missed check; an oracle that is quietly wrong costs the
        credibility of every verdict in the sweep, because nothing downstream can
        tell the two apart. Fail closed.
        """
        prev = getattr(self, "_pending_exact_op", None)
        if prev is not None:
            self._exact_ledger_ok = False
            logger.warning(
                f"  exact-sum ledger UNKNOWN from here: a {prev!r} movement was "
                f"staged and no CONFIRM_TOTAL consumed it before this {op!r}. "
                f"The running sum no longer tracks the device, so the exact "
                f"check abstains for the rest of this run — the band, "
                f"arithmetic and delta checks continue.")
        self._pending_exact_op = op

    def _check_total_exact(self, gate: str, label: str, observed: str) -> bool:
        """Compare the displayed total against the SUM OF WHAT WAS ACTUALLY LOGGED.

        This is the strongest check available on the daily total, and it needs
        nothing from the model. The tester performed the ADD_ENTRY steps, so it
        knows which foods went in; adding up their authoritative energies gives
        the total the screen must show, to the calorie.

        WHY IT MATTERS: the model expresses the total as a BAND, and the band
        oracle recovers it by dividing observed kcal by one food's portion size.
        That tolerates half a rung either way -- +/-450 kcal with a 900 kcal
        portion -- so a total of 1200 passes as "one portion". It also only works
        while every entry is the same food: mixed diaries make the division a
        guess, and with the current foods it happens to come out right with only
        31 kcal of margin, which is luck rather than a check.

        Summing removes both problems. Reported as a FINDING, not as the verdict:
        the specification says bands, so an exact mismatch is not a violation of
        anything it states. It belongs next to the verdict, not instead of it.

        Returns True when it was able to evaluate. The caller then SKIPS the two
        weaker checks -- "is the total a whole number of portions" and "did it
        move by one portion" -- because both assume a single-food diary and would
        flag every correct mixed total. They exist only for the case where the
        food energies are not declared and this check cannot run.
        """
        op = getattr(self, "_pending_exact_op", None)
        self._pending_exact_op = None
        # A movement was lost earlier, so the running sum is not the device's.
        # Abstain: returning False hands the total to the weaker arithmetic and
        # delta checks, which derive everything from the screen and are therefore
        # unaffected by the ledger's state.
        if not getattr(self, "_exact_ledger_ok", True):
            return False
        food, kcal = self._food_kcal(label)
        expected = getattr(self, "_expected_total_kcal", None)
        if expected is None or kcal is None or op is None:
            return False

        up = label.upper()
        if "REJECTED" in up:
            pass                                  # refused: nothing was written
        elif op == "add":
            expected += kcal
        else:
            expected -= kcal
        self._expected_total_kcal = max(0.0, expected)

        from .quantity_resolver import parse_total
        cur, _goal = parse_total(observed)
        if cur is None:
            return False
        if abs(cur - self._expected_total_kcal) <= 0.5:      # allow display rounding
            logger.info(f"  total exact: {cur:g} kcal == sum of entries logged")
            return True
        logger.error(
            f"TOTAL MISMATCH at {gate}: the entries logged so far sum to "
            f"{self._expected_total_kcal:g} kcal, but the app shows {cur:g} "
            f"(off by {cur - self._expected_total_kcal:+g}). The band oracle "
            f"cannot see this -- it tolerates half a portion either way.")
        self._capture_oracle_failure(f"total_mismatch_{gate}")
        self.execution_log.append(StepResult(
            verdict=None, gate_name=gate,
            error=(f"TOTAL MISMATCH: logged entries sum to "
                   f"{self._expected_total_kcal:g}, app shows {cur:g} "
                   f"({cur - self._expected_total_kcal:+g})")))
        return True

    def _check_total_delta(self, gate: str, label: str, observed: str, resolver) -> None:
        """Did the total MOVE the way the last diary action implies?

        WHY THIS EXISTS: the bucket oracle answers "is the total in the right
        band", which stops discriminating once the bands saturate -- above ~543
        kcal everything is OVER. Observed live: an ADD_ENTRY completed, the total
        stayed at 775 instead of going to 930, and the oracle passed it because
        775 and 930 are both OVER. The arithmetic check missed it too, because 775
        IS a valid multiple of the portion size; "is this a possible total?" is
        simply the wrong question.

        This asks the right one: a committed add must raise the total by exactly
        one portion, a remove must lower it by one, and a rejected add must leave
        it alone. That property survives saturation, needs no model change, and is
        computed from values already captured.

        Reported as a finding, NOT as the verdict: the model specifies buckets, so
        the bucket comparison stays the ioco result. Claiming a conformance failure
        from an oracle the specification does not contain would be overreach.
        """
        op = getattr(self, "_pending_entry_op", None)
        self._pending_entry_op = None
        unit = getattr(resolver, "unit", None)
        from .quantity_resolver import parse_total
        cur, _goal = parse_total(observed)
        prev = getattr(self, "_last_total_kcal", None)
        # Unconditional, because this check silently declined to fire on a live run
        # that reproduced offline. Every early exit below is now visible instead of
        # having to be inferred from its absence.
        logger.debug(f"  [delta] op={op!r} prev={prev!r} cur={cur!r} unit={unit!r} "
                     f"observed={observed!r}")
        if not unit or unit <= 0:
            return
        if cur is not None:
            self._last_total_kcal = cur
        if op is None or prev is None or cur is None:
            return                       # nothing to compare against yet

        up = label.upper()
        if "REJECTED" in up:
            expected_delta = 0.0         # a refused entry must change nothing
            what = "a rejected entry"
        elif op == "add":
            expected_delta = float(unit)
            what = "a committed entry"
        else:
            expected_delta = -float(unit)
            what = "a removed entry"

        actual = cur - prev
        if abs(actual - expected_delta) <= 0.5:      # allow the SUT's rounding
            return
        logger.error(
            f"TOTAL DELTA at {gate}: {what} should move the total by "
            f"{expected_delta:+g} kcal, but it went {prev:g} -> {cur:g} "
            f"({actual:+g}). The bucket oracle cannot see this once the buckets "
            f"saturate.")
        self.execution_log.append(StepResult(
            verdict=None, gate_name=gate,
            error=(f"TOTAL DELTA: {what} moved the total {actual:+g} kcal, "
                   f"expected {expected_delta:+g} ({prev:g} -> {cur:g})")))

    def _oracle_after_observe(self, matched_label: str, r):
        """Run the gate oracle for a transition the OBSERVATION selected.

        Until now `_validate_checkpoint` had exactly one call site: the shortcut
        that fires when a state offers a single abstract transition. Every gate
        reached at a state with several allowed outputs therefore skipped the
        oracle completely — no band check, and no update to the exact-sum ledger.

        The missing ledger update is the damaging half. The ledger is a running
        sum kept by `_check_total_exact`, and the ADD_ENTRY / REMOVE_ENTRY that
        moves it stages its operation in `_pending_exact_op` for the NEXT
        CONFIRM_TOTAL to apply. If that CONFIRM_TOTAL never reaches the oracle,
        the staged operation is not applied — it is silently overwritten by the
        following gate. A skipped REMOVE_ENTRY leaves its -900 kcal unapplied,
        the ledger sits 900 above the device for the rest of the run, and the
        next CONFIRM_TOTAL reports a TOTAL MISMATCH against a total the app
        computed correctly. That is a false counter-example manufactured by the
        tester's own bookkeeping, and because a mismatch is a finding rather than
        a verdict it can ride along inside a PASS.

        `_last_observed` is normally left in g_dict by the preceding OBSERVE
        step, but one of the two matching paths pops it; recover it from the
        StepResult's captured values so the oracle sees the same reading the
        selection did.
        """
        if not matched_label:
            return None
        if r is not None and getattr(r, "captured", None) and \
                "_last_observed" not in self.g_dict:
            self.g_dict["_last_observed"] = str(next(iter(r.captured.values())))
        gate = matched_label.split()[0].rstrip(";")
        return self._validate_checkpoint(gate, matched_label)

    def _declared_oracle(self):
        if self._obs_oracle is None:
            from .observation_oracle import ObservationOracle
            self._obs_oracle = ObservationOracle.from_type_description(self.td)
        return self._obs_oracle

    def _validate_declared_types(self, head: str, label: str):
        """Compare the label's offers with what the walk observed, for every
        type type_description.yml declares with `role:` at this gate.

        This is the oracle that makes a single-alternative checkpoint mean
        something for a system the strict oracles below were not written
        for. The observations are the OBSERVE steps since the previous
        checkpoint, by element; they are consumed here whether or not any
        type is declared, because the next checkpoint must not read this
        segment's values.

        A mismatch is a counter-example candidate and returns FAIL with the
        evidence captured. A type that could not be read (no number, no
        rendering, no observation in scope) is a warning, never a verdict:
        the tester failing to read a value is not the SUT failing.
        """
        observations = [(e, t) for e, t in self._pending_observations]
        self._pending_observations = []
        try:
            oracle = self._declared_oracle()
            if not oracle.declared_at(head):
                return None
            from .observation_oracle import Observation
            obs = [Observation(e, t) for e, t in observations]
            mismatches, unclassified = oracle.check(head, label, obs)
        except Exception as e:
            logger.warning(f"  {head} declared-type oracle skipped: {e}")
            return None
        for u in unclassified:
            logger.warning(f"  {head} oracle could not read {u.type_name} "
                           f"(AUT expects {u.expected}): {u.reason}")
        if not mismatches:
            checked = [t for t in oracle.declared_at(head)
                       if t not in {u.type_name for u in unclassified}
                       and t in oracle.offers(label)]
            if checked:
                logger.info(f"  {head} oracle OK: {', '.join(checked)} agree with "
                            f"{label!r} on {observations}")
            return None
        for m in mismatches:
            logger.error(f"{head} mismatch — {m.type_name}: AUT expects {m.expected}, "
                         f"observed {m.text!r} classifies as {m.got}")
        m = mismatches[0]
        self._capture_oracle_failure(
            f"{head.lower()}_{m.type_name.lower()}_{m.expected}_got_{m.got}")
        self.execution_log.append(StepResult(
            verdict=Verdict.FAIL, gate_name=head,
            error="; ".join(f"{m.type_name} {m.text!r} classifies as {m.got}, "
                            f"expected {m.expected}" for m in mismatches)))
        return Verdict.FAIL

    def _validate_checkpoint(self, gate: str, label: str):
        """STRICT oracle for observable checkpoint values: the per-food Calorie at
        FOOD_INFO and the DailyTotal bucket at CONFIRM_TOTAL. The observed on-screen
        value (captured as _last_observed) must match what the AUT/authoritative
        model expects. Returns Verdict.FAIL on mismatch (a counter-example), else
        None."""
        head = gate.split()[0].upper()
        # The declared-type oracle first, for every gate: it acts only on the
        # types type_description.yml marks with `role:` at this gate, so a
        # system that declares none is untouched, and a system that declares
        # them no longer passes a checkpoint it was never checked at.
        _v = self._validate_declared_types(head, label)
        if _v is not None:
            return _v
        if head == "FOOD_INFO":
            return self._validate_food_info(gate, label)
        # Remember what the walk just did to the diary, so the next CONFIRM_TOTAL
        # can check the total MOVED as that action implies -- see
        # _check_total_delta. Tracked here because this method already sees every
        # gate in order.
        if head == "ADD_ENTRY":
            self._pending_entry_op = "add"
            self._stage_exact_op("add")
            return None
        if head == "REMOVE_ENTRY":
            self._pending_entry_op = "remove"
            self._stage_exact_op("remove")
            return None
        if head != "CONFIRM_TOTAL":
            return None
        toks = label.replace("!", " ").split()[1:]        # drop the gate name
        # Find the bucket by VALUE, not by position: TotalChannel carries a
        # trailing FoodId for traceability, so the total is no longer the last
        # offer. A positional read would silently disable this oracle.
        expected = next((t.upper() for t in toks
                         if t.upper() in self._TOTAL_BUCKETS), None)
        observed = self.g_dict.get("_last_observed")
        if not expected or not observed or expected not in self._TOTAL_BUCKETS:
            return None
        try:
            from .quantity_resolver import QuantityResolver, parse_total
            r = getattr(self, "_qty_resolver", None)
            if r is None:
                r = QuantityResolver.from_type_description(self.td)
                self._qty_resolver = r
            # Strongest first. If the exact sum could be evaluated it answers the
            # question completely, and the two weaker checks below assume a
            # single-food diary -- they would flag every correct mixed total.
            if not self._check_total_exact(gate, label, observed):
                self._check_total_arithmetic(gate, observed, r)
                self._check_total_delta(gate, label, observed, r)
            # Runs unconditionally, unlike the fallbacks above: it asks a question
            # none of the others do -- whether the app's two views of the same day
            # agree with each other -- so an exact-sum match is no reason to skip
            # it. Costs three element reads at a point the tester has already
            # stopped.
            self._check_macro_consistency(gate, observed)
            if r.matches_total(expected, observed):
                logger.info(f"  CONFIRM_TOTAL oracle OK: {observed!r} -> {expected}")
                return None
            cur, goal = parse_total(observed)
            got = r.classify_total(cur, goal)
            logger.error(f"CONFIRM_TOTAL mismatch — AUT expects {expected}, observed "
                         f"{observed!r} (classifies as {got})")
            self._capture_oracle_failure(f"confirm_total_{expected}_got_{got}")
            self.execution_log.append(StepResult(
                verdict=Verdict.FAIL, gate_name=gate,
                error=f"total {observed!r} classifies as {got}, expected {expected}"))
            return Verdict.FAIL
        except Exception as e:
            logger.warning(f"  CONFIRM_TOTAL oracle skipped: {e}")
            return None

    def _authoritative_now(self, fid: str):
        """The food's energy as the SUT's own catalogue currently holds it.

        Only meaningful while a fault has rewritten that catalogue. Returns None
        when there is no injector, no product name for the abstract food, or the
        read fails -- in which case the caller keeps the declared fixture value.

        Reading it back rather than hardcoding the injected constant keeps the
        oracle honest if the injection changes: it compares the app against the
        database, which is the question, instead of against a number written down
        in two places.
        """
        inj = getattr(self, "_fault_injector", None)
        tgt = (getattr(self, "_fault_target", "") or "").upper()
        if inj is None or tgt != "CACHE_STALE":
            return None
        # FoodId.abstract_values maps the abstract id to the real product name, the
        # same table seed_foods.sh and check_env.sh assert against.
        name = ((self.td or {}).get("FoodId", {}).get("abstract_values") or {}).get(fid)
        if not name:
            return None
        try:
            v = inj._scalar(f"SELECT energy FROM Product WHERE name = '{name}' LIMIT 1")
            return float(v) if v not in (None, "") else None
        except Exception:
            return None

    def _validate_food_info(self, gate: str, label: str):
        """STRICT Calorie oracle at FOOD_INFO: the observed per-food kcal
        (observe(el_calories) -> _last_observed) must equal the food's
        AUTHORITATIVE value from type_description (Calorie.abstract_values, seeded
        by seed_foods.sh). A stale reading (CACHE_STALE's 999) or a corrupt/absent
        one (DB_CORRUPT's NULL) does NOT match and is reported as a counter-example
        rather than silently captured. Returns Verdict.FAIL on mismatch, else None."""
        toks = label.replace("!", " ").split()[1:]        # e.g. [FOOD_APPLE, KCAL_APPLE]
        fid = toks[0].lower() if toks else None           # -> food_apple
        observed = self.g_dict.get("_last_observed")
        if not fid or not observed:
            return None
        cal_spec = (self.td or {}).get("Calorie", {})
        expected_s = (cal_spec.get("abstract_values") or {}).get(fid)
        if expected_s is None:
            return None                                   # no authoritative value -> can't pin

        # UNDER CACHE_STALE, THE DECLARED VALUE IS NO LONGER THE AUTHORITATIVE ONE.
        #
        # The injection rewrites the energy in the app's own Product table, and that
        # table IS the app's source of truth. So after injection the declared 900 is
        # simply out of date, and comparing against it inverts the test:
        #
        #     app reads its database, shows 999   -> "FAIL"   (but it is CORRECT)
        #     app serves a cached 900             -> "PASS"   (but it is STALE)
        #
        # It failed the app for being right and passed it for being wrong. That is
        # not a stricter oracle, it is a backwards one, and it made all 48
        # cache_stale test cases uninterpretable.
        #
        # The fix is to ask the database what the authoritative value is NOW, rather
        # than assuming it still matches the fixture. The check then means what it
        # was always supposed to mean: does the app agree with its own catalogue, or
        # is it serving something it read earlier?
        stale_exp = self._authoritative_now(fid)
        if stale_exp is not None and abs(stale_exp - float(expected_s)) >= 0.5:
            logger.info(f"  CACHE_STALE active: authoritative value for {fid} is now "
                        f"{stale_exp:g} kcal in the database, not the fixture's "
                        f"{float(expected_s):g}. Serving {float(expected_s):g} would "
                        f"mean the app did not revalidate.")
            expected_s = stale_exp
        try:
            from .quantity_resolver import parse_calorie
            exp = float(expected_s)
            obs = parse_calorie(observed)
            if obs is None:
                logger.warning(f"  FOOD_INFO oracle skipped: can't parse kcal from {observed!r}")
                return None
            if abs(obs - exp) < 0.5:
                logger.info(f"  FOOD_INFO oracle OK: {fid} shows {observed!r} == "
                            f"authoritative {exp:g} kcal")
                return None
            # A FINDING, NOT A VERDICT.
            #
            # This compares the displayed energy against authoritative data
            # (type_description, or the app's own catalogue under CACHE_STALE).
            # That is ground truth the ABSTRACT TEST CASE never asked about: the
            # paper's oracle is the expected-output set of the current state, and
            # nothing else. Ending a walk here would be the concretization engine
            # supplying a verdict of its own.
            #
            # So it is reported the way TOTAL MISMATCH and ARITHMETIC
            # INCONSISTENCY already are -- recorded, surfaced by
            # classify_failure.py, and never allowed to terminate the walk or
            # decide the outcome.
            #
            # Measured across the 793-case sweep before this change: 664 runs
            # exercised this check and every one agreed, 0 mismatches. Demoting
            # it therefore alters no verdict in the campaign to date.
            logger.error(f"FOOD_INFO FINDING — {fid} authoritative {exp:g} kcal, "
                         f"observed {observed!r} ({obs:g}); walk continues")
            self._capture_oracle_failure(f"food_info_{fid}")
            self.execution_log.append(StepResult(
                verdict=None, gate_name=gate,
                error=f"FOOD_INFO FINDING: {fid} observed {obs:g} kcal, "
                      f"expected authoritative {exp:g}"))
            return None
        except Exception as e:
            logger.warning(f"  FOOD_INFO oracle skipped: {e}")
            return None

    def _external_dependency_controls(self) -> tuple[set, set]:
        """(engaged_by, cleared_by) selectors, from concrete_domain.yml.

        A SUT may offer controls that switch it to a data source outside itself
        (an external catalogue, a third-party API). If the test fixture cannot
        populate that source, everything downstream of such a control fails for
        want of data rather than because the SUT misbehaved. Which controls
        those are is a property of the SUT, so it is declared in the concrete
        domain under `external_dependencies:` and never named here.
        """
        cached = getattr(self, "_ext_dep_cache", None)
        if cached is not None:
            return cached
        domain = (self.em or {}).get("concrete_domain") or {}
        spec   = domain.get("external_dependencies") or {}
        values = domain.get("concrete_values") or {}

        def _sel(names):
            out = set()
            for n in names or []:
                v = values.get(n)
                if v:
                    out.add(str(v).strip().lower())
            return out

        cached = (_sel(spec.get("engaged_by")), _sel(spec.get("cleared_by")))
        self._ext_dep_cache = cached
        if cached[0]:
            logger.debug(f"  [ext-dep] engaged_by={cached[0]} cleared_by={cached[1]}")
        return cached

    def _note_action(self, action: dict) -> None:
        """Record whether a step that just SUCCEEDED moved the walk into, or out
        of, an external-data-source context. Tracked as state because the step
        that eventually fails is not the one that engaged the source — it is a
        later wait_for on content the empty source never produced."""
        engaged_by, cleared_by = self._external_dependency_controls()
        if not engaged_by:
            return
        sel = (action.get("selector") or "").strip().lower()
        if not sel:
            return
        if sel in cleared_by:
            if getattr(self, "_ext_dep_engaged", None):
                logger.debug("  [ext-dep] left external source context")
            self._ext_dep_engaged = None
        elif sel in engaged_by:
            logger.info(f"  external data source engaged: {action.get('selector')!r} "
                        f"— failures downstream of this are INCONCLUSIVE, not FAIL")
            self._ext_dep_engaged = action.get("selector")

    def unrealizable_values(self) -> set:
        """Abstract values this deployment cannot produce, from the concrete domain.

        Declared per type for readability (`FoodSource: [EXTERNAL]`) and flattened
        here, because a transition label carries bare tokens (`!EXTERNAL`) with no
        type attached. Lower-cased to match how parse_gate_and_params normalises.
        """
        cached = getattr(self, "_unrealizable_cache", None)
        if cached is not None:
            return cached
        domain = (self.em or {}).get("concrete_domain") or {}
        raw = domain.get("unrealizable") or {}
        vals = set()
        if isinstance(raw, dict):
            for _type, names in raw.items():
                for n in (names or []):
                    vals.add(str(n).strip().lower())
        else:                                   # a bare list is accepted too
            for n in raw:
                vals.add(str(n).strip().lower())
        self._unrealizable_cache = vals
        if vals:
            logger.debug(f"  [unrealizable] {sorted(vals)}")
        return vals

    def blocking_value(self, label: str) -> str | None:
        """The unrealizable value this transition needs, if any."""
        vals = self.unrealizable_values()
        if not vals:
            return None
        _gate, params = self.reader.parse_gate_and_params(label)
        for _pname, aval in params:
            if aval in vals:
                return aval
        return None

    def realizable_here(self, graph: AUTGraph) -> tuple[bool, str | None]:
        """Can this test case reach :PASS: at all in this environment?

        Deletes every transition needing an unrealizable value and asks whether a
        verdict is still reachable, reusing _compute_pass_reachable. Answered from
        the graph alone: no device, no emulator time, and the reason names the value
        rather than whichever concrete step happened to fail first.
        """
        vals = self.unrealizable_values()
        if not vals:
            return True, None
        blocked = [t for t in graph.transitions if self.blocking_value(t.label)]
        if not blocked:
            return True, None
        pruned = AUTGraph(initial=graph.initial,
                          transitions=[t for t in graph.transitions
                                       if not self.blocking_value(t.label)])
        # _compute_pass_reachable writes self._pass_distance as a side effect, so
        # keep the real one: this is a hypothetical graph, not the walk's.
        saved = getattr(self, "_pass_distance", None)
        try:
            reachable = self._compute_pass_reachable(pruned)
        finally:
            if saved is not None:
                self._pass_distance = saved
        if graph.initial in reachable:
            return True, None
        needed = sorted({self.blocking_value(t.label) for t in blocked})
        return False, (f"not executable in this environment: every route to a "
                       f"verdict needs {', '.join(needed)}, which this deployment "
                       f"cannot produce")

    def _inconclusive_reason(self, action: dict, gate: str) -> str | None:
        """Why this failed step is NOT evidence about the SUT — or None if it is.

        A conformance FAIL has to be earned: the tester applied its stimulus and
        the SUT answered wrongly. Each check below is a way that never happened,
        so no observation exists to judge and the run is INCONCLUSIVE. Single
        source of truth, so the verdict and the reported reason cannot disagree.
        """
        # 1. The executor knows it lost track of the SUT (screen anchor absent,
        #    gate precondition never met). It reports that directly rather than
        #    making us infer it from a selector name.
        pf = getattr(self.executor, "last_precondition_failure", None)
        if pf:
            return pf

        # 2. An external data source this fixture cannot populate. Checked before
        #    the fault target because it makes a step unappliable on ANY test
        #    purpose — including the nominal one, where there is no fault at all.
        engaged = getattr(self, "_ext_dep_engaged", None)
        if engaged:
            return (f"external source {engaged!r} engaged and the fixture "
                    f"cannot populate it")

        # 3. A targeted fault that provably did not take effect, so the SUT was
        #    never challenged. Consulted live, never mapped up front: the moment
        #    the fault becomes injectable the same run yields a real PASS/FAIL.
        tgt = getattr(self, "_fault_target", None)
        inj = getattr(self, "_fault_injector", None)
        if not tgt:
            return None
        _m = inj.manifested(tgt) if inj is not None else None
        logger.debug(f"  [inconc-guard] target={tgt} manifested={_m} "
                     f"selector={action.get('selector')!r}")
        if _m is False:
            return f"{tgt} did not manifest (precondition absent / injection no-op)"
        return None

    def _judge_missing_observable(self, state, outgoing, t, r: StepResult) -> StepResult:
        """A WAIT_FOR that timed out: the SUT did not show what the System
        Interface waits for. Whether that is a verdict is the test case's
        question, not the tester's.

        WAIT_FOR is not a stimulus. It is how the SI renders "the output the
        specification requires here is on screen" (an error message after a
        failed save, the list after a cancel). Treating its absence as
        "stimulus could not be applied" reported the SUT's silence as the
        tester's failure: with a fault injected and the app showing no error,
        the run came back UNEXECUTABLE and the obligation "a failed save is
        reported" could never fail. That is the defect this method exists to
        surface, and it is judged the way the multi-observation case already
        is (see the structural branch): by whether the case offers quiescence
        at this state.

          apparatus failed (anchor lost, external source)  -> UNEXECUTABLE
          the case permits quiescence here (delta offered) -> INCONCLUSIVE
          the case does not                                -> FAIL, evidence kept
        """
        reason = self._inconclusive_reason({}, r.gate_name or "WAIT_FOR")
        if reason:                                # not the SUT's doing
            return StepResult(verdict=Verdict.UNEXECUTABLE, gate_name=r.gate_name,
                              error=f"UNEXECUTABLE ({reason}): {t.label}",
                              concrete_values=r.concrete_values, duration_ms=r.duration_ms)
        _delta_ok = any(self.reader.is_quiescence_sentinel(x.label) for x in outgoing)
        if _delta_ok:
            logger.info(f"State {state} waits for {t.label} — it never appeared, and "
                        f"this state PERMITS quiescence (delta offered), so no "
                        f"output was required: INCONCLUSIVE, not a conformance FAIL.")
            return StepResult(verdict=Verdict.INCONC, gate_name=r.gate_name,
                              error=f"INCONCLUSIVE (quiescence permitted): {t.label} "
                                    f"never appeared", concrete_values=r.concrete_values,
                              duration_ms=r.duration_ms)
        logger.error(f"State {state} waits for {t.label} — it never appeared and this "
                     f"state does NOT permit quiescence. The specification required "
                     f"an output here and none appeared: CONFORMANCE FAILURE.")
        _, params = self.reader.parse_gate_and_params(t.label)
        self._capture_oracle_failure(
            f"missing_{str(params[0][1]).lower() if params else 'observable'}")
        return StepResult(verdict=Verdict.FAIL, gate_name=r.gate_name,
                          error=f"{t.label}: the specification required this observable "
                                f"and it never appeared",
                          concrete_values=r.concrete_values, duration_ms=r.duration_ms)

    def _step_failure_verdict(self, action: dict, gate: str) -> "Verdict":
        """A step the tester could not apply is never a verdict.

        This used to choose between INCONCLUSIVE and FAIL depending on whether a
        reason for the failure was known. Both answers were wrong, for the same
        reason: the walk did not happen, so neither outcome is a statement about
        the SUT. Knowing WHY the stimulus could not be applied is a diagnostic
        question; it does not promote the run to evidence.

        `_inconclusive_reason` is still consulted, but only for the explanation
        recorded on the step -- never to select the outcome.
        """
        reason = self._inconclusive_reason(action, gate)
        logger.info(f"  {reason or 'stimulus could not be applied'}"
                    f" -> UNEXECUTABLE (not a verdict)")
        return Verdict.UNEXECUTABLE

    # `def run_graph` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> Verdict` documents the expected return type.
    def run_graph(self, graph: AUTGraph) -> Verdict:
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.g_dict = {}
        # Re-seed: this reset runs at the START OF EACH WALK and previously
        # discarded the static bindings, so every {{TOKEN}} route reverted
        # to a literal placeholder mid-run.
        self._seed_static_bindings()
        # `self.` stores this value on the current object, so other methods in the same object can use it later during the same concretization run.
        self.execution_log = []
        # Per-walk state: which external data source, if any, the walk is inside,
        # and the running total the delta check compares against. Reset here so a
        # --aut-dir batch cannot carry one test case's context into the next.
        self._ext_dep_engaged = None
        self._last_total_kcal = None
        self._pending_entry_op = None
        # The exact-sum oracle's running expectation. Starts at 0 because
        # seed_foods.sh clears the diary before every run.
        self._expected_total_kcal = 0.0
        self._pending_exact_op = None
        # False once a staged movement is lost; see _stage_exact_op.
        self._exact_ledger_ok = True

        # Pre-flight: is this test case executable in this deployment at all? Asked
        # of the graph before any UI is touched, so an unrunnable case costs no
        # emulator time and reports WHY rather than surfacing as whichever concrete
        # step failed first. A test case that was never executable is INCONCLUSIVE;
        # calling it FAIL would be a claim about the SUT that nothing supports.
        ok, why = self.realizable_here(graph)
        if not ok:
            # The test case needs an abstract value this deployment cannot
            # produce, so the walk cannot start. Decided before any stimulus is
            # applied, which makes it the clearest possible non-verdict.
            logger.warning(f"SKIPPED — {why}")
            self.execution_log.append(StepResult(
                verdict=Verdict.UNEXECUTABLE, gate_name="(pre-flight)",
                error=f"UNREALIZABLE: {why}"))
            return Verdict.UNEXECUTABLE

        # NOT pruned. It is tempting to delete the unrealizable transitions and let
        # the walker route around them, and it is wrong: these test cases are
        # CONTROLLABLE (verified with check_controllability.py -- 0 states offering
        # more than one input), and every EXTERNAL transition is the ONLY outgoing
        # transition of its state. The tester has no alternative to take. Removing
        # it would strand the walk at a dead end and execute something other than
        # the generated test case, which is not a test result at all.
        #
        # So the walk proceeds normally and stops the moment it is ASKED for a
        # stimulus this environment cannot supply -- see _blocked_transition_verdict
        # below, called from the walk. Reaching that point is a fact about the run,
        # not about the SUT, so the verdict is INCONCLUSIVE with the value named.

        # States from which a :PASS: is still reachable — used to steer among
        # alternative concrete stimuli toward the on-path branch.
        self._pass_reachable = self._compute_pass_reachable(graph)

        # Structural-decomposition AUT? If the graph spells out concrete UI steps
        # (TAP/ENTER_TEXT/…), abstract gates are treated as advance-only
        # checkpoints (see the checkpoint branch in the walk loop).
        self._structural_mode = any(
            self.reader.is_structural_ui_label(t.label) for t in graph.transitions)

        # NOTE, from the 2026-08-27 Moodle sweep: six of nine cases reported
        # INCONCLUSIVE at the identical step, waiting for "Add submission" on an
        # assignment that already had one. Local backtracking was tried here and
        # REMOVED: the concrete steps are separate transitions, so the state
        # whose precondition fails has exactly ONE outgoing edge and there is
        # nothing to re-choose. The real choice point is far upstream, so
        # recovering would mean unwinding the walk and replaying the prefix
        # against a re-reset fixture -- a different design, not a patch here.
        # The defect was in the MODEL, which offered a stimulus the SUT cannot
        # provide; it is fixed in specification_moodle.lnt by guarding the first
        # save on the submission not already existing.

        # Tracks whether a connectivity fault is currently injected, so it can be
        # restored when the walk ends (see run_aut/run_bcg finally clauses).
        self._fault_active = False

        # Pre-inject `timing: pre` faults whose gate appears in this AUT (the
        # corrupt/read-only state must pre-exist the read/write it disrupts):
        # DB_CORRUPT, CACHE_STALE, DISRUPTION_DB, STORAGE_FULL.
        if getattr(self, "_fault_injector", None) is not None:
            self._fault_injector.pre_inject([t.label for t in graph.transitions])

        # Same for the browser/DisruptionExecutor path. Without this, a fault
        # whose mechanism blocks a WRITE was installed AFTER the click that
        # performed the write -- the actions for a gate are emitted before the
        # gate, and the fault gate sits after the stimulus -- so it bit nothing
        # and the run reported a verdict for an undisrupted SUT. See
        # DisruptionExecutor.pre_inject for the measured orderings.
        _de = getattr(self, "disruption_executor", None)
        if _de is not None and getattr(_de, "pre_inject", None):
            if not _de.pre_inject([t.label for t in graph.transitions]):
                self._injection_failed = True
                logger.error("  pre-injected fault not confirmed — walk not started, no verdict")
                self.execution_log.append(StepResult(
                    verdict=Verdict.UNEXECUTABLE, gate_name="(pre-inject)",
                    error="pre-injected fault not confirmed active"))
                return Verdict.UNEXECUTABLE

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        state = graph.initial
        # Budget the walk from the SIZE OF THE TEST CASE, not a fixed number.
        #
        # A flat 500 exhausted 11 runs in the 2026-08-23 sweep and reported them
        # INCONCLUSIVE -- a verdict about the walker's patience, not about the
        # SUT. Those walks were not looping: they reached ~85 checkpoints and ~20
        # CONFIRM_TOTAL observations, which is simply what a large test case
        # costs when the model legitimately revisits states.
        #
        # Four steps per transition leaves room for that revisiting while still
        # bounding a genuine cycle, and the floor keeps small test cases from
        # being budgeted to nothing. Exhausting THIS is evidence of a loop;
        # exhausting a constant was evidence of nothing.
        MAX_STEPS = max(500, 4 * len(graph.transitions))
        logger.debug(f"  step budget {MAX_STEPS} "
                     f"({len(graph.transitions)} transitions x4, floor 500)")

        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for _ in range(MAX_STEPS):
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            outgoing = graph.outgoing(state)

            # Follow only THIS tc's target fault through the multi-fault graph: drop
            # transitions labelled with any OTHER fault gate. The SI loops, so a
            # refused fault (e.g. DISRUPTION_DB inside tc_storage_full) stays
            # PASS-reachable via the loop and would otherwise lure the walker away
            # from the real target (STORAGE_FULL). Never empty the set.
            _tgt = getattr(self, "_fault_target", None)
            _inj = getattr(self, "_fault_injector", None)
            if _tgt and _inj is not None:
                _kept = [t for t in outgoing
                         if not (_inj.is_fault_gate(t.label.split()[0].upper().rstrip(";"))
                                 and t.label.split()[0].upper().rstrip(";") != _tgt)]
                if _kept:
                    outgoing = _kept

            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if not outgoing:
                # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                # A non-trap state with no outgoing transitions. In a well-formed
                # test case this cannot happen, so it means the AUT is malformed
                # or pruning removed every arm -- a defect in the apparatus or
                # the model, not an observation about the SUT.
                logger.warning(f"Dead end at state {state} — UNEXECUTABLE "
                               f"(malformed test case or over-pruned)")
                return Verdict.UNEXECUTABLE

            # ---- tau transitions ------------------------------------
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            internal = [t for t in outgoing if self.reader.is_internal_label(t.label)]
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if internal:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                state = internal[0].target
                # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                logger.debug(f"  tau -> state {state}")
                # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                continue

            # ---- fault gates (inject out-of-band, then advance) -------------
            # Any gate the disruption_mapping knows about (UE1_KILL, DB_CORRUPT,
            # DISRUPTION_DB, STORAGE_*, CACHE_STALE, EXTAPI_FAIL, ...) must be caught
            # here before the checkpoint branch would advance past it. `gate`-timing
            # faults fire now via the AndroidFaultInjector; `pre`-timing ones were
            # already injected before the walk (inject_gate is then a no-op). When no
            # injector is present, fall back to the connectivity-only path.
            real_nf = [t for t in outgoing
                       if not self.reader.is_quiescence_sentinel(t.label)]

            def _is_fault_gate(lbl: str) -> bool:
                g = lbl.split()[0].upper().rstrip(";")
                if self._fault_injector is not None and self._fault_injector.is_fault_gate(g):
                    return True
                # The DisruptionExecutor path. Without this, a SUT driven
                # through the browser recognised only the gates in
                # NETWORK_FAULT_GATES -- one of Moodle's eight -- and walked
                # straight past the other seven, injecting nothing while still
                # reporting a verdict for each. activate_disruption was
                # reachable only from a DISRUPTION_OCCURS label, which TESTOR
                # does not emit for a plain fault gate.
                de = getattr(self, "disruption_executor", None)
                if de is not None and getattr(de, "is_fault_gate", None) \
                        and de.is_fault_gate(g):
                    return True
                return g in self.NETWORK_FAULT_GATES

            # Only inject a fault gate whose target can still reach :PASS: — the
            # composed fault AUTs contain OTHER faults as branches that the test
            # purpose refuses (they lead to REFUSE). Grabbing the first fault gate
            # blindly would wander into a refused branch (e.g. DISRUPTION_DB inside
            # tc_storage_full); restrict to the pass-reachable (target) fault.
            _target = getattr(self, "_fault_target", None)
            fault_candidates = [
                t for t in real_nf
                if _is_fault_gate(t.label)
                and (_target is None or t.label.split()[0].upper().rstrip(";") == _target)
                and (not getattr(self, "_pass_reachable", None) or t.target in self._pass_reachable)
            ]
            fault_t = fault_candidates[0] if fault_candidates else None
            if fault_t is not None:
                gate = fault_t.label.split()[0].upper().rstrip(";")
                if self._fault_injector is not None:
                    self._fault_injector.inject_gate(gate)   # gate-timing only; pre/none = no-op
                    # NB: do NOT set _fault_active here — the injector owns its own
                    # restore(); _fault_active drives the legacy set_ue1_offline path
                    # (Appium mobile:shell), which needs --allow-insecure adb_shell.
                else:
                    de = getattr(self, "disruption_executor", None)
                    set_offline = getattr(self.executor, "set_ue1_offline", None)
                    if de is not None and getattr(de, "is_fault_gate", None) \
                            and de.is_fault_gate(gate):
                        # activate_disruption VERIFIES the fault took effect and
                        # returns False if it did not, so a fault that silently
                        # failed to bite cannot be walked past as though it had.
                        if de.activate_disruption(gate):
                            self._active_disruptions.add(gate)
                            logger.info(f"  {gate} injected and confirmed")
                        else:
                            # Stop here, as Algorithm 1 does: walking on would
                            # test an undisrupted SUT and cost the whole case
                            # for a result that is discarded anyway.
                            logger.error(f"  {gate}: injection FAILED or was not"
                                         f" confirmed — walk stopped, no verdict")
                            self._injection_failed = True
                            self.execution_log.append(StepResult(
                                verdict=Verdict.UNEXECUTABLE, gate_name=gate,
                                error=f"{gate} not confirmed active"))
                            return Verdict.UNEXECUTABLE
                    elif set_offline and gate in self.NETWORK_FAULT_GATES:
                        set_offline(True)
                        self._fault_active = True
                        logger.info(f"  {gate} injected — device connectivity disabled")
                    else:
                        logger.warning(f"  {gate}: no injector configured")
                self.execution_log.append(StepResult(verdict=None, gate_name=gate))
                state = fault_t.target
                continue

            # ---- structural UI gates (NAVIGATE_TO/CLICK/WAIT_FOR/…) -----
            # Legacy parameterless structural gates are bundled into meaningful
            # gate traversal paths and advance like taus. New typed structural
            # gates carry concrete route/selector/value/element enums and can be
            # executed directly from concrete_domain.yml.
            # Quiescence sentinels (:DELTA:/LOCK) are often offered alongside the
            # structural stimuli; they are not transitions to *take* here, so
            # exclude them when deciding whether this is a structural state.
            real = [t for t in outgoing
                    if not self.reader.is_quiescence_sentinel(t.label)]
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if real and all(self.reader.is_structural_ui_label(t.label) for t in real):
                # Among alternative concrete stimuli, steer toward a branch that can
                # still reach :PASS: (avoids off-path :INCONCLUSIVE: arms such as
                # TAP CV_BACK vs TAP CV_SAVE at the add-food confirm state).
                # When the alternatives are observations, ASK THE SUT which one
                # occurred rather than picking by distance to :PASS:.
                _picked = self._choose_by_observed_presence(real)
                if _picked is False:
                    # The SUT produced NONE of the outputs this state observes.
                    # That is a counter-example UNLESS the test case permits
                    # quiescence here, so ask the case, never assume.
                    #
                    # Deciding this the other way is how a real finding gets
                    # buried: a disruption that leaves the SUT silent when the
                    # specification demands an output is precisely the defect
                    # this method exists to catch, and calling it INCONCLUSIVE
                    # would report the tester's patience instead of the SUT's
                    # behaviour.
                    _delta_ok = any(self.reader.is_quiescence_sentinel(x.label)
                                    for x in outgoing)
                    _labels = [x.label for x in real]
                    if _delta_ok:
                        logger.info(
                            f"State {state} observes {_labels} — the SUT "
                            f"produced none of them, and this state PERMITS "
                            f"quiescence (delta offered), so no output was "
                            f"required: INCONCLUSIVE, not a conformance FAIL.")
                        return Verdict.INCONC
                    logger.error(
                        f"State {state} observes {_labels} — the SUT produced "
                        f"NONE of them and this state does NOT permit "
                        f"quiescence. The specification required an output "
                        f"here and none appeared: CONFORMANCE FAILURE.")
                    return Verdict.FAIL
                t = _picked if _picked is not None else self._choose_toward_pass(real)
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                gate = t.label.split()[0].rstrip(";")
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if self._has_typed_structural_params(t.label):
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    r = self._perform_typed_structural_transition(t)
                    # An observable that never appeared, whether the SI waits
                    # for it (WAIT_FOR -> UNEXECUTABLE) or reads it (OBSERVE
                    # -> "timed out"), is judged by the case, not by which
                    # primitive noticed its absence.
                    _absent = ((gate.upper() == "WAIT_FOR" and r.verdict == Verdict.UNEXECUTABLE)
                               or (gate.upper() == "OBSERVE" and r.verdict == Verdict.FAIL
                                   and "timed out" in (r.error or "")))
                    if _absent:
                        r = self._judge_missing_observable(state, outgoing, t, r)
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    self.execution_log.append(r)
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if r.verdict is not None:
                        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                        return r.verdict
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    state = t.target
                    # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                    continue
                # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                logger.info(f"  structural {gate} — advance")
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                self.execution_log.append(StepResult(verdict=None, gate_name=gate))
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                state = t.target
                # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                continue

            # ---- abstract checkpoint gates (structural-decomposition AUTs) ----
            # When the test case spells out the concrete UI as structural steps
            # (TAP/ENTER_TEXT/WAIT_FOR/OBSERVE), the abstract gates in between
            # (SEARCH_FOOD, FOOD_INFO, ADD_ENTRY, CONFIRM_TOTAL, …) are milestone
            # markers, not actions to re-drive — the structural steps already did
            # the work and the observation. Re-running their SI element-map
            # actions would navigate away from the screen the structural steps
            # left us on. So advance through them as checkpoints.
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if getattr(self, "_structural_mode", False):
                real = [t for t in outgoing
                        if not self.reader.is_quiescence_sentinel(t.label)]
                abstract = [t for t in real
                            if not self.reader.is_structural_ui_label(t.label)
                            and not self.reader.is_verdict_label(t.label)
                            and not self.reader.is_internal_label(t.label)]
                # ONE alternative only. Where a state offers SEVERAL abstract
                # transitions, choosing between them here is wrong: they are
                # OUTPUTS, and which one occurs is the SUT's decision, not the
                # tester's. A specification may allow more than one output after
                # a trace and the tester must accept any of them.
                #
                # Observed live 2026-08-17: after removing an entry from a
                # saturated total the specification offers CONFIRM_TOTAL !OVER or
                # !HIGH (OVER means "four or more", so removing one leaves "three
                # or more"). This shortcut picked !OVER by pass-distance, the app
                # showed 2700 kcal = !HIGH, and the run was reported as a
                # counter-example -- while the exact-sum oracle confirmed 2700 was
                # correct. Multiple alternatives now fall through to the normal
                # observe path, which matches whichever output actually appears.
                # A TESTER's choice between an abstract input and a concrete
                # step: the SI offers both after a shared prefix (open a row
                # -> VIEW it, or CLICK its Delete button). Neither branch above
                # took it -- the state is not all-structural, and not a single
                # abstract gate -- so the concrete click fell through to the
                # observation path below and was READ instead of clicked (the
                # delete dialog never opened). Inputs only: choosing among
                # OUTPUTS is the SUT's decision and stays with the observe path.
                # The abstract labels here are known to be inputs without any
                # gate list: the case is controllable (TESTOR), so a state where
                # the tester can ACT (click, type, navigate) offers no SUT
                # output besides quiescence. Hence: only when every concrete
                # alternative is a tester action, never a wait or an observe.
                _structural = [t for t in real if self.reader.is_structural_ui_label(t.label)]
                _acts = all(t.label.split()[0].rstrip(";").upper() not in ("WAIT_FOR", "OBSERVE")
                            for t in _structural)
                if (abstract and _structural and _acts
                        and len(abstract) + len(_structural) == len(real)):
                    t = self._choose_toward_pass(real)
                    gate = t.label.split()[0].rstrip(";")
                    if t in _structural and self._has_typed_structural_params(t.label):
                        r = self._perform_typed_structural_transition(t)
                        self.execution_log.append(r)
                        if r.verdict is not None:
                            return r.verdict
                    else:
                        _v = self._validate_checkpoint(gate, t.label)
                        if _v is not None:
                            return _v
                        logger.info(f"  checkpoint {gate} — advance (chosen among inputs)")
                        self.execution_log.append(StepResult(verdict=None, gate_name=gate))
                    state = t.target
                    continue
                if abstract and len(abstract) == len(real) and len(abstract) == 1:
                    t = abstract[0]
                    gate = t.label.split()[0].rstrip(";")
                    # STRICT oracle: validate the observed value at this checkpoint
                    # against the AUT's expected discretized value (DailyTotal bucket
                    # at CONFIRM_TOTAL). A mismatch is a counter-example.
                    _v = self._validate_checkpoint(gate, t.label)
                    if _v is not None:
                        return _v
                    logger.info(f"  checkpoint {gate} — advance (concrete steps done)")
                    self.execution_log.append(StepResult(verdict=None, gate_name=gate))
                    state = t.target
                    continue

            # ---- classify -------------------------------------------
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            inputs   = [t for t in outgoing
                        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                        if self.reader.classify_label(t.label) in (Direction.INPUT, Direction.BOTH)]
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            inputs   = self._sort_inputs(inputs)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if self.forced_disruption_key is not None:
                # Keep only inputs that match the forced disruption key, or normal inputs if none match
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                disruption_inputs = [t for t in inputs if t.label.strip().startswith("DISRUPTION_OCCURS")]
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                exact_match = [t for t in disruption_inputs if t.label.strip() == self.forced_disruption_key]
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if exact_match:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    inputs = exact_match
                # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
                else:
                    # If forced key not found, remove all disruption inputs and continue with normal
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    inputs = [t for t in inputs if not t.label.strip().startswith("DISRUPTION_OCCURS")]             
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            outputs  = [t for t in outgoing
                        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                        if self.reader.classify_label(t.label) == Direction.OUTPUT]
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            verdicts = [t for t in outgoing
                        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                        if self.reader.is_verdict_label(t.label)]

            # ---- pure verdict state (e.g., :PASS:) -------------------
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if verdicts:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                vt = verdicts[0]
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                v  = self._map_transition_verdict(vt.label)
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                self.execution_log.append(StepResult(verdict=v, gate_name=vt.label))
                # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                logger.info(f"Verdict transition: {vt.label} -> {v.name}")
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return v

            # ---- single input, no outputs ---------------------------
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if inputs and not outputs:
                # Any (PASS)-labelled input is a terminal verdict — prefer it
                # over looping inputs (e.g. APP_TIMEOUT (PASS) at tc_a1 state 13).
                # `pass` is an intentional no-op: it tells Python 'do nothing here' while keeping the syntax valid.
                pass_t = next((t for t in inputs if "(PASS)" in t.label), None)
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if pass_t is not None:
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    self._perform_transition(pass_t)
                    # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                    logger.info(f"  TGV quiescence PASS: {pass_t.label}")
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return Verdict.PASS
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                t = inputs[0]
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                r = self._perform_transition(t)
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                self.execution_log.append(r)
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if r.verdict is not None:
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return r.verdict
                # TGV verdict suffix on an input transition.
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if "(PASS)" in t.label:
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return Verdict.PASS
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if "(FAIL)" in t.label:
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return Verdict.FAIL
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if "(INCONCLUSIVE)" in t.label:
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return Verdict.INCONC
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                state = t.target
                # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                continue

            # ---- output-only transitions (no inputs) ----------------
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if outputs and not inputs:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                outputs = sorted(outputs, key=lambda t: self._OUTPUT_PRIORITY.get(t.label.split()[0].upper(), 50))
                # LOCK is TGV's quiescence sentinel — never observable; it is the
                # branch taken when the SUT stays silent. Observe only the real
                # outputs; fall back to LOCK's verdict on timeout.
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                lock_t = next((t for t in outputs
                               # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                               if self.reader.is_quiescence_sentinel(t.label)), None)
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                expected = {t.label: t for t in outputs
                            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                            if not self.reader.is_quiescence_sentinel(t.label)}

                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                r, matched_label = (self._observe_transition(expected)
                                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                                    if expected else (None, None))
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if r is not None:
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    self.execution_log.append(r)

                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if matched_label and matched_label in expected:
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if self.reader.is_attack_label(matched_label) or \
                       self.reader.is_failure_label(matched_label):
                        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                        logger.info(f"Attack/Failure observed: {matched_label}")
                        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                        return Verdict.FAIL
                    # TGV encodes verdict in the label suffix: "; INPUT (PASS)" etc.
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    v = self.reader.verdict_from_suffix(matched_label)
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if v is not None:
                        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                        logger.info(f"TGV {v.name} verdict from label: {matched_label}")
                        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                        return v
                    # The observation selected this branch, so the gate oracle owes
                    # it the same scrutiny the single-alternative path gets.
                    _v = self._oracle_after_observe(matched_label, r)
                    if _v is not None:
                        return _v
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    state = expected[matched_label].target
                    # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                    continue

                # A real output was observed but violated a constraint — genuine FAIL.
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if r is not None and r.verdict == Verdict.FAIL and r.gate_name != "OBSERVE":
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return Verdict.FAIL

                # SUT stayed silent (timeout). Quiescence is expected iff a LOCK
                # branch exists — take its verdict instead of a blanket FAIL.
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if lock_t is not None:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    v = self.reader.verdict_from_suffix(lock_t.label) or Verdict.INCONC
                    # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                    logger.info(f"Quiescence (LOCK) observed -> {v.name}: {lock_t.label}")
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    self.execution_log.append(StepResult(verdict=v, gate_name="LOCK"))
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return v

                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return Verdict.FAIL

            # ---- mixed: inputs AND outputs ----------------------------
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if inputs and outputs:
                # Non-quiescence input carrying (PASS) is an intentional test
                # action (e.g. UE1_OFFLINE (PASS) in tc_u1) — fire it immediately.
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                immediate_t = next(
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    (t for t in inputs
                     # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                     if "(PASS)" in t.label
                     # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                     and t.label.split()[0].upper().rstrip(";")
                         # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                         not in self.reader.QUIESCENCE_GATES),
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    None
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if immediate_t:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    r = self._perform_transition(immediate_t)
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    self.execution_log.append(r)
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if r.verdict is not None:
                        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                        return r.verdict
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return Verdict.PASS

                # Otherwise observe expected SUT outputs first. LOCK is the
                # quiescence sentinel — exclude it from observation, use on timeout.
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                outputs_sorted = sorted(
                    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                    outputs,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    key=lambda t: self._OUTPUT_PRIORITY.get(t.label.split()[0].upper(), 50)
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                lock_t = next((t for t in outputs_sorted
                               # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                               if self.reader.is_quiescence_sentinel(t.label)), None)
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                expected_out = {t.label: t for t in outputs_sorted
                                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                                if not self.reader.is_quiescence_sentinel(t.label)}
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                r, matched_label = (self._observe_transition(expected_out)
                                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                                    if expected_out else (None, None))
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if r is not None:
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    self.execution_log.append(r)

                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if matched_label and matched_label in expected_out:
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if self.reader.is_attack_label(matched_label) or \
                       self.reader.is_failure_label(matched_label):
                        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                        return Verdict.FAIL
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    v = self.reader.verdict_from_suffix(matched_label)
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if v is not None:
                        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                        return v
                    # The observation selected this branch, so the gate oracle owes
                    # it the same scrutiny the single-alternative path gets.
                    _v = self._oracle_after_observe(matched_label, r)
                    if _v is not None:
                        return _v
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    state = expected_out[matched_label].target
                    # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                    continue

                # No output observed — quiescence PASS if available (APP_TIMEOUT (PASS)).
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                quiescence_t = next((t for t in inputs if "(PASS)" in t.label), None)
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if quiescence_t is not None:
                    # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                    logger.info(f"  Quiescence PASS after output timeout: {quiescence_t.label}")
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return Verdict.PASS

                # Quiescence (LOCK) branch among the outputs — take its verdict.
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if lock_t is not None:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    v = self.reader.verdict_from_suffix(lock_t.label) or Verdict.INCONC
                    # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                    logger.info(f"Quiescence (LOCK) observed -> {v.name}: {lock_t.label}")
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    self.execution_log.append(StepResult(verdict=v, gate_name="LOCK"))
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return v

                # Last resort: fire first input.
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                t = inputs[0]
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                r = self._perform_transition(t)
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                self.execution_log.append(r)
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if r.verdict is not None:
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return r.verdict
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if "(PASS)" in t.label:
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return Verdict.PASS
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if "(FAIL)" in t.label:
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return Verdict.FAIL
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if "(INCONCLUSIVE)" in t.label:
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return Verdict.INCONC
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                state = t.target
                # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                continue

        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
        # The budget is a property of the harness, not of the specification. A
        # walk that ran out of steps did not reach a trap state, so it has no
        # verdict to report -- raise the budget, or fix the loop, and run again.
        logger.warning(f"Exceeded MAX_STEPS ({MAX_STEPS}) — UNEXECUTABLE")
        return Verdict.UNEXECUTABLE

    # --------------------------------------------------------------
    # Transition execution helpers
    # --------------------------------------------------------------
    # `def _perform_transition` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> StepResult` documents the expected return type.
    def _perform_transition(self, t: AUTTransition) -> StepResult:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        start = time.time()
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        gate, params = self.reader.parse_gate_and_params(t.label)

        # The test case is asking for a stimulus this deployment cannot supply. It
        # is forced -- these test cases are controllable, so there is no alternative
        # transition to take instead -- and the tester simply cannot comply.
        #
        # No observation follows, so there is nothing to judge: INCONCLUSIVE, with
        # the value named. Checked HERE, the single point every transition passes
        # through, so no call site can forget it; and checked BEFORE the executor is
        # touched, so the run stops cleanly rather than failing several steps later
        # on a screen that was never going to appear.
        blocked = self.blocking_value(t.label)
        if blocked:
            reason = (f"test case requires {blocked!r}, which this environment "
                      f"cannot produce (see `unrealizable` in the concrete domain)")
            logger.warning(f"  UNREALIZABLE: {reason}")
            return StepResult(
                verdict=Verdict.INCONC, gate_name=gate,
                error=f"UNREALIZABLE: {reason}",
                duration_ms=(time.time() - start) * 1000)

        # --- Special gates (disruption, offline) ---
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate.startswith("DISRUPTION_OCCURS"):
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if self.disruption_executor is None:
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return StepResult(
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    verdict=Verdict.FAIL,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    gate_name=gate,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    error="DisruptionExecutor not configured (missing --disruption-mapping)",
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    duration_ms=(time.time() - start) * 1000,
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            disruption_key = t.label.strip()
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            success = self.disruption_executor.activate_disruption(disruption_key)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if not success:
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return StepResult(
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    verdict=Verdict.FAIL,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    gate_name=gate,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    error=f"Failed to activate disruption: {disruption_key}",
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    duration_ms=(time.time() - start) * 1000,
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.info(f"  DISRUPTION {t.label}")
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return StepResult(
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                verdict=None,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                gate_name=gate,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                duration_ms=(time.time() - start) * 1000,
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )

        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate == "UE1_OFFLINE":
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            set_offline = getattr(self.executor, "set_ue1_offline", None)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if set_offline:
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                set_offline(True)
                # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                logger.info("  UE1_OFFLINE fired — browser set offline via CDP")
            # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
            else:
                # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                logger.warning("  UE1_OFFLINE: executor has no set_ue1_offline()")
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return StepResult(
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                verdict=None,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                gate_name=gate,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                duration_ms=(time.time() - start) * 1000,
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )

        # --- Normal gates (with or without parameters) ---
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        l_dict = {}
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        concrete = {}
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if params:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            resolver = Resolver(self.sampler, self.em, self.g_dict)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            concrete = resolver.resolve_params(gate, params, l_dict)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if concrete is None:
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return StepResult(
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    verdict=Verdict.FAIL, gate_name=gate,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    error=f"Param resolution failed for {gate}",
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    duration_ms=(time.time() - start) * 1000
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
        concrete.update(self.g_dict)

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        spec = self.em.get("gates", {}).get(gate, {})
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        traversal_paths = spec.get("traversal_paths")

        # --- Bundled traversal for high‑level gates ---
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if traversal_paths:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            current_screen = getattr(self.executor, "_current_screen", "SCR_HOME")
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            path_actions = traversal_paths.get(current_screen)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if not path_actions:
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return StepResult(
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    verdict=Verdict.FAIL,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    gate_name=gate,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    error=f"No traversal actions for screen {current_screen}",
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    duration_ms=(time.time() - start) * 1000,
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
            # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
            for action in path_actions:
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if not self.executor.perform(action, concrete):
                    # Same dynamic FAIL-vs-INCONCLUSIVE classification as above.
                    _v = self._step_failure_verdict(action, gate)
                    _reason = self._inconclusive_reason(action, gate) or "not challenged"
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return StepResult(
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        verdict=_v,
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        gate_name=gate,
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        error=f"{f'INCONCLUSIVE ({_reason}): ' if _v == Verdict.INCONC else ''}Traversal action failed: {action}",
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        concrete_values=concrete,
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        duration_ms=(time.time() - start) * 1000,
                    # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                    )
                # The step succeeded — track entry into / exit from an external source.
                self._note_action(action)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            observe_spec = spec.get("observe")
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if observe_spec:
                # This calls an executor `wait` method from executors.py, which means the algorithm is watching the SUT for an expected concrete output.
                observed, timed_out = self.executor.wait(observe_spec, self.timeout)
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if timed_out:
                    # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                    return StepResult(
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        verdict=Verdict.FAIL,
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        gate_name=gate,
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        error=f"Observation timed out after traversal",
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        duration_ms=(time.time() - start) * 1000,
                    # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                    )
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if params:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    key = params[0][1]
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    self.g_dict[key] = str(observed)
                    # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                    logger.info(f"  Captured: {key} = {observed}")
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.info(f"  INPUT  {t.label} (traversal executed)")
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return StepResult(
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                verdict=None,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                gate_name=gate,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                concrete_values=concrete,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                captured={},
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                duration_ms=(time.time() - start) * 1000,
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )

        # --- Original handling for gates without traversal_paths ---
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        actions = spec.get("actions", [])
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        resolved_actions = []
        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for action in actions:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            ac = dict(action)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if "param" in ac:
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                ac["param"] = concrete.get(ac["param"], ac["param"])
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            resolved_actions.append(ac)

        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for action in resolved_actions:
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if not self.executor.perform(action, concrete):
                # Same dynamic FAIL-vs-INCONCLUSIVE classification as the typed and
                # traversal paths: a stimulus the tester could not apply produced no
                # observation, so it is not by itself a conformance verdict.
                _v = self._step_failure_verdict(action, gate)
                _reason = self._inconclusive_reason(action, gate) or "not challenged"
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return StepResult(
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    verdict=_v, gate_name=gate,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    error=f"{f'INCONCLUSIVE ({_reason}): ' if _v == Verdict.INCONC else ''}UI action failed: {action}",
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    concrete_values=concrete,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    duration_ms=(time.time() - start) * 1000
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
            # The step succeeded — track entry into / exit from an external source.
            self._note_action(action)

        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
        logger.debug(f"[RESOLVED] gate={gate} params={params} concrete={concrete}")
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        observe_spec = spec.get("observe")
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        captured = {}
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if observe_spec:
            # This calls an executor `wait` method from executors.py, which means the algorithm is watching the SUT for an expected concrete output.
            observed, timed_out = self.executor.wait(observe_spec, self.timeout)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if timed_out:
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return StepResult(
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    verdict=Verdict.FAIL, gate_name=gate,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    error=f"Quiescence at {gate}",
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    duration_ms=(time.time() - start) * 1000
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if observed is not None:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                key = params[0][1] if params else gate.lower()
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if key in self.g_dict:
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if str(observed) != str(self.g_dict[key]):
                        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                        return StepResult(
                            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                            verdict=Verdict.FAIL, gate_name=gate,
                            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                            error=f"Constraint violation at {gate}: "
                                  # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                                  f"expected '{self.g_dict[key]}', got '{observed}'",
                            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                            duration_ms=(time.time() - start) * 1000
                        # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                        )
                # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
                else:
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    self.g_dict[key] = str(observed)
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if key in ("sess_0", "sess_1", "sess_2", "sess_3"):
                        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                        self.g_dict["session_id"] = str(observed)
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    captured[key] = str(observed)
                    # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                    logger.info(f"  Captured: {key} = {observed}")

        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
        logger.info(f"  INPUT  {t.label}")
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return StepResult(
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            verdict=None, gate_name=gate,
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            concrete_values=concrete, captured=captured,
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            duration_ms=(time.time() - start) * 1000
        # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
        )
    
    
    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.

    def _seed_static_bindings(self) -> None:
        """Seed g_dict from concrete_domain.bindings, if the SUT declares any.

        {{TOKEN}} in a route is filled by _substitute from g_dict, which until
        now held ONLY values captured at runtime. A SUT whose routes carry
        ids known ahead of time (Moodle's course / cmid / user ids) therefore
        navigated to the LITERAL placeholder: the browser fetched
        "/mod/assign/view.php?id={{ASSIGN_CMID}}", Moodle rendered a page with
        no submission table, and the first wait_for failed. The verdict was
        FAIL for a run in which nothing had been tested.

        Static bindings are seeded FIRST so anything captured during the walk
        overwrites them -- a runtime value is always more specific than a
        declared default.
        """
        cd = (self.em or {}).get("concrete_domain") or {}
        bindings = cd.get("bindings") or {}
        for k, v in bindings.items():
            if v is None:
                continue
            self.g_dict.setdefault(str(k), str(v))
        if bindings:
            logger.info(f"  static bindings seeded: "
                        f"{', '.join(f'{k}={v}' for k, v in bindings.items())}")

    def _observe_transition(
        # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
        self, expected: dict[str, AUTTransition]
    # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
    ) -> tuple[StepResult, str | None]:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        start = time.time()

        # Each candidate output is waited for in turn, so the worst case here is
        # len(expected) * self.timeout. The wait used to be clamped to
        # min(self.timeout, 3) to keep that bounded, but the clamp meant --timeout
        # silently did nothing at these two sites: raising it to tell a slow SUT
        # from a silent one changed no behaviour at all. One meaning for the flag
        # is worth the slower worst case (FoodYou's AUTs offer 1-3 candidates).
        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for label, transition in expected.items():
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            gate, params = self.reader.parse_gate_and_params(label)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            spec = self.em.get("gates", {}).get(gate, {})

            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            observe_spec = spec.get("observe")
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if not observe_spec:
                # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                continue

            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            concrete = {}
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if params:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                l_dict = {}
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                resolver = Resolver(self.sampler, self.em, self.g_dict)
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                concrete = resolver.resolve_params(gate, params, l_dict) or {}
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            concrete.update(self.g_dict)

            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            url_template = spec.get("url")
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            nav_ok = False
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if url_template:
                # `try` starts a protected block: Python attempts the indented code and jumps to `except` if an error happens.
                try:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    inner_exec = getattr(self.executor, "inner", self.executor)
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    substitute = getattr(inner_exec, "_substitute", None)
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    url = substitute(url_template, concrete) if substitute else url_template
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    base_url = inner_exec.base_url
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    full_url = base_url + url
                    # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                    logger.debug(f"[OBSERVE] Trying {gate} at {full_url}")
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    inner_exec.driver.get(full_url)
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    wait_for = spec.get("wait_for")
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if wait_for:
                        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                        inner_exec._wait_for_element(wait_for, timeout=5)
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    nav_ok = True
                # `except` catches an error from the matching `try` block so the concretization run can report or recover instead of crashing immediately.
                except Exception:
                    # `pass` is an intentional no-op: it tells Python 'do nothing here' while keeping the syntax valid.
                    pass  # Fall through to direct executor.wait() for mock/simple executors

            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if url_template and not nav_ok:
                # Navigation unavailable (e.g., MockExecutor). Try a direct wait so
                # mock-mode tests can still exercise the graph walker.
                # `try` starts a protected block: Python attempts the indented code and jumps to `except` if an error happens.
                try:
                    # This calls an executor `wait` method from executors.py, which means the algorithm is watching the SUT for an expected concrete output.
                    observed, timed_out = self.executor.wait(observe_spec, self.timeout)
                # `except` catches an error from the matching `try` block so the concretization run can report or recover instead of crashing immediately.
                except Exception:
                    # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                    continue
            # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
            else:
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if url_template:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    actions = spec.get("actions", [])
                    # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
                    for action in actions:
                        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                        if not self.executor.perform(action, concrete):
                            # `continue` skips the rest of the current loop body and moves straight to the next loop round.
                            continue

                # This calls an executor `wait` method from executors.py, which means the algorithm is watching the SUT for an expected concrete output.
                observed, timed_out = self.executor.wait(observe_spec, self.timeout)

            # --- matching logic shared by both navigation modes -----------
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if not timed_out and observed is not None:
                # Determine which label in expected best matches the observed value
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                obs_lower = str(observed).strip().lower()
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                best_label = label
                # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
                for candidate in expected:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    cand_tokens = candidate.split()
                    # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
                    for tok in cand_tokens[1:]:
                        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                        if tok.startswith("!") or tok.startswith("?"):
                            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                            if tok[1:].lower() == obs_lower:
                                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                                best_label = candidate
                                # `break` exits the nearest loop immediately.
                                break

                # The literal comparison above only fires when the SUT renders the
                # abstract token itself ("COMMITTED"). A value like "2700 / 2000 kcal"
                # matches nothing, so best_label silently stayed at whichever
                # alternative came first — the tester picking its own output. When a
                # state offers several outputs, the OBSERVATION selects the branch:
                # ask the interpretation function which allowed value this reading
                # actually satisfies.
                best_label = self._select_by_observation(expected, observed, best_label)

                # Capture into g_dict using the best_label's params, not original
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                best_gate, best_params = self.reader.parse_gate_and_params(best_label)
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                captured = {}
                # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                if best_params:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    key = best_params[0][1]
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if key in self.g_dict:
                        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                        if obs_lower != str(self.g_dict[key]).lower():
                            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                            return (
                                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                                StepResult(
                                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                                    verdict=Verdict.FAIL, gate_name=best_gate,
                                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                                    error=f"Constraint violation at {best_gate}",
                                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                                    duration_ms=(time.time() - start) * 1000,
                                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                                ),
                                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                                None,
                            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                            )
                    # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
                    else:
                        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                        self.g_dict[key] = str(observed)
                        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                        captured[key] = str(observed)
                        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                        logger.info(f"  Captured: {key} = {observed}")
                # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
                else:
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    key = best_gate.lower()
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    self.g_dict[key] = str(observed)
                    # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                    captured[key] = str(observed)

                # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                logger.info(f"  OUTPUT {best_label}")
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return (
                    # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                    StepResult(
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        verdict=None, gate_name=best_gate,
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        concrete_values=concrete, captured=captured,
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        duration_ms=(time.time() - start) * 1000,
                    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                    ),
                    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                    best_label,
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )

        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        last_observed = self.g_dict.pop("_last_observed", None)
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if expected and last_observed is not None:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            obs_lower = str(last_observed).strip().lower()
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            best_label = next(iter(expected))
            # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
            for candidate in expected:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                cand_tokens = candidate.split()
                # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
                for tok in cand_tokens[1:]:
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if tok.startswith(("!", "?")) and tok[1:].lower().rstrip(";") == obs_lower:
                        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                        best_label = candidate
                        # `break` exits the nearest loop immediately.
                        break
            # Same blind spot as the primary matcher above: a rendered value never
            # equals the abstract token, so let the observation choose the branch.
            best_label = self._select_by_observation(expected, last_observed, best_label)
            # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
            best_gate, best_params = self.reader.parse_gate_and_params(best_label)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            captured = {}
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if best_params:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                key = best_params[-1][1]
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                self.g_dict[key] = str(last_observed)
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                captured[key] = str(last_observed)
            # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
            logger.info(f"  OUTPUT {best_label} (matched prior OBSERVE)")
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return (
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                StepResult(
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    verdict=None, gate_name=best_gate,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    concrete_values=dict(self.g_dict), captured=captured,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    duration_ms=(time.time() - start) * 1000,
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                ),
                # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                best_label,
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )
        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
        logger.warning(f"No expected output matched after {self.timeout}s")
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return (
            # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
            StepResult(
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                verdict=Verdict.FAIL, gate_name="OBSERVE",
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                error=f"No expected output matched",
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                duration_ms=(time.time() - start) * 1000,
            # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
            ),
            # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
            None,
        # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
        )
        
        
    # `def _map_transition_verdict` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> Verdict` documents the expected return type.
    def _map_transition_verdict(self, label: str) -> Verdict:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        gate = label.strip().split()[0].upper()
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate in ("PASS", ":PASS:"):
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return Verdict.PASS
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if gate in (":INCONCLUSIVE:",):
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return Verdict.INCONC
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return Verdict.FAIL

    # --------------------------------------------------------------
    # Flat step execution (unchanged from v2)
    # --------------------------------------------------------------
    # `def _execute_step_flat` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> StepResult` documents the expected return type.
    def _execute_step_flat(self, step: ParsedStep) -> StepResult:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        start = time.time()
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if step.gate_name in self.VMAP:
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return StepResult(
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                verdict=self.VMAP[step.gate_name],
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                gate_name=step.gate_name,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                duration_ms=(time.time() - start) * 1000
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        r = self._execute_unified_flat(step)
        # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
        r.duration_ms = (time.time() - start) * 1000
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return r

    # `def _execute_unified_flat` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called and `-> StepResult` documents the expected return type.
    def _execute_unified_flat(self, step: ParsedStep) -> StepResult:
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        start = time.time()
        
        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if step.gate_name.startswith("DISRUPTION_OCCURS"):
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if self.disruption_executor is None:
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return StepResult(
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    verdict=Verdict.FAIL,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    gate_name=step.gate_name,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    error="DisruptionExecutor not configured (missing --disruption-mapping)",
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    duration_ms=(time.time() - start) * 1000,
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            disruption_key = step.gate_name  # or extract from params
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            success = self.disruption_executor.activate_disruption(disruption_key)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if not success:
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return StepResult(
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    verdict=Verdict.FAIL,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    gate_name=step.gate_name,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    error=f"Failed to activate disruption: {disruption_key}",
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    duration_ms=(time.time() - start) * 1000,
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return StepResult(
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                verdict=None,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                gate_name=step.gate_name,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                duration_ms=(time.time() - start) * 1000,
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )
    
    # … rest of existing _execute_unified_flat unchanged …
                    
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        spec         = self.em.get(step.gate_name, {})
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        actions      = spec.get("actions", [])
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        observe_spec = spec.get("observe")
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        concrete     = {}
        # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
        l_dict       = {}

        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if step.params:
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            resolver = Resolver(self.sampler, self.em, self.g_dict)
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            concrete = resolver.resolve_params(
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                step.gate_name, step.params, l_dict
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if concrete is None:
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return StepResult(
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    verdict=Verdict.FAIL, gate_name=step.gate_name,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    error=f"Param resolution failed for {step.gate_name}",
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    duration_ms=(time.time() - start) * 1000
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )

        # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
        for action in actions:
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if not self.executor.perform(action, concrete):
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return StepResult(
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    verdict=Verdict.FAIL, gate_name=step.gate_name,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    error=f"UI action failed: {action}",
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    concrete_values=concrete,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    duration_ms=(time.time() - start) * 1000,
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )

        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
        if observe_spec:
            # This calls an executor `wait` method from executors.py, which means the algorithm is watching the SUT for an expected concrete output.
            observed, timed_out = self.executor.wait(observe_spec, self.timeout)
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if timed_out:
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return StepResult(
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    verdict=Verdict.FAIL, gate_name=step.gate_name,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    error=f"Quiescence: {step.gate_name} timed out after {self.timeout}s",
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    duration_ms=(time.time() - start) * 1000,
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if observed is None:
                # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                return StepResult(
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    verdict=Verdict.FAIL, gate_name=step.gate_name,
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    error=f"Unexpected output at {step.gate_name}",
                    # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                    duration_ms=(time.time() - start) * 1000,
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                )

            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            captured = {}
            # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
            if step.params:
                # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
                for pname, aval in step.params:
                    # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                    if aval in self.g_dict:
                        # `if` asks a yes/no question at runtime; when the condition before the colon is true, Python runs the indented block underneath.
                        if str(observed) != str(self.g_dict[aval]):
                            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
                            return StepResult(
                                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                                verdict=Verdict.FAIL, gate_name=step.gate_name,
                                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                                error=f"Constraint violation at {step.gate_name}: "
                                      # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                                      f"expected '{self.g_dict[aval]}', "
                                      # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                                      f"observed '{observed}'",
                                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                                duration_ms=(time.time() - start) * 1000,
                            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                            )
                    # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
                    else:
                        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                        self.g_dict[aval] = str(observed)
                        # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                        captured[aval]    = str(observed)
                        # This logging call records what the concretization code is doing, which helps you debug the story of a test run without changing behavior.
                        logger.info(f"  Captured: {aval} = {observed}")
            # `else` is the fallback branch; Python runs the indented block under it when the previous conditions in the same chain were false.
            else:
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                key = step.gate_name.lower()
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                self.g_dict[key] = str(observed)
                # This line calls a function or method: Python evaluates the values inside the parentheses and passes them into the named operation.
                captured[key]    = str(observed)

            # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
            return StepResult(
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                verdict=None, gate_name=step.gate_name,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                concrete_values=concrete, captured=captured,
                # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
                duration_ms=(time.time() - start) * 1000,
            # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
            )

        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return StepResult(
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            verdict=None, gate_name=step.gate_name,
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            concrete_values=concrete,
            # This assignment stores the value on the right side into the name on the left side, so later lines can reuse it without recomputing it.
            duration_ms=(time.time() - start) * 1000,
        # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
        )

    # `def get_report` creates a reusable function/method; `self` is the current object, commas separate parameters, and the colon starts the indented instructions that run when it is called.
    def get_report(self):
        # `return` immediately hands a value back to the caller; in this code that often means giving the algorithm a verdict, a parsed object, or a success/failure result.
        return {
            # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
            "steps": len(self.execution_log),
            # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
            "g_dict_final": dict(self.g_dict),
            # This line is part of a structured Python expression; the colon usually separates a key from a value in a dictionary or starts an indented block when used after a statement.
            "execution_log": [
                # This line participates in the concretization flow; read it as one small step in preparing data, moving through the AUT graph, translating LNT UI instructions, or driving the concrete executor.
                {
                    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                    "gate": r.gate_name,
                    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                    "verdict": r.verdict.name if r.verdict else None,
                    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                    "concrete_values": r.concrete_values,
                    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                    "captured": r.captured,
                    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                    "error": r.error,
                    # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
                    "duration_ms": round(r.duration_ms, 2),
                # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
                }
                # `for` repeats the indented block once for each item in the collection, binding the current item to the loop variable named before `in`.
                for r in self.execution_log
            # The trailing comma means this item belongs to a larger list, dictionary, tuple, function call, or argument list that continues across multiple lines.
            ],
        # This closing bracket ends the list, dictionary, tuple, or function-call structure opened above.
        }
