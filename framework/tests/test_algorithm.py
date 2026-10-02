"""
test_algorithm.py
Comprehensive tests for the concretization algorithm.

Tests cover:
- Happy path (PASS verdict)
- Fail on unexpected output
- Fail on quiescence (timeout)
- Constraint violation (wrong session ID)
- System-generated value capture and reuse
- Tester-generated value sampling and reuse
- Gates with no parameters
- Empty ATC
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from concretization.algorithm import (
    ConcretizationAlgorithm, BCGReader, Sampler,
    Verdict, Direction, ParsedStep, AUTGraph, AUTTransition,
)
from concretization.executors import MockExecutor


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────

TYPE_DESCRIPTION = {
    "Username": {
        "base": "String",
        "origin": "tester_generated",
        "regex": "[a-z]{5}@a\\.c",
        "abstract_values": {
            "name1_at_a_c": "alice@a.c",
            "name2_at_b_c": "bob@b.c",
        },
    },
    "Password": {
        "base": "String",
        "origin": "tester_generated",
        "abstract_values": {
            "pass_1": "Secure!01",
            "pass_2": "Health@99",
        },
    },
    "SessionId": {
        "base": "String",
        "origin": "system_generated",
        "capture_at": "SUBMIT_CHECKIN",
        "abstract_values": {
            "sess_0": "captured_at_runtime",
        },
    },
    "MessageContent": {
        "base": "String",
        "origin": "tester_generated",
        "abstract_values": {
            "m1": "Patient vitals reviewed.",
            "m2": "Urgent: critical condition.",
        },
    },
}

ELEMENT_MAP = {
    "REGISTER": {
        "param_types": {"param_0": "Username", "param_1": "Password"},
        "actions": [
            {"type": "navigate", "page": "/register"},
            {"gate": "REGISTER", "action": "type", "element": "#username", "value": "param_0"},
            {"gate": "REGISTER", "action": "type", "element": "#password", "value": "param_1"},
            {"gate": "REGISTER", "action": "click", "element": "#register-btn"},
        ],
    },
    "LOGIN": {
        "param_types": {"param_0": "Username", "param_1": "Password"},
        "actions": [
            {"type": "navigate", "page": "/login"},
            {"gate": "LOGIN", "action": "type", "element": "#username", "value": "param_0"},
            {"gate": "LOGIN", "action": "type", "element": "#password", "value": "param_1"},
            {"gate": "LOGIN", "action": "click", "element": "#login-btn"},
        ],
    },
    "CONFIRMED": {
        "observe": {
            "element": "#confirmed-username",
            "capture": "text",
        },
    },
    "SUBMIT_CHECKIN": {
        "observe": {
            "element": "#session-id",
            "capture": "attribute",
            "attribute": "data-session-id",
        },
    },
    "RECORD_SPO2": {
        "actions": [
            {"gate": "RECORD_SPO2", "action": "click", "element": "#record-spo2"},
        ],
    },
    "RECORD_HEARTRATE": {
        "actions": [
            {"gate": "RECORD_HEARTRATE", "action": "click", "element": "#record-hr"},
        ],
    },
    "RECEIVE_ZONE_STATUS": {
        "observe": {
            "element": "#zone-indicator",
            "capture": "text",
        },
    },
    "GENERATE_ALERT_URGENT": {
        "observe": {
            "element": "#alert-banner",
            "capture": "attribute",
            "attribute": "data-session",
            "expected": None,
        },
    },
    "ACCESS_PATIENT_DATA": {
        "param_types": {"param_0": "SessionId"},
        "actions": [
            {"gate": "ACCESS_PATIENT_DATA", "action": "click", "element": "#access-btn"},
        ],
    },
    "NURSE_OUTREACH": {
        "param_types": {"param_0": "MessageContent"},
        "actions": [
            {"gate": "NURSE_OUTREACH", "action": "type", "element": "#outreach-msg", "value": "param_0"},
            {"gate": "NURSE_OUTREACH", "action": "click", "element": "#outreach-btn"},
        ],
    },
    "ACKNOWLEDGE_ALERT": {
        "param_types": {"param_0": "SessionId"},
        "actions": [
            {"gate": "ACKNOWLEDGE_ALERT", "action": "click", "element": "#ack-btn"},
        ],
    },
    "SEND_MESSAGE": {
        "param_types": {"param_0": "MessageContent"},
        "actions": [
            {"gate": "SEND_MESSAGE", "action": "type", "element": "#msg-input", "value": "param_0"},
            {"gate": "SEND_MESSAGE", "action": "click", "element": "#send-btn"},
        ],
    },
    "CHECKIN_ACCEPTED": {
        "observe": {
            "element": "#checkin-status",
            "expected_text": "accepted",
        },
    },
}


def make_algorithm(mock_outputs, fail_at=None):
    executor = MockExecutor(mock_outputs=mock_outputs, fail_at=fail_at or set())
    return ConcretizationAlgorithm(
        element_map      = ELEMENT_MAP,
        type_description = TYPE_DESCRIPTION,
        executor         = executor,
        timeout_seconds  = 5,
    )


# ─────────────────────────────────────────────────────────────────
# BCGReader tests
# ─────────────────────────────────────────────────────────────────

class TestBCGReader:

    def test_parse_login(self):
        reader = BCGReader()
        steps = reader.parse_labels(["LOGIN !NAME1_AT_A_C !PASS_1"])
        assert len(steps) == 1
        s = steps[0]
        assert s.gate_name == "LOGIN"
        assert s.direction == Direction.INPUT
        assert s.params[0][1] == "name1_at_a_c"
        assert s.params[1][1] == "pass_1"

    def test_parse_output_gate(self):
        reader = BCGReader()
        steps = reader.parse_labels(["GENERATE_ALERT_URGENT !SESS_0"])
        assert steps[0].direction == Direction.OUTPUT

    def test_parse_no_params(self):
        reader = BCGReader()
        steps = reader.parse_labels(["RECORD_SPO2"])
        assert steps[0].gate_name == "RECORD_SPO2"
        assert steps[0].params == []

    def test_skip_internal(self):
        reader = BCGReader()
        steps = reader.parse_labels(["i", "T_ACCEPT", "OTHERWISE", "LOGIN !NAME1_AT_A_C !PASS_1"])
        assert len(steps) == 1
        assert steps[0].gate_name == "LOGIN"

    def test_skip_typed_structural_in_flat_legacy_mode(self):
        reader = BCGReader()
        steps = reader.parse_labels([
            "NAVIGATE !RT_GROUP_CREATE",
            "CLICK !SEL_SUBMIT_BTN",
            "TYPE_INTO !SEL_AMOUNT_INPUT !CV_AMOUNT_50",
            "LOGIN !NAME1_AT_A_C !PASS_1",
        ])
        assert len(steps) == 1
        assert steps[0].gate_name == "LOGIN"

    def test_parse_pass_verdict(self):
        reader = BCGReader()
        steps = reader.parse_labels(["PASS"])
        assert steps[0].gate_name == "PASS"

    def test_mixed_labels(self):
        reader = BCGReader()
        labels = [
            "LOGIN !NAME1_AT_A_C !PASS_1",
            "CONFIRMED ?NAME1_AT_A_C",
            "RECORD_SPO2",
            "PASS",
        ]
        steps = reader.parse_labels(labels)
        assert len(steps) == 4
        assert steps[2].params == []


# ─────────────────────────────────────────────────────────────────
# Sampler tests
# ─────────────────────────────────────────────────────────────────

class TestSampler:

    def test_sample_username(self):
        s = Sampler(TYPE_DESCRIPTION)
        val = s.sample("Username", "name1_at_a_c")
        assert val == "alice@a.c"

    def test_sample_password(self):
        s = Sampler(TYPE_DESCRIPTION)
        val = s.sample("Password", "pass_1")
        assert val == "Secure!01"

    def test_system_generated_returns_none(self):
        s = Sampler(TYPE_DESCRIPTION)
        val = s.sample("SessionId", "sess_0")
        assert val is None

    def test_unknown_type_returns_value(self):
        s = Sampler(TYPE_DESCRIPTION)
        val = s.sample("UnknownType", "some_value")
        assert val == "some_value"

    def test_sample_message(self):
        s = Sampler(TYPE_DESCRIPTION)
        val = s.sample("MessageContent", "m1")
        assert val == "Patient vitals reviewed."


# ─────────────────────────────────────────────────────────────────
# Main algorithm tests
# ─────────────────────────────────────────────────────────────────

class TestConcretizationAlgorithm:

    # ── Happy path: full red zone session → PASS ──────────────────

    def test_red_zone_pass(self):
        """
        Full red zone session.
        Patient registers, logs in, submits vitals.
        System assigns red zone, fires urgent alert.
        Nurse acknowledges. PASS.
        """
        labels = [
            "REGISTER !NAME1_AT_A_C !PASS_1",
            "LOGIN !NAME1_AT_A_C !PASS_1",
            "CONFIRMED ?NAME1_AT_A_C",
            "SUBMIT_CHECKIN ?SESS_0",
            "RECORD_SPO2",
            "RECORD_HEARTRATE",
            "RECEIVE_ZONE_STATUS ?RED",
            "GENERATE_ALERT_URGENT !SESS_0",
            "ACCESS_PATIENT_DATA !SESS_0",
            "NURSE_OUTREACH !M1",
            "ACKNOWLEDGE_ALERT !SESS_0",
            "PASS",
        ]

        # Mock system responses in order of wait() calls
        mock_outputs = [
            "alice@a.c",            # CONFIRMED: system shows username
            "3f2a1b4c-0000-0000",   # SUBMIT_CHECKIN: system assigns session
            "red",                  # RECEIVE_ZONE_STATUS: system says red
            "3f2a1b4c-0000-0000",   # GENERATE_ALERT_URGENT: system sends session
        ]

        algo = make_algorithm(mock_outputs)
        verdict = algo.run(labels)
        assert verdict == Verdict.PASS

    def test_typed_structural_aut_labels_execute_directly(self):
        element_map = {
            "concrete_domain": {
                "routes": {"rt_group_create": "/groups/create"},
                "selectors": {
                    "sel_amount_input": {
                        "selector": "//input[@placeholder='0.00']",
                        "by": "xpath",
                    },
                    "sel_submit_btn": {
                        "selector": "//button[@type='submit']",
                        "by": "xpath",
                    },
                },
                "elements": {
                    "el_expense_form": {
                        "selector": "//input[@placeholder='Monday evening restaurant']",
                        "by": "xpath",
                    },
                    "el_group_url": {
                        "selector": "//button[@role='tab'][contains(.,'Balances')]",
                        "by": "xpath",
                        "attribute": "url_group_id",
                    }
                },
                "concrete_values": {"cv_amount_50": "50"},
            },
            "gates": {},
        }
        executor = MockExecutor(mock_outputs=["grp-123"])
        algo = ConcretizationAlgorithm(
            element_map=element_map,
            type_description={},
            executor=executor,
            timeout_seconds=1,
        )
        graph = AUTGraph(
            initial=0,
            transitions=[
                AUTTransition(0, "NAVIGATE !RT_GROUP_CREATE; OUTPUT", 1),
                AUTTransition(1, "WAIT_FOR !EL_EXPENSE_FORM; OUTPUT", 2),
                AUTTransition(2, "TYPE_INTO !SEL_AMOUNT_INPUT !CV_AMOUNT_50; OUTPUT", 3),
                AUTTransition(3, "CLICK !SEL_SUBMIT_BTN; OUTPUT", 4),
                AUTTransition(4, "OBSERVE !EL_GROUP_URL; INPUT", 5),
                AUTTransition(5, ":PASS:", 6),
            ],
        )

        verdict = algo.run_graph(graph)

        assert verdict == Verdict.PASS
        performed = [entry["action"] for entry in executor.action_log]
        assert performed == [
            {"action": "navigate", "url": "/groups/create"},
            {
                "selector": "//input[@placeholder='Monday evening restaurant']",
                "by": "xpath",
                "action": "wait_for",
            },
            {
                "selector": "//input[@placeholder='0.00']",
                "by": "xpath",
                "action": "clear_and_type",
                "param": "50",
            },
            {
                "selector": "//button[@type='submit']",
                "by": "xpath",
                "action": "click",
            },
        ]

    def test_foodyou_visible_tap_wait_observe_labels_execute_directly(self):
        element_map = {
            "concrete_domain": {
                "elements": {
                    "el_search_input": "search-input",
                    "el_calories": "calories",
                },
                "concrete_values": {
                    "cv_breakfast": "Breakfast",
                    "cv_apple": "Apple",
                },
            },
            "gates": {},
        }
        executor = MockExecutor(mock_outputs=["52"])
        algo = ConcretizationAlgorithm(
            element_map=element_map,
            type_description={},
            executor=executor,
            timeout_seconds=1,
        )
        graph = AUTGraph(
            initial=0,
            transitions=[
                AUTTransition(0, "TAP !CV_BREAKFAST; OUTPUT", 1),
                AUTTransition(1, "WAIT_FOR !EL_SEARCH_INPUT; OUTPUT", 2),
                AUTTransition(2, "TAP !CV_APPLE; OUTPUT", 3),
                AUTTransition(3, "SEARCH_FOOD !FOOD_APPLE; OUTPUT", 4),
                AUTTransition(4, "OBSERVE !EL_CALORIES; INPUT", 5),
                AUTTransition(5, "FOOD_INFO !FOOD_APPLE !CALORIE (52); INPUT", 6),
                AUTTransition(6, ":PASS:", 7),
            ],
        )

        verdict = algo.run_graph(graph)

        assert verdict == Verdict.PASS
        performed = [entry["action"] for entry in executor.action_log]
        assert performed[:3] == [
            {"selector": "Breakfast", "by": "id", "action": "click"},
            {"selector": "search-input", "by": "id", "action": "wait_for"},
            {"selector": "Apple", "by": "id", "action": "click"},
        ]

    # ── Green zone session → PASS ─────────────────────────────────

    def test_green_zone_pass(self):
        labels = [
            "REGISTER !NAME1_AT_A_C !PASS_1",
            "LOGIN !NAME1_AT_A_C !PASS_1",
            "CONFIRMED ?NAME1_AT_A_C",
            "SUBMIT_CHECKIN ?SESS_0",
            "RECORD_SPO2",
            "RECORD_HEARTRATE",
            "RECEIVE_ZONE_STATUS ?GREEN",
            "CHECKIN_ACCEPTED !SESS_0",
            "PASS",
        ]
        session = "sess-abc-123"
        # CHECKIN_ACCEPTED !SESS_0: system echoes same session back
        # constraint check: observed must equal g_dict["sess_0"]
        mock_outputs = [
            "alice@a.c",  # CONFIRMED
            session,      # SUBMIT_CHECKIN captures session
            "green",      # RECEIVE_ZONE_STATUS
            session,      # CHECKIN_ACCEPTED: system sends same session, constraint holds
        ]
        algo = make_algorithm(mock_outputs)
        verdict = algo.run(labels)
        assert verdict == Verdict.PASS

    # ── Quiescence: system never shows alert → FAIL ───────────────

    def test_quiescence_fail(self):
        """System receives red zone vitals but never fires an alert."""
        labels = [
            "SUBMIT_CHECKIN ?SESS_0",
            "RECEIVE_ZONE_STATUS ?RED",
            "GENERATE_ALERT_URGENT !SESS_0",  # system should fire this
        ]
        mock_outputs = [
            "sess-abc-123",    # SUBMIT_CHECKIN
            "red",             # RECEIVE_ZONE_STATUS
            "__TIMEOUT__",     # GENERATE_ALERT_URGENT: nothing appears
        ]
        algo = make_algorithm(mock_outputs)
        verdict = algo.run(labels)
        assert verdict == Verdict.FAIL

        # Check error message explains the quiescence
        last = algo.execution_log[-1]
        assert "Quiescence" in last.error or "timeout" in last.error.lower()

    # ── Constraint violation: wrong session in alert → FAIL ───────

    def test_constraint_violation_session(self):
        """
        Session ID in GENERATE_ALERT_URGENT does not match
        the one captured at SUBMIT_CHECKIN.
        """
        labels = [
            "SUBMIT_CHECKIN ?SESS_0",
            "RECEIVE_ZONE_STATUS ?RED",
            "GENERATE_ALERT_URGENT !SESS_0",  # must match captured sess_0
        ]
        mock_outputs = [
            "session-CORRECT-abc",   # captured at SUBMIT_CHECKIN
            "red",
            "session-WRONG-xyz",     # alert carries DIFFERENT session → violation
        ]
        algo = make_algorithm(mock_outputs)
        verdict = algo.run(labels)
        assert verdict == Verdict.FAIL

        last = algo.execution_log[-1]
        assert "Constraint violation" in last.error

    # ── UI action failure → FAIL ──────────────────────────────────

    def test_ui_action_failure(self):
        """Login button click fails (element not found)."""
        labels = [
            "LOGIN !NAME1_AT_A_C !PASS_1",
            "PASS",
        ]
        # Fail at the LOGIN gate
        executor = MockExecutor(
            mock_outputs=[],
            fail_at={"LOGIN"},
        )
        algo = ConcretizationAlgorithm(
            element_map=ELEMENT_MAP,
            type_description=TYPE_DESCRIPTION,
            executor=executor,
        )
        verdict = algo.run(labels)
        assert verdict == Verdict.FAIL

    # ── Value reuse: username same at REGISTER and LOGIN ──────────

    def test_username_reused_across_gates(self):
        """
        Username sampled at REGISTER must be identical at LOGIN.
        Verified by checking g_dict is not used (tester-generated)
        but l_dict/sampler returns same value for same abstract key.
        """
        labels = [
            "REGISTER !NAME1_AT_A_C !PASS_1",
            "LOGIN !NAME1_AT_A_C !PASS_1",
            "CONFIRMED ?NAME1_AT_A_C",
            "PASS",
        ]
        mock_outputs = ["alice@a.c"]  # CONFIRMED returns the username

        algo = make_algorithm(mock_outputs)
        verdict = algo.run(labels)
        assert verdict == Verdict.PASS

        # Verify alice@a.c was captured
        assert algo.g_dict.get("name1_at_a_c") == "alice@a.c"

    # ── System value capture and reuse ────────────────────────────

    def test_session_captured_and_reused(self):
        """
        Session ID captured at SUBMIT_CHECKIN must be available
        in g_dict for reuse in GENERATE_ALERT_URGENT.
        """
        labels = [
            "SUBMIT_CHECKIN ?SESS_0",
            "RECEIVE_ZONE_STATUS ?RED",
            "GENERATE_ALERT_URGENT !SESS_0",
            "PASS",
        ]
        session_uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        mock_outputs = [
            session_uuid,   # SUBMIT_CHECKIN captures this
            "red",
            session_uuid,   # GENERATE_ALERT_URGENT: matches → no violation
        ]

        algo = make_algorithm(mock_outputs)
        verdict = algo.run(labels)
        assert verdict == Verdict.PASS
        assert algo.g_dict["sess_0"] == session_uuid

    # ── Gates with no parameters ──────────────────────────────────

    def test_parameterless_gates(self):
        """RECORD_SPO2 and RECORD_HEARTRATE have no parameters."""
        labels = [
            "RECORD_SPO2",
            "RECORD_HEARTRATE",
            "PASS",
        ]
        algo = make_algorithm([])
        verdict = algo.run(labels)
        assert verdict == Verdict.PASS

    # ── Empty ATC → INCONC ────────────────────────────────────────

    def test_empty_atc(self):
        algo = make_algorithm([])
        verdict = algo.run([])
        assert verdict == Verdict.UNEXECUTABLE  # dead end: no verdict

    # ── ATC with only internal gates → INCONC ────────────────────

    def test_only_internal_gates(self):
        algo = make_algorithm([])
        verdict = algo.run(["i", "i", "T_ACCEPT"])
        assert verdict == Verdict.UNEXECUTABLE  # dead end: no verdict

    # ── Execution report structure ────────────────────────────────

    def test_report_structure(self):
        labels = ["REGISTER !NAME1_AT_A_C !PASS_1", "PASS"]
        algo = make_algorithm([])
        algo.run(labels)
        report = algo.get_report()

        assert "steps" in report
        assert "g_dict_final" in report
        assert "execution_log" in report
        assert len(report["execution_log"]) == 2

        first = report["execution_log"][0]
        assert first["gate"] == "REGISTER"
        assert "duration_ms" in first

    # ── Yellow zone path ─────────────────────────────────────────

    def test_yellow_zone_pass(self):
        labels = [
            "SUBMIT_CHECKIN ?SESS_0",
            "RECEIVE_ZONE_STATUS ?YELLOW",
            "GENERATE_ALERT_ROUTINE !SESS_0",
            "VIEW_ACTION_PLAN !SESS_0",
            "ACKNOWLEDGE_ALERT !SESS_0",
            "PASS",
        ]
        session = "yellow-session-001"
        mock_outputs = [
            session,    # SUBMIT_CHECKIN
            "yellow",   # RECEIVE_ZONE_STATUS
            session,    # GENERATE_ALERT_ROUTINE
        ]

        # Add VIEW_ACTION_PLAN to element map for this test
        element_map_extended = {
            **ELEMENT_MAP,
            "GENERATE_ALERT_ROUTINE": {
                "observe": {
                    "element": "#alert-banner",
                    "capture": "attribute",
                    "attribute": "data-session",
                },
            },
            "VIEW_ACTION_PLAN": {
                "param_types": {"param_0": "SessionId"},
                "actions": [
                    {"action": "click", "element": "#view-plan-btn"},
                ],
            },
        }

        executor = MockExecutor(mock_outputs=mock_outputs)
        algo = ConcretizationAlgorithm(
            element_map      = element_map_extended,
            type_description = TYPE_DESCRIPTION,
            executor         = executor,
        )
        verdict = algo.run(labels)
        assert verdict == Verdict.PASS


# ─────────────────────────────────────────────────────────────────
# Integration test: full red zone sequence with report
# ─────────────────────────────────────────────────────────────────

class TestIntegration:

    def test_full_red_zone_with_report(self):
        labels = [
            "REGISTER !NAME1_AT_A_C !PASS_1",
            "LOGIN !NAME1_AT_A_C !PASS_1",
            "CONFIRMED ?NAME1_AT_A_C",
            "SUBMIT_CHECKIN ?SESS_0",
            "RECORD_SPO2",
            "RECORD_HEARTRATE",
            "RECEIVE_ZONE_STATUS ?RED",
            "GENERATE_ALERT_URGENT !SESS_0",
            "ACCESS_PATIENT_DATA !SESS_0",
            "NURSE_OUTREACH !M1",
            "ACKNOWLEDGE_ALERT !SESS_0",
            "PASS",
        ]
        session = "full-test-session-uuid"
        mock_outputs = [
            "alice@a.c",
            session,
            "red",
            session,
        ]

        algo = make_algorithm(mock_outputs)
        verdict = algo.run(labels)
        report = algo.get_report()

        assert verdict == Verdict.PASS
        assert report["g_dict_final"]["sess_0"] == session
        assert report["g_dict_final"]["name1_at_a_c"] == "alice@a.c"

        # All steps should have executed
        gates = [s["gate"] for s in report["execution_log"]]
        assert "REGISTER" in gates
        assert "GENERATE_ALERT_URGENT" in gates
        assert "PASS" in gates


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
