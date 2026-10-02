"""
observation_oracle.py
---------------------
The checkpoint oracle that reads its vocabulary from type_description.yml
instead of from a case study.

WHY IT EXISTS. On a structural walk the concrete steps do the observing
(OBSERVE !EL_TOTAL_SPENDING -> "$40.00") and the abstract gate that follows
(CONFIRM !COMMITTED !S1 !LOGGED !EXP_C) is a checkpoint the walker advances
through. Where a state offers a single such gate the walker used to advance
without comparing what it had read against what the label claims, unless the
gate was one of the four FoodYou gates the strict oracles are keyed on. For any
other system the label's offers were never checked, and a PASS said only that
every element the SI waits for appeared. The first Spliit run passed that way:
"$40.00" and "dinner c" were captured, S1 and LOGGED were never looked at.

HOW A SYSTEM OPTS IN. A type in type_description.yml declares

    capture_at: CONFIRM          # the gate whose label carries it
    role: band | enum | names    # how an observation is read into it
    observed_from: el_x          # optional; the element(s) the value is read
                                 # from, one key or a list; absent = any
                                 # observation since the previous checkpoint

and the oracle classifies the type from the observations, then compares the
result with the offer the label carries for that type. A type without `role:`
is left alone, so systems that predate this hook keep their behaviour.

ROLES
  band   numeric rungs, the inverse of a `bump` in the model: the first number
         in the observation is divided by the unit (`bucket_unit`, or
         `bucket_unit_from: {type, value}` resolved through that type's
         abstract_values), rung = round(n / unit), saturating at the last
         value; n <= 0 is the first value; a positive n under half a unit is
         still the second value ("something was written").
  enum   the value whose abstract_values rendering occurs in the observation
         (case-insensitive, whitespace-collapsed). An empty rendering never
         matches, so "absent" cannot be encoded this way; use `names`.
  names  relational: `names: {type: T, when_named: X, when_not: Y}`. The
         classification is X when an observation contains the rendering of
         the label's OWN offer of type T, else Y. This is how "the log names
         the row just written" is stated without hard-coding a title.

         Optional `and_phrase: {VALUE: "literal text"}`, checked BEFORE
         when_named/when_not: VALUE is returned when the observation
         contains BOTH the title (T's rendering) AND that literal text
         together. For a log that renders more than one VERB against the
         same title -- "created by" vs "deleted by" -- where when_named
         alone cannot tell them apart, since the title occurs in both. A
         config that declares no and_phrase is unaffected; every existing
         use of `names` still checks the title alone.

WHAT IT RETURNS. `check` yields one Mismatch per declared type whose
classification disagrees with the label, and one Unclassified per declared
type it could not read (no number, no rendering found). A mismatch is a
counter-example candidate; an unclassified type is a warning, never a
verdict, because the tester failing to read a value is not the SUT failing.

Standalone, no framework imports:  python3 framework/concretization/observation_oracle.py
"""

from __future__ import annotations
import re
from dataclasses import dataclass

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_THOUSANDS_RE = re.compile(r"(?<=\d),(?=\d{3}\b)")


