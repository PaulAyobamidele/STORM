"""
quantity_resolver.py
--------------------
Bridge between the DISCRETIZED quantities carried in the AUT/model and the REAL
numbers the SUT shows on screen.

The model abstracts two numeric quantities:

  * Calorie   — an OPAQUE per-food token (kcal_apple, ...). It is CAPTURED at
                FOOD_INFO: the tester reads the real number and binds the token,
                then checks consistency (same food -> same value). We just need
                to pull the number out of e.g. "7 kcal".

  * DailyTotal — a saturating BUCKET (EMPTY, LOW, MODERATE, HIGH, OVER) captured
                at CONFIRM_TOTAL. The diary shows "N / GOAL kcal" (e.g.
                "7 / 2000 kcal"); the oracle must map that real N to the bucket
                the AUT expects. Key domain rule: EMPTY means *nothing logged*
                (N == 0), so any positive N is at least LOW — a midpoint/nearest
                classifier would wrongly bucket 7 as EMPTY.

This module is deliberately standalone (no framework imports) so it can be unit
run: `python3 framework/concretization/quantity_resolver.py`. Wire `matches_total`
into the CONFIRM_TOTAL oracle and `parse_calorie` into the FOOD_INFO capture.

The bucket boundaries are expressed as fractions of the daily GOAL, and the goal
is read straight off the screen ("N / GOAL kcal"), so nothing is hard-coded to
2000. Override the fractions (or the goal fallback) from type_description.yml if
a SUT uses a different scale.

DISCRETIZATION (resolved 2026-08-11). The model bumps DailyTotal one rung *per
committed entry* (1 entry -> LOW, 2 -> MODERATE, ...), while this resolver
originally bucketed by *kcal fraction of the goal*. Those two agreed only while
every test case logged at most one entry; the first multi-entry journey made them
disagree (2 x 155 kcal = rung 2 = MODERATE by the model, but 15.5% of a 2000 kcal
goal = LOW by fraction) and produced a FAIL that said nothing about the SUT.

The fix is SERVINGS mode: set `unit` to the kcal of one committed entry and
classify by rung = round(current / unit), which is exactly `bump` applied that
many times from EMPTY. This does not tune thresholds to fit data -- it makes the
concrete classifier compute the model's own function. Fraction mode remains the
default for SUTs whose totals really are goal-relative.

LIMITATION: servings mode assumes every entry contributes the SAME energy, i.e. a
fixed reference portion of a single food under test (FoodYou: 100 g of defaultF).
Retarget `unit` whenever that food changes, and prefer naming the food in
type_description.yml over hard-coding the number.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field

# Ordered smallest -> largest. EMPTY is the "nothing logged" bucket (N == 0);
# OVER is "at or beyond the goal". The middle rungs split (0, goal) by fraction.
DEFAULT_BUCKET_ORDER = ["EMPTY", "LOW", "MODERATE", "HIGH", "OVER"]

# Upper edge (inclusive) of each positive sub-goal bucket, as a fraction of GOAL.
# LOW <= 1/3 goal, MODERATE <= 2/3 goal, HIGH < goal, OVER >= goal.
DEFAULT_FRACTIONS = {"LOW": 1.0 / 3.0, "MODERATE": 2.0 / 3.0, "HIGH": 1.0}

# Fallback goal if the screen shows a bare "N kcal" with no "/ GOAL".
DEFAULT_GOAL = 2000.0

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def parse_numbers(text: str) -> list[float]:
    """Every number in a string, in order. '7 / 2000 kcal' -> [7.0, 2000.0]."""
    return [float(x) for x in _NUM_RE.findall(text or "")]


def parse_calorie(text: str) -> float | None:
    """The single kcal figure from a FOOD_INFO / el_calories observation.
    '7 kcal' -> 7.0 ; 'Energy  52 kcal' -> 52.0 ; '' -> None."""
    nums = parse_numbers(text)
    return nums[0] if nums else None


def parse_total(text: str) -> tuple[float | None, float | None]:
    """Return (current, goal) from a daily-total observation.

    "7 / 2000 kcal"      -> (7.0, 2000.0)     # progress / goal
    "1993 calories left" -> (None, None)      # only the remaining; goal unknown here
    "7 kcal"             -> (7.0, None)        # bare current
    ""                   -> (None, None)
    """
    nums = parse_numbers(text)
    if not nums:
        return (None, None)
    if len(nums) >= 2 and ("/" in text):
        return (nums[0], nums[1])          # "current / goal"
    return (nums[0], None)


@dataclass
class QuantityResolver:
    """Classify observed reals into abstract buckets, and vice versa.

    goal        : fallback daily goal when the screen doesn't carry "/ GOAL".
    fractions   : upper-edge fraction of goal for each positive bucket.
    bucket_order: smallest -> largest bucket names (EMPTY first, OVER last).
    """
    goal: float = DEFAULT_GOAL
    fractions: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_FRACTIONS))
    bucket_order: list[str] = field(default_factory=lambda: list(DEFAULT_BUCKET_ORDER))
    # kcal contributed by ONE committed entry. When set, classification counts
    # servings instead of binning kcal by fraction of goal -- see classify_total.
    unit: float | None = None

    # ---- classify a real number into a bucket ----------------------------
    def classify_total(self, current: float | None, goal: float | None = None) -> str | None:
        """Map an observed kcal total to its DailyTotal bucket.

        SERVINGS mode (self.unit set) -- the inverse of `bump` in
        foodyou_types.lnt: the model advances DailyTotal one rung per committed
        entry, and every entry is one reference portion of the food under test,
        so rung == round(current / unit), saturating at the last bucket. Use this
        whenever the model's bump counts entries, or multi-entry journeys
        disagree with the model (2 x 155 kcal is rung 2 = MODERATE, but only
        15.5% of a 2000 kcal goal = LOW by fraction).

        FRACTION mode (default) -- bin kcal as a fraction of the goal:
        EMPTY iff current == 0; OVER iff current >= goal; else LOW/MODERATE/HIGH.
        """
        if current is None:
            return None
        g = goal if (goal and goal > 0) else self.goal
        empty, *mids, over = self.bucket_order      # EMPTY ... OVER
        if current <= 0:
            return empty

        if self.unit and self.unit > 0:
            # round(), not floor(): the displayed total is the SUT's own sum, so
            # a rounding cent on either side must not drop a rung.
            rung = int(round(current / self.unit))
            if rung <= 0:                # positive but under half a portion --
                return mids[0] if mids else over   # still "something logged"
            return self.bucket_order[min(rung, len(self.bucket_order) - 1)]

        if current >= g:
            return over
        for name in mids:                            # LOW, MODERATE, HIGH ...
            edge = self.fractions.get(name)
            if edge is not None and current <= edge * g:
                return name
        return mids[-1] if mids else over            # just under the goal -> top mid (HIGH)

    # ---- the oracle the executor calls at CONFIRM_TOTAL ------------------
    def matches_total(self, expected_bucket: str, observed_text: str) -> bool:
        """True iff the observed 'N / GOAL kcal' classifies to expected_bucket."""
        current, goal = parse_total(observed_text)
        got = self.classify_total(current, goal)
        return got is not None and got.upper() == (expected_bucket or "").upper()

    # ---- inverse: a representative real number for a bucket --------------
    def representative(self, bucket: str, goal: float | None = None) -> float:
        """A concrete kcal value that sits inside `bucket` (for reporting / input
        generation). Midpoint of the bucket's [lo, hi) range."""
        g = goal if (goal and goal > 0) else self.goal
        empty, *mids, over = self.bucket_order
        b = (bucket or "").upper()
        if b == empty:
            return 0.0
        if self.unit and self.unit > 0:
            # Exact rung value, so representative() round-trips classify_total().
            try:
                return self.bucket_order.index(b) * self.unit
            except ValueError:
                return self.unit
        if b == over:
            return g * 1.1
        lo = 0.0
        for name in mids:
            hi = self.fractions.get(name, 1.0) * g
            if b == name:
                return (lo + hi) / 2.0
            lo = hi
        return g / 2.0

    @classmethod
    def from_type_description(cls, type_desc: dict) -> "QuantityResolver":
        """Build from a parsed type_description.yml. Reads DailyTotal.bucket order
        if present; keeps the fraction defaults unless the yaml overrides them via
        an optional `bucket_fractions` map.

        Servings mode is selected by either
            <bucket_type>.bucket_unit: 155            # units per rung, explicit
        or, preferred, a reference to another type's abstract value, so the
        oracle stays in step with the fixture instead of duplicating the number:
            <bucket_type>.bucket_unit_from:
              type:  Calorie                          # any type in this yaml
              value: food_egg                         # a key in its abstract_values
        Both the bucket type and the referenced type are named BY THE YAML -- no
        SUT vocabulary is hard-coded here.
        """
        r = cls()
        dt = (type_desc or {}).get("DailyTotal", {})
        vals = dt.get("values")
        if vals:
            r.bucket_order = list(vals)
        fr = dt.get("bucket_fractions")
        if isinstance(fr, dict):
            r.fractions.update({k: float(v) for k, v in fr.items()})
        goal = dt.get("goal")
        if goal:
            r.goal = float(goal)

        unit = dt.get("bucket_unit")
        if unit is None:
            ref = dt.get("bucket_unit_from")
            if isinstance(ref, dict):
                src_type, src_val = ref.get("type"), ref.get("value")
                vals = ((type_desc or {}).get(src_type, {}) or {}).get("abstract_values", {})
                unit = vals.get(src_val)
                if unit is None:
                    # Failing loudly matters: a silent fallback to fraction
                    # bucketing is what produced a FAIL that blamed the SUT for a
                    # disagreement between the two discretizations.
                    raise ValueError(
                        f"bucket_unit_from {{type: {src_type!r}, value: {src_val!r}}} "
                        f"does not resolve -- no such key in {src_type!r}.abstract_values.")
        if unit is not None:
            r.unit = float(unit)
        return r