def _norm(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def first_number(text) -> float | None:
    """The first number in a rendered value. '$1,200.00' -> 1200.0; '' -> None."""
    m = _NUM_RE.search(_THOUSANDS_RE.sub("", str(text or "")))
    return float(m.group()) if m else None


@dataclass
class Observation:
    element: str          # the el_* key the value was read from, lower-case
    text: str             # what the executor returned


@dataclass
class Mismatch:
    type_name: str
    expected: str         # the label's offer
    got: str              # what the observation classifies as
    text: str             # the observation that decided it


@dataclass
class Unclassified:
    type_name: str
    expected: str
    reason: str


class ObservationOracle:
    def __init__(self, td: dict):
        self.td = {k: v for k, v in (td or {}).items() if isinstance(v, dict)}
        # abstract value (upper) -> type name, for reading a label's offers
        self._type_of: dict[str, str] = {}
        for tname, spec in self.td.items():
            for v in spec.get("values") or []:
                self._type_of.setdefault(str(v).upper(), tname)

    @classmethod
    def from_type_description(cls, td: dict) -> "ObservationOracle":
        return cls(td)

    # ---- what a gate carries ----------------------------------------------
    def declared_at(self, gate: str) -> list[str]:
        """Types with a `role:` whose capture_at is this gate."""
        g = (gate or "").split()[0].rstrip(";").upper()

        def gates(s):
            # One gate, or a list: a type the model reports at more than one
            # gate (a submission version shown to the student AND to the grader).
            c = s.get("capture_at", "")
            return {str(x).upper() for x in (c if isinstance(c, list) else [c])}

        return [t for t, s in self.td.items() if s.get("role") and g in gates(s)]

    def offers(self, label: str) -> dict[str, str]:
        """type name -> the offer (upper) the label carries for it."""
        toks = label.replace("!", " ").split()[1:]
        out: dict[str, str] = {}
        for t in toks:
            tn = self._type_of.get(t.upper())
            if tn and tn not in out:
                out[tn] = t.upper()
        return out

    # ---- reading one type from the observations ---------------------------
    def _rendering(self, tname: str, value: str) -> str | None:
        av = (self.td.get(tname) or {}).get("abstract_values") or {}
        for k, v in av.items():
            if str(k).upper() == str(value).upper():
                return None if v in (None, "captured_at_runtime") else str(v)
        return None

    def _values(self, tname: str) -> list[str]:
        return [str(v).upper() for v in (self.td.get(tname) or {}).get("values") or []]

    def _unit(self, tname: str) -> float | None:
        spec = self.td.get(tname) or {}
        unit = spec.get("bucket_unit")
        if unit is None:
            ref = spec.get("bucket_unit_from")
            if isinstance(ref, dict):
                unit = self._rendering(ref.get("type", ""), ref.get("value", ""))
                if unit is None:
                    raise ValueError(
                        f"{tname}.bucket_unit_from {ref} does not resolve -- no such "
                        f"key in {ref.get('type')!r}.abstract_values")
        return first_number(unit) if unit is not None else None

    def _scope(self, tname: str, observations: list[Observation]) -> list[Observation]:
        src = (self.td.get(tname) or {}).get("observed_from")
        if not src:
            return list(observations)
        keys = {str(s).lower() for s in (src if isinstance(src, list) else [src])}
        return [o for o in observations if o.element.lower() in keys]

    def classify(self, tname: str, label_offers: dict[str, str],
                 observations: list[Observation]):
        """-> (value | None, text | None, reason). value None = unclassified."""
        spec = self.td.get(tname) or {}
        role = str(spec.get("role", "")).lower()
        values = self._values(tname)
        scope = self._scope(tname, observations)
        if not scope:
            return None, None, "no observation in scope"

        if role == "band":
            unit = self._unit(tname)
            if not unit or unit <= 0:
                return None, None, "no positive unit (bucket_unit / bucket_unit_from)"
            for o in scope:
                n = first_number(o.text)
                if n is None:
                    continue
                if n <= 0:
                    return values[0], o.text, ""
                rung = int(round(n / unit))
                rung = max(rung, 1)
                return values[min(rung, len(values) - 1)], o.text, ""
            return None, None, "no number in the observation"

        if role == "enum":
            for o in scope:
                hits = [v for v in values
                        if (r := self._rendering(tname, v)) and _norm(r) in _norm(o.text)]
                if len(hits) == 1:
                    return hits[0], o.text, ""
                if len(hits) > 1:
                    # prefer the longest rendering, if it is unique
                    ranked = sorted(hits, key=lambda v: -len(self._rendering(tname, v)))
                    if len(self._rendering(tname, ranked[0])) > len(self._rendering(tname, ranked[1])):
                        return ranked[0], o.text, ""
                    return None, o.text, f"ambiguous: {', '.join(hits)}"
            return None, None, "no rendering found in the observation"

        if role == "names":
            cfg = spec.get("names") or {}
            of_type, x, y = cfg.get("type"), cfg.get("when_named"), cfg.get("when_not")
            if not (of_type and x and y):
                return None, None, "names: needs type, when_named, when_not"
            offer = label_offers.get(of_type)
            if offer is None:
                return None, None, f"label carries no {of_type}"
            r = self._rendering(of_type, offer)
            if not r:
                return None, None, f"{of_type}.{offer} has no rendering"
            texts = "; ".join(o.text for o in scope)
            # The title and the phrase must occur in the SAME entry (line):
            # a list holding "Dinner C created by" and "Groceries A deleted by"
            # does not say Dinner C was deleted.
            lines = [ln for o in scope for ln in str(o.text).splitlines()]
            for value, phrase in (cfg.get("and_phrase") or {}).items():
                if any(_norm(r) in _norm(ln) and _norm(phrase) in _norm(ln) for ln in lines):
                    return str(value).upper(), texts, ""
            named = any(_norm(r) in _norm(o.text) for o in scope)
            return (str(x).upper() if named else str(y).upper(), texts, "")

        return None, None, f"unknown role {role!r}"

    # ---- the two questions the walker asks --------------------------------
    def check(self, gate: str, label: str, observations: list[Observation]):
        """Compare every declared type at this gate with the label's offer."""
        mismatches: list[Mismatch] = []
        unclassified: list[Unclassified] = []
        offers = self.offers(label)
        for tname in self.declared_at(gate):
            expected = offers.get(tname)
            if expected is None:
                continue            # the label does not carry this type
            got, text, reason = self.classify(tname, offers, observations)
            if got is None:
                unclassified.append(Unclassified(tname, expected, reason))
            elif got != expected:
                mismatches.append(Mismatch(tname, expected, got, text or ""))
        return mismatches, unclassified

    def fits(self, gate: str, labels: list[str], observations: list[Observation]) -> list[str]:
        """The labels the observations are consistent with (no mismatch on any
        declared type). Used where a state allows several outputs."""
        out = []
        for lbl in labels:
            mm, _ = self.check(gate, lbl, observations)
            if not mm:
                out.append(lbl)
        return out


# ---------------------------------------------------------------------------
# Self-test:  python3 framework/concretization/observation_oracle.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    td = {
        "ExpenseId": {"values": ["exp_a", "exp_b", "exp_c"],
                      "abstract_values": {"exp_a": "Groceries A", "exp_b": "Bus pass B",
                                          "exp_c": "Dinner C"}},
        "Amount": {"abstract_values": {"exp_a": "12.00", "exp_b": "25.00", "exp_c": "40.00"}},
        "SpendBand": {"values": ["S0", "S1", "S2", "S3", "S_MORE"], "capture_at": "CONFIRM",
                      "role": "band", "observed_from": "el_total_spending",
                      "bucket_unit_from": {"type": "Amount", "value": "exp_c"}},
        "LogState": {"values": ["LOGGED", "UNLOGGED", "DELETED"], "capture_at": "CONFIRM",
                     "role": "names", "observed_from": "el_activity_latest",
                     "names": {"type": "ExpenseId", "when_named": "LOGGED",
                               "when_not": "UNLOGGED",
                               "and_phrase": {"DELETED": "deleted by"}}},
        "WriteStatus": {"values": ["COMMITTED", "ROLLED_BACK", "REJECTED"],
                        "capture_at": "CONFIRM"},        # no role: not read
        "Status": {"values": ["DRAFT", "SUBMITTED"], "capture_at": "SUBMISSION_STATUS",
                   "role": "enum",
                   "abstract_values": {"DRAFT": "Draft (not submitted)",
                                       "SUBMITTED": "Submitted for grading"}},
    }
    o = ObservationOracle(td)
    L = "CONFIRM !COMMITTED !S1 !LOGGED !EXP_C"
    ok = True

    def case(name, gate, label, obs, want_mm, want_uc=0):
        global ok
        mm, uc = o.check(gate, label, obs)
        good = ([(m.type_name, m.got) for m in mm] == want_mm) and (len(uc) == want_uc)
        ok &= good
        print(f"{'PASS' if good else 'FAIL'}  {name}: mismatches={[(m.type_name, m.expected, m.got) for m in mm]}"
              f" unclassified={[(u.type_name, u.reason) for u in uc]}")

    ob = lambda e, t: Observation(e, t)
    case("nominal read", "CONFIRM", L,
         [ob("el_total_spending", "$40.00"), ob("el_activity_latest", "“dinner c”")], [])
    case("stale total", "CONFIRM", L,
         [ob("el_total_spending", "$0.00"), ob("el_activity_latest", "“dinner c”")],
         [("SpendBand", "S0")])
    case("log names another row", "CONFIRM", L,
         [ob("el_total_spending", "$40.00"), ob("el_activity_latest", "“groceries a”")],
         [("LogState", "UNLOGGED")])
    case("rolled back but logged (O5)", "CONFIRM", "CONFIRM !ROLLED_BACK !S0 !UNLOGGED !EXP_C",
         [ob("el_total_spending", "$0.00"), ob("el_activity_latest", "“dinner c”")],
         [("LogState", "LOGGED")])
    case("two rows, thousands separator", "CONFIRM", "CONFIRM !COMMITTED !S2 !LOGGED !EXP_C",
         [ob("el_total_spending", "$80.00"), ob("el_activity_latest", "“dinner c”")], [])
    case("saturates", "CONFIRM", "CONFIRM !COMMITTED !S_MORE !LOGGED !EXP_C",
         [ob("el_total_spending", "$1,200.00"), ob("el_activity_latest", "“dinner c”")], [])
    case("no total read", "CONFIRM", L,
         [ob("el_activity_latest", "“dinner c”")], [], want_uc=1)
    case("enum role", "SUBMISSION_STATUS", "SUBMISSION_STATUS !SUBMITTED",
         [ob("el_status", "  Submitted for grading \n")], [])
    case("enum role wrong", "SUBMISSION_STATUS", "SUBMISSION_STATUS !SUBMITTED",
         [ob("el_status", "Draft (not submitted)")], [("Status", "DRAFT")])
    case("other gate: nothing declared", "ADD", "ADD !JOHN !EXP_C !VALID !ONCE",
         [ob("el_total_spending", "$40.00")], [])
    case("clean delete, and_phrase distinguishes the verb", "CONFIRM",
         "CONFIRM !COMMITTED !S0 !DELETED !EXP_C",
         [ob("el_total_spending", "$0.00"),
          ob("el_activity_latest", "“Dinner C” deleted by someone")], [])
    case("delete claimed but the old create entry is still on screen", "CONFIRM",
         "CONFIRM !COMMITTED !S0 !DELETED !EXP_C",
         [ob("el_total_spending", "$0.00"),
          ob("el_activity_latest", "“dinner c” created by someone")],
         [("LogState", "LOGGED")])
    case("another row deleted, this one created: still LOGGED", "CONFIRM",
         "CONFIRM !COMMITTED !S2 !LOGGED !EXP_C",
         [ob("el_total_spending", "$80.00"),
          ob("el_activity_latest", "today\n10:46 pm\nexpense “dinner c” created by someone.\n"
                                   "10:46 pm\nexpense “groceries a” deleted by someone.")], [])
    case("ADD context unaffected by and_phrase (no regression)", "CONFIRM", L,
         [ob("el_total_spending", "$40.00"), ob("el_activity_latest", "“dinner c”")], [])

    fits = o.fits("CONFIRM", [L, "CONFIRM !COMMITTED !S2 !LOGGED !EXP_C"],
                  [ob("el_total_spending", "$80.00"), ob("el_activity_latest", "“dinner c”")])
    good = fits == ["CONFIRM !COMMITTED !S2 !LOGGED !EXP_C"]
    ok &= good
    print(f"{'PASS' if good else 'FAIL'}  fits picks the S2 label: {fits}")
    raise SystemExit(0 if ok else 1)