# ---------------------------------------------------------------------------
# Self-test / demo:  python3 framework/concretization/quantity_resolver.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    r = QuantityResolver()
    cases = [
        # (observed on screen, expected bucket)
        ("0 / 2000 kcal",    "EMPTY"),    # nothing logged / rolled-back write
        ("7 / 2000 kcal",    "LOW"),      # one TestApple -> LOW (NOT EMPTY)
        ("300 / 2000 kcal",  "LOW"),
        ("900 / 2000 kcal",  "MODERATE"),
        ("1500 / 2000 kcal", "HIGH"),
        ("2000 / 2000 kcal", "OVER"),
        ("2200 / 2000 kcal", "OVER"),
    ]
    ok = True
    print("FRACTION mode (goal-relative)")
    print(f"{'observed':>18}  {'-> bucket':<10} expected  result")
    for text, expected in cases:
        got = r.matches_total(expected, text)
        cur, goal = parse_total(text)
        bucket = r.classify_total(cur, goal)
        ok &= got
        print(f"{text:>18}  {bucket:<10} {expected:<8}  {'PASS' if got else 'FAIL'}")

    # SERVINGS mode: one rung per committed entry (FoodYou, TestEgg 155 kcal).
    # The 310 case is the real 2026-08-11 failure -- LOW by fraction, MODERATE
    # by the model's bump.
    s = QuantityResolver(unit=155.0)
    scases = [
        ("0 / 2000 kcal",   "EMPTY"),      # nothing logged / rolled-back write
        ("155 / 2000 kcal", "LOW"),        # 1 TestEgg
        ("310 / 2000 kcal", "MODERATE"),   # 2 -- was LOW under fraction bucketing
        ("465 / 2000 kcal", "HIGH"),       # 3
        ("620 / 2000 kcal", "OVER"),       # 4, saturating
        ("930 / 2000 kcal", "OVER"),       # 6 -- stays OVER, matching bump
    ]
    print("\nSERVINGS mode (unit = 155 kcal / entry)")
    print(f"{'observed':>18}  {'-> bucket':<10} expected  result")
    for text, expected in scases:
        got = s.matches_total(expected, text)
        cur, goal = parse_total(text)
        bucket = s.classify_total(cur, goal)
        ok &= got
        print(f"{text:>18}  {bucket:<10} {expected:<8}  {'PASS' if got else 'FAIL'}")

    # representative() must round-trip back through classify_total().
    for b in s.bucket_order:
        rt = s.classify_total(s.representative(b))
        ok &= (rt == b)
        print(f"round-trip {b:<9} -> {s.representative(b):>6.0f} kcal -> {rt:<9}"
              f"  {'PASS' if rt == b else 'FAIL'}")

    print("\ncalorie parse:", parse_calorie("7 kcal"), parse_calorie("Energy  52 kcal"))
    raise SystemExit(0 if ok else 1)
